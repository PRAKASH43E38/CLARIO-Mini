import logging
import json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
import uuid

from backend.database.connection import get_clario_ai_db, get_user_db
from backend.schemas.contracts import (
    ElaraEvaluationRequest,
    ElaraEvaluationResponse,
    AgentTask,
    AgentResult
)
from backend.agents.elara.agent import elara_agent
from backend.services.evaluation_interface import evaluation_interface
from backend.auth.session import get_current_user_id

from backend.services.orchestration_service import OrchestrationService

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])
logger = logging.getLogger(__name__)

@router.post("/levels/{level_id}")
async def evaluate_level(
    level_id: str,
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Triggers Elara to evaluate a level based on collected evidence.
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

        # 2. Verify quiz completion (Required evidence)
        with get_clario_ai_db() as ai_db:
            quiz = ai_db.execute(
                "SELECT status FROM quizzes WHERE session_id = ? AND level_id = ?",
                (session_id, level_id)
            ).fetchone()
            if not quiz or quiz["status"] != 'COMPLETED':
                raise HTTPException(
                    status_code=400,
                    detail="Cannot evaluate level: Quiz is not completed."
                )

        # 3. Gather evidence bundle via controlled interface
        evidence_bundle = evaluation_interface.get_evidence_bundle(session_id, level_id, user_id)

        # 4. Prepare Elara request
        request_data = {
            **evidence_bundle,
            "mira_evidence": evidence_bundle["mira_evidence"],
            "ayan_evidence": evidence_bundle["ayan_evidence"],
            "kira_evidence": evidence_bundle["kira_evidence"],
            "zayn_evidence": evidence_bundle["zayn_evidence"],
        }

        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_name="elara",
            session_id=session_id,
            instruction="Perform a comprehensive, objective evaluation of the learner's mastery.",
            input_data=request_data
        )

        # 5. Call Elara
        result = await elara_agent.process_task(task)

        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error_message)

        evaluation_data = ElaraEvaluationResponse(**result.output_data)

        # 6. Persist evaluation to DB
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                """
                INSERT INTO elara_evaluations
                (evaluation_id, session_id, level_id, overall_evaluation, global_strengths, global_weaknesses, evidence_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_data.evaluation_id,
                    evaluation_data.session_id,
                    evaluation_data.level_id,
                    evaluation_data.overall_evaluation,
                    json.dumps(evaluation_data.global_strengths),
                    json.dumps(evaluation_data.global_weaknesses),
                    evaluation_data.evidence_summary
                )
            )

            # Persist per-concept evaluations
            for concept_eval in evaluation_data.concept_evaluations:
                ai_db.execute(
                    """
                    INSERT INTO concept_evaluations
                    (concept_eval_id, evaluation_id, concept_name, understanding, reasoning, application, assessment, mastery_score, strengths, weaknesses, mistakes, evidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        evaluation_data.evaluation_id,
                        concept_eval.concept,
                        concept_eval.understanding,
                        concept_eval.reasoning,
                        concept_eval.application,
                        concept_eval.assessment,
                        concept_eval.mastery_score,
                        json.dumps(concept_eval.strengths),
                        json.dumps(concept_eval.weaknesses),
                        json.dumps(concept_eval.mistakes),
                        json.dumps(concept_eval.evidence)
                    )
                )

        # 7. Orchestration integration: transition to EVALUATION_COMPLETED if active run exists
        try:
            with get_clario_ai_db() as ai_db:
                run = ai_db.execute(
                    "SELECT id, current_stage FROM orchestration_runs WHERE session_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                    (session_id,)
                ).fetchone()
                if run:
                    if run["current_stage"] == "QUIZ_COMPLETED":
                        OrchestrationService.transition_state(run["id"], user_id, "ELARA_EVALUATION")
                        OrchestrationService.transition_state(run["id"], user_id, "EVALUATION_COMPLETED")
                    elif run["current_stage"] == "ELARA_EVALUATION":
                        OrchestrationService.transition_state(run["id"], user_id, "EVALUATION_COMPLETED")

            OrchestrationService.record_event(session_id, "EVALUATION_COMPLETED", {
                "evaluation_id": evaluation_data.evaluation_id,
                "level_id": level_id
            })
        except Exception as orch_err:
            logger.warning(f"Orchestration transition warning (non-fatal): {orch_err}")

        return evaluation_data

    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/levels/{level_id}")
