import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.agents.ayan.agent import AyanAgent
from backend.schemas.contracts import AyanThinkingRequest, AyanThinkingResponse, AgentTask, AgentResult
from backend.services.research_interface import ResearchInterface

class TestAyanAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = AyanAgent()
        self.sample_request_data = {
            "session_id": "session-123",
            "user_id": "user-456",
            "level_id": "level-789",
            "objective": "Understand the second law of thermodynamics",
            "concepts": ["Entropy", "Heat Death"],
            "mira_context": {
                "lesson_content": "Entropy is the measure of disorder in a system...",
                "conceptual_breakdown": []
            },
            "nova_knowledge": {
                "summary": "The second law states that total entropy can never decrease.",
                "facts": ["Entropy increases in isolated systems", "Energy flows from hot to cold"]
            },
            "learner_profile": {
                "learning_style": "analytical",
                "cala_signals": {"learner_level": "intermediate"}
            }
        }

    @patch("backend.agents.ayan.agent.provider_service.generate_content")
    async def test_process_task_success(self, mock_generate):
        # Mock LLM response
        mock_response = AyanThinkingResponse(
            session_id="session-123",
            level_id="level-789",
            questions=[
                {
                    "question_id": "q1",
                    "text": "Why can't a broken cup spontaneously reassemble?",
                    "type": "cause_effect",
                    "target_concept": "Entropy",
                    "ideal_answer_guideline": "Mention increase in entropy and arrow of time."
                }
            ],
            challenge_rationale="Testing application of entropy to physical examples."
        )
        mock_generate.return_value = mock_response

        task = AgentTask(
            task_id="task-ayan-1",
            agent_name="ayan",
            session_id="session-123",
            instruction="Generate critical thinking questions",
            input_data=self.sample_request_data
        )

        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.output_data["questions"]), 1)
        self.assertEqual(result.output_data["questions"][0]["text"], "Why can't a broken cup spontaneously reassemble?")

    @patch("backend.agents.ayan.agent.provider_service.generate_content")
    async def test_process_task_llm_failure(self, mock_generate):
        mock_generate.side_effect = Exception("LLM Provider Timeout")
        task = AgentTask(
            task_id="task-ayan-2",
            agent_name="ayan",
            session_id="session-123",
            instruction="Generate questions",
            input_data=self.sample_request_data
        )
        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "error")
        self.assertIn("LLM Provider Timeout", result.error_message)

    async def test_prompt_construction(self):
        request = AyanThinkingRequest(**self.sample_request_data)
        prompt = self.agent._build_prompt(request)
        self.assertIn("AYAN, the CLARIO Critical Thinking Agent", prompt)
        self.assertIn("second law of thermodynamics", prompt)
        self.assertIn("Entropy is the measure of disorder", prompt)
        self.assertIn("Entropy increases in isolated systems", prompt)

if __name__ == "__main__":
    unittest.main()
