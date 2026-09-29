import logging
from typing import Any, Dict, List
from datetime import datetime, timezone
import uuid

from backend.schemas.contracts import (
    ElaraEvaluationRequest,
    ElaraEvaluationResponse,
    ConceptEvaluation,
    AgentTask,
    AgentResult
)
from backend.providers.service import provider_service

logger = logging.getLogger(__name__)

class ElaraAgent:
    """
    ELARA: The Evaluation Agent.
    Responsible for objective evidence-based assessment of learner mastery
    across a level. Elara determines WHAT HAPPENED.
    """

    def __init__(self):
        self.name = "elara"
        self.role = "Evaluation Agent"

    async def process_task(self, task: AgentTask) -> AgentResult:
        """
        Analyzes the aggregated evidence bundle and produces a per-concept evaluation.
        """
        try:
            # Validate input
            request = ElaraEvaluationRequest(**task.input_data)

            # Generate the evaluation using the provider abstraction
            response = await self._generate_evaluation(request)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="success",
                output_data=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Elara processing error: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="error",
                error_message=str(e)
            )

    async def _generate_evaluation(self, request: ElaraEvaluationRequest) -> ElaraEvaluationResponse:
        """
        Constructs the evaluation prompt and calls the LLM provider.
        """
        prompt = self._build_prompt(request)

        # Use the system provider abstraction
        raw_response = await provider_service.generate_content(
            prompt=prompt,
            response_format=ElaraEvaluationResponse
        )

        # Ensure response is a Pydantic model
        if isinstance(raw_response, ElaraEvaluationResponse):
            return raw_response

        return ElaraEvaluationResponse(**raw_response)

    def _build_prompt(self, request: ElaraEvaluationRequest) -> str:
        """
        Constructs a specialized prompt for an objective, evidence-based evaluation.
        """
        prompt = f"""
        You are ELARA, the CLARIO Evaluation Agent. Your role is to act as an objective academic judge.
        Your goal is to evaluate the learner's mastery of the current level based ONLY on the provided evidence.

        LEVEL CONTEXT:
        - Objective: {request.objective}
        - Concepts: {', '.join(request.concepts)}
        - Learner Profile: {request.learner_profile}

        EVIDENCE BUNDLE:
        1. Teaching Evidence (Mira): {request.mira_evidence}
        2. Critical Thinking Evidence (Ayan): {request.ayan_evidence}
        3. Application Evidence (Kira): {request.kira_evidence}
        4. Assessment Evidence (Zayn): {request.zayn_evidence}

        EVALUATION MANDATE:
        - Determine WHAT HAPPENED. State facts based on the evidence.
        - For each concept, analyze understanding, reasoning, application, and assessment performance.
        - Identify specific strengths, weaknesses, and misconceptions (mistakes).
        - Assign a mastery_score (0.0 to 1.0) for each concept.
        - A score of 0.8-0.9 usually indicates sufficient evidence for level completion.

        STRICT BOUNDARIES:
        - DO NOT suggest remediation actions.
        - DO NOT decide if the learner should proceed to the next level.
        - DO NOT unlock roadmap levels or change difficulty.
        - DO NOT orchestrate other agents.
        - Your output must be a pure evaluation, not a decision.

        OUTPUT FORMAT:
        Respond in structured JSON matching the ElaraEvaluationResponse schema:
        - evaluation_id: {str(uuid.uuid4())}
        - session_id: {request.session_id}
        - level_id: {request.level_id}
        - overall_evaluation: A high-level summary of performance across the level.
        - concept_evaluations: A list of ConceptEvaluation objects (one for each concept in the list).
        - global_strengths: Key strengths observed across all concepts.
        - global_weaknesses: Key gaps observed across all concepts.
        - evidence_summary: A summary of the evidence used to reach these conclusions.
        """
        return prompt

elara_agent = ElaraAgent()
