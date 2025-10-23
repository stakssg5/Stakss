from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import secrets


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("DB_PATH", str(BASE_DIR / "demo_users.db")))


@dataclass
class PublicUser:
    id: int
    full_name: str
    email: str


class AuthService:
    """
    Minimal demo authentication service using the existing SQLite database.

    Credentials: email + cvv (since the demo schema has no password column).
    This is FOR DEMO ONLY.
    """

    # In-memory token store: token -> PublicUser
    _sessions: Dict[str, PublicUser] = {}

    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def authenticate(self, email: str, cvv: str) -> Optional[PublicUser]:
        """Return PublicUser if credentials are valid, else None."""
        query = (
            "SELECT id, full_name, email FROM users WHERE email = ? AND cvv = ? LIMIT 1"
        )
        with self._connect() as conn:
            cur = conn.execute(query, (email, cvv))
            row = cur.fetchone()
            if not row:
                return None
            return PublicUser(id=row[0], full_name=row[1], email=row[2])

    def create_session(self, user: PublicUser) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user
        return token

    def get_user_by_token(self, token: str) -> Optional[PublicUser]:
        return self._sessions.get(token)

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)
