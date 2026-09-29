import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from backend.core.config import settings

# user.db tables (plus the new profiles and mind_profiles tables for Phase 1).
# Mind Profile data lives ONLY in user.db - never in nova.db or clario_ai.db.


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: (row[key] if row[key] is not None else "") for key in row.keys()}


@contextmanager
def get_db_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class UserDb:
    """Database access for user.db: users, user_profiles, mind_profiles."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def user_exists(self, email: str) -> bool:
        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,))
            return cur.fetchone() is not None

    def get_profile_by_email(self, email: str) -> dict | None:
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, email, password_hash, created_at, updated_at FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def create_user(self, user_id: str, email: str, password_hash: str) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash),
            )

    def upsert_profile(self, profile: dict[str, Any]) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_profiles
                    (user_id, display_name, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name
                """,
                (
                    profile["user_id"],
                    profile.get("display_name", ""),
                    _utcnow(),
                ),
            )

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id, display_name, created_at FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return _row_to_dict(row) if row else None

    def update_profile(self, user_id: str, patch: dict[str, Any]) -> None:
        keys = [k for k in ("display_name", "target_topic", "learning_goals", "preferences_json") if k in patch]
        if not keys:
            return
        with get_db_connection(self.db_path) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in keys)
            conn.execute(
                f"""
                UPDATE user_profiles
                SET {set_clause}
                WHERE user_id = ?
                """,
                (*map(patch.get, keys), user_id),
            )

    def get_mind_profile(self, user_id: str) -> dict[str, Any] | None:
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id, answers_json, updated_at FROM mind_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return _row_to_dict(row) if row else None

    def upsert_mind_profile(self, user_id: str, answers: list[str]) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO mind_profiles (user_id, answers_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    answers_json = excluded.answers_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, self._answers_to_json(answers), _utcnow()),
            )

    @staticmethod
    def _answers_to_json(answers: list[str]) -> str:
        return json.dumps(answers, ensure_ascii=False)

    def get_mind_questions(self) -> list[str]:
        return [
            "When you learn something new, what usually keeps you going?",
            "What makes you lose interest while learning?",
            "If you get stuck, what would you prefer CLARIO to do?",
            "Which kind of learning experience feels most natural to you?",
            "What would make you want to come back and continue learning?",
        ]

    def mind_questions_answered(self, user_id: str) -> int:
        profile = self.get_mind_profile(user_id)
        if not profile or not profile["answers_json"]:
            return 0
        answers = json.loads(profile["answers_json"])
        return len(answers) if isinstance(answers, list) else 0
