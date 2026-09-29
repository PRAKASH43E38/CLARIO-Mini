import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.agents.mira.agent import MiraAgent
from backend.schemas.contracts import MiraTeachingRequest, MiraTeachingResponse, AgentTask, AgentResult
from backend.services.research_interface import ResearchInterface

class TestMiraAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = MiraAgent()
        self.sample_request_data = {
            "task_id": "task-123",
            "session_id": "session-456",
            "user_id": "user-789",
            "level_id": "level-1",
            "level_objective": "Understand basic quantum entanglement",
            "concepts": ["Superposition", "Entanglement"],
            "research_context": {
                "summary": "Quantum entanglement is a physical phenomenon where particles remain connected.",
                "facts": ["Particles share a state", "Information is not transferred faster than light"]
            },
            "mind_profile": {
                "learning_style": "visual",
                "pace_preference": "standard"
            },
            "cala_signals": {
                "learner_level": "beginner",
                "confidence_signal": "low"
            },
            "session_inputs": {
                "interest": "science fiction",
                "goal": "Pass physics exam"
            }
        }

    @patch("backend.agents.mira.agent.provider_service.generate_content")
    async def test_process_task_success(self, mock_generate):
        # Mock LLM response
        mock_response = MiraTeachingResponse(
            task_id="task-123",
            session_id="session-456",
            level_id="level-1",
            lesson_content="Welcome to Quantum Physics...",
            conceptual_breakdown=[{"concept": "Superposition", "explanation": "..."}],
            analogies=[{"analogy": "A spinning coin", "explanation": "..."}],
            adaptation_rationale="Using sci-fi interests for visual learner",
            suggested_pacing="standard"
        )
        mock_generate.return_value = mock_response

        task = AgentTask(
            task_id="task-123",
            agent_name="mira",
            session_id="session-456",
            instruction="Teach the user about quantum entanglement",
            input_data=self.sample_request_data
        )

        result = await self.agent.process_task(task)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.output_data["lesson_content"], "Welcome to Quantum Physics...")
        mock_generate.assert_called_once()

    @patch("backend.agents.mira.agent.provider_service.generate_content")
    async def test_process_task_llm_failure(self, mock_generate):
        mock_generate.side_effect = Exception("LLM API Down")

        task = AgentTask(
            task_id="task-123",
            agent_name="mira",
            session_id="session-456",
            instruction="Teach the user",
            input_data=self.sample_request_data
        )

        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "error")
        self.assertIn("LLM API Down", result.error_message)

    async def test_prompt_construction(self):
        request = MiraTeachingRequest(**self.sample_request_data)
        prompt = self.agent._build_prompt(request)

        self.assertIn("MIRA, the CLARIO Teaching Agent", prompt)
        self.assertIn("Quantum entanglement", prompt)
        self.assertIn("visual", prompt)
        self.assertIn("science fiction", prompt)
        self.assertIn("Quantum entanglement is a physical phenomenon", prompt)

class TestResearchInterface(unittest.TestCase):
    @patch("backend.services.research_interface.get_clario_ai_db")
    @patch("backend.services.research_interface.get_nova_db")
    def test_get_research_context_success(self, mock_nova, mock_ai):
        # Mock clario_ai.db to return a request_id
        mock_ai_conn = MagicMock()
        mock_ai_conn.execute.return_value.fetchone.return_value = {"request_id": "req-123"}
        mock_ai.return_value.__enter__.return_value = mock_ai_conn

        # Mock nova.db to return a summary
        mock_nova_conn = MagicMock()
        mock_nova_conn.execute.return_value.fetchone.return_value = {"summary": "Nova Research Summary"}
        mock_nova.return_value.__enter__.return_value = mock_nova_conn

        context = ResearchInterface.get_research_context("level-1")

        self.assertEqual(context["summary"], "Nova Research Summary")
        self.assertIn("Nova Research Summary", context["facts"])

    @patch("backend.services.research_interface.get_clario_ai_db")
    def test_get_research_context_no_orchestration(self, mock_ai):
        mock_ai_conn = MagicMock()
        mock_ai_conn.execute.return_value.fetchone.return_value = None
        mock_ai.return_value.__enter__.return_value = mock_ai_conn

        context = ResearchInterface.get_research_context("level-1")
        self.assertEqual(context["summary"], "No research performed for this level.")

if __name__ == "__main__":
    unittest.main()
