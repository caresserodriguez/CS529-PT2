import hashlib
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "serviceflow.db"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL DEFAULT '',
    business_name TEXT NOT NULL DEFAULT '',
    email         TEXT NOT NULL DEFAULT '' COLLATE NOCASE,
    contact       TEXT NOT NULL DEFAULT '',
    username      TEXT UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
)
"""

_MIGRATIONS = [
    ("name",          "TEXT NOT NULL DEFAULT ''"),
    ("business_name", "TEXT NOT NULL DEFAULT ''"),
    ("email",         "TEXT NOT NULL DEFAULT ''"),
    ("contact",       "TEXT NOT NULL DEFAULT ''"),
]


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def ensure_users_table() -> None:
    with _conn() as conn:
        conn.execute(_USERS_DDL)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        for col, definition in _MIGRATIONS:
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
                except Exception:
                    pass
    from serviceflow_ai.doc_manager import ensure_table as _ensure_docs
    _ensure_docs()


def get_user_id(email: str) -> int | None:
    email = email.strip().lower()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id FROM users WHERE lower(username) = ?", (email,)
            ).fetchone()
    return row["id"] if row else None


def get_user_profile(user_id: int) -> dict:
    with _conn() as conn:
        row = conn.execute(
            "SELECT name, business_name, email, contact FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row:
        return {
            "name": row["name"] or "",
            "business_name": row["business_name"] or "",
            "email": row["email"] or "",
            "contact": row["contact"] or "",
        }
    return {"name": "", "business_name": "", "email": "", "contact": ""}


def _hash(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + dk.hex()


def _check(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 260_000)
        return dk.hex() == dk_hex
    except Exception:
        return False


def register_user(
    name: str,
    business_name: str,
    email: str,
    contact: str,
    password: str,
) -> tuple[bool, str]:
    email = email.strip().lower()
    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO users (name, business_name, email, contact, username, password_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name.strip(), business_name.strip(), email, contact.strip(), email, _hash(password)),
            )
        return True, "Account created. You can now log in."
    except sqlite3.IntegrityError:
        return False, "An account with this email address already exists."


def verify_user(email: str, password: str) -> bool:
    email = email.strip().lower()
    with _conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE lower(username) = ?", (email,)
            ).fetchone()
    return bool(row) and _check(password, row["password_hash"])
