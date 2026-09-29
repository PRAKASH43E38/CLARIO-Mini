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
            response = raw_response
        else:
            response = ZaynQuizResponse(**raw_response)

        # Enforce exact 10 questions with strict format (5 Easy fill-in-blanks, 3 Medium paragraph, 2 Hard Python coding)
        unique_questions = []
        seen_texts = set()
        for q in response.questions:
            normalized_text = q.question_text.strip().lower()
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_questions.append(q)

        if len(unique_questions) < 10:
            fallback_qs = self._generate_logical_quiz_questions(request.concepts, request.objective)
            for fq in fallback_qs:
                if fq.question_text.strip().lower() not in seen_texts:
                    seen_texts.add(fq.question_text.strip().lower())
                    unique_questions.append(fq)
                if len(unique_questions) == 10:
                    break

        # Re-index order 1 to 10
        for i, q in enumerate(unique_questions[:10]):
            q.order = i + 1
        response.questions = unique_questions[:10]
        return response

    def _generate_logical_quiz_questions(self, concepts: list[str], objective: str) -> list[ZaynQuestion]:
        """
        Generates exactly 10 unique, non-repeating questions:
        - 5 Easy: Fill in the blanks (with '____')
        - 3 Medium: Paragraph-based scenario explanation
        - 2 Hard: Python coding challenge
        """
        c1 = concepts[0] if concepts else "Core Concept"
        c2 = concepts[1] if len(concepts) > 1 else c1

        return [
            # 5 EASY: Fill in the Blank (30s)
            ZaynQuestion(
                question_id="q-zayn-1",
                concept=c1,
                difficulty="Easy",
                question_type="Fill in the Blank",
                question_text=f"Fill in the blank: The primary mechanism of {c1} is to ____ dependencies across system modules.",
                expected_answer="decouple / isolate / abstract",
                time_limit_seconds=30,
                order=1
            ),
            ZaynQuestion(
                question_id="q-zayn-2",
                concept=c1,
                difficulty="Easy",
                question_type="Fill in the Blank",
                question_text=f"Fill in the blank: In Python programming, the keyword ____ is used to define an asynchronous coroutine function.",
                expected_answer="async",
                time_limit_seconds=30,
                order=2
            ),
            ZaynQuestion(
                question_id="q-zayn-3",
                concept=c2,
                difficulty="Easy",
                question_type="Fill in the Blank",
                question_text=f"Fill in the blank: In resilient architecture, {c2} guarantees that operations are ____, meaning repeated execution yields the identical outcome.",
                expected_answer="idempotent / deterministic",
                time_limit_seconds=30,
                order=3
            ),
            ZaynQuestion(
                question_id="q-zayn-4",
                concept=c1,
                difficulty="Easy",
                question_type="Fill in the Blank",
                question_text="Fill in the blank: In database transactions, executing ____ commits all unwritten state changes permanently to disk.",
                expected_answer="commit",
                time_limit_seconds=30,
                order=4
            ),
            ZaynQuestion(
                question_id="q-zayn-5",
                concept=c2,
                difficulty="Easy",
                question_type="Fill in the Blank",
                question_text=f"Fill in the blank: When tuning {c2}, ____ latency represents the transit duration elapsed before data transfer commences.",
                expected_answer="network / response / round-trip",
                time_limit_seconds=30,
                order=5
            ),

            # 3 MEDIUM: Paragraph Explanation (60s)
            ZaynQuestion(
                question_id="q-zayn-6",
                concept=c1,
                difficulty="Medium",
                question_type="Paragraph",
                question_text=f"Paragraph Analysis: 'A backend service utilizing {c1} experiences cascading thread exhaustion because upstream clients immediately retry timed-out requests in tight loops.' In a well-structured paragraph, analyze how this retry storm develops and explain how exponential backoff with jitter mitigates the failure.",
                expected_answer="Thorough paragraph explaining retry storm dynamics, resource exhaustion, and exponential backoff with jitter spreading request spikes.",
                time_limit_seconds=60,
                order=6
            ),
            ZaynQuestion(
                question_id="q-zayn-7",
                concept=c2,
                difficulty="Medium",
                question_type="Paragraph",
                question_text=f"Paragraph Analysis: 'A database query on {c2} takes 12 seconds under load because it conducts full-table scans across unindexed foreign keys.' In a coherent paragraph, explain the mechanics of B-Tree indexing and how composite indexing restructures execution plans.",
                expected_answer="Paragraph detailing B-tree traversal versus linear sequential scan, index selectivity, and IO overhead reduction.",
                time_limit_seconds=60,
                order=7
            ),
            ZaynQuestion(
                question_id="q-zayn-8",
                concept=c1,
                difficulty="Medium",
                question_type="Paragraph",
                question_text=f"Paragraph Analysis: 'Two asynchronous workers simultaneously mutate shared state in {c1} without mutex protection, producing non-deterministic data corruption.' In a clear paragraph, explain the root cause of race conditions and formulate a synchronization strategy.",
                expected_answer="Paragraph discussing critical sections, thread interleaving, atomic operations, and lock-based or optimistic concurrency controls.",
                time_limit_seconds=60,
                order=8
            ),

            # 2 HARD: Python Coding Challenge (90s)
            ZaynQuestion(
                question_id="q-zayn-9",
                concept=c1,
                difficulty="Hard",
                question_type="Python Coding",
                question_text=f"Python Coding Challenge: Write a Python function `def process_records(records: list[dict], min_val: float) -> list[dict]:` that iterates through `records`, filters those where `item['score'] >= min_val`, normalizes the score by dividing by 100.0, and returns the filtered records sorted descending by score. Write clean, syntactically valid Python code.",
                expected_answer="def process_records(records: list[dict], min_val: float) -> list[dict]:\n    filtered = [{**r, 'score': r['score'] / 100.0} for r in records if r.get('score', 0) >= min_val]\n    return sorted(filtered, key=lambda x: x['score'], reverse=True)",
                time_limit_seconds=90,
                order=9
            ),
            ZaynQuestion(
                question_id="q-zayn-10",
                concept=c2,
                difficulty="Hard",
                question_type="Python Coding",
                question_text=f"Python Coding Challenge: Implement a Python class `class TaskQueue:` with methods `__init__(self, max_capacity: int)` and `def push(self, task: str) -> bool:`, `def pop(self) -> str | None:` that implements a thread-safe FIFO queue with size limits. Return False on push if at capacity, and None on pop if empty. Write complete, valid Python code.",
                expected_answer="from collections import deque\nimport threading\n\nclass TaskQueue:\n    def __init__(self, max_capacity: int):\n        self.queue = deque()\n        self.max = max_capacity\n        self.lock = threading.Lock()\n    def push(self, task: str) -> bool:\n        with self.lock:\n            if len(self.queue) >= self.max:\n                return False\n            self.queue.append(task)\n            return True\n    def pop(self) -> str | None:\n        with self.lock:\n            return self.queue.popleft() if self.queue else None",
                time_limit_seconds=90,
                order=10
            )
        ]

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
        Every question must be completely unique and logically progressive (NO duplicates, NO repeated questions).

        1. 5 Easy Questions: (Timer: 30s).
           - Question Type: 'Fill in the Blank'
           - MUST use '____' (blank) in the question_text.
           - Test core keywords, terminology, and syntax.

        2. 3 Medium Questions: (Timer: 60s).
           - Question Type: 'Paragraph'
           - Give a scenario paragraph and ask the learner to explain the analysis/solution in a paragraph.

        3. 2 Hard Questions: (Timer: 90s).
           - Question Type: 'Python Coding'
           - Coding challenge in the Python language. Provide a clear function/class signature to implement in Python.

        REQUIREMENTS:
        - Each question must target a specific concept from the list.
        - Provide clear 'expected_answer' criteria for scoring.
        - Assign the correct 'time_limit_seconds' based on difficulty (Easy: 30, Medium: 60, Hard: 90).
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
