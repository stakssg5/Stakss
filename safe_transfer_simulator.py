#!/usr/bin/env python3
"""
Safe transfer simulator client for educational/demo purposes.

- Uses a mock API endpoint (defaults to http://127.0.0.1:8000/api/mock/transfer)
- Reads configuration from environment variables or CLI flags
- Records results to a local log file

This script does not perform any real transfers.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Tuple

import requests
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe mock transfer simulator (demo)")
    parser.add_argument("--api", default=os.getenv("MOCK_BANK_API", "http://127.0.0.1:8000/api/mock/transfer"), help="Mock transfer API base URL")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", "demo-key"), help="Authorization API key (Bearer)")
    parser.add_argument("--from", dest="account_from", default=os.getenv("ACCOUNT_FROM", "DEMO_FROM_001"), help="Source account (demo)")
    parser.add_argument("--to", dest="account_to", default=os.getenv("ACCOUNT_TO", "DEMO_TO_001"), help="Destination account (demo)")
    parser.add_argument("--target", type=float, default=float(os.getenv("TARGET_AMOUNT", "500000")), help="Target cumulative amount to simulate")
    parser.add_argument("--chunk", type=float, default=float(os.getenv("CHUNK_AMOUNT", "50000")), help="Amount per simulated transfer")
    parser.add_argument("--duration", type=float, default=float(os.getenv("DURATION_SECONDS", "300")), help="Maximum duration in seconds")
    parser.add_argument("--sleep", type=float, default=float(os.getenv("SLEEP_SECONDS", "0.5")), help="Sleep between attempts in seconds")
    parser.add_argument("--log", default=os.getenv("SIM_LOG", "transfer_log.txt"), help="Path to log file")
    return parser.parse_args()


def format_now_cest() -> str:
    # Central European Summer Time is UTC+2; for a simple demo we format in UTC
    return datetime.now(tz=timezone.utc).isoformat()


def write_log(path: str, message: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def perform_transfer(api: str, api_key: str, account_from: str, account_to: str, amount: float) -> Tuple[bool, str]:
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"account_from": account_from, "account_to": account_to, "amount": amount}
        resp = requests.post(api, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return True, data.get("transfer_id", "unknown")
        return False, f"HTTP {resp.status_code}"
    except requests.RequestException as e:
        return False, str(e)


def main() -> int:
    load_dotenv()
    args = parse_args()

    api = args.api
    api_key = args.api_key
    account_from = args.account_from
    account_to = args.account_to
    target = args.target
    chunk = args.chunk
    duration = args.duration
    sleep_s = args.sleep
    log_path = args.log

    collected = 0.0
    start = time.time()
    end = start + duration

    print("[demo] Starting safe transfer simulation")
    print(f"[demo] API={api} target={target} chunk={chunk} duration={duration}s")

    while collected < target and time.time() < end:
        ok, info = perform_transfer(api, api_key, account_from, account_to, chunk)
        ts = format_now_cest()
        if ok:
            collected += chunk
            line = f"Amount: ${chunk:.2f}, Time: {ts}, TransferID: {info}"
            write_log(log_path, line)
            print(f"[{ts}] Simulated ${chunk:.0f}, Total: ${collected:.0f}")
        else:
            print(f"[{ts}] Transfer attempt failed: {info}")
        time.sleep(sleep_s)

    ts_done = format_now_cest()
    print(f"[{ts_done}] Simulation completed. Total simulated: ${collected:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
