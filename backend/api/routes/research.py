from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth.session import get_current_user_id
from backend.schemas.contracts import NovaResearchRequest, NovaResearchResult
from backend.agents.nova.agent import NovaAgent
from backend.services.tavily_research_service import TavilyResearchService
from backend.database.connection import get_clario_ai_db
import uuid

router = APIRouter(prefix="/research", tags=["research"])

# Dependency for NovaAgent
def get_nova_agent():
    return NovaAgent(tavily_service=TavilyResearchService())

@router.post("/levels/{level_id}", response_model=NovaResearchResult)
async def research_level(
    level_id: str,
    user_id: str = Depends(get_current_user_id),
    nova_agent: NovaAgent = Depends(get_nova_agent)
):
    """
    Triggers Nova to conduct research for a specific roadmap level.
    """
    # 1. Fetch Level and Session context from DB
    with get_clario_ai_db() as conn:
        level = conn.execute(
            "SELECT roadmap_id, title, description FROM roadmap_levels WHERE level_id = ?",
            (level_id,)
        ).fetchone()

        if not level:
            raise HTTPException(status_code=404, detail="Level not found.")

        roadmap = conn.execute(
            "SELECT session_id, topic FROM roadmaps WHERE roadmap_id = ?",
            (level["roadmap_id"],)
        ).fetchone()

        session_id = roadmap["session_id"]

    # 2. Construct Research Request
    # In a full implementation, we'd fetch the Mind Profile and Session Inputs
    # For now, we use placeholders to satisfy the contract
    request = NovaResearchRequest(
        request_id=str(uuid.uuid4()),
        session_id=session_id,
        level_id=level_id,
        level_objective=level["description"],
        concepts=["General concept 1", "General concept 2"], # Should come from roadmap_levels.key_concepts
        learning_goal="Master the level objectives",
        learner_level="Intermediate",
        relevant_mind_profile={},
        relevant_session_inputs={},
        interest_context="General interest",
        research_requirements="Comprehensive overview with technical depth"
    )

    # 3. Execute Research
    try:
        result = await nova_agent.conduct_research(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research execution failed: {str(e)}"
        )
