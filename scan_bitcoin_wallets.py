#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import os
import re
import sys
import threading
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import requests
from mnemonic import Mnemonic

# bip-utils for key derivation and address generation
from bip_utils import (
    Bip39SeedGenerator,
    Bip44, Bip44Coins, Bip44Changes,
    Bip49, Bip49Coins,
    Bip84, Bip84Coins,
)


@dataclass
class AddressBalance:
    address: str
    confirmed_sats: int
    unconfirmed_sats: int

    @property
    def total_sats(self) -> int:
        return self.confirmed_sats + self.unconfirmed_sats


@dataclass
class WalletScanResult:
    source: str  # file path where mnemonic was found
    mnemonic: str
    derivation: str  # bip84/bip49/bip44
    total_confirmed_sats: int
    total_unconfirmed_sats: int
    addresses: List[AddressBalance]


MEMPOOL_BASES = [
    "https://mempool.space/api",
    "https://blockstream.info/api",
]


def human_sats(sats: int) -> str:
    btc = sats / 100_000_000
    return f"{sats} sats (~{btc:.8f} BTC)"


def is_probably_text(path: str, max_probe: int = 8192) -> bool:
    try:
        with open(path, 'rb') as f:
            chunk = f.read(max_probe)
    except Exception:
        return False
    if not chunk:
        return True
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode('utf-8')
        return True
    except Exception:
        return False


def iter_files(root: str, max_file_size: int, exclude_dirs: Sequence[str]) -> Iterable[str]:
    exclude_set = set(exclude_dirs)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_set and not d.startswith('.')]
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                if os.path.islink(full):
                    continue
                size = os.path.getsize(full)
                if size > max_file_size:
                    continue
            except Exception:
                continue
            if not is_probably_text(full):
                continue
            yield full


MNEMONIC_REGEX = re.compile(r"\b(?:[a-z]{3,}\s+){11,23}[a-z]{3,}\b", re.IGNORECASE)


def find_mnemonic_candidates(text: str) -> List[str]:
    # Normalize whitespace, lowercase for detection
    normalized = re.sub(r"\s+", " ", text.strip()).lower()
    candidates = set()
    for match in MNEMONIC_REGEX.finditer(normalized):
        phrase = match.group(0).strip()
        # collapse multiple spaces
        phrase = re.sub(r"\s+", " ", phrase)
        # ensure 12-24 words
        n = len(phrase.split())
        if 12 <= n <= 24:
            candidates.add(phrase)
    return list(candidates)


def validate_mnemonic(phrase: str) -> bool:
    try:
        m = Mnemonic("english")
        return bool(m.check(phrase))
    except Exception:
        return False


def derive_addresses(
    mnemonic: str,
    derivation: str,
    account_index: int,
    change_type: str,  # 'ext' or 'int'
    start_index: int,
    count: int,
    passphrase: str = "",
) -> List[str]:
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate(passphrase)

    if derivation == "bip84":
        ctx = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)
    elif derivation == "bip49":
        ctx = Bip49.FromSeed(seed_bytes, Bip49Coins.BITCOIN)
    elif derivation == "bip44":
        ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    else:
        raise ValueError(f"Unknown derivation: {derivation}")

    acct = ctx.Purpose().Coin().Account(account_index)
    change_enum = Bip44Changes.CHAIN_EXT if change_type == "ext" else Bip44Changes.CHAIN_INT
    chg = acct.Change(change_enum)

    addrs: List[str] = []
    for i in range(start_index, start_index + count):
        addr_ctx = chg.AddressIndex(i)
        addr = addr_ctx.PublicKey().ToAddress()
        addrs.append(addr)
    return addrs


