import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.agents.kira.agent import KiraAgent
from backend.schemas.contracts import KiraApplicationRequest, KiraApplicationResponse, AgentTask, AgentResult
from backend.services.research_interface import ResearchInterface

class TestKiraAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = KiraAgent()
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
            "ayan_context": {
                "questions": [
                    {"text": "Why can't a broken cup spontaneously reassemble?", "type": "cause_effect"}
                ]
            },
            "nova_knowledge": {
                "summary": "The second law states that total entropy can never decrease.",
                "facts": ["Entropy increases in isolated systems"]
            },
            "learner_profile": {
                "learning_style": "analytical",
                "cala_signals": {"learner_level": "intermediate"}
            }
        }

    @patch("backend.agents.kira.agent.provider_service.generate_content")
    async def test_process_task_success(self, mock_generate):
        # Mock LLM response
        mock_response = KiraApplicationResponse(
            session_id="session-123",
            level_id="level-789",
            scenarios=[
                {
                    "scenario_id": "s1",
                    "text": "You are designing a refrigerator...",
                    "target_concept": "Entropy",
                    "ideal_response_guideline": "Must explain heat transfer and external work."
                }
            ],
            application_rationale="Applying entropy to appliance design."
        )
        mock_generate.return_value = mock_response

        task = AgentTask(
            task_id="task-kira-1",
            agent_name="kira",
            session_id="session-123",
            instruction="Generate application scenarios",
            input_data=self.sample_request_data
        )

        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.output_data["scenarios"]), 1)
        self.assertEqual(result.output_data["scenarios"][0]["text"], "You are designing a refrigerator...")

    @patch("backend.agents.kira.agent.provider_service.generate_content")
    async def test_process_task_llm_failure(self, mock_generate):
        mock_generate.side_effect = Exception("LLM Provider Timeout")
        task = AgentTask(
            task_id="task-kira-2",
            agent_name="kira",
            session_id="session-123",
            instruction="Generate scenarios",
            input_data=self.sample_request_data
        )
        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "error")
        self.assertIn("LLM Provider Timeout", result.error_message)

    async def test_prompt_construction(self):
        request = KiraApplicationRequest(**self.sample_request_data)
        prompt = self.agent._build_prompt(request)
        self.assertIn("KIRA, the CLARIO Application Agent", prompt)
        self.assertIn("second law of thermodynamics", prompt)
        self.assertIn("Entropy is the measure of disorder", prompt)

if __name__ == "__main__":
    unittest.main()
