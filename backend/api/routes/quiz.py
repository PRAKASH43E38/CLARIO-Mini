import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any
import uuid
from datetime import datetime, timezone

from backend.database.connection import get_clario_ai_db, get_user_db
from backend.schemas.contracts import (
    ZaynQuizRequest,
    ZaynQuizResponse,
    ZaynAnswerSubmission,
    AgentTask,
    AgentResult
)
from backend.agents.zayn.agent import zayn_agent
from backend.auth.session import get_current_user_id
from backend.services.research_interface import ResearchInterface

router = APIRouter(prefix="/quiz", tags=["Quiz"])
logger = logging.getLogger(__name__)
research_interface = ResearchInterface()

@router.post("/start")
async def start_quiz(session_id: str, level_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Triggers Zayn to generate the quiz for the current level.
    """
    try:
        # 1. Verify session ownership
        with get_user_db() as user_db:
            session = user_db.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()
            if not session:
                raise HTTPException(status_code=403, detail="Session not found or ownership mismatch")

        # 2. Gather context for Zayn
        with get_clario_ai_db() as ai_db:
            # Get level objective and concepts
            level = ai_db.execute(
                "SELECT title, objective FROM roadmap_levels WHERE level_id = ?",
                (level_id,)
            ).fetchone()
            if not level:
                raise HTTPException(status_code=404, detail="Level not found")

            concepts = ai_db.execute(
                "SELECT concept_name FROM level_concepts WHERE level_id = ?",
                (level_id,)
            ).fetchall()
            concept_list = [c["concept_name"] for c in concepts]

            # Fetch contexts from previous agents
            # Mira
            mira_interactions = ai_db.execute(
                "SELECT response_payload_json FROM teaching_interactions WHERE session_id = ? AND level_id = ?",
                (session_id, level_id)
            ).fetchall()
            mira_context = {"lesson_content": " ".join([i["response_payload_json"] for i in mira_interactions])}

            # Ayan
            ayan_challenges = ai_db.execute(
                "SELECT questions_json FROM thinking_challenges WHERE session_id = ? AND level_id = ?",
                (session_id, level_id)
            ).fetchone()
            ayan_context = {"questions": ayan_challenges["questions_json"] if ayan_challenges else []}

            # Kira
            kira_scenarios = ai_db.execute(
                "SELECT scenarios_json FROM application_scenarios WHERE session_id = ? AND level_id = ?",
                (session_id, level_id)
            ).fetchone()
            kira_context = {"scenarios": kira_scenarios["scenarios_json"] if kira_scenarios else []}

        # 3. Get research from Nova via interface
        nova_knowledge = research_interface.get_research_context(level_id)

        # 4. Prepare Zayn request
        # In a real scenario, we'd fetch the user profile from user_db
        user_profile = {"learning_style": "analytical"}

        request_data = {
            "session_id": session_id,
            "user_id": user_id,
            "level_id": level_id,
            "objective": level["objective"],
            "concepts": concept_list,
            "mira_context": mira_context,
            "ayan_context": ayan_context,
            "kira_context": kira_context,
            "nova_knowledge": nova_knowledge,
            "learner_profile": user_profile
        }

        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_name="zayn",
            session_id=session_id,
            instruction="Generate a balanced 10-question quiz",
            input_data=request_data
        )

        # 5. Call Zayn
        result = await zayn_agent.process_task(task)

        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error_message)

        quiz_data = ZaynQuizResponse(**result.output_data)

        # 6. Persist quiz to DB
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT INTO quizzes (quiz_id, session_id, level_id, questions_json) VALUES (?, ?, ?, ?)",
                (quiz_data.quiz_id, session_id, level_id, quiz_data.model_dump_json())
            )

        return quiz_data

    except Exception as e:
        logger.error(f"Quiz start error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/respond")
async def respond_to_quiz(submission: ZaynAnswerSubmission, user_id: str = Depends(get_current_user_id)):
    """
    Records a learner's response to a single quiz question.
    """
    try:
        # Verify ownership
        with get_user_db() as user_db:
            session = user_db.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (submission.session_id, user_id)
            ).fetchone()
            if not session:
                raise HTTPException(status_code=403, detail="Unauthorized session access")

        # Record response
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT INTO quiz_responses (response_id, quiz_id, question_id, user_answer, response_time_seconds, is_timeout) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), submission.quiz_id, submission.question_id, submission.answer, submission.response_time_seconds, submission.is_timeout)
            )

        return {"status": "recorded"}

    except Exception as e:
        logger.error(f"Quiz response error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

from backend.services.orchestration_service import OrchestrationService

@router.post("/complete")
async def complete_quiz(session_id: str, quiz_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Signals completion of the quiz and marks it as completed in DB.
    """
    try:
        with get_clario_ai_db() as ai_db:
            # Verify quiz exists and belongs to session
            quiz = ai_db.execute(
                "SELECT 1 FROM quizzes WHERE quiz_id = ? AND session_id = ?",
                (quiz_id, session_id)
            ).fetchone()
            if not quiz:
                raise HTTPException(status_code=404, detail="Quiz not found")

            ai_db.execute(
                "UPDATE quizzes SET status = 'COMPLETED' WHERE quiz_id = ?",
                (quiz_id,)
            )

            # Check if active orchestration run exists and transition state
            try:
                run = ai_db.execute(
                    "SELECT id, current_stage FROM orchestration_runs WHERE session_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                    (session_id,)
                ).fetchone()
                if run and run["current_stage"] == "ZAYN_QUIZ":
                    OrchestrationService.transition_state(run["id"], user_id, "QUIZ_COMPLETED")

                OrchestrationService.record_event(session_id, "QUIZ_COMPLETED", {
                    "quiz_id": quiz_id
                })
            except Exception as orch_err:
                logger.warning(f"Orchestration transition warning (non-fatal): {orch_err}")

        return {"status": "quiz_completed"}

    except Exception as e:
        logger.error(f"Quiz completion error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
