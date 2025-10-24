from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .cards import generate_cards, CARD_SPECS


@dataclass(frozen=True)
class CardRow:
    id: int
    brand_key: str
    brand: str
    number: str
    expiry_month: int
    expiry_year: int
    cvv: str
    zip: str


class CardStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_cards (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  brand_key TEXT NOT NULL,
                  brand TEXT NOT NULL,
                  number TEXT NOT NULL,
                  expiry_month INTEGER NOT NULL,
                  expiry_year INTEGER NOT NULL,
                  cvv TEXT NOT NULL,
                  zip TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_cards_brand ON test_cards(brand_key)"
            )

    def seed_if_empty(self, target_total: int = 60) -> int:
        with self._connect() as conn:
            cur = conn.execute("SELECT COUNT(1) AS c FROM test_cards")
            count = int(cur.fetchone()[0])
            if count > 0:
                return 0
            # Seed evenly across brands
            keys = list(CARD_SPECS.keys())
            per_brand = max(1, target_total // max(1, len(keys)))
            total_inserted = 0
            for key in keys:
                cards = generate_cards(count=per_brand, brand=key)
                self.insert_cards(cards)
                total_inserted += len(cards)
            return total_inserted

    def insert_cards(self, cards: Iterable[Dict[str, Any]]) -> int:
        rows = [
            (
                c["brand_key"],
                c["brand"],
                c["number"],
                int(c["expiry_month"]),
                int(c["expiry_year"]),
                str(c["cvv"]),
                str(c.get("zip", "00000")),
            )
            for c in cards
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO test_cards (
                    brand_key, brand, number, expiry_month, expiry_year, cvv, zip
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            return conn.total_changes

    def fetch_cards(self, count: int = 5, brand: Optional[str] = None) -> List[Dict[str, Any]]:
        count = max(1, min(20, int(count)))
        with self._connect() as conn:
            if brand:
                cur = conn.execute(
                    """
                    SELECT id, brand_key, brand, number, expiry_month, expiry_year, cvv, zip
                    FROM test_cards
                    WHERE brand_key = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (brand.lower(), count),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT id, brand_key, brand, number, expiry_month, expiry_year, cvv, zip
                    FROM test_cards
                    ORDER BY RANDOM()
                    LIMIT ?
                    """,
                    (count,),
                )
            rows = [dict(r) for r in cur.fetchall()]
        return rows
