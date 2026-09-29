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
            response = raw_response
        else:
            response = AyanThinkingResponse(**raw_response)

        # Enforce unique, non-duplicate logical critical questions
        unique_questions = []
        seen_texts = set()
        for q in response.questions:
            normalized_text = q.text.strip().lower()
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_questions.append(q)

        if not unique_questions:
            unique_questions = self._generate_logical_critical_questions(request.concepts, request.objective)

        response.questions = unique_questions
        return response

    def _generate_logical_critical_questions(self, concepts: list[str], objective: str) -> list[AyanQuestion]:
        """Generates exactly 5 unique, logical Socratic reasoning questions across distinct categories."""
        c1 = concepts[0] if concepts else "Core Concept"
        c2 = concepts[1] if len(concepts) > 1 else c1
        return [
            AyanQuestion(
                question_id="q-ayan-1",
                text=f"What is the underlying causality of {c1}? Why must the system execute it this way rather than using synchronous in-memory state?",
                type="reasoning",
                target_concept=c1,
                ideal_answer_guideline="Demonstrate deductive reasoning explaining causality, lifecycle dynamics, and state transitions."
            ),
            AyanQuestion(
                question_id="q-ayan-2",
                text=f"What computational and latency trade-offs emerge when relying heavily on {c1} under high concurrency?",
                type="explanation",
                target_concept=c1,
                ideal_answer_guideline="Analyze resource constraints (memory, CPU, IO) and architectural bottlenecks."
            ),
            AyanQuestion(
                question_id="q-ayan-3",
                text=f"Under what specific edge conditions or race conditions would {c2} produce inconsistent results or deadlocks?",
                type="cause_effect",
                target_concept=c2,
                ideal_answer_guideline="Identify boundary conditions, concurrent write conflicts, or asynchronous timing hazards."
            ),
            AyanQuestion(
                question_id="q-ayan-4",
                text=f"Why is the widespread assumption that '{c1} is universally suitable for all workloads' flawed or dangerous in production?",
                type="misconception",
                target_concept=c1,
                ideal_answer_guideline="Deconstruct common industry misconceptions and identify scenarios where alternatives outperform it."
            ),
            AyanQuestion(
                question_id="q-ayan-5",
                text=f"How does {c1} integrate with {c2} to guarantee fault tolerance and zero data corruption during partial system failures?",
                type="application",
                target_concept=c2,
                ideal_answer_guideline="Synthesize system-level interactions, retry policies, and transactional boundaries."
            )
        ]

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
