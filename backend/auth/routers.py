import json
import secrets
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from backend.auth.session import PasswordHasher, SessionStore, get_current_user_id
from backend.core.config import settings
from backend.database.connection import get_user_db
from backend.schemas.contracts import (
    AuthResponse,
    LoginRequest,
    MindProfileInput,
    MindProfileResponse,
    RegisterRequest,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter()
session_store = SessionStore(settings.SESSION_DB_PATH)
MIND_QUESTIONS_COUNT = 5


def _read_answers(raw_answers: str | None) -> list[str]:
    if not raw_answers:
        return []
    try:
        answers = json.loads(raw_answers)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Stored mind profile is invalid.") from exc
    if (
        not isinstance(answers, list)
        or any(
            not isinstance(answer, str)
            or not answer.strip()
            or len(answer) > 2000
            for answer in answers
        )
        or len(answers) > MIND_QUESTIONS_COUNT
    ):
        raise HTTPException(status_code=500, detail="Stored mind profile is invalid.")
    return answers


def _get_user_record(user_id: str) -> sqlite3.Row:
    with get_user_db() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.created_at, u.updated_at, p.display_name,
                   m.answers_json, m.updated_at AS mind_updated_at
            FROM users AS u
            LEFT JOIN user_profiles AS p ON p.user_id = u.id
            LEFT JOIN mind_profiles AS m ON m.user_id = u.id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return row


def _profile_response(row: sqlite3.Row) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=row["id"],
        name=row["display_name"] or "",
        email=row["email"],
        created_at=row["created_at"],
        updated_at=row["updated_at"] or row["created_at"],
    )


def _auth_response(user_id: str) -> AuthResponse:
    row = _get_user_record(user_id)
    answers = _read_answers(row["answers_json"])
    return AuthResponse(
        **_profile_response(row).model_dump(),
        mind_profile_completed=len(answers) == MIND_QUESTIONS_COUNT
        and all(answer.strip() for answer in answers),
    )


def _require_owner(request: Request, user_id: str) -> None:
    if get_current_user_id(request) != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own profile.")


def _set_session_cookie(response: Response, user_id: str) -> None:
    token = session_store.create_session(user_id)
    response.set_cookie(
        key="clario_session",
        value=token,
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="lax",
        path="/",
    )


@router.post("/auth/register", status_code=201, response_model=AuthResponse, tags=["Authentication"])
def register(body: RegisterRequest, response: Response) -> AuthResponse:
    user_id = secrets.token_urlsafe(16)
    password_hash = PasswordHasher.hash(body.password)
    try:
        with get_user_db() as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, body.email, password_hash),
            )
            conn.execute(
                "INSERT INTO user_profiles (user_id, display_name) VALUES (?, ?)",
                (user_id, body.name),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="A user with this email already exists.",
        ) from exc

    _set_session_cookie(response, user_id)
    return _auth_response(user_id)


@router.post("/auth/login", response_model=AuthResponse, tags=["Authentication"])
def login(body: LoginRequest, response: Response) -> AuthResponse:
    with get_user_db() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (body.email,),
        ).fetchone()
    if row is None or not row["password_hash"] or not PasswordHasher.verify(
        body.password, row["password_hash"]
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    _set_session_cookie(response, row["id"])
    return _auth_response(row["id"])


@router.get("/auth/me", response_model=AuthResponse, tags=["Authentication"])
def whoami(request: Request) -> AuthResponse:
    return _auth_response(get_current_user_id(request))


@router.post("/auth/logout", status_code=204, tags=["Authentication"])
def logout(request: Request, response: Response) -> Response:
    token = request.cookies.get("clario_session")
    if token:
        session_store.invalidate(token)
    response.delete_cookie(
        key="clario_session",
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="lax",
        path="/",
    )
    response.status_code = 204
    return response


@router.get("/profile/{user_id}", response_model=UserProfileResponse, tags=["Profile"])
def get_profile(user_id: str, request: Request) -> UserProfileResponse:
    _require_owner(request, user_id)
    return _profile_response(_get_user_record(user_id))


@router.put("/profile/{user_id}", response_model=UserProfileResponse, tags=["Profile"])
def update_profile(
    user_id: str,
    body: UserProfileUpdate,
    request: Request,
) -> UserProfileResponse:
    _require_owner(request, user_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_user_db() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (user_id, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = excluded.display_name,
                updated_at = excluded.updated_at
            """,
            (user_id, body.name, timestamp, timestamp),
        )
        conn.execute(
            "UPDATE users SET updated_at = ? WHERE id = ?",
            (timestamp, user_id),
        )
    return _profile_response(_get_user_record(user_id))


@router.get(
    "/mind-profile/{user_id}",
    response_model=MindProfileResponse,
    tags=["Mind Profile"],
)
def get_mind_profile(user_id: str, request: Request) -> MindProfileResponse:
    _require_owner(request, user_id)
    row = _get_user_record(user_id)
    answers = _read_answers(row["answers_json"])
    return MindProfileResponse(
        user_id=user_id,
        answers=answers,
        completed=len(answers) == MIND_QUESTIONS_COUNT and all(answer.strip() for answer in answers),
        updated_at=row["mind_updated_at"],
    )


def _save_mind_profile(user_id: str, answers: list[str]) -> MindProfileResponse:
    clean_answers = [answer.strip() for answer in answers]
    if any(not answer for answer in clean_answers):
        raise HTTPException(status_code=422, detail="Each answer must be non-empty.")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_user_db() as conn:
        conn.execute(
            """
            INSERT INTO mind_profiles (user_id, answers_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                answers_json = excluded.answers_json,
                updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(clean_answers, ensure_ascii=False), timestamp),
        )
    return MindProfileResponse(
        user_id=user_id,
        answers=clean_answers,
        completed=True,
        updated_at=timestamp,
    )


@router.post(
    "/mind-profile/{user_id}",
    response_model=MindProfileResponse,
    status_code=201,
    tags=["Mind Profile"],
)
def create_mind_profile(
    user_id: str,
    body: MindProfileInput,
    request: Request,
) -> MindProfileResponse:
    _require_owner(request, user_id)
    row = _get_user_record(user_id)
    current_answers = _read_answers(row["answers_json"])
    if len(current_answers) == MIND_QUESTIONS_COUNT:
        raise HTTPException(
            status_code=409,
            detail="Mind profile already exists. Use PUT to edit it.",
        )
    return _save_mind_profile(user_id, body.answers)


@router.put(
    "/mind-profile/{user_id}",
    response_model=MindProfileResponse,
    tags=["Mind Profile"],
)
def update_mind_profile(
    user_id: str,
    body: MindProfileInput,
    request: Request,
) -> MindProfileResponse:
    _require_owner(request, user_id)
    _get_user_record(user_id)
    return _save_mind_profile(user_id, body.answers)
