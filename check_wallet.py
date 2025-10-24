#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict

from app.services.balances import BalanceService
from app.services.prices import PriceService


async def _check_once(chain: str, address: str) -> Dict[str, Any]:
    balances = await BalanceService().get_balance(chain=chain, address=address)
    prices = await PriceService().get_prices([balances["symbol"]])
    price = float(prices.get(balances["symbol"], 0.0))
    balance = float(balances["balance"])  # BTC or native units
    return {
        "chain": chain,
        "address": address,
        "symbol": balances["symbol"],
        "balance": balance,
        "price_usd": price,
        "balance_usd": balance * price,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check a crypto wallet balance and USD value (demo).",
    )
    parser.add_argument(
        "address",
        help="Wallet address to check (e.g., BTC address)",
    )
    parser.add_argument(
        "--chain",
        default="btc",
        help="Blockchain to query (default: btc)",
        choices=["btc", "eth", "bsc", "sol", "avax", "ltc", "op", "matic", "ton", "trx"],
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text",
    )
    return parser


def _print_human(result: Dict[str, Any]) -> None:
    symbol = result["symbol"]
    balance = float(result["balance"])
    price = float(result["price_usd"]) if result.get("price_usd") is not None else 0.0
    balance_usd = float(result.get("balance_usd", 0.0))

    print(f"Chain     : {result['chain']}")
    print(f"Address   : {result['address']}")
    print(f"Asset     : {symbol}")
    print(f"Balance   : {balance:,.8f} {symbol}")
    print(f"Price USD : ${price:,.2f}")
    print(f"Total USD : ${balance_usd:,.2f}")


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        result = asyncio.run(_check_once(chain=args.chain, address=args.address))
    except ValueError as exc:
        parser.error(str(exc))
        return
    except Exception as exc:  # network or unexpected
        parser.error(f"Request failed: {exc}")
        return

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)


if __name__ == "__main__":
    main()
