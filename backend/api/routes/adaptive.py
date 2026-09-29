import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.auth.session import get_current_user_id
from backend.database.connection import get_user_db
from backend.services.adaptive_decision_service import adaptive_decision_service

router = APIRouter(prefix="/adaptive", tags=["Adaptive Decisions"])
logger = logging.getLogger(__name__)


class AdaptiveEvaluateRequest(BaseModel):
    session_id: Optional[str] = None
    force: bool = False


class AdaptiveRemediateRequest(BaseModel):
    session_id: Optional[str] = None
    concept: Optional[str] = None


@router.post("/evaluate/{level_id}")
async def evaluate_adaptive_decision(
    level_id: str,
    session_id: Optional[str] = Query(None),
    payload: Optional[AdaptiveEvaluateRequest] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Triggers CLARIO-AI to analyze Elara's evaluation deterministically and decide WHAT HAPPENS NEXT.
    Supports concept isolation, concept-specific difficulty changes, level completion, and remediation.
    """
    try:
        actual_session_id = session_id or (payload.session_id if payload else None)
        force = payload.force if payload else False

        if not actual_session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        # Verify session ownership
        with get_user_db() as u_db:
            session = u_db.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (actual_session_id, user_id)
            ).fetchone()
            if not session:
                raise HTTPException(status_code=403, detail="Session not found or ownership mismatch")

        result = adaptive_decision_service.make_decision(
            session_id=actual_session_id,
            level_id=level_id,
            user_id=user_id,
            force_reevaluate=force
        )

        return result

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"Adaptive decision validation: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Adaptive decision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decision/{level_id}")
async def get_adaptive_decision(
    level_id: str,
    session_id: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves the active adaptive decision, per-concept performances, and any struggle intervention signals.
    """
    try:
        with get_user_db() as u_db:
            session = u_db.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()
            if not session:
                raise HTTPException(status_code=403, detail="Session not found or ownership mismatch")

        # Fetch latest decision from DB
        decision_data = adaptive_decision_service._get_existing_decision(session_id, level_id, "")
        concept_perfs = adaptive_decision_service.get_concept_performances(session_id, level_id)
        struggle = adaptive_decision_service.detect_meaningful_struggle(session_id, level_id)

        if not decision_data and not concept_perfs:
            raise HTTPException(status_code=404, detail="No adaptive decision found for this level")

        return {
            "decision": decision_data,
            "concept_performances": [cp.model_dump() for cp in concept_perfs],
            "struggle_intervention": struggle
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching adaptive decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remediate/{level_id}")
async def trigger_remediation(
    level_id: str,
    session_id: Optional[str] = Query(None),
    concept: Optional[str] = Query(None),
    payload: Optional[AdaptiveRemediateRequest] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Initiates targeted remediation for ONLY the weak concept using a differentiated pedagogical
    approach and new retest task. Strong concepts remain completely untouched.
    """
    try:
        actual_session_id = session_id or (payload.session_id if payload else None)
        target_concept = concept or (payload.concept if payload else None)

        if not actual_session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        # Verify session ownership
        with get_user_db() as u_db:
            session = u_db.execute(
                "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
                (actual_session_id, user_id)
            ).fetchone()
            if not session:
                raise HTTPException(status_code=403, detail="Session not found or ownership mismatch")

        remediation_pkg = adaptive_decision_service.remediate_concept(
            session_id=actual_session_id,
            level_id=level_id,
            user_id=user_id,
            concept=target_concept
        )

        return remediation_pkg

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"Remediation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Remediation failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))
