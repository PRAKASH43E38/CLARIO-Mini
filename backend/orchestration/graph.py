from typing import TypedDict, Any
from backend.core.config import settings
from contextlib import nullcontext
from backend.schemas.contracts import AgentTask, AgentResult

try:
    from langgraph.graph import StateGraph, START, END
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False

try:
    from langsmith import Client, tracing_context
except ImportError:
    Client = None
    tracing_context = None


class ClarioOrchestrationState(TypedDict):
    """
    Typed state for the CLARIO-AI orchestrator.
    Contains only information necessary for routing and state transitions.
    """
    session_id: str
    user_id: str
    current_stage: str
    current_level_id: str | None
    roadmap_id: str | None
    agent_outputs: dict[str, Any]
    orchestration_run_id: str
    is_completed: bool
    adaptive_decision: str


# Keep the old name as an alias for backward compatibility
OrchestrationState = ClarioOrchestrationState


async def transition_to_cala(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "CALA_PROCESSED"}

async def transition_to_roadmap(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "ROADMAP_CREATED"}

async def transition_to_unlock(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "LEVEL_UNLOCKED"}

async def transition_to_entry(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "LEVEL_ENTERED"}

async def transition_to_research_ready(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "READY_FOR_LEVEL_RESEARCH"}

async def transition_to_ayan_thinking(state: ClarioOrchestrationState) -> dict:
    """Transition to Ayan's critical thinking challenge phase."""
    return {"current_stage": "AYAN_THINKING"}

async def transition_to_thinking_completed(state: ClarioOrchestrationState) -> dict:
    """Transition after learner has submitted all thinking responses."""
    return {"current_stage": "THINKING_COMPLETED"}

async def transition_to_kira_application(state: ClarioOrchestrationState) -> dict:
    """Transition to Kira's real-world application phase."""
    return {"current_stage": "KIRA_APPLICATION"}

async def transition_to_application_completed(state: ClarioOrchestrationState) -> dict:
    """Transition after learner has completed application tasks."""
    return {"current_stage": "APPLICATION_COMPLETED"}


async def transition_to_zayn_quiz(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "ZAYN_QUIZ"}

async def transition_to_quiz_completed(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "QUIZ_COMPLETED"}

async def transition_to_elara_evaluation(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "ELARA_EVALUATION"}

async def transition_to_evaluation_completed(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "EVALUATION_COMPLETED"}

async def transition_to_adaptive_decision(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "ADAPTIVE_DECISION"}

async def transition_to_complete_level(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "COMPLETE_LEVEL"}

async def transition_to_unlock_next_level(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "UNLOCK_NEXT_LEVEL"}

async def transition_to_remediate(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "REMEDIATE"}

async def transition_to_reduce_difficulty(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "REDUCE_DIFFICULTY"}

async def transition_to_mira_reteach(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "MIRA_RETEACH"}

async def transition_to_targeted_retest(state: ClarioOrchestrationState) -> dict:
    return {"current_stage": "TARGETED_RETEST"}


def route_adaptive_decision(state: ClarioOrchestrationState) -> str:
    """Route using the decision already made by CLARIO-AI."""
    decision = state.get("adaptive_decision", "COMPLETE_LEVEL").upper()
    if decision in {"REMEDIATE", "RETEACH", "REDUCE_DIFFICULTY", "RETEST"}:
        return "remediate"
    return "complete_level"


