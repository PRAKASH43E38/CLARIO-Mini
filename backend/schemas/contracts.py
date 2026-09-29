from datetime import datetime, timezone
import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


MindAnswer = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("password")
    @classmethod
    def limit_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes.")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value


class MindProfileInput(BaseModel):
    answers: list[MindAnswer] = Field(min_length=5, max_length=5)


class UserProfileResponse(BaseModel):
    user_id: str
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class AuthResponse(UserProfileResponse):
    mind_profile_completed: bool


class MindProfileResponse(BaseModel):
    user_id: str
    answers: list[MindAnswer] = Field(min_length=0, max_length=5)
    completed: bool
    updated_at: datetime | None = None


class UserProfile(BaseModel):
    """User identity and personal profile baseline."""
    user_id: str
    email: str
    name: str | None = None
    display_name: str | None = None
    learning_goals: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None


class MindProfile(BaseModel):
    """Cognitive and learning preference profile for adaptive personalization."""
    user_id: str
    answers: list[MindAnswer] | None = Field(default=None, min_length=5, max_length=5)
    updated_at: datetime | None = None
    learning_style: str | None = None
    pace_preference: str | None = None
    strengths: list[str] = Field(default_factory=list)
    growth_areas: list[str] = Field(default_factory=list)
    prior_knowledge_level: str = "beginner"


SessionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class SessionInputs(BaseModel):
    """The four required, session-specific learning inputs."""
    model_config = ConfigDict(extra="forbid")

    task: SessionText
    goal: SessionText
    learner_state: SessionText
    interest: SessionText


class SessionInputsResponse(SessionInputs):
    """Saved four-input record belonging to one learning session."""
    session_id: str
    updated_at: datetime


class LearningSession(BaseModel):
    """Lifecycle and ownership metadata for an independent learning session."""
    session_id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class LearningSessionList(BaseModel):
    sessions: list[LearningSession]


class RoadmapLevel(BaseModel):
    """A milestone level within a structured learning roadmap."""
    level_number: int
    title: str
    description: str
    key_concepts: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int | None = None


class Roadmap(BaseModel):
    """Structured curriculum / roadmap generated for the session."""
    session_id: str
    topic: str
    levels: list[RoadmapLevel] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class ConceptEvaluation(BaseModel):
    """Granular evaluation of a single concept within a level."""
    concept: str
    understanding: str  # Qualitative analysis of core grasp
    reasoning: str       # Analysis of logical deduction/synthesis
    application: str     # Analysis of real-world transfer
    assessment: str     # Quiz performance on this concept
    mastery_score: float = Field(description="Estimated mastery from 0.0 to 1.0")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

class ElaraEvaluationResponse(BaseModel):
    """Structured level-wide evaluation from Elara."""
    evaluation_id: str
    session_id: str
    level_id: str
    overall_evaluation: str
    concept_evaluations: list[ConceptEvaluation]
    global_strengths: list[str] = Field(default_factory=list)
    global_weaknesses: list[str] = Field(default_factory=list)
    evidence_summary: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ElaraEvaluationRequest(BaseModel):
    """Context and evidence bundle required for Elara to evaluate a level."""
    session_id: str
    user_id: str
    level_id: str
    objective: str
    concepts: list[str]
    # Evidence Bundles
    mira_evidence: dict[str, Any]
    ayan_evidence: dict[str, Any]
    kira_evidence: dict[str, Any]
    zayn_evidence: dict[str, Any]
    learner_profile: dict[str, Any]

class CALAResult(BaseModel):
    """
    CLARIO Adaptive Learner Algorithm result.
    Inferred analysis based ONLY on Mind Profile and Session Inputs.
    """
    cala_result_id: str
    user_id: str
    session_id: str
    learner_level: str
    confidence_signal: str
    sentiment_signal: str
    difficulty_signals: str
    learning_preferences: str
    motivation_signals: str
    recommended_starting_level: int
    recommended_learning_strategy: str
    initial_weakness_signals: str
    reasoning_summary: str
    misconception_signals: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MiraTeachingRequest(BaseModel):
    """Context required for Mira to generate personalized teaching content."""
    task_id: str
    session_id: str
    user_id: str
    level_id: str
    level_objective: str
    concepts: list[str]
    # Context from Nova (passed via the controlled interface)
    research_context: dict[str, Any]
    # Personalization context
    mind_profile: dict[str, Any]
    cala_signals: dict[str, Any]
    session_inputs: dict[str, Any]

class MiraTeachingResponse(BaseModel):
    """Structured pedagogical content generated by Mira."""
    task_id: str
    session_id: str
    level_id: str
    lesson_content: str
    conceptual_breakdown: list[dict[str, str]]
    analogies: list[dict[str, str]]
    adaptation_rationale: str
    suggested_pacing: str
    reference_urls: list[str] = Field(default_factory=list)
    interview_url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TeachingInteraction(BaseModel):
    """Records a specific interaction between the learner and Mira."""
    interaction_id: str
    session_id: str
    level_id: str
    user_input: str | None = None
    mira_response: str
    interaction_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NovaResearchRequest(BaseModel):
    """Context required for Nova to conduct targeted web research."""
    request_id: str
    session_id: str
    level_id: str
    level_objective: str
    concepts: list[str]
    learning_goal: str = "Master concepts"
    learner_level: str = "beginner"
    relevant_mind_profile: dict[str, Any] = Field(default_factory=dict)
    relevant_session_inputs: dict[str, Any] = Field(default_factory=dict)
    interest_context: str = "General"
    research_requirements: str = "Comprehensive overview"

