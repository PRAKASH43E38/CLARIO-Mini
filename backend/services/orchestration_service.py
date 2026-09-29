import uuid
import json
from datetime import datetime, timezone
from backend.database.connection import get_clario_ai_db, get_user_db


class OrchestrationService:
    """
    Manages the state and transitions of the CLARIO-AI orchestration loop.
    """

    VALID_TRANSITIONS = {
        "SESSION_CREATED": ["CALA_PROCESSED"],
        "CALA_PROCESSED": ["ROADMAP_CREATED"],
        "ROADMAP_CREATED": ["LEVEL_UNLOCKED"],
        "LEVEL_UNLOCKED": ["LEVEL_ENTERED"],
        "LEVEL_ENTERED": ["READY_FOR_LEVEL_RESEARCH"],
        "READY_FOR_LEVEL_RESEARCH": ["NOVA_RESEARCH", "MIRA_TEACHING", "AYAN_THINKING"],
        "NOVA_RESEARCH": ["MIRA_TEACHING", "AYAN_THINKING"],
        "MIRA_TEACHING": ["TEACHING_COMPLETED", "AYAN_THINKING"],
        "TEACHING_COMPLETED": ["AYAN_THINKING"],
        "AYAN_THINKING": ["THINKING_COMPLETED"],
        "THINKING_COMPLETED": ["KIRA_APPLICATION"],
        "KIRA_APPLICATION": ["APPLICATION_COMPLETED"],
        "APPLICATION_COMPLETED": ["ZAYN_QUIZ"],
        "ZAYN_QUIZ": ["QUIZ_COMPLETED"],
        "QUIZ_COMPLETED": ["ELARA_EVALUATION"],
        "ELARA_EVALUATION": ["EVALUATION_COMPLETED"],
        "EVALUATION_COMPLETED": ["ADAPTIVE_DECISION", "CLARIO_AI_DECISION"],
        "ADAPTIVE_DECISION": ["COMPLETE_LEVEL", "REMEDIATE", "UNLOCK_NEXT_LEVEL", "COMPLETE_GOAL"],
        "CLARIO_AI_DECISION": ["COMPLETE_LEVEL", "REMEDIATE", "UNLOCK_NEXT_LEVEL", "COMPLETE_GOAL"],
        "COMPLETE_LEVEL": ["UNLOCK_NEXT_LEVEL", "COMPLETE_GOAL"],
        "UNLOCK_NEXT_LEVEL": ["LEVEL_ENTERED", "SESSION_COMPLETED"],
        "COMPLETE_GOAL": ["SESSION_COMPLETED"],
        "REMEDIATE": ["REDUCE_DIFFICULTY", "MIRA_RETEACH", "MIRA"],
        "REDUCE_DIFFICULTY": ["MIRA_RETEACH", "MIRA"],
        "MIRA_RETEACH": ["TARGETED_RETEST"],
        "MIRA": ["TARGETED_RETEST"],
        "TARGETED_RETEST": ["ELARA_EVALUATION"],
    }

    @staticmethod
    def create_orchestration_state(session_id: str, user_id: str) -> str:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with get_clario_ai_db() as conn:
            conn.execute(
                "INSERT INTO orchestration_runs (id, session_id, current_stage, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, session_id, "SESSION_CREATED", "ACTIVE", now, now)
            )
        return run_id

    @staticmethod
    def transition_state(run_id: str, user_id: str, target_state: str) -> str:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with get_clario_ai_db() as conn:
            row = conn.execute(
                "SELECT current_stage, session_id FROM orchestration_runs WHERE id = ?",
                (run_id,)
            ).fetchone()

            if not row:
                raise ValueError("Orchestration run not found.")

            current_state = row["current_stage"]

            if target_state not in OrchestrationService.VALID_TRANSITIONS.get(current_state, []):
                raise ValueError(f"Invalid transition: {current_state} -> {target_state}")

            conn.execute(
                "UPDATE orchestration_runs SET current_stage = ?, updated_at = ? WHERE id = ?",
                (target_state, now, run_id)
            )

        return target_state

    @staticmethod
    def get_current_state(run_id: str) -> dict:
        with get_clario_ai_db() as conn:
            row = conn.execute(
                "SELECT * FROM orchestration_runs WHERE id = ?",
                (run_id,)
            ).fetchone()
            if not row:
                raise ValueError("Orchestration run not found.")
            return dict(row)

    @staticmethod
    def record_event(session_id: str, event_type: str, payload: dict | None = None, run_id: str | None = None) -> None:
        """Record an orchestration event in agent_executions table."""
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        with get_clario_ai_db() as conn:
            actual_run_id = run_id
            if not actual_run_id:
                row = conn.execute(
                    "SELECT id FROM orchestration_runs WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                    (session_id,)
                ).fetchone()
                if row:
                    actual_run_id = row["id"]

            if actual_run_id:
                conn.execute(
                    "INSERT INTO agent_executions (id, run_id, agent_name, task_type, input_payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), actual_run_id, "clario_ai", event_type, json.dumps(payload or {}), now)
                )


orchestration_service = OrchestrationService()
