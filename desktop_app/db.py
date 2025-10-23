from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path(__file__).resolve().parent / "people.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS person (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                city TEXT NOT NULL,
                country TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_if_empty(n: int = 200) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM person")
        count = cur.fetchone()[0]
        if count and count > 0:
            return
        try:
            from faker import Faker
        except Exception:
            raise RuntimeError("Faker not installed. Install from desktop_app/requirements.txt")
        fake = Faker()
        rows = []
        for _ in range(n):
            rows.append((fake.first_name(), fake.last_name(), fake.email(), fake.city(), fake.country()))
        cur.executemany(
            "INSERT INTO person(first_name, last_name, email, city, country) VALUES (?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def search_people(query: str, limit: int = 25) -> List[Tuple[int, str, str, str, str, str]]:
    q = f"%{query.lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, first_name, last_name, email, city, country
            FROM person
            WHERE lower(first_name) LIKE ?
               OR lower(last_name) LIKE ?
               OR lower(email) LIKE ?
               OR lower(city) LIKE ?
               OR lower(country) LIKE ?
            ORDER BY last_name, first_name
            LIMIT ?
            """,
            (q, q, q, q, q, limit),
        )
        return cur.fetchall()
    finally:
        conn.close()
