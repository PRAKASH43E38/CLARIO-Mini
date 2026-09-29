import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json

from backend.database.connection import get_clario_ai_db, get_user_db
from backend.schemas.contracts import ElaraEvaluationRequest

logger = logging.getLogger(__name__)

class EvaluationInterface:
    """
    Aggregation service that gathers evidence from all four learning agents
    to create a bundle for Elara's evaluation.
    """

    def get_evidence_bundle(self, session_id: str, level_id: str, user_id: str) -> Dict[str, Any]:
        """
        Gathers and maps evidence from Mira, Ayan, Kira, and Zayn.
        """
        try:
            with get_clario_ai_db() as ai_db:
                # 1. Get Roadmap Context
                level = ai_db.execute(
                    "SELECT title, objective FROM roadmap_levels WHERE level_id = ?",
                    (level_id,)
                ).fetchone()
                if not level:
                    raise ValueError(f"Level {level_id} not found.")

                concepts = ai_db.execute(
                    "SELECT concept_name FROM level_concepts WHERE level_id = ?",
                    (level_id,)
                ).fetchall()
                concept_list = [c["concept_name"] for c in concepts]

                # 2. Mira Evidence (Teaching Interactions)
                mira_data = ai_db.execute(
                    "SELECT response_payload_json FROM teaching_interactions WHERE session_id = ? AND level_id = ?",
                    (session_id, level_id)
                ).fetchall()
                mira_evidence = {"interactions": [i["response_payload_json"] for i in mira_data]}

                # 3. Ayan Evidence (Thinking Challenges & Responses)
                ayan_challenges = ai_db.execute(
                    "SELECT questions_json FROM thinking_challenges WHERE session_id = ? AND level_id = ?",
                    (session_id, level_id)
                ).fetchone()
                ayan_responses = ai_db.execute(
                    """
                    SELECT tr.question_id, tr.user_answer
                    FROM thinking_responses tr
                    JOIN thinking_challenges tc ON tr.challenge_id = tc.challenge_id
                    WHERE tc.session_id = ? AND tc.level_id = ?
                    """,
                    (session_id, level_id)
                ).fetchall()
                ayan_evidence = {
                    "challenges": ayan_challenges["questions_json"] if ayan_challenges else [],
                    "responses": [dict(r) for r in ayan_responses]
                }

                # 4. Kira Evidence (Application Scenarios & Responses)
                kira_scenarios = ai_db.execute(
                    "SELECT scenarios_json FROM application_scenarios WHERE session_id = ? AND level_id = ?",
                    (session_id, level_id)
                ).fetchone()
                kira_responses = ai_db.execute(
                    """
                    SELECT ar.scenario_id, ar.user_response
                    FROM application_responses ar
                    JOIN application_scenarios as sc ON ar.scenario_id = sc.scenario_id
                    WHERE sc.session_id = ? AND sc.level_id = ?
                    """,
                    (session_id, level_id)
                ).fetchall()
                kira_evidence = {
                    "scenarios": kira_scenarios["scenarios_json"] if kira_scenarios else [],
                    "responses": [dict(r) for r in kira_responses]
                }

                # 5. Zayn Evidence (Quiz & Responses)
                quiz = ai_db.execute(
                    "SELECT quiz_id, questions_json FROM quizzes WHERE session_id = ? AND level_id = ?",
                    (session_id, level_id)
                ).fetchone()
                zayn_responses = ai_db.execute(
                    """
                    SELECT qr.question_id, qr.user_answer, qr.response_time_seconds, qr.is_timeout
                    FROM quiz_responses qr
                    JOIN quizzes q ON qr.quiz_id = q.quiz_id
                    WHERE q.session_id = ? AND q.level_id = ?
                    """,
                    (session_id, level_id)
                ).fetchall()
                zayn_evidence = {
                    "quiz": quiz["questions_json"] if quiz else [],
                    "responses": [dict(r) for r in zayn_responses]
                }

                # 6. User Profile
                with get_user_db() as user_db:
                    profile = user_db.execute(
                        "SELECT * FROM user_profiles WHERE user_id = ?",
                        (user_id,)
                    ).fetchone()
                    user_profile = dict(profile) if profile else {}

                return {
                    "session_id": session_id,
                    "user_id": user_id,
                    "level_id": level_id,
                    "objective": level["objective"],
                    "concepts": concept_list,
                    "mira_evidence": mira_evidence,
                    "ayan_evidence": ayan_evidence,
                    "kira_evidence": kira_evidence,
                    "zayn_evidence": zayn_evidence,
                    "learner_profile": user_profile
                }

        except Exception as e:
            logger.error(f"Error gathering evaluation evidence: {e}")
            raise e

evaluation_interface = EvaluationInterface()
