import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.agents.zayn.agent import ZaynAgent
from backend.schemas.contracts import ZaynQuizRequest, ZaynQuizResponse, AgentTask, AgentResult
from backend.providers.service import provider_service

class TestZaynAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = ZaynAgent()
        self.sample_request_data = {
            "session_id": "session-123",
            "user_id": "user-456",
            "level_id": "level-789",
            "objective": "Understand the basics of Quantum Entanglement",
            "concepts": ["Superposition", "Bell's Theorem"],
            "mira_context": {
                "lesson_content": "Quantum entanglement occurs when particles interact in ways such that the quantum state of each particle cannot be described independently...",
                "conceptual_breakdown": []
            },
            "ayan_context": {
                "questions": [
                    {"text": "If two particles are entangled, does information travel faster than light?", "type": "reasoning"}
                ]
            },
            "kira_context": {
                "scenarios": [
                    {"text": "Using entanglement for quantum cryptography...", "target_concept": "Bell's Theorem"}
                ]
            },
            "nova_knowledge": {
                "summary": "Entanglement is a key feature of quantum mechanics.",
                "facts": ["Particles remain connected regardless of distance"]
            },
            "learner_profile": {
                "learning_style": "analytical",
                "cala_signals": {"learner_level": "intermediate"}
            }
        }

    @patch("backend.agents.zayn.agent.provider_service.generate_content")
    async def test_process_task_success(self, mock_generate):
        # Mock LLM response matching ZaynQuizResponse
        mock_response = ZaynQuizResponse(
            quiz_id="quiz-abc",
            session_id="session-123",
            level_id="level-789",
            questions=[
                {
                    "question_id": f"q{i}",
                    "concept": "Superposition",
                    "difficulty": "Easy" if i < 5 else "Medium" if i < 8 else "Hard",
                    "question_type": "MCQ",
                    "question_text": f"Question {i} text",
                    "expected_answer": "Ans {i}",
                    "time_limit_seconds": 30 if i < 5 else 60 if i < 8 else 90,
                    "order": i + 1
                } for i in range(10)
            ],
            quiz_rationale="Balanced quiz based on provided context."
        )
        mock_generate.return_value = mock_response

        task = AgentTask(
            task_id="task-zayn-1",
            agent_name="zayn",
            session_id="session-123",
            instruction="Generate a balanced 10-question quiz",
            input_data=self.sample_request_data
        )

        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.output_data["questions"]), 10)
        self.assertEqual(result.output_data["questions"][0]["difficulty"], "Easy")
        self.assertEqual(result.output_data["questions"][9]["difficulty"], "Hard")

    @patch("backend.agents.zayn.agent.provider_service.generate_content")
    async def test_process_task_llm_failure(self, mock_generate):
        mock_generate.side_effect = Exception("LLM Provider Error")
        task = AgentTask(
            task_id="task-zayn-2",
            agent_name="zayn",
            session_id="session-123",
            instruction="Generate quiz",
            input_data=self.sample_request_data
        )
        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "error")
        self.assertIn("LLM Provider Error", result.error_message)

    async def test_prompt_construction(self):
        request = ZaynQuizRequest(**self.sample_request_data)
        prompt = self.agent._build_prompt(request)
        self.assertIn("ZAYN, the CLARIO Quiz Agent", prompt)
        self.assertIn("Quantum Entanglement", prompt)
        self.assertIn("STRICT QUIZ DISTRIBUTION", prompt)
        self.assertIn("5 Easy Questions", prompt)
        self.assertIn("3 Medium Questions", prompt)
        self.assertIn("2 Hard Questions", prompt)

if __name__ == "__main__":
    unittest.main()
