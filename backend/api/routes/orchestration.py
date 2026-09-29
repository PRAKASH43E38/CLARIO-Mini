from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth.session import get_current_user_id
from backend.services.orchestration_service import OrchestrationService
from backend.services.session_service import SessionService
from backend.services.cala_service import CALAService
from backend.services.roadmap_service import RoadmapService
from backend.services.end_to_end_loop_service import end_to_end_loop_service
from backend.database.connection import get_user_db, get_clario_ai_db

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


class LoopInitializeRequest(BaseModel):
    session_id: Optional[str] = None


class LoopRunLevelRequest(BaseModel):
    session_id: str
    simulated_answers: Optional[Dict[str, Any]] = None


class LoopRemediateRequest(BaseModel):
    session_id: str
    concept: Optional[str] = None
    simulated_retest_score: Optional[float] = 0.92


@router.post("/initialize")
async def initialize_orchestration(user_id: str = Depends(get_current_user_id)):
    """
    Starts the orchestration for the user.
    Requires an active session in READY_FOR_CALA state.
    """
    # 1. Find the most recent READY_FOR_CALA session
    with get_user_db() as conn:
        session = conn.execute(
            "SELECT session_id FROM learning_sessions WHERE user_id = ? AND status = 'READY_FOR_CALA' ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()

    if not session:
        raise HTTPException(status_code=400, detail="No session ready for orchestration.")

    session_id = session["session_id"]

    # 2. Create orchestration run
    run_id = OrchestrationService.create_orchestration_state(session_id, user_id)

    # 3. Move through initial deterministic stages
    OrchestrationService.transition_state(run_id, user_id, "CALA_PROCESSED")
    OrchestrationService.transition_state(run_id, user_id, "ROADMAP_CREATED")

    return {"run_id": run_id, "status": "ROADMAP_CREATED"}


@router.post("/enter-level/{level_id}")
async def enter_level(level_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Enters a specific roadmap level.
    Validates that the level is unlocked and the user owns the session.
    """
    # 1. Verify level exists and is unlocked
    with get_clario_ai_db() as conn:
        level = conn.execute(
            "SELECT roadmap_id, status FROM roadmap_levels WHERE level_id = ?",
            (level_id,)
        ).fetchone()

        if not level:
            raise HTTPException(status_code=404, detail="Level not found.")

        if level["status"] != 'UNLOCKED':
            raise HTTPException(status_code=403, detail="Level is currently locked.")

        # Verify session ownership
        roadmap = conn.execute(
            "SELECT session_id FROM roadmaps WHERE roadmap_id = ?",
            (level["roadmap_id"],)
        ).fetchone()

        session_id = roadmap["session_id"]

    # Check user ownership in user.db
    with get_user_db() as user_conn:
        owner = user_conn.execute(
            "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        ).fetchone()
        if not owner:
            raise HTTPException(status_code=403, detail="Access denied to this session.")

    return {"status": "READY_FOR_LEVEL_RESEARCH", "level_id": level_id}


# =============================================================================
# PHASE 13: Complete End-to-End Adaptive Learning Loop Routes
# =============================================================================

@router.post("/loop/initialize")
async def loop_initialize(payload: Optional[LoopInitializeRequest] = None, user_id: str = Depends(get_current_user_id)):
    """
    Step: USER -> AUTH -> 5 MIND -> 4 SESSION INPUTS -> CALA -> ROADMAP -> CLARIO-AI -> LEVEL 1 UNLOCK
    Initializes the entire personalized journey for a ready session.
    """
    session_id = payload.session_id if payload and payload.session_id else None
    if not session_id:
        with get_user_db() as conn:
            sess = conn.execute(
                "SELECT session_id FROM learning_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            ).fetchone()
            if not sess:
                raise HTTPException(status_code=400, detail="No session found for this user.")
            session_id = sess["session_id"]

    try:
        return end_to_end_loop_service.initialize_journey(user_id=user_id, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/loop/enter-level/{level_id}")
async def loop_enter_level(level_id: str, session_id: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """
    Step: LEVEL ENTRY -> READY_FOR_LEVEL_RESEARCH
    """
    if not session_id:
        with get_clario_ai_db() as ai_conn:
            lvl = ai_conn.execute("SELECT roadmap_id FROM roadmap_levels WHERE level_id = ?", (level_id,)).fetchone()
            if lvl:
                rm = ai_conn.execute("SELECT session_id FROM roadmaps WHERE roadmap_id = ?", (lvl["roadmap_id"],)).fetchone()
                if rm:
                    session_id = rm["session_id"]
    if not session_id:
        raise HTTPException(status_code=404, detail="Session for level not found.")

    try:
        return end_to_end_loop_service.enter_level(user_id=user_id, session_id=session_id, level_id=level_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/loop/run-level/{level_id}")
async def loop_run_level(level_id: str, payload: LoopRunLevelRequest, user_id: str = Depends(get_current_user_id)):
    """
    Step: NOVA -> VALIDATED RESEARCH -> MIRA -> AYAN -> KIRA -> ZAYN -> ELARA -> CLARIO-AI DECISION
    Executes the entire multi-agent learning cycle for a level.
    """
    try:
        return await end_to_end_loop_service.execute_level_flow(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id,
            simulated_answers=payload.simulated_answers
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/loop/remediate-cycle/{level_id}")
async def loop_remediate_cycle(level_id: str, payload: LoopRemediateRequest, user_id: str = Depends(get_current_user_id)):
    """
    Step: REMEDIATION -> REDUCE_DIFFICULTY -> MIRA -> RETEST -> ELARA -> CLARIO-AI DECISION
    Executes a targeted differentiated reteaching and retest cycle for a struggling concept.
    """
    try:
        return await end_to_end_loop_service.execute_remediation_cycle(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id,
            concept=payload.concept,
            simulated_retest_score=payload.simulated_retest_score or 0.92
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/loop/status/{session_id}")
async def loop_status(session_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Retrieves complete live journey tracking status.
    """
    try:
        return end_to_end_loop_service.get_journey_status(user_id=user_id, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/loop/final-report/{session_id}")
async def loop_final_report(session_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Retrieves the comprehensive executive Final Learning Report for a completed goal.
    """
    try:
        return end_to_end_loop_service.get_or_create_final_report(user_id=user_id, session_id=session_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REAL INTERACTIVE MULTI-AGENT WORKFLOW ENDPOINTS (CLARIO-AI + 6 AGENTS)
# =============================================================================

class StepStartRequest(BaseModel):
    session_id: str

class StepMiraCompleteRequest(BaseModel):
    session_id: str
    response_text: Optional[str] = "I have understood the foundational concepts."

class StepAyanSubmitRequest(BaseModel):
    session_id: str
    challenge_id: str
    answers: Dict[str, str]

class StepKiraSubmitRequest(BaseModel):
    session_id: str
    scenario_id: str
    responses: Dict[str, str]

class StepZaynSubmitRequest(BaseModel):
    session_id: str
    quiz_id: str
    answers: list[Dict[str, Any]]


@router.post("/step/start/{level_id}")
async def step_start(level_id: str, payload: StepStartRequest, user_id: str = Depends(get_current_user_id)):
    """
    CLARIO-AI triggers Nova research with Tavily/preferred sources, then prompts Mira to teach concepts.
    Pauses at Mira for learner reading and interaction.
    """
    try:
        return await end_to_end_loop_service.start_interactive_level(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/mira-complete/{level_id}")
async def step_mira_complete(level_id: str, payload: StepMiraCompleteRequest, user_id: str = Depends(get_current_user_id)):
    """
    Learner completes reading/interacting with Mira.
    CLARIO-AI awards XP and triggers Ayan for Socratic critical thinking challenges.
    """
    try:
        return await end_to_end_loop_service.submit_mira_teaching(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id,
            response_text=payload.response_text or "Understood"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/ayan-submit/{level_id}")
async def step_ayan_submit(level_id: str, payload: StepAyanSubmitRequest, user_id: str = Depends(get_current_user_id)):
    """
    Learner submits critical thinking reasoning to Ayan.
    CLARIO-AI records responses, awards XP, and triggers Kira for real-world scenarios.
    """
    try:
        return await end_to_end_loop_service.submit_ayan_thinking(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id,
            challenge_id=payload.challenge_id,
            answers=payload.answers
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/kira-submit/{level_id}")
async def step_kira_submit(level_id: str, payload: StepKiraSubmitRequest, user_id: str = Depends(get_current_user_id)):
    """
    Learner submits practical solution to Kira.
    CLARIO-AI records responses, awards XP, and triggers Zayn for 10-question assessment (5 Easy, 3 Med, 2 Hard).
    """
    try:
        return await end_to_end_loop_service.submit_kira_application(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id,
            scenario_id=payload.scenario_id,
            responses=payload.responses
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/zayn-submit/{level_id}")
async def step_zayn_submit(level_id: str, payload: StepZaynSubmitRequest, user_id: str = Depends(get_current_user_id)):
    """
    Learner completes Zayn quiz.
    CLARIO-AI triggers Elara to evaluate evidence, then CLARIO-AI makes the adaptive decision.
    """
    try:
        return await end_to_end_loop_service.submit_zayn_quiz(
            user_id=user_id,
            session_id=payload.session_id,
            level_id=level_id,
            quiz_id=payload.quiz_id,
            answers=payload.answers
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/step/state/{level_id}")
async def step_state(level_id: str, session_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Retrieves the real live state of all 6 agents + CLARIO-AI for the workflow visualizer.
    """
    try:
        return end_to_end_loop_service.get_workflow_state(
            user_id=user_id,
            session_id=session_id,
            level_id=level_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



