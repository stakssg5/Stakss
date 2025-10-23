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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS camera (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                country_code TEXT NOT NULL,
                url TEXT NOT NULL,
                is_public INTEGER NOT NULL DEFAULT 1,
                is_fixed INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(country_code) REFERENCES country(code)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS person_camera (
                person_id INTEGER NOT NULL,
                camera_id INTEGER NOT NULL,
                PRIMARY KEY(person_id, camera_id),
                FOREIGN KEY(person_id) REFERENCES person(id) ON DELETE CASCADE,
                FOREIGN KEY(camera_id) REFERENCES camera(id) ON DELETE CASCADE
            )
            """
        )
        # Helpful search indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_person_country ON person(country)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_landmark_country ON landmark(country_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gov_country ON government(country_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_camera_country ON camera(country_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_person_camera_person ON person_camera(person_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_person_camera_camera ON person_camera(camera_id)")
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


def seed_camera_if_empty() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM camera")
        if (cur.fetchone() or [0])[0] == 0:
            # Use demo video path for sample cameras; users can replace with real, permissioned streams
            demo_url = "resources/forensic.mp4"
            cams = [
                ("Times Square Demo Cam", "New York", "US", demo_url, 1, 1),
                ("London Bridge Demo Cam", "London", "GB", demo_url, 1, 1),
                ("Paris Center Demo Cam", "Paris", "FR", demo_url, 1, 1),
            ]
            cur.executemany(
                "INSERT INTO camera(name, location, country_code, url, is_public, is_fixed) VALUES (?,?,?,?,?,?)",
                cams,
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


def search_people_exact(name: str, limit: int = 25) -> List[Tuple[int, str, str, str, str, str]]:
    norm = " ".join(name.strip().split()).lower()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, first_name, last_name, email, city, country
            FROM person
            WHERE lower(first_name || ' ' || last_name) = ?
               OR lower(first_name) = ?
               OR lower(last_name) = ?
            ORDER BY last_name, first_name
            LIMIT ?
            """,
            (norm, norm, norm, limit),
        )
        return cur.fetchall()
    finally:
        conn.close()


def search_people_by_email(query: str, *, exact: bool = False, limit: int = 25) -> List[Tuple[int, str, str, str, str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if exact:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(email) = ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (query.strip().lower(), limit),
            )
        else:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(email) LIKE ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (f"%{query.strip().lower()}%", limit),
            )
        return cur.fetchall()
    finally:
        conn.close()


def search_people_by_city(query: str, *, exact: bool = False, limit: int = 25) -> List[Tuple[int, str, str, str, str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if exact:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(city) = ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (query.strip().lower(), limit),
            )
        else:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(city) LIKE ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (f"%{query.strip().lower()}%", limit),
            )
        return cur.fetchall()
    finally:
        conn.close()


def search_people_by_country_name(query: str, *, exact: bool = False, limit: int = 25) -> List[Tuple[int, str, str, str, str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if exact:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(country) = ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (query.strip().lower(), limit),
            )
        else:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, city, country
                FROM person
                WHERE lower(country) LIKE ?
                ORDER BY last_name, first_name
                LIMIT ?
                """,
                (f"%{query.strip().lower()}%", limit),
            )
        return cur.fetchall()
    finally:
        conn.close()


def search_people_by_id(person_id: int) -> List[Tuple[int, str, str, str, str, str]]:
    person = get_person(person_id)
    return [person] if person else []


def list_countries() -> List[Tuple[str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT code, name FROM country ORDER BY name")
        return cur.fetchall()
    finally:
        conn.close()


def get_country_code_by_name(country_name: str) -> Optional[str]:
    name = " ".join(country_name.strip().split())
    if not name:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT code FROM country WHERE name = ?", (name,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_person(person_id: int) -> Optional[Tuple[int, str, str, str, str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, first_name, last_name, email, city, country FROM person WHERE id = ?",
            (person_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def search_landmarks(query: str, country_code: Optional[str] = None, limit: int = 50) -> List[Tuple[int, str, str, str]]:
    q = f"%{query.lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        if country_code:
            cur.execute(
                """
                SELECT l.id, l.name, COALESCE(l.city, ''), c.name
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
                SELECT l.id, l.name, COALESCE(l.city, ''), c.name
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


def search_government(query: str, country_code: Optional[str] = None, limit: int = 50) -> List[Tuple[int, str, str, str]]:
    q = f"%{query.lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        if country_code:
            cur.execute(
                """
                SELECT g.id, g.office, g.person_name, c.name
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
                SELECT g.id, g.office, g.person_name, c.name
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
                WHERE (SELECT name FROM country WHERE code = ?) = country AND (
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


def delete_people(ids: List[int]) -> int:
    if not ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany("DELETE FROM person WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def delete_landmarks(ids: List[int]) -> int:
    if not ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany("DELETE FROM landmark WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def delete_government(ids: List[int]) -> int:
    if not ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany("DELETE FROM government WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def search_cameras(
    query: str,
    country_code: Optional[str] = None,
    public_only: bool = False,
    fixed_only: bool = False,
    limit: int = 100,
) -> List[Tuple[int, str, str, str, str, int, int]]:
    q = f"%{(query or '').lower()}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        clauses = ["(lower(cam.name) LIKE ? OR lower(cam.location) LIKE ?)"]
        params: List[object] = [q, q]
        if country_code:
            clauses.append("cam.country_code = ?")
            params.append(country_code)
        if public_only:
            clauses.append("cam.is_public = 1")
        if fixed_only:
            clauses.append("cam.is_fixed = 1")
        where = " AND ".join(clauses)
        sql = (
            "SELECT cam.id, cam.name, COALESCE(cam.location, ''), c.name, cam.url, cam.is_public, cam.is_fixed "
            "FROM camera cam JOIN country c ON c.code = cam.country_code "
            f"WHERE {where} ORDER BY cam.name LIMIT ?"
        )
        params.append(limit)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def insert_camera(name: str, location: str, country_code: str, url: str, is_public: bool, is_fixed: bool) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO camera(name, location, country_code, url, is_public, is_fixed) VALUES (?,?,?,?,?,?)",
            (name, location, country_code, url, 1 if is_public else 0, 1 if is_fixed else 0),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def delete_cameras(ids: List[int]) -> int:
    if not ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany("DELETE FROM camera WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def list_cameras_for_person(person_id: int) -> List[Tuple[int, str, str, str, str]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT cam.id, cam.name, COALESCE(cam.location, ''), c.name, cam.url
            FROM person_camera pc
            JOIN camera cam ON cam.id = pc.camera_id
            JOIN country c ON c.code = cam.country_code
            WHERE pc.person_id = ?
            ORDER BY cam.name
            """,
            (person_id,),
        )
        return cur.fetchall()
    finally:
        conn.close()


def link_camera_to_person(person_id: int, camera_id: int) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO person_camera(person_id, camera_id) VALUES (?, ?)",
            (person_id, camera_id),
        )
        conn.commit()
    finally:
        conn.close()


def unlink_cameras_from_person(person_id: int, camera_ids: List[int]) -> int:
    if not camera_ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(
            "DELETE FROM person_camera WHERE person_id = ? AND camera_id = ?",
            [(person_id, cid) for cid in camera_ids],
        )
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()