def fetch_balance_for_address(address: str, session: Optional[requests.Session] = None, timeout: float = 10.0) -> AddressBalance:
    sess = session or requests.Session()
    last_exc: Optional[Exception] = None
    for base in MEMPOOL_BASES:
        url = f"{base}/address/{address}"
        try:
            resp = sess.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                c = data.get("chain_stats", {})
                m = data.get("mempool_stats", {})
                confirmed = int(c.get("funded_txo_sum", 0)) - int(c.get("spent_txo_sum", 0))
                unconfirmed = int(m.get("funded_txo_sum", 0)) - int(m.get("spent_txo_sum", 0))
                return AddressBalance(address=address, confirmed_sats=confirmed, unconfirmed_sats=unconfirmed)
        except Exception as e:
            last_exc = e
            continue
    # On failure, assume zero to keep scan moving
    return AddressBalance(address=address, confirmed_sats=0, unconfirmed_sats=0)


def scan_derivation_with_gap_limit(
    mnemonic: str,
    derivation: str,
    account_index: int,
    gap_limit: int,
    max_scan: int,
    batch_size: int,
    passphrase: str = "",
) -> Tuple[int, int, List[AddressBalance]]:
    total_confirmed = 0
    total_unconfirmed = 0
    results: List[AddressBalance] = []

    session = requests.Session()
    lock = threading.Lock()

    def scan_chain(change_type: str) -> Tuple[int, int, List[AddressBalance]]:
        nonlocal session
        zero_run = 0
        i = 0
        chain_results: List[AddressBalance] = []
        chain_confirmed = 0
        chain_unconfirmed = 0

        while zero_run < gap_limit and i < max_scan:
            count = min(batch_size, max_scan - i)
            addrs = derive_addresses(mnemonic, derivation, account_index, change_type, i, count, passphrase)

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(addrs))) as ex:
                futs = [ex.submit(fetch_balance_for_address, a, session) for a in addrs]
                balances = [f.result() for f in futs]

            for bal in balances:
                chain_results.append(bal)
                if bal.total_sats > 0:
                    chain_confirmed += bal.confirmed_sats
                    chain_unconfirmed += bal.unconfirmed_sats
                    zero_run = 0
                else:
                    zero_run += 1
            i += count
        return chain_confirmed, chain_unconfirmed, chain_results

    for chain in ("ext", "int"):
        c_conf, c_unconf, c_res = scan_chain(chain)
        total_confirmed += c_conf
        total_unconfirmed += c_unconf
        results.extend(c_res)

    return total_confirmed, total_unconfirmed, results


def scan_mnemonic_balances(
    mnemonic: str,
    derivations: Sequence[str],
    account_index: int,
    gap_limit: int,
    max_scan: int,
    batch_size: int,
    passphrase: str = "",
) -> List[WalletScanResult]:
    out: List[WalletScanResult] = []
    for deriv in derivations:
        c, u, addrs = scan_derivation_with_gap_limit(
            mnemonic=mnemonic,
            derivation=deriv,
            account_index=account_index,
            gap_limit=gap_limit,
            max_scan=max_scan,
            batch_size=batch_size,
            passphrase=passphrase,
        )
        out.append(
            WalletScanResult(
                source="<stdin>",
                mnemonic=mnemonic,
                derivation=deriv,
                total_confirmed_sats=c,
                total_unconfirmed_sats=u,
                addresses=addrs,
            )
        )
    return out


