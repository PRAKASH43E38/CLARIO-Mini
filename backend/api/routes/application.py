import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime, timezone

from backend.auth.session import get_current_user_id
from backend.database.connection import get_clario_ai_db, get_user_db
from backend.schemas.contracts import KiraApplicationResponse, KiraResponseSubmission, AgentTask
from backend.agents.kira.agent import kira_agent
from backend.services.research_interface import ResearchInterface
from backend.services.orchestration_service import orchestration_service

router = APIRouter(prefix="/application", tags=["application"])
logger = logging.getLogger(__name__)

@router.post("/start")
async def start_application_phase(
    payload: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
):
    """
    Triggers Kira to generate practical application scenarios for the current level.
    """
    session_id = payload.get("session_id")
    level_id = payload.get("level_id")

    if not session_id or not level_id:
        raise HTTPException(status_code=400, detail="session_id and level_id are required")

    # 1. Verify session ownership
    with get_user_db() as user_conn:
        session = user_conn.execute(
            "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=403, detail="Session does not belong to current user")

    # 2. Gather context for Kira
    with get_clario_ai_db() as ai_conn:
        # Fetch roadmap/level objective
        level_row = ai_conn.execute(
            "SELECT title, objective FROM roadmap_levels WHERE level_id = ?",
            (level_id,)
        ).fetchone()
        if not level_row:
            raise HTTPException(status_code=404, detail="Level not found")

        # Fetch Mira's teaching output
        teaching_row = ai_conn.execute(
            "SELECT response_payload_json FROM teaching_interactions WHERE level_id = ? ORDER BY timestamp DESC LIMIT 1",
            (level_id,)
        ).fetchone()
        mira_context = json.loads(teaching_row["response_payload_json"]) if teaching_row else {}

        # Fetch Ayan's challenge context
        ayan_row = ai_conn.execute(
            "SELECT questions_json FROM thinking_challenges WHERE level_id = ? ORDER BY created_at DESC LIMIT 1",
            (level_id,)
        ).fetchone()
        ayan_context = json.loads(ayan_row["questions_json"]) if ayan_row else {}

    # Fetch Nova knowledge via controlled interface
    nova_knowledge = ResearchInterface.get_research_context(level_id)

    # Gather Learner Profile (simplified)
    with get_user_db() as user_conn:
        profile_row = user_conn.execute(
            "SELECT answers_json FROM mind_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        learner_profile = json.loads(profile_row["answers_json"]) if profile_row else {}

    # 3. Construct Agent Task
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        agent_name="kira",
        session_id=session_id,
        instruction="Generate real-world application scenarios",
        input_data={
            "session_id": session_id,
            "user_id": user_id,
            "level_id": level_id,
            "objective": level_row["objective"],
            "concepts": [], # Should be fetched from level_concepts table
            "mira_context": mira_context,
            "ayan_context": ayan_context,
            "nova_knowledge": nova_knowledge,
            "learner_profile": learner_profile
        }
    )

    # 4. Execute Kira
    result = await kira_agent.process_task(task)
    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error_message)

    # 5. Persist the application set
    scenario_id = str(uuid.uuid4())
    response_data = result.output_data
    with get_clario_ai_db() as ai_conn:
        ai_conn.execute(
            "INSERT INTO application_scenarios (scenario_id, session_id, level_id, scenarios_json, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (scenario_id, session_id, level_id, json.dumps(response_data["scenarios"]), response_data["application_rationale"], datetime.now(timezone.utc).isoformat())
        )

    return {
        "scenario_id": scenario_id,
        "scenarios": response_data["scenarios"],
        "rationale": response_data["application_rationale"]
    }

@router.post("/respond")
async def respond_to_application(
    submission: KiraResponseSubmission,
    user_id: str = Depends(get_current_user_id)
):
    """
    Records the learner's response to a specific application scenario.
    """
    # 1. Verify ownership
    with get_user_db() as user_conn:
        session = user_conn.execute(
            "SELECT 1 FROM learning_sessions WHERE session_id = ? AND user_id = ?",
            (submission.session_id, user_id)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=403, detail="Session does not belong to current user")

    # 2. Verify scenario exists
    with get_clario_ai_db() as ai_conn:
        scenario = ai_conn.execute(
            "SELECT scenario_id FROM application_scenarios WHERE session_id = ? AND level_id = (SELECT level_id FROM application_scenarios WHERE session_id = ? LIMIT 1)",
            (submission.session_id, submission.session_id)
        ).fetchone()

        if not scenario:
            raise HTTPException(status_code=404, detail="No active application scenario found for this session")

    # 3. Persist response
    with get_clario_ai_db() as ai_conn:
        ai_conn.execute(
            "INSERT INTO application_responses (response_id, scenario_id, user_response, timestamp) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), scenario["scenario_id"], submission.user_response, datetime.now(timezone.utc).isoformat())
        )

    return {"status": "success", "message": "Application response recorded"}