def build_clario_orchestration_graph():
    """Build the LangGraph orchestration graph if langgraph is available."""
    if not _LANGGRAPH_AVAILABLE:
        return None

    workflow = StateGraph(ClarioOrchestrationState)

    workflow.add_node("cala", transition_to_cala)
    workflow.add_node("roadmap", transition_to_roadmap)
    workflow.add_node("unlock", transition_to_unlock)
    workflow.add_node("entry", transition_to_entry)
    workflow.add_node("research_ready", transition_to_research_ready)
    workflow.add_node("ayan_thinking", transition_to_ayan_thinking)
    workflow.add_node("thinking_completed", transition_to_thinking_completed)
    workflow.add_node("kira_application", transition_to_kira_application)
    workflow.add_node("application_completed", transition_to_application_completed)
    workflow.add_node("zayn_quiz", transition_to_zayn_quiz)
    workflow.add_node("quiz_completed", transition_to_quiz_completed)
    workflow.add_node("elara_evaluation", transition_to_elara_evaluation)
    workflow.add_node("evaluation_completed", transition_to_evaluation_completed)
    workflow.add_node("adaptive_decision", transition_to_adaptive_decision)
    workflow.add_node("complete_level", transition_to_complete_level)
    workflow.add_node("unlock_next_level", transition_to_unlock_next_level)
    workflow.add_node("remediate", transition_to_remediate)
    workflow.add_node("reduce_difficulty", transition_to_reduce_difficulty)
    workflow.add_node("mira_reteach", transition_to_mira_reteach)
    workflow.add_node("targeted_retest", transition_to_targeted_retest)

    workflow.add_edge(START, "cala")
    workflow.add_edge("cala", "roadmap")
    workflow.add_edge("roadmap", "unlock")
    workflow.add_edge("unlock", "entry")
    workflow.add_edge("entry", "research_ready")
    workflow.add_edge("research_ready", "ayan_thinking")
    workflow.add_edge("ayan_thinking", "thinking_completed")
    workflow.add_edge("thinking_completed", "kira_application")
    workflow.add_edge("kira_application", "application_completed")
    workflow.add_edge("application_completed", "zayn_quiz")
    workflow.add_edge("zayn_quiz", "quiz_completed")
    workflow.add_edge("quiz_completed", "elara_evaluation")
    workflow.add_edge("elara_evaluation", "evaluation_completed")
    workflow.add_edge("evaluation_completed", "adaptive_decision")

    # Branch A: Mastery achieved
    workflow.add_conditional_edges(
        "adaptive_decision",
        route_adaptive_decision,
        {"complete_level": "complete_level", "remediate": "remediate"},
    )
    workflow.add_edge("complete_level", "unlock_next_level")
    workflow.add_edge("unlock_next_level", END)

    # Branch B: Remediation required
    workflow.add_edge("adaptive_decision", "remediate")
    workflow.add_edge("remediate", "reduce_difficulty")
    workflow.add_edge("reduce_difficulty", "mira_reteach")
    workflow.add_edge("mira_reteach", "targeted_retest")
    workflow.add_edge("targeted_retest", "elara_evaluation")

    return workflow.compile()


def langsmith_config(state: ClarioOrchestrationState) -> dict[str, Any]:
    """Return opt-in tracing metadata for a LangGraph invocation."""
    config: dict[str, Any] = {
        "run_name": "clario_learning_workflow",
        "tags": ["clario", "orchestration"],
        "metadata": {
            "session_id": state["session_id"],
            "orchestration_run_id": state["orchestration_run_id"],
        },
    }
    return config


async def invoke_clario_graph(state: ClarioOrchestrationState) -> dict[str, Any]:
    """Invoke the CLARIO-AI-owned workflow through its compiled LangGraph."""
    graph = build_clario_orchestration_graph()
    if graph is None:
        raise RuntimeError("LangGraph is required. Install backend/requirements.txt.")
    config = langsmith_config(state)
    tracing_enabled = bool(
        settings.LANGSMITH_TRACING
        and settings.LANGSMITH_API_KEY
        and Client is not None
        and tracing_context is not None
    )
    if not tracing_enabled:
        return await graph.ainvoke(state, config=config)

    client = Client(
        api_key=settings.LANGSMITH_API_KEY,
        api_url=settings.LANGSMITH_ENDPOINT,
    )
    with tracing_context(
        enabled=True,
        project_name=settings.LANGSMITH_PROJECT,
        client=client,
    ):
        return await graph.ainvoke(state, config=config)


# Build the graph; will be None if langgraph is not installed
clario_graph = build_clario_orchestration_graph()
