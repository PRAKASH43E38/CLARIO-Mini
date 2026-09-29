import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.core.config import settings


def verify_phase1() -> None:
    with TemporaryDirectory(prefix="clario-phase1-verification-") as temporary:
        data_dir = Path(temporary)
        settings.DATA_DIR = data_dir
        settings.USER_DB_PATH = data_dir / "user.db"
        settings.NOVA_DB_PATH = data_dir / "nova.db"
        settings.CLARIO_AI_DB_PATH = data_dir / "clario_ai.db"
        settings.SESSION_DIR = data_dir
        settings.SESSION_DB_PATH = data_dir / "sessions.db"

        legacy_db = sqlite3.connect(settings.USER_DB_PATH)
        legacy_db.executescript(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE user_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                target_topic TEXT,
                learning_goals TEXT,
                preferences_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            CREATE TABLE mind_profiles (
                user_id TEXT PRIMARY KEY,
                answers_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            INSERT INTO users (id, email) VALUES ('legacy-user', 'legacy@example.com');
            INSERT INTO user_profiles (user_id, display_name)
                VALUES ('legacy-user', 'Legacy Learner');
            """
        )
        legacy_db.close()

        from fastapi.testclient import TestClient

        from backend.database.connection import (
            get_clario_ai_db,
            get_nova_db,
            get_user_db,
        )
        from backend.main import app

        with TestClient(app) as client:
            with get_user_db() as conn:
                tables = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(user_profiles)")
                }
                assert {"users", "user_profiles", "mind_profiles"} <= tables
                assert "updated_at" in columns
                migrated_profile = conn.execute(
                    "SELECT display_name, updated_at FROM user_profiles WHERE user_id = ?",
                    ("legacy-user",),
                ).fetchone()
                assert migrated_profile["display_name"] == "Legacy Learner"
                assert migrated_profile["updated_at"] is not None

            registration = client.post(
                "/auth/register",
                json={
                    "name": "Avery Learner",
                    "email": "AVERY@example.com",
                    "password": "secure-pass-123",
                },
            )
            assert registration.status_code == 201, registration.text
            identity = registration.json()
            user_id = identity["user_id"]
            assert identity["email"] == "avery@example.com"
            assert identity["name"] == "Avery Learner"
            assert "password_hash" not in registration.text
            assert "secure-pass-123" not in registration.text

            with get_user_db() as conn:
                password_hash = conn.execute(
                    "SELECT password_hash FROM users WHERE id = ?", (user_id,)
                ).fetchone()["password_hash"]
                assert password_hash.startswith("$2b$")

            duplicate = client.post(
                "/auth/register",
                json={
                    "name": "Duplicate",
                    "email": "avery@example.com",
                    "password": "secure-pass-123",
                },
            )
            assert duplicate.status_code == 409

            bad_login = client.post(
                "/auth/login",
                json={"email": "avery@example.com", "password": "incorrect"},
            )
            assert bad_login.status_code == 401
            login = client.post(
                "/auth/login",
                json={"email": "avery@example.com", "password": "secure-pass-123"},
            )
            assert login.status_code == 200
            assert "password_hash" not in login.text

            profile = client.get(f"/profile/{user_id}")
            assert profile.status_code == 200
            assert profile.json()["name"] == "Avery Learner"
            updated_profile = client.put(
                f"/profile/{user_id}", json={"name": "Avery Updated"}
            )
            assert updated_profile.status_code == 200
            assert updated_profile.json()["name"] == "Avery Updated"

            answers = [
                "Curiosity, practice, and small wins.",
                "Repetitive explanations.",
                "Offer a hint, then explain another way.",
                "A mix of examples and trying it myself.",
                "Seeing progress and having a clear next step.",
            ]
            saved_mind_profile = client.post(
                f"/mind-profile/{user_id}", json={"answers": answers}
            )
            assert saved_mind_profile.status_code == 201, saved_mind_profile.text
            assert saved_mind_profile.json()["answers"] == answers
            assert saved_mind_profile.json()["completed"] is True
            assert client.get(f"/mind-profile/{user_id}").json()["answers"] == answers
            assert client.post(
                f"/mind-profile/{user_id}", json={"answers": answers}
            ).status_code == 409

            revised_answers = list(answers)
            revised_answers[0] = "Curiosity, practice, small wins, and progress."
            updated_mind_profile = client.put(
                f"/mind-profile/{user_id}", json={"answers": revised_answers}
            )
            assert updated_mind_profile.status_code == 200
            assert updated_mind_profile.json()["answers"] == revised_answers
            assert client.put(
                f"/mind-profile/{user_id}", json={"answers": answers[:4]}
            ).status_code == 422
            assert client.get(f"/mind-profile/{user_id}").json()["answers"] == revised_answers
            assert client.get("/profile/legacy-user").status_code == 403

            with get_user_db() as conn:
                assert conn.execute(
                    "SELECT COUNT(*) FROM user_profiles WHERE user_id = ?", (user_id,)
                ).fetchone()[0] == 1
                assert conn.execute(
                    "SELECT COUNT(*) FROM mind_profiles WHERE user_id = ?", (user_id,)
                ).fetchone()[0] == 1
            with get_nova_db() as conn:
                assert conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'mind_profiles'"
                ).fetchone()[0] == 0
            with get_clario_ai_db() as conn:
                assert conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'mind_profiles'"
                ).fetchone()[0] == 0

            assert client.get("/health").json()["status"] == "healthy"
            session_cookie = client.cookies.get("clario_session")

        with TestClient(app) as restarted_client:
            restarted_client.cookies.set("clario_session", session_cookie)
            session = restarted_client.get("/auth/me")
            assert session.status_code == 200
            assert session.json()["mind_profile_completed"] is True
            assert restarted_client.get(f"/mind-profile/{user_id}").json()["answers"] == revised_answers
            logout = restarted_client.post("/auth/logout")
            assert logout.status_code == 204
            assert restarted_client.get("/auth/me").status_code == 401

    print("PHASE 1 VERIFICATION PASSED")


if __name__ == "__main__":
    verify_phase1()
