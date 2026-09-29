import uuid
import json
from datetime import datetime, timezone
from backend.database.connection import get_user_db
from backend.schemas.contracts import CALAResult
from backend.providers.service import provider_service


class CALAService:
    """
    CLARIO Adaptive Learner Algorithm (CALA).
    Analyzes learner profiles and session inputs to determine a personalized starting point.
    """

    @staticmethod
    def run_analysis(user_id: str, session_id: str) -> CALAResult:
        # 1. Load context
        mind_profile = CALAService._get_mind_profile(user_id)
        session_inputs = CALAService._get_session_inputs(session_id)

        # 2. Construct prompt for the LLM
        prompt = CALAService._build_prompt(mind_profile, session_inputs)

        # 3. Phase 0 placeholder — generate a deterministic CALA result
        # Full LLM-driven analysis is reserved for subsequent phases.
        cala_result = CALAResult(
            cala_result_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            learner_level="beginner",
            confidence_signal="moderate",
            sentiment_signal="curious",
            difficulty_signals="standard",
            learning_preferences="visual, step-by-step",
            motivation_signals="intrinsic, goal-driven",
            recommended_starting_level=1,
            recommended_learning_strategy="scaffolded with examples",
            initial_weakness_signals="none detected from inputs",
            reasoning_summary=f"Placeholder CALA analysis for session {session_id}. Full LLM integration pending.",
            misconception_signals=None,
        )

        # 4. Persist result
        CALAService._persist_result(cala_result)

        return cala_result

    @staticmethod
    def _get_mind_profile(user_id: str) -> dict:
        with get_user_db() as conn:
            row = conn.execute(
                "SELECT answers_json FROM mind_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if not row:
                raise ValueError("Mind profile not found for user.")
            return json.loads(row["answers_json"])

    @staticmethod
    def _get_session_inputs(session_id: str) -> dict:
        with get_user_db() as conn:
            row = conn.execute(
                "SELECT task, goal, learner_state, interest FROM session_inputs WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            if not row:
                raise ValueError("Session inputs not found for this session.")
            return dict(row)

    @staticmethod
    def _build_prompt(mind_profile: dict, session_inputs: dict) -> str:
        return f"""
        You are the CALA (CLARIO Adaptive Learner Algorithm) engine.
        Your goal is to perform an initial learner analysis based on their cognitive profile and current learning goals.

        LEARNER MIND PROFILE (Persistent Preferences):
        {json.dumps(mind_profile, indent=2)}

        CURRENT SESSION INPUTS:
        - Task: {session_inputs['task']}
        - Goal: {session_inputs['goal']}
        - Current State: {session_inputs['learner_state']}
        - Interest: {session_inputs['interest']}

        ANALYSIS REQUIREMENTS:
        1. Determine the learner's baseline level for this specific task.
        2. Identify cognitive signals (confidence, sentiment) from their phrasing.
        3. Analyze motivation and learning preferences.
        4. Recommend a starting level (integer) and a high-level learning strategy.
        5. Identify any initial weakness signals or potential misconceptions inferred from their input.

        DO NOT measure actual mastery. This is a PREDICTIVE analysis based on self-reported data.
        """

    @staticmethod
    def _persist_result(result: CALAResult) -> None:
        with get_user_db() as conn:
            # Prevent duplicate results for the same session (keep latest)
            conn.execute(
                "DELETE FROM cala_results WHERE session_id = ?",
                (result.session_id,)
            )
            conn.execute(
                "INSERT INTO cala_results (cala_result_id, user_id, session_id, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (result.cala_result_id, result.user_id, result.session_id, result.model_dump_json(), datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
            )
