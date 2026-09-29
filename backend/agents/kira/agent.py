import logging
from typing import Any, Dict, List
from datetime import datetime, timezone
import uuid

from backend.schemas.contracts import KiraApplicationRequest, KiraApplicationResponse, KiraScenario, AgentTask, AgentResult
from backend.providers.service import provider_service

logger = logging.getLogger(__name__)

class KiraAgent:
    """
    KIRA: The Real-World Application Agent.
    Responsible for converting concepts into practical scenarios and tasks
    to ensure the learner can apply knowledge in real-world situations.
    """

    def __init__(self):
        self.name = "kira"
        self.role = "Application Agent"

    async def process_task(self, task: AgentTask) -> AgentResult:
        """
        Entry point for the orchestrator.
        Generates practical application scenarios based on teaching and critical thinking phases.
        """
        try:
            # Validate input
            request = KiraApplicationRequest(**task.input_data)

            # Generate application scenarios using the provider abstraction
            response = await self._generate_application_scenarios(request)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="success",
                output_data=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Kira processing error: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="error",
                error_message=str(e)
            )

    async def _generate_application_scenarios(self, request: KiraApplicationRequest) -> KiraApplicationResponse:
        """
        Constructs the application prompt and calls the LLM provider.
        """
        prompt = self._build_prompt(request)

        # Use the system provider abstraction
        raw_response = await provider_service.generate_content(
            prompt=prompt,
            response_format=KiraApplicationResponse
        )

        # Ensure response is a Pydantic model
        if isinstance(raw_response, KiraApplicationResponse):
            return raw_response

        return KiraApplicationResponse(**raw_response)

    def _build_prompt(self, request: KiraApplicationRequest) -> str:
        """
        Constructs a specialized prompt for real-world application.
        """
        # Teaching context from Mira
        mira_content = request.mira_context.get("lesson_content", "No teaching content provided.")

        # Critical thinking context from Ayan
        ayan_context = request.ayan_context.get("questions", [])

        # Validated knowledge from Nova
        nova_facts = request.nova_knowledge.get("facts", [])

        # Learner profile
        learner_profile = request.learner_profile

        prompt = f"""
        You are KIRA, the CLARIO Application Agent. Your goal is to create practical, real-world scenarios
        where the learner must apply the following concepts:
        Concepts: {', '.join(request.concepts)}
        Objective: {request.objective}

        TEACHING CONTEXT (Mira's lesson):
        {mira_content}

        CRITICAL THINKING CONTEXT (Ayan's challenges):
        {ayan_context}

        VALIDATED KNOWLEDGE (Core Facts):
        {nova_facts}

        LEARNER PROFILE:
        {learner_profile}

        Application Requirements:
        1. Generate a set of realistic scenarios (Real-world scenario, Practical decision, Problem-solving, etc.).
        2. Scenarios must force the learner to apply the core concepts in a non-trivial way.
        3. Ensure scenarios are relevant to the learner's interests and level.
        4. For each scenario, provide an 'ideal_response_guideline' to assist in later evaluation.
        5. Do NOT evaluate the learner's performance here; only generate the task.

        OUTPUT FORMAT:
        Respond in structured JSON matching the KiraApplicationResponse schema:
        - session_id: {request.session_id}
        - level_id: {request.level_id}
        - scenarios: A list of KiraScenario objects (each with scenario_id, text, target_concept, and ideal_response_guideline).
        - application_rationale: Explain why these scenarios effectively test the application of the concepts.
        """
        return prompt

kira_agent = KiraAgent()
