#!/usr/bin/env python3
"""
Safe demo CLI that mimics a colored, step-by-step terminal like the screenshot,
without doing anything harmful. It:
  - Initializes a local SQLite DB with fake sample users (if missing or --init-db)
  - Reads N user rows using parameterized queries (safe against injection)
  - Writes extracted rows to a CSV file

Usage examples:
  python safe_sqlite_extractor.py --init-db --count 5
  python safe_sqlite_extractor.py -n 10 -w 3.5 -o extracted.csv

This is for DEMONSTRATION ONLY. Do not use with real or sensitive data.
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import sqlite3
import string
import time
from dataclasses import dataclass

# -----------------------------
# Minimal ANSI color utilities
# -----------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}

TAG_COLORS = {
    "READY": COLORS["green"],
    "TARGET": COLORS["magenta"],
    "INJECT": COLORS["blue"],
    "INFO": COLORS["cyan"],
    "SQL": COLORS["yellow"],
    "AUTH": COLORS["red"],
    "TABLE": COLORS["magenta"],
    "EXTRACT": COLORS["cyan"],
    "PARSE": COLORS["blue"],
    "SUCCESS": COLORS["green"],
    "PREP": COLORS["yellow"],
    "WRITE": COLORS["blue"],
    "WAIT": COLORS["yellow"],
}


def tag(tag_name: str, message: str) -> None:
    color = TAG_COLORS.get(tag_name, COLORS["white"])  # default white
    print(f"{color}[{tag_name}]{RESET} {message}", flush=True)


# -----------------------------
# Data models and utilities
# -----------------------------
@dataclass
class User:
    id: int
    full_name: str
    email: str
    cc_number: str
    exp_month: int
    exp_year: int
    cvv: str


FIRST_NAMES = [
    "Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey",
    "Riley", "Drew", "Quinn", "Avery", "Jamie", "Cameron",
]
LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White",
]


def luhn_checksum_digit(number_without_check: str) -> str:
    digits = [int(d) for d in number_without_check]
    # Luhn algorithm: double every second digit from right
    checksum = 0
    parity = (len(digits) + 1) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    check_digit = (10 - (checksum % 10)) % 10
    return str(check_digit)


def generate_fake_card_number(prefix: str = "411111") -> str:
    length = 16
    random_length = length - len(prefix) - 1
    body = "".join(random.choice(string.digits) for _ in range(random_length))
    partial = prefix + body
    check = luhn_checksum_digit(partial)
    return partial + check


def generate_user(user_id: int) -> User:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}@example.com"
    cc = generate_fake_card_number(random.choice(["411111", "550000", "601100"]))
    exp_month = random.randint(1, 12)
    exp_year = 2029 + random.randint(0, 6)
    cvv = "".join(random.choice(string.digits) for _ in range(3))
    return User(
        id=user_id,
        full_name=name,
        email=email,
        cc_number=cc,
        exp_month=exp_month,
        exp_year=exp_year,
        cvv=cvv,
    )


# -----------------------------
# SQLite helpers
# -----------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    cc_number TEXT NOT NULL,
    exp_month INTEGER NOT NULL,
    exp_year INTEGER NOT NULL,
    cvv TEXT NOT NULL
);
"""

INSERT_SQL = (
    "INSERT INTO users (id, full_name, email, cc_number, exp_month, exp_year, cvv)"
    " VALUES (?, ?, ?, ?, ?, ?, ?)"
)

SELECT_COUNT_SQL = "SELECT COUNT(*) FROM users"
SELECT_BY_OFFSET_SQL = (
    "SELECT id, full_name, email, cc_number, exp_month, exp_year, cvv "
    "FROM users ORDER BY id LIMIT 1 OFFSET ?"
)


def initialize_db(db_path: str, num_records: int = 100) -> None:
    tag("INFO", f"Initializing demo database at '{db_path}' with {num_records} users...")
    with sqlite3.connect(db_path) as conn:
        conn.execute(SCHEMA_SQL)
        conn.execute("DELETE FROM users")  # reset for deterministic runs
        for i in range(1, num_records + 1):
            u = generate_user(i)
            conn.execute(
                INSERT_SQL,
                (u.id, u.full_name, u.email, u.cc_number, u.exp_month, u.exp_year, u.cvv),
            )
        conn.commit()
    tag("SUCCESS", "Demo database ready.")


# -----------------------------
# Core extraction flow
# -----------------------------

def ensure_header(csv_path: str) -> None:
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "full_name", "email", "cc_number", "exp_month", "exp_year", "cvv"])


def extract_record(db_path: str, offset: int) -> User:
    tag("INFO", "Connecting to database server...")
    with sqlite3.connect(db_path) as conn:
        tag("INFO", "Database connection established...")
        tag("SQL", "Executing parameterized SELECT query...")
        cur = conn.execute(SELECT_BY_OFFSET_SQL, (offset,))
        row = cur.fetchone()
        tag("TABLE", "Accessing 'users' table...")
        if not row:
            raise RuntimeError("No data returned for the given offset")
        tag("EXTRACT", "Extracting row data...")
        user = User(*row)
        tag("PARSE", "Parsing database response...")
        tag("SUCCESS", "Data extraction successful")
        return user


def append_to_csv(csv_path: str, user: User) -> None:
    tag("PREP", "Preparing data for output...")
    ensure_header(csv_path)
    tag("WRITE", f"Writing to local file '{csv_path}'...")
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            user.id,
            user.full_name,
            user.email,
            user.cc_number,
            user.exp_month,
            user.exp_year,
            user.cvv,
        ])
    # Compact single-line preview similar to the screenshot
    short_preview = (
        f"{user.cc_number}|{user.exp_month:02}|{user.exp_year % 100:02}|{user.cvv} "
        f"{user.full_name} {user.email}"
    )
    tag("SUCCESS", f"Data extracted: {short_preview}")


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Safe SQLite demo extractor with colorful tags")
    p.add_argument("-n", "--count", type=int, default=5, help="Number of records to process")
    p.add_argument("-w", "--wait", type=float, default=2.5, help="Seconds to wait between records")
    p.add_argument("-d", "--db", default="demo_users.db", help="Path to SQLite database file")
    p.add_argument("-o", "--output", default="extracted_users.csv", help="Output CSV path")
    p.add_argument("--init-db", action="store_true", help="Recreate and seed the demo database")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.init_db or not os.path.exists(args.db):
        initialize_db(args.db, num_records=max(args.count, 50))

    tag("READY", "CLI ready.")
    tag("TARGET", f"Processing {args.count} user record(s)...")

    # Precompute total rows to keep offsets in range
    with sqlite3.connect(args.db) as conn:
        total_rows = conn.execute(SELECT_COUNT_SQL).fetchone()[0]

    for i in range(1, args.count + 1):
        tag("INJECT", f"Processing record #{i}...")
        # We intentionally use a safe, parameterized query
        tag("AUTH", "Using parameterized query to avoid injection (safe).")
        offset = (i - 1) % max(total_rows, 1)
        user = extract_record(args.db, offset)
        append_to_csv(args.output, user)
        if i < args.count:
            tag("WAIT", f"Waiting {args.wait:.1f}s before next operation...")
            time.sleep(args.wait)
    tag("READY", "All done.")


if __name__ == "__main__":
    main()
