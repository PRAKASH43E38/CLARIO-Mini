import uuid
from datetime import datetime, timezone
from typing import List
from backend.database.connection import get_user_db
from backend.schemas.contracts import LearningSession, SessionInputs, SessionInputsResponse

class SessionService:
    @staticmethod
    def create_session(user_id: str) -> LearningSession:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with get_user_db() as conn:
            conn.execute(
                "INSERT INTO learning_sessions (session_id, user_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, 'INPUTS_PENDING', now, now)
            )

        return LearningSession(
            session_id=session_id,
            user_id=user_id,
            status='INPUTS_PENDING',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def save_inputs(session_id: str, user_id: str, inputs: SessionInputs) -> SessionInputsResponse:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with get_user_db() as conn:
            # Verify ownership
            session = conn.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()

            if not session:
                raise PermissionError("Session not found or access denied.")

            # Upsert inputs
            conn.execute(
                """
                INSERT INTO session_inputs (session_id, task, goal, learner_state, interest, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    task=excluded.task,
                    goal=excluded.goal,
                    learner_state=excluded.learner_state,
                    interest=excluded.interest,
                    updated_at=excluded.updated_at
                """,
                (session_id, inputs.task, inputs.goal, inputs.learner_state, inputs.interest, now, now)
            )

            # Advance status
            conn.execute(
                "UPDATE learning_sessions SET status = 'INPUTS_COMPLETED', updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )

        return SessionInputsResponse(
            session_id=session_id,
            task=inputs.task,
            goal=inputs.goal,
            learner_state=inputs.learner_state,
            interest=inputs.interest,
            updated_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def finalize_session(session_id: str, user_id: str) -> LearningSession:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with get_user_db() as conn:
            # Verify ownership and state
            session = conn.execute(
                "SELECT status FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()

            if not session:
                raise PermissionError("Session not found or access denied.")

            if session['status'] != 'INPUTS_COMPLETED':
                raise ValueError(f"Session must be in INPUTS_COMPLETED state, currently {session['status']}")

            conn.execute(
                "UPDATE learning_sessions SET status = 'READY_FOR_CALA', updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )

        return LearningSession(
            session_id=session_id,
            user_id=user_id,
            status='READY_FOR_CALA',
            created_at=datetime.now(timezone.utc), # Simplified for response
            updated_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def get_session(session_id: str, user_id: str) -> LearningSession:
        with get_user_db() as conn:
            row = conn.execute(
                "SELECT session_id, user_id, status, created_at, updated_at FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()

            if not row:
                raise PermissionError("Session not found or access denied.")

            return LearningSession(**dict(row))

    @staticmethod
    def get_session_inputs(session_id: str, user_id: str) -> SessionInputsResponse:
        with get_user_db() as conn:
            # Verify ownership via learning_sessions
            session = conn.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()

            if not session:
                raise PermissionError("Session not found or access denied.")

            row = conn.execute(
                "SELECT session_id, task, goal, learner_state, interest, updated_at FROM session_inputs WHERE session_id = ?",
                (session_id,)
            ).fetchone()

            if not row:
                raise ValueError("No inputs saved for this session.")

            return SessionInputsResponse(**dict(row))

    @staticmethod
    def list_user_sessions(user_id: str) -> List[LearningSession]:
        with get_user_db() as conn:
            rows = conn.execute(
                "SELECT session_id, user_id, status, created_at, updated_at FROM learning_sessions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()

            return [LearningSession(**dict(row)) for row in rows]
