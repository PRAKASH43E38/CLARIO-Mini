
import logging
from typing import Any, Dict, List
from datetime import datetime, timezone

from backend.schemas.contracts import MiraTeachingRequest, MiraTeachingResponse, AgentTask, AgentResult
from backend.providers.service import provider_service

logger = logging.getLogger(__name__)

class MiraAgent:
    """
    MIRA: The Teaching Agent.
    Responsible for transforming raw research and learner context into
    personalized, pedagogically sound educational content.
    """

    def __init__(self):
        self.name = "mira"
        self.role = "Teaching Agent"

    async def process_task(self, task: AgentTask) -> AgentResult:
        """
        Entry point for the orchestrator.
        Processes a MiraTeachingRequest and returns structured teaching content.
        """
        try:
            # Validate input
            request = MiraTeachingRequest(**task.input_data)

            # Generate personalized content using the provider abstraction
            response = await self._generate_teaching_content(request)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="success",
                output_data=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Mira processing error: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                session_id=task.session_id,
                status="error",
                error_message=str(e)
            )

    def _is_interview_task(self, request: MiraTeachingRequest) -> bool:
        """Determines if the topic, concepts, goal, or inputs relate to interview preparation."""
        check_str = (
            f"{request.level_objective} "
            f"{' '.join(request.concepts)} "
            f"{request.session_inputs.get('goal', '')} "
            f"{request.session_inputs.get('interest', '')} "
            f"{request.session_inputs.get('learner_state', '')} "
            f"{request.session_inputs.get('topic', '')}"
        ).lower()
        return "interview" in check_str

    async def _generate_teaching_content(self, request: MiraTeachingRequest) -> MiraTeachingResponse:
        """
        Constructs the pedagogical prompt and calls the LLM provider.
        Guarantees interview URL provision when the task is an interview.
        """
        prompt = self._build_prompt(request)

        # Use the system provider abstraction
        raw_response = await provider_service.generate_content(
            prompt=prompt,
            response_format=MiraTeachingResponse
        )

        if isinstance(raw_response, MiraTeachingResponse):
            response = raw_response
        else:
            response = MiraTeachingResponse(**raw_response)

        # Ensure 5 logical non-duplicate checkpoint questions exist
        if not response.checkpoint_questions or len(response.checkpoint_questions) < 5:
            response.checkpoint_questions = self._generate_logical_checkpoint_questions(
                request.concepts,
                request.level_objective
            )

        # Ensure interview URL is explicitly included if this is an interview task
        if self._is_interview_task(request):
            interview_url = "https://www.indiabix.com/"
            if interview_url not in response.lesson_content:
                response.lesson_content += (
                    f"\n\n---\n### 🎯 Interview Preparation Resources & Practice\n"
                    f"Practice real technical interview questions, MCQs, and domain problems at: "
                    f"[{interview_url}]({interview_url}) (IndiaBIX Interview Prep Portal)"
                )
            response.interview_url = interview_url
            if interview_url not in response.reference_urls:
                response.reference_urls.append(interview_url)

        return response

    def _generate_logical_checkpoint_questions(self, concepts: list[str], objective: str) -> list[dict[str, str]]:
        """Generates exactly 5 unique, logical, non-repeating comprehension questions."""
        c1 = concepts[0] if concepts else "Core Concept"
        c2 = concepts[1] if len(concepts) > 1 else c1
        return [
            {
                "question_id": "mira-cp-1",
                "stage": "1. Foundational Definition",
                "question": f"In your own words, what is the foundational principle and purpose of {c1}?",
                "concept": c1,
                "focus": "Core Definition & Purpose"
            },
            {
                "question_id": "mira-cp-2",
                "stage": "2. Operational Mechanism",
                "question": f"Step-by-step, how does {c1} execute and transform inputs during runtime?",
                "concept": c1,
                "focus": "Execution Mechanism"
            },
            {
                "question_id": "mira-cp-3",
                "stage": "3. Critical Constraint",
                "question": f"What crucial boundary condition or failure state must be guarded against when applying {c2}?",
                "concept": c2,
                "focus": "Boundary & Constraint"
            },
            {
                "question_id": "mira-cp-4",
                "stage": "4. Comparative Difference",
                "question": f"How does the architectural approach of {c1} compare against alternative or older patterns?",
                "concept": c1,
                "focus": "Architectural Comparison"
            },
            {
                "question_id": "mira-cp-5",
                "stage": "5. Practical Synthesis",
                "question": f"How do {', '.join(concepts)} integrate together to ensure clarity and system reliability?",
                "concept": c1,
                "focus": "Real-world Synthesis"
            }
        ]

    def _build_prompt(self, request: MiraTeachingRequest) -> str:
        """
        Constructs a highly personalized pedagogical prompt.
        """
        research_summary = request.research_context.get("summary", "No research available.")
        facts = request.research_context.get("facts", [])

        learning_style = request.mind_profile.get("learning_style", "general")
        level = request.cala_signals.get("learner_level", "beginner")
        interest = request.session_inputs.get("interest", "general")

        interview_guideline = ""
        if self._is_interview_task(request):
            interview_guideline = """
        INTERVIEW TASK SPECIAL DIRECTIVE:
        The learner is preparing for an INTERVIEW. You MUST provide the official interview resource URL (https://www.indiabix.com/) prominently in your lesson_content markdown with clear guidance on what interview question patterns to practice.
            """

        prompt = f"""
        You are MIRA, the CLARIO Teaching Agent. Your goal is to teach the following concepts:
        Concepts: {', '.join(request.concepts)}
        Objective: {request.level_objective}

        LEARNER PROFILE:
        - Learning Style: {learning_style}
        - Current Level: {level}
        - Personal Interests: {interest}
        - CALA Signals: {request.cala_signals}

        RESEARCH CONTEXT (Validated Knowledge):
        - Summary: {research_summary}
        - Key Facts: {facts}
        {interview_guideline}

        PEDAGOGICAL REQUIREMENTS:
        1. Adapt the explanation style to the learner's profile.
        2. Use scaffolding: start with simple foundations and build complexity.
        3. Incorporate the learner's interests to make the content relatable.
        4. Provide clear analogies that bridge existing knowledge to new concepts.
        5. Manage cognitive load: do not overwhelm the learner.
        6. Be encouraging but maintain academic rigor.
        7. Provide exactly 5 logical, sequential comprehension checkpoint questions with zero duplicates.

        OUTPUT FORMAT:
        You must respond in a structured JSON format matching the MiraTeachingResponse schema:
        - lesson_content: Comprehensive, adaptive explanation in Markdown.
        - conceptual_breakdown: A list of key concepts with their specific explanations.
        - analogies: A list of analogies tailored to the learner's interests.
        - adaptation_rationale: Explain WHY you chose this specific teaching approach.
        - checkpoint_questions: List of 5 distinct, sequential comprehension questions.
        - suggested_pacing: 'accelerated', 'standard', or 'measured'.
        """
        return prompt

mira_agent = MiraAgent()
