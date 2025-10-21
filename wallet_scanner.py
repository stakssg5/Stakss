#!/usr/bin/env python3
import argparse
import csv
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ETH_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
# BTC: legacy (1/3) + bech32 (bc1...) rough pattern
BTC_RE = re.compile(
    r"\b(?:bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"
)

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "dist",
    "build",
}

TEXT_EXTS = {
    ".txt",
    ".log",
    ".json",
    ".csv",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".yml",
    ".yaml",
    ".ini",
    ".toml",
    ".html",
    ".css",
    ".xml",
}

def is_probably_text(path: Path, sample_bytes: int = 4096) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_bytes)
        if b"\x00" in chunk:
            return False
        # Try a quick decode
        try:
            chunk.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    except Exception:
        return False

def applicable_regexes(networks: set[str]):
    regs = []
    if "eth" in networks:
        regs.append(("ETH", ETH_RE))
    if "btc" in networks:
        regs.append(("BTC", BTC_RE))
    return regs

def scan_file(path: str, networks: list[str]) -> list[tuple[str, str, str, int]]:
    regs = applicable_regexes(set(networks))
    results: list[tuple[str, str, str, int]] = []
    p = Path(path)
    try:
        with p.open("rb") as f:
            for lineno, raw in enumerate(f, start=1):
                try:
                    line = raw.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                for net, regex in regs:
                    for m in regex.finditer(line):
                        addr = m.group(0)
                        results.append((net, addr, str(p), lineno))
    except Exception:
        # Skip unreadable files
        return []
    return results

def iter_files(paths: list[str], exclude_dirs: set[str], max_size_bytes: int) -> list[Path]:
    files: list[Path] = []
    for root in paths:
        root_path = Path(root)
        if root_path.is_file():
            if root_path.stat().st_size <= max_size_bytes:
                files.append(root_path)
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            for fn in filenames:
                fp = Path(dirpath) / fn
                try:
                    st = fp.stat()
                except Exception:
                    continue
                if st.st_size > max_size_bytes:
                    continue
                # Prefer text-like files quickly
                if fp.suffix.lower() in TEXT_EXTS or is_probably_text(fp):
                    files.append(fp)
    return files

def main():
    parser = argparse.ArgumentParser(
        description="Scan files for ETH and BTC wallet addresses (auditing use)."
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument("--networks", default="eth,btc", help="Comma list: eth,btc")
    parser.add_argument("--exclude-dir", action="append", default=[],
                        help="Directory name to exclude (can repeat)")
    parser.add_argument("--max-size-mb", type=int, default=200,
                        help="Skip files larger than this size")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 4,
                        help="Parallel worker processes")
    parser.add_argument("--csv", default="wallet_matches.csv", help="Output CSV path")
    args = parser.parse_args()

    networks = [s.strip().lower() for s in args.networks.split(",") if s.strip()]
    if not networks:
        print("No networks selected.", file=sys.stderr)
        sys.exit(1)

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)
    max_size_bytes = args.max_size_mb * 1024 * 1024

    print("Indexing files...")
    files = iter_files(args.paths, exclude_dirs, max_size_bytes)
    if not files:
        print("No files to scan.")
        return
    print(f"Found {len(files)} file(s) to scan.")

    dedup = set()
    rows = []
    futures = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for fp in files:
            futures.append(ex.submit(scan_file, str(fp), networks))
        processed = 0
        for fut in as_completed(futures):
            processed += 1
            if processed % 250 == 0:
                print(f"Scanned {processed}/{len(files)} files...")
            try:
                matches = fut.result()
            except Exception:
                continue
            for net, addr, fpath, lineno in matches:
                key = (net, addr)
                if key in dedup:
                    continue
                dedup.add(key)
                rows.append({"network": net, "address": addr, "file": fpath, "line": lineno})

    if rows:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["network", "address", "file", "line"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Done. {len(rows)} unique address(es) written to {args.csv}")
    else:
        print("Done. No addresses found.")

if __name__ == "__main__":
    main()
