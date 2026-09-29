import logging
from typing import Any, Dict, List
from datetime import datetime, timezone
import uuid

from backend.schemas.contracts import AyanThinkingRequest, AyanThinkingResponse, AyanQuestion, AgentTask, AgentResult
from backend.providers.service import provider_service

logger = logging.getLogger(__name__)

class AyanAgent:
    """
    AYAN: The Critical Thinking Agent.
    Responsible for generating higher-order thinking questions to verify
    deep understanding and surface misconceptions.
    """

    def __init__(self):
        self.name = "ayan"
        self.role = "Critical Thinking Agent"

    async def process_task(self, task: AgentTask) -> AgentResult:
        """
        Entry point for the orchestrator.
        Generates a set of critical thinking questions based on Mira's teaching and Nova's research.
        """
        try:
            # Validate input
            request = AyanThinkingRequest(**task.input_data)

            # Generate critical thinking questions using the provider abstraction
            response = await self._generate_critical_questions(request)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="success",
                output_data=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Ayan processing error: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="error",
                error_message=str(e)
            )

    async def _generate_critical_questions(self, request: AyanThinkingRequest) -> AyanThinkingResponse:
        """
        Constructs the Socratic prompt and calls the LLM provider.
        """
        prompt = self._build_prompt(request)

        # Use the system provider abstraction
        raw_response = await provider_service.generate_content(
            prompt=prompt,
            response_format=AyanThinkingResponse
        )

        # Ensure response is a Pydantic model
        if isinstance(raw_response, AyanThinkingResponse):
            return raw_response

        return AyanThinkingResponse(**raw_response)

    def _build_prompt(self, request: AyanThinkingRequest) -> str:
        """
        Constructs a specialized prompt for critical thinking generation.
        """
        # Teaching context from Mira
        mira_content = request.mira_context.get("lesson_content", "No teaching content provided.")

        # Validated knowledge from Nova
        nova_facts = request.nova_knowledge.get("facts", [])

        # Learner profile and signals
        learner_profile = request.learner_profile

        prompt = f"""
        You are AYAN, the CLARIO Critical Thinking Agent. Your goal is to challenge the learner's
        understanding of the following concepts:
        Concepts: {', '.join(request.concepts)}
        Objective: {request.objective}

        TEACHING CONTEXT (What Mira taught):
        {mira_content}

        VALIDATED KNOWLEDGE (Core Facts):
        {nova_facts}

        LEARNER PROFILE:
        {learner_profile}

        Socratic Challenge Requirements:
        1. Generate exactly 5 critical thinking questions.
        2. Distribute questions across these types: reasoning, explanation, comparison, cause_effect, application, misconception.
        3. Do NOT ask simple recall questions (e.g., "What is X?").
        4. Ask questions that require the learner to synthesize information or apply it to a new scenario.
        5. Ensure questions are grounded in the teaching context but push the learner to the edge of their current understanding.
        6. For each question, provide an 'ideal_answer_guideline' that describes what a correct, deep response looks like.

        OUTPUT FORMAT:
        Respond in structured JSON matching the AyanThinkingResponse schema:
        - session_id: {request.session_id}
        - level_id: {request.level_id}
        - questions: A list of 5 AyanQuestion objects (each with question_id, text, type, target_concept, and ideal_answer_guideline).
        - challenge_rationale: Explain why this specific set of questions was chosen for this learner.
        """
        return prompt

ayan_agent = AyanAgent()
