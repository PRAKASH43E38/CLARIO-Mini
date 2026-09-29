import secrets
import sqlite3
import bcrypt
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from fastapi import HTTPException, Request
from backend.core.config import settings

SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _unix_now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


@contextmanager
def get_session_db(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or settings.SESSION_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_session_db(db_path: Path | None = None) -> None:
    """Create the sessions table in a dedicated SQLite file."""
    path = db_path or settings.SESSION_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_session_db(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )


class SessionStore:
    """Minimal session store. Secure enough for Phase 1."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def create_session(self, user_id: str) -> str:
        init_session_db(self.db_path)
        token = secrets.token_urlsafe(32)
        expires_at = _unix_now() + SESSION_TTL_SECONDS
        with get_session_db(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, _utcnow_iso(), expires_at),
            )
        return token

    def get_user_id(self, token: str) -> str | None:
        init_session_db(self.db_path)
        with get_session_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)
            ).fetchone()
            if row is None or row["expires_at"] <= _unix_now():
                if row is not None:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None
            return row["user_id"]

    def invalidate(self, token: str) -> None:
        init_session_db(self.db_path)
        with get_session_db(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def cleanup_expired(self) -> None:
        with get_session_db(self.db_path) as conn:
            conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?", (_unix_now(),)
            )


class PasswordHasher:
    """bcrypt wrapper. Cost factor 12 keeps hashing cost reasonable."""

    @staticmethod
    def hash(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            return False


def get_current_user_id(request: Request) -> str:
    """Dependency: return the authenticated user_id from the session cookie."""
    token = request.cookies.get("clario_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user_id = SessionStore(settings.SESSION_DB_PATH).get_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired.")
    return user_id
