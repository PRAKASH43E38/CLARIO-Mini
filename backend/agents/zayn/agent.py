import logging
from typing import Any, Dict, List
from datetime import datetime, timezone
import uuid

from backend.schemas.contracts import ZaynQuizRequest, ZaynQuizResponse, ZaynQuestion, AgentTask, AgentResult
from backend.providers.service import provider_service

logger = logging.getLogger(__name__)

class ZaynAgent:
    """
    ZAYN: The Quiz Agent.
    Responsible for generating a 10-question assessment for the current level,
    following a strict difficulty distribution (5 Easy, 3 Medium, 2 Hard).
    """

    def __init__(self):
        self.name = "zayn"
        self.role = "Quiz Agent"

    async def process_task(self, task: AgentTask) -> AgentResult:
        """
        Entry point for the orchestrator.
        Generates a structured quiz based on teaching, thinking, and application context.
        """
        try:
            # Validate input
            request = ZaynQuizRequest(**task.input_data)

            # Generate the quiz using the provider abstraction
            response = await self._generate_quiz(request)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="success",
                output_data=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Zayn processing error: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="error",
                error_message=str(e)
            )

    async def _generate_quiz(self, request: ZaynQuizRequest) -> ZaynQuizResponse:
        """
        Constructs the assessment prompt and calls the LLM provider.
        """
        prompt = self._build_prompt(request)

        # Use the system provider abstraction
        raw_response = await provider_service.generate_content(
            prompt=prompt,
            response_format=ZaynQuizResponse
        )

        # Ensure response is a Pydantic model
        if isinstance(raw_response, ZaynQuizResponse):
            return raw_response

        return ZaynQuizResponse(**raw_response)

    def _build_prompt(self, request: ZaynQuizRequest) -> str:
        """
        Constructs a specialized prompt for a balanced 10-question quiz.
        """
        mira_content = request.mira_context.get("lesson_content", "No teaching content provided.")
        ayan_context = request.ayan_context.get("questions", [])
        kira_context = request.kira_context.get("scenarios", [])
        nova_facts = request.nova_knowledge.get("facts", [])
        learner_profile = request.learner_profile

        prompt = f"""
        You are ZAYN, the CLARIO Quiz Agent. Your goal is to generate a 10-question assessment for the current level.

        Concepts: {', '.join(request.concepts)}
        Objective: {request.objective}

        CONTEXT:
        - Teaching Content (Mira): {mira_content}
        - Critical Thinking (Ayan): {ayan_context}
        - Practical Application (Kira): {kira_context}
        - Validated Knowledge (Nova): {nova_facts}
        - Learner Profile: {learner_profile}

        STRICT QUIZ DISTRIBUTION:
        You must generate exactly 10 questions with the following split:
        1. 5 Easy Questions: (Timer: 30s). Focus on core conceptual understanding.
        2. 3 Medium Questions: (Timer: 60s). Focus on application and reasoning.
        3. 2 Hard Questions: (Timer: 90s). Focus on synthesis and complex problem solving.

        QUESTION TYPES:
        Mix the following types:
        - Fill in the blank
        - Typed short answer
        - Coding completion
        - Full coding/problem-solving (for Hard questions)

        REQUIREMENTS:
        - Each question must target a specific concept from the list.
        - Provide clear 'expected_answer' criteria for scoring.
        - Assign the correct 'time_limit_seconds' based on difficulty.
        - Ensure questions are ordered from 1 to 10.

        OUTPUT FORMAT:
        Respond in structured JSON matching the ZaynQuizResponse schema:
        - quiz_id: {str(uuid.uuid4())}
        - session_id: {request.session_id}
        - level_id: {request.level_id}
        - questions: A list of 10 ZaynQuestion objects.
        - quiz_rationale: Explain how this quiz distribution verifies the learner's progress.
        """
        return prompt

zayn_agent = ZaynAgent()