class ResearchSource(BaseModel):
    """Metadata for a single retrieved web source."""
    url: str
    title: str
    domain: str
    snippet: str
    content: str | None = None
    relevance_score: float = 1.0
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NovaResearchResult(BaseModel):
    """Structured output of a Nova research run."""
    request_id: str
    query_set: list[str]
    sources: list[ResearchSource]
    research_summary: str
    key_knowledge_facts: list[str]
    sufficiency_signal: bool = True
    status: str = "completed"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentTask(BaseModel):
    """Task assigned by the CLARIO-AI orchestrator to a specialized agent."""
    task_id: str
    agent_name: str
    session_id: str
    instruction: str
    input_data: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Standardized result returned by a specialized agent back to CLARIO-AI."""
    task_id: str
    agent_name: str
    session_id: str
    status: str = "success"
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class ElaraEvaluation(BaseModel):
    """Objective assessment and critique performed by Elara."""
    evaluation_id: str
    session_id: str
    overall_score: float = 0.0
    clarity_rating: float = 0.0
    strengths_observed: list[str] = Field(default_factory=list)
    weaknesses_observed: list[str] = Field(default_factory=list)
    critique: str | None = None


class AdaptiveDecision(BaseModel):
    """Routing and pedagogical decision made by CLARIO-AI."""
    decision_id: str
    session_id: str
    level_id: str
    decision_type: Literal[
        "CONTINUE",
        "RETEACH",
        "RETEST",
        "REDUCE_DIFFICULTY",
        "INCREASE_DIFFICULTY",
        "COMPLETE_LEVEL",
        "UNLOCK_NEXT_LEVEL",
        "COMPLETE_GOAL"
    ]
    reason: str
    target_concept: str | None = None
    target_agent: str | None = None
    old_difficulty: str | None = None
    new_difficulty: str | None = None
    mastery_score: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Compatibility fields
    next_agent: str | None = None
    reasoning: str | None = None


class ConceptPerformance(BaseModel):
    """Learner's quantified mastery of an individual concept."""
    session_id: str
    level_id: str
    concept: str
    understanding: str | None = None
    reasoning: str | None = None
    application: str | None = None
    assessment: str | None = None
    mastery_score: float = 0.0
    difficulty: str = "Medium"
    attempts: int = 1
    mistakes: list[str] = Field(default_factory=list)
    status: Literal["learning", "mastered", "remediating", "unexplored"] = "learning"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Compatibility fields
    concept_id: str | None = None
    concept_name: str | None = None
    attempts_count: int | None = None


class LearningEvent(BaseModel):
    """Discrete learning telemetry event recorded in session history."""
    event_id: str
    session_id: str
    event_type: str
    agent_source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AyanQuestion(BaseModel):
    """A single critical thinking question generated by Ayan."""
    question_id: str
    text: str
    type: Literal["reasoning", "explanation", "comparison", "cause_effect", "application", "misconception"]
    target_concept: str
    ideal_answer_guideline: str

class AyanThinkingRequest(BaseModel):
    """Context required for Ayan to generate critical thinking questions."""
    session_id: str
    user_id: str
    level_id: str
    objective: str
    concepts: list[str]
    mira_context: dict[str, Any]
    nova_knowledge: dict[str, Any]
    learner_profile: dict[str, Any]

class AyanThinkingResponse(BaseModel):
    """Set of critical thinking questions generated by Ayan."""
    session_id: str
    level_id: str
    questions: list[AyanQuestion]
    challenge_rationale: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AyanResponseSubmission(BaseModel):
    """Learner's submission for a specific thinking question."""
    session_id: str
    question_id: str
    user_answer: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KiraScenario(BaseModel):
    """A practical application scenario generated by Kira."""
    scenario_id: str
    text: str
    target_concept: str
    ideal_response_guideline: str

class KiraApplicationRequest(BaseModel):
    """Context required for Kira to generate application scenarios."""
    session_id: str
    user_id: str
    level_id: str
    objective: str
    concepts: list[str]
    ayan_context: dict[str, Any]
    mira_context: dict[str, Any]
    nova_knowledge: dict[str, Any]
    learner_profile: dict[str, Any]

class KiraApplicationResponse(BaseModel):
    """Set of practical application scenarios generated by Kira."""
    session_id: str
    level_id: str
    scenarios: list[KiraScenario]
    application_rationale: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KiraResponseSubmission(BaseModel):
    """Learner's submission for a specific application scenario."""
    session_id: str
    scenario_id: str
    user_response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ZaynQuestion(BaseModel):
    """A single quiz question generated by Zayn."""
    question_id: str
    concept: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    question_type: str
    question_text: str
    expected_answer: str
    time_limit_seconds: int
    order: int

class ZaynQuizRequest(BaseModel):
    """Context required for Zayn to generate a level assessment."""
    session_id: str
    user_id: str
    level_id: str
    objective: str
    concepts: list[str]
    mira_context: dict[str, Any]
    ayan_context: dict[str, Any]
    kira_context: dict[str, Any]
    nova_knowledge: dict[str, Any]
    learner_profile: dict[str, Any]

class ZaynQuizResponse(BaseModel):
    """The generated 10-question assessment from Zayn."""
    quiz_id: str
    session_id: str
    level_id: str
    questions: list[ZaynQuestion]
    quiz_rationale: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ZaynAnswerSubmission(BaseModel):
    """Learner's submission for a specific quiz question."""
    session_id: str
    quiz_id: str
    question_id: str
    answer: str
    response_time_seconds: float
    is_timeout: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
