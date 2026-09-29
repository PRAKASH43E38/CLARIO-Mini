from backend.core.config import settings
from backend.models.db import UserDb


class ProfileService:
    """Handles user profile read/write in user.db (never in other DBs)."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db = UserDb(db_path or settings.USER_DB_PATH)

    def user_exists(self, email: str) -> bool:
        return self._db.user_exists(email)

    def get_by_email(self, email: str) -> dict | None:
        return self._db.get_profile_by_email(email)

    def create_user(self, user_id: str, email: str, password_hash: str) -> None:
        self._db.create_user(user_id, email, password_hash)

    def upsert_profile(self, profile: dict[str, str]) -> None:
        self._db.upsert_profile(profile)

    def get_profile(self, user_id: str) -> dict | None:
        return self._db.get_profile(user_id)

    def update_display_name(self, user_id: str, display_name: str | None = None) -> None:
        if display_name is not None:
            self._db.update_profile(user_id, {"display_name": display_name})
