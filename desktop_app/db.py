from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional

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
        # Basic geodata tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS country (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS landmark (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT,
                country_code TEXT NOT NULL,
                FOREIGN KEY(country_code) REFERENCES country(code)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS government (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                office TEXT NOT NULL,
                person_name TEXT NOT NULL,
                country_code TEXT NOT NULL,
                FOREIGN KEY(country_code) REFERENCES country(code)
            )
            """
        )
        # Helpful search indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_person_country ON person(country)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_landmark_country ON landmark(country_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gov_country ON government(country_code)")
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


def seed_geo_if_empty() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Countries
        cur.execute("SELECT COUNT(1) FROM country")
        if (cur.fetchone() or [0])[0] == 0:
            countries = [
                ("US", "United States"),
                ("GB", "United Kingdom"),
                ("FR", "France"),
                ("DE", "Germany"),
                ("JP", "Japan"),
                ("IN", "India"),
                ("BR", "Brazil"),
                ("CA", "Canada"),
                ("AU", "Australia"),
                ("CN", "China"),
            ]
            cur.executemany("INSERT INTO country(code, name) VALUES (?,?)", countries)

        # Landmarks
        cur.execute("SELECT COUNT(1) FROM landmark")
        if (cur.fetchone() or [0])[0] == 0:
            landmarks = [
                ("Statue of Liberty", "New York", "US"),
                ("Golden Gate Bridge", "San Francisco", "US"),
                ("Grand Canyon", "Arizona", "US"),
                ("Big Ben", "London", "GB"),
                ("Tower Bridge", "London", "GB"),
                ("Eiffel Tower", "Paris", "FR"),
                ("Louvre Museum", "Paris", "FR"),
                ("Brandenburg Gate", "Berlin", "DE"),
                ("Neuschwanstein Castle", "Bavaria", "DE"),
                ("Tokyo Tower", "Tokyo", "JP"),
                ("Fushimi Inari Shrine", "Kyoto", "JP"),
                ("Taj Mahal", "Agra", "IN"),
                ("India Gate", "New Delhi", "IN"),
                ("Christ the Redeemer", "Rio de Janeiro", "BR"),
                ("CN Tower", "Toronto", "CA"),
                ("Sydney Opera House", "Sydney", "AU"),
                ("Great Wall", "Beijing", "CN"),
            ]
            cur.executemany(
                "INSERT INTO landmark(name, city, country_code) VALUES (?,?,?)",
                landmarks,
            )

        # Government officials (sample data with fake names)
        cur.execute("SELECT COUNT(1) FROM government")
        if (cur.fetchone() or [0])[0] == 0:
            try:
                from faker import Faker
            except Exception:
                raise RuntimeError("Faker not installed. Install from desktop_app/requirements.txt")
            fake = Faker()
            gov_rows = []
            def add_roles(code: str, roles: List[str]):
                for office in roles:
                    gov_rows.append((office, fake.name(), code))

            add_roles("US", ["President", "Secretary of State"])  
            add_roles("GB", ["Prime Minister", "Foreign Secretary"])  
            add_roles("FR", ["President", "Prime Minister"])  
            add_roles("DE", ["Chancellor", "Foreign Minister"])  
            add_roles("JP", ["Prime Minister", "Foreign Minister"])  
            add_roles("IN", ["Prime Minister", "External Affairs Minister"])  
            add_roles("BR", ["President", "Foreign Minister"])  
            add_roles("CA", ["Prime Minister", "Foreign Minister"])  
            add_roles("AU", ["Prime Minister", "Foreign Minister"])  
            add_roles("CN", ["President", "Premier"])  

            cur.executemany(
                "INSERT INTO government(office, person_name, country_code) VALUES (?,?,?)",
                gov_rows,
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


def list_countries() -> List[Tuple[str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT code, name FROM country ORDER BY name")
        return cur.fetchall()
    finally:
        conn.close()


def search_landmarks(query: str, country_code: Optional[str] = None, limit: int = 50) -> List[Tuple[str, str, str]]:
    q = f"%{query.lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        if country_code:
            cur.execute(
                """
                SELECT l.name, COALESCE(l.city, ''), c.name
                FROM landmark l JOIN country c ON c.code = l.country_code
                WHERE l.country_code = ? AND lower(l.name) LIKE ?
                ORDER BY l.name
                LIMIT ?
                """,
                (country_code, q, limit),
            )
        else:
            cur.execute(
                """
                SELECT l.name, COALESCE(l.city, ''), c.name
                FROM landmark l JOIN country c ON c.code = l.country_code
                WHERE lower(l.name) LIKE ?
                ORDER BY l.name
                LIMIT ?
                """,
                (q, limit),
            )
        return cur.fetchall()
    finally:
        conn.close()


def search_government(query: str, country_code: Optional[str] = None, limit: int = 50) -> List[Tuple[str, str, str]]:
    q = f"%{query.lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        if country_code:
            cur.execute(
                """
                SELECT g.office, g.person_name, c.name
                FROM government g JOIN country c ON c.code = g.country_code
                WHERE g.country_code = ? AND (lower(g.office) LIKE ? OR lower(g.person_name) LIKE ?)
                ORDER BY g.office
                LIMIT ?
                """,
                (country_code, q, q, limit),
            )
        else:
            cur.execute(
                """
                SELECT g.office, g.person_name, c.name
                FROM government g JOIN country c ON c.code = g.country_code
                WHERE lower(g.office) LIKE ? OR lower(g.person_name) LIKE ?
                ORDER BY g.office
                LIMIT ?
                """,
                (q, q, limit),
            )
        return cur.fetchall()
    finally:
        conn.close()


def search_people_by_country(query: str, country_code: Optional[str], limit: int = 25) -> List[Tuple[int, str, str, str, str, str]]:
    q = f"%{query.lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        if country_code:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE country = ? AND (
                      lower(first_name) LIKE ? OR lower(last_name) LIKE ? OR lower(email) LIKE ? OR lower(city) LIKE ?
                )
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (country_code, q, q, q, q, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(first_name) LIKE ? OR lower(last_name) LIKE ? OR lower(email) LIKE ? OR lower(city) LIKE ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (q, q, q, q, limit),
            )
        return cur.fetchall()
    finally:
        conn.close()