def scan_path_for_mnemonics(
    path: str,
    max_file_size: int,
    exclude_dirs: Sequence[str],
) -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = {}
    m = Mnemonic("english")

    if os.path.isfile(path):
        files = [path]
    else:
        files = list(iter_files(path, max_file_size, exclude_dirs))

    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except Exception:
            continue
        candidates = find_mnemonic_candidates(text)
        valid_phrases = []
        for cand in candidates:
            if m.check(cand):
                valid_phrases.append(cand)
        if valid_phrases:
            found[f] = valid_phrases
    return found


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Scan files for BIP39 mnemonics and fetch Bitcoin balances.")
    p.add_argument("path", nargs="?", default=".", help="File or directory to scan (default: current directory)")
    p.add_argument("--gap-limit", type=int, default=20, help="Gap limit per chain (default: 20)")
    p.add_argument("--max-scan", type=int, default=200, help="Max addresses per chain to scan (default: 200)")
    p.add_argument("--batch-size", type=int, default=10, help="Concurrent query batch size (default: 10)")
    p.add_argument("--account-index", type=int, default=0, help="Account index (default: 0)")
    p.add_argument("--passphrase", default="", help="Optional BIP39 passphrase (default: empty)")
    p.add_argument(
        "--derivation",
        default="auto",
        choices=["auto", "bip84", "bip49", "bip44"],
        help="Derivation to use. 'auto' scans bip84,bip49,bip44.",
    )
    p.add_argument("--max-file-size", type=int, default=5_000_000, help="Skip files larger than this many bytes (default: 5MB)")
    p.add_argument("--json", action="store_true", help="Output results as JSON")
    p.add_argument(
        "--exclude-dir",
        action="append",
        default=[".git", "node_modules", "venv", ".venv", "__pycache__", ".cursor"],
        help="Directory names to exclude (can be specified multiple times)",
    )
    p.add_argument("--show-addresses", action="store_true", help="Include per-address balances in output")

    args = p.parse_args(argv)

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"Path does not exist: {path}", file=sys.stderr)
        return 2

    print(f"Scanning for mnemonics in: {path}")
    found = scan_path_for_mnemonics(path, args.max_file_size, args.exclude_dir)

    if not found:
        print("No valid BIP39 mnemonics found.")
        return 0

    derivations = ["bip84", "bip49", "bip44"] if args.derivation == "auto" else [args.derivation]

    results: List[WalletScanResult] = []

    for fpath, phrases in found.items():
        for phrase in phrases:
            for deriv in derivations:
                c, u, addrs = scan_derivation_with_gap_limit(
                    mnemonic=phrase,
                    derivation=deriv,
                    account_index=args.account_index,
                    gap_limit=args.gap_limit,
                    max_scan=args.max_scan,
                    batch_size=args.batch_size,
                    passphrase=args.passphrase,
                )
                if args.json:
                    results.append(
                        WalletScanResult(
                            source=fpath,
                            mnemonic=phrase,
                            derivation=deriv,
                            total_confirmed_sats=c,
                            total_unconfirmed_sats=u,
                            addresses=addrs if args.show_addresses else [],
                        )
                    )
                else:
                    print()
                    print(f"Source: {fpath}")
                    print(f"Mnemonic: {phrase}")
                    print(f"Derivation: {deriv}")
                    print(f"Confirmed: {human_sats(c)}")
                    print(f"Unconfirmed: {human_sats(u)}")
                    if args.show_addresses:
                        nonzero = [a for a in addrs if a.total_sats > 0]
                        print(f"Non-zero addresses ({len(nonzero)}):")
                        for a in nonzero:
                            print(f"  {a.address}: {human_sats(a.total_sats)} (confirmed {a.confirmed_sats}, unconfirmed {a.unconfirmed_sats})")

    if args.json:
        # Convert dataclasses to dicts
        def addr_to_dict(a: AddressBalance) -> Dict[str, object]:
            return {
                "address": a.address,
                "confirmed_sats": a.confirmed_sats,
                "unconfirmed_sats": a.unconfirmed_sats,
                "total_sats": a.total_sats,
            }

        payload = [
            {
                "source": r.source,
                "mnemonic": r.mnemonic,
                "derivation": r.derivation,
                "confirmed_sats": r.total_confirmed_sats,
                "unconfirmed_sats": r.total_unconfirmed_sats,
                "total_sats": r.total_confirmed_sats + r.total_unconfirmed_sats,
                "addresses": [addr_to_dict(a) for a in r.addresses],
            }
            for r in results
        ]
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