async def get_level_evaluation(
    level_id: str,
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves the most recent Elara evaluation for a given level and session.
    """
    try:
        # Verify session ownership
        with get_user_db() as user_db:
            session = user_db.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()
            if not session:
                raise HTTPException(status_code=403, detail="Session not found or ownership mismatch")

        with get_clario_ai_db() as ai_db:
            eval_row = ai_db.execute(
                """
                SELECT * FROM elara_evaluations
                WHERE session_id = ? AND level_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (session_id, level_id)
            ).fetchone()

            if not eval_row:
                raise HTTPException(status_code=404, detail="No evaluation found for this level")

            concept_rows = ai_db.execute(
                "SELECT * FROM concept_evaluations WHERE evaluation_id = ?",
                (eval_row["evaluation_id"],)
            ).fetchall()

            concepts = []
            for cr in concept_rows:
                concepts.append({
                    "concept": cr["concept_name"],
                    "understanding": cr["understanding"],
                    "reasoning": cr["reasoning"],
                    "application": cr["application"],
                    "assessment": cr["assessment"],
                    "mastery_score": cr["mastery_score"],
                    "strengths": json.loads(cr["strengths"]) if cr["strengths"] else [],
                    "weaknesses": json.loads(cr["weaknesses"]) if cr["weaknesses"] else [],
                    "mistakes": json.loads(cr["mistakes"]) if cr["mistakes"] else [],
                    "evidence": json.loads(cr["evidence"]) if cr["evidence"] else []
                })

            return {
                "evaluation_id": eval_row["evaluation_id"],
                "session_id": eval_row["session_id"],
                "level_id": eval_row["level_id"],
                "overall_evaluation": eval_row["overall_evaluation"],
                "concept_evaluations": concepts,
                "global_strengths": json.loads(eval_row["global_strengths"]) if eval_row["global_strengths"] else [],
                "global_weaknesses": json.loads(eval_row["global_weaknesses"]) if eval_row["global_weaknesses"] else [],
                "evidence_summary": eval_row["evidence_summary"]
            }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error fetching evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{evaluation_id}")
async def get_evaluation_by_id(
    evaluation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves a specific evaluation by evaluation_id.
    """
    try:
        with get_clario_ai_db() as ai_db:
            eval_row = ai_db.execute(
                "SELECT * FROM elara_evaluations WHERE evaluation_id = ?",
                (evaluation_id,)
            ).fetchone()

            if not eval_row:
                raise HTTPException(status_code=404, detail="Evaluation not found")

            # Verify session ownership
            with get_user_db() as user_db:
                session = user_db.execute(
                    "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                    (eval_row["session_id"], user_id)
                ).fetchone()
                if not session:
                    raise HTTPException(status_code=403, detail="Unauthorized access to evaluation")

            concept_rows = ai_db.execute(
                "SELECT * FROM concept_evaluations WHERE evaluation_id = ?",
                (evaluation_id,)
            ).fetchall()

            concepts = []
            for cr in concept_rows:
                concepts.append({
                    "concept": cr["concept_name"],
                    "understanding": cr["understanding"],
                    "reasoning": cr["reasoning"],
                    "application": cr["application"],
                    "assessment": cr["assessment"],
                    "mastery_score": cr["mastery_score"],
                    "strengths": json.loads(cr["strengths"]) if cr["strengths"] else [],
                    "weaknesses": json.loads(cr["weaknesses"]) if cr["weaknesses"] else [],
                    "mistakes": json.loads(cr["mistakes"]) if cr["mistakes"] else [],
                    "evidence": json.loads(cr["evidence"]) if cr["evidence"] else []
                })

            return {
                "evaluation_id": eval_row["evaluation_id"],
                "session_id": eval_row["session_id"],
                "level_id": eval_row["level_id"],
                "overall_evaluation": eval_row["overall_evaluation"],
                "concept_evaluations": concepts,
                "global_strengths": json.loads(eval_row["global_strengths"]) if eval_row["global_strengths"] else [],
                "global_weaknesses": json.loads(eval_row["global_weaknesses"]) if eval_row["global_weaknesses"] else [],
                "evidence_summary": eval_row["evidence_summary"]
            }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error fetching evaluation by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

