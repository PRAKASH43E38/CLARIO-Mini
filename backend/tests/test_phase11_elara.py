import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json
import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.agents.elara.agent import ElaraAgent
from backend.schemas.contracts import (
    ElaraEvaluationRequest,
    ElaraEvaluationResponse,
    ConceptEvaluation,
    AgentTask,
    AgentResult
)
from backend.services.evaluation_interface import EvaluationInterface
from backend.services.orchestration_service import OrchestrationService
from backend.database.connection import get_user_db, get_clario_ai_db, init_all_databases
from backend.auth.session import get_current_user_id


class TestElaraAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = ElaraAgent()
        self.sample_request_data = {
            "session_id": "session-123",
            "user_id": "user-456",
            "level_id": "level-789",
            "objective": "Understand the basics of Quantum Entanglement",
            "concepts": ["Superposition", "Entanglement"],
            "mira_evidence": {
                "interactions": ["Mira explained superposition and gave a cat analogy."]
            },
            "ayan_evidence": {
                "challenges": [{"text": "Why can't we use it for FTL communication?"}],
                "responses": [{"question_id": "q1", "user_answer": "Because of the no-communication theorem."}]
            },
            "kira_evidence": {
                "scenarios": [{"text": "Quantum Key Distribution scenario"}],
                "responses": [{"scenario_id": "s1", "user_response": "Correctly implemented QKD protocol."}]
            },
            "zayn_evidence": {
                "quiz": [{"question_text": "What is Bell's Theorem?", "expected_answer": "..."}],
                "responses": [{"question_id": "q1", "user_answer": "Correct answer", "response_time_seconds": 45, "is_timeout": False}]
            },
            "learner_profile": {
                "learning_style": "analytical"
            }
        }

    @patch("backend.agents.elara.agent.provider_service.generate_content")
    async def test_process_task_success(self, mock_generate):
        mock_response = ElaraEvaluationResponse(
            evaluation_id="eval-abc",
            session_id="session-123",
            level_id="level-789",
            overall_evaluation="Strong grasp of the basics.",
            concept_evaluations=[
                ConceptEvaluation(
                    concept="Superposition",
                    understanding="Deep conceptual grasp",
                    reasoning="Strong deductive logic",
                    application="Accurate practical application in QKD",
                    assessment="100% on quiz questions",
                    mastery_score=0.95,
                    strengths=["Cat analogy grasp", "Measurement theory"],
                    weaknesses=[],
                    mistakes=[],
                    evidence=["mira_interaction_1", "zayn_quiz_q1"]
                )
            ],
            global_strengths=["Analytical reasoning", "Attention to detail"],
            global_weaknesses=[],
            evidence_summary="Consistent performance across all agents."
        )
        mock_generate.return_value = mock_response

        task = AgentTask(
            task_id="task-elara-1",
            agent_name="elara",
            session_id="session-123",
            instruction="Perform evaluation",
            input_data=self.sample_request_data
        )

        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.output_data["evaluation_id"], "eval-abc")
        self.assertEqual(len(result.output_data["concept_evaluations"]), 1)

        # Verify all required output elements
        concept_eval = result.output_data["concept_evaluations"][0]
        self.assertIn("understanding", concept_eval)
        self.assertIn("reasoning", concept_eval)
        self.assertIn("application", concept_eval)
        self.assertIn("assessment", concept_eval)
        self.assertIn("strengths", concept_eval)
        self.assertIn("weaknesses", concept_eval)
        self.assertIn("mistakes", concept_eval)
        self.assertIn("mastery_score", concept_eval)
        self.assertIn("evidence", concept_eval)

    @patch("backend.agents.elara.agent.provider_service.generate_content")
    async def test_process_task_llm_failure(self, mock_generate):
        mock_generate.side_effect = Exception("LLM Provider Error")
        task = AgentTask(
            task_id="task-elara-2",
            agent_name="elara",
            session_id="session-123",
            instruction="Evaluate",
            input_data=self.sample_request_data
        )
        result = await self.agent.process_task(task)
        self.assertEqual(result.status, "error")
        self.assertIn("LLM Provider Error", result.error_message)

    async def test_prompt_construction(self):
        request = ElaraEvaluationRequest(**self.sample_request_data)
        prompt = self.agent._build_prompt(request)
        self.assertIn("ELARA, the CLARIO Evaluation Agent", prompt)
        self.assertIn("objective academic judge", prompt)
        self.assertIn("STRICT BOUNDARIES", prompt)
        self.assertIn("DO NOT suggest remediation", prompt)
        self.assertIn("DO NOT decide if the learner should proceed", prompt)
        self.assertIn("DO NOT unlock roadmap levels", prompt)
        self.assertIn("DO NOT orchestrate other agents", prompt)
        self.assertIn("Quantum Entanglement", prompt)

    async def test_strict_boundaries_contract(self):
        """Verify Elara outputs only evaluation data and no orchestration decisions."""
        response = ElaraEvaluationResponse(
            evaluation_id="eval-strict-1",
            session_id="session-123",
            level_id="level-789",
            overall_evaluation="Level mastered.",
            concept_evaluations=[
                ConceptEvaluation(
                    concept="Superposition",
                    understanding="Proficient",
                    reasoning="Sound",
                    application="Capable",
                    assessment="90%",
                    mastery_score=0.9,
                    strengths=["Linear algebra formulation"],
                    weaknesses=[],
                    mistakes=[],
                    evidence=["evidence_1"]
                )
            ],
            global_strengths=["Foundational grasp"],
            global_weaknesses=[],
            evidence_summary="Sufficient evidence."
        )
        dump = response.model_dump()
        self.assertNotIn("next_agent", dump)
        self.assertNotIn("remediation", dump)
        self.assertNotIn("difficulty_change", dump)
        self.assertNotIn("unlock_level", dump)


class TestEvaluationInterface(unittest.TestCase):
    def setUp(self):
        init_all_databases()
        self.interface = EvaluationInterface()
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self.user_id = f"user-{uuid.uuid4().hex[:8]}"
        self.level_id = f"lvl-{uuid.uuid4().hex[:8]}"
        self.roadmap_id = f"rm-{uuid.uuid4().hex[:8]}"

        # Seed database with user and session
        with get_user_db() as u_db:
            u_db.execute(
                "INSERT INTO users (id, email) VALUES (?, ?)",
                (self.user_id, f"{self.user_id}@example.com")
            )
            u_db.execute(
                "INSERT INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
                (self.session_id, self.user_id)
            )
            u_db.execute(
                "INSERT INTO user_profiles (user_id, display_name) VALUES (?, 'Test Learner')",
                (self.user_id,)
            )

        # Seed clario_ai.db with session, roadmap, level, concepts, and evidence from Mira, Ayan, Kira, Zayn
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT OR REPLACE INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
                (self.session_id, self.user_id)
            )
            ai_db.execute(
                "INSERT INTO roadmaps (roadmap_id, session_id, topic) VALUES (?, ?, 'Physics')",
                (self.roadmap_id, self.session_id)
            )
            ai_db.execute(
                "INSERT INTO roadmap_levels (level_id, roadmap_id, level_number, title, objective, status) VALUES (?, ?, 1, 'Quantum Basics', 'Understand superposition', 'UNLOCKED')",
                (self.level_id, self.roadmap_id)
            )
            ai_db.execute(
                "INSERT INTO level_concepts (concept_id, level_id, concept_name) VALUES (?, ?, 'Superposition')",
                (str(uuid.uuid4()), self.level_id)
            )

            # 1. Mira evidence
            ai_db.execute(
                "INSERT INTO teaching_interactions (interaction_id, session_id, level_id, response_payload_json) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), self.session_id, self.level_id, "Mira taught superposition with wave equations.")
            )

            # 2. Ayan evidence
            chal_id = str(uuid.uuid4())
            ai_db.execute(
                "INSERT INTO thinking_challenges (challenge_id, session_id, level_id, questions_json) VALUES (?, ?, ?, ?)",
                (chal_id, self.session_id, self.level_id, json.dumps([{"text": "Explain phase difference"}]))
            )
            ai_db.execute(
                "INSERT INTO thinking_responses (response_id, challenge_id, question_id, user_answer) VALUES (?, ?, 'q1', 'Phase difference affects interference')",
                (str(uuid.uuid4()), chal_id)
            )

            # 3. Kira evidence
            scen_id = str(uuid.uuid4())
            ai_db.execute(
                "INSERT INTO application_scenarios (scenario_id, session_id, level_id, scenarios_json) VALUES (?, ?, ?, ?)",
                (scen_id, self.session_id, self.level_id, json.dumps([{"text": "Build interferometer"}]))
            )
            ai_db.execute(
                "INSERT INTO application_responses (response_id, scenario_id, user_response) VALUES (?, ?, 'Calibrate lasers first')",
                (str(uuid.uuid4()), scen_id)
            )

            # 4. Zayn evidence
            quiz_id = str(uuid.uuid4())
            ai_db.execute(
                "INSERT INTO quizzes (quiz_id, session_id, level_id, questions_json, status) VALUES (?, ?, ?, ?, 'COMPLETED')",
                (quiz_id, self.session_id, self.level_id, json.dumps([{"text": "State Schrodinger equation"}]))
            )
            ai_db.execute(
                "INSERT INTO quiz_responses (response_id, quiz_id, question_id, user_answer, response_time_seconds, is_timeout) VALUES (?, ?, 'q1', 'i hbar d/dt psi = H psi', 25.0, 0)",
                (str(uuid.uuid4()), quiz_id)
            )

    def test_get_evidence_bundle_aggregates_all_four_agents(self):
        bundle = self.interface.get_evidence_bundle(self.session_id, self.level_id, self.user_id)
        self.assertEqual(bundle["session_id"], self.session_id)
        self.assertEqual(bundle["level_id"], self.level_id)
        self.assertEqual(bundle["objective"], "Understand superposition")
        self.assertIn("Superposition", bundle["concepts"])

        # Mira evidence present
        self.assertIn("mira_evidence", bundle)
        self.assertEqual(len(bundle["mira_evidence"]["interactions"]), 1)

        # Ayan evidence present
        self.assertIn("ayan_evidence", bundle)
        self.assertEqual(len(bundle["ayan_evidence"]["responses"]), 1)

        # Kira evidence present
        self.assertIn("kira_evidence", bundle)
        self.assertEqual(len(bundle["kira_evidence"]["responses"]), 1)

        # Zayn evidence present
        self.assertIn("zayn_evidence", bundle)
        self.assertEqual(len(bundle["zayn_evidence"]["responses"]), 1)

        # Profile present
        self.assertIn("learner_profile", bundle)
        self.assertEqual(bundle["learner_profile"]["display_name"], "Test Learner")


class TestEvaluationRoutes(unittest.TestCase):
    def setUp(self):
        init_all_databases()
        self.client = TestClient(app)
        self.user_id = f"user-{uuid.uuid4().hex[:8]}"
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self.level_id = f"lvl-{uuid.uuid4().hex[:8]}"
        self.roadmap_id = f"rm-{uuid.uuid4().hex[:8]}"

        # Override user auth dependency
        app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        # Setup database
        with get_user_db() as u_db:
            u_db.execute("INSERT INTO users (id, email) VALUES (?, ?)", (self.user_id, f"{self.user_id}@test.com"))
            u_db.execute("INSERT INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')", (self.session_id, self.user_id))

        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT OR REPLACE INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
                (self.session_id, self.user_id)
            )
            ai_db.execute("INSERT INTO roadmaps (roadmap_id, session_id, topic) VALUES (?, ?, 'AI')", (self.roadmap_id, self.session_id))
            ai_db.execute("INSERT INTO roadmap_levels (level_id, roadmap_id, level_number, title, objective, status) VALUES (?, ?, 1, 'Search Algorithms', 'Master BFS and DFS', 'UNLOCKED')", (self.level_id, self.roadmap_id))
            ai_db.execute("INSERT INTO level_concepts (concept_id, level_id, concept_name) VALUES (?, ?, 'BFS')", (str(uuid.uuid4()), self.level_id))

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_evaluate_level_requires_quiz_completed(self):
        # Without completed quiz, returns 400
        resp = self.client.post(f"/evaluation/levels/{self.level_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Quiz is not completed", resp.json()["detail"])

    def test_evaluate_level_requires_session_ownership(self):
        other_user = "other-user-999"
        app.dependency_overrides[get_current_user_id] = lambda: other_user
        resp = self.client.post(f"/evaluation/levels/{self.level_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 403)

    @patch("backend.agents.elara.agent.provider_service.generate_content")
    def test_evaluate_level_success_and_persistence(self, mock_generate):
        # 1. Complete quiz in DB
        quiz_id = str(uuid.uuid4())
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT INTO quizzes (quiz_id, session_id, level_id, questions_json, status) VALUES (?, ?, ?, '[]', 'COMPLETED')",
                (quiz_id, self.session_id, self.level_id)
            )

        # 2. Setup orchestration run at QUIZ_COMPLETED
        run_id = OrchestrationService.create_orchestration_state(self.session_id, self.user_id)
        # Advance through orchestration stages up to QUIZ_COMPLETED
        OrchestrationService.transition_state(run_id, self.user_id, "CALA_PROCESSED")
        OrchestrationService.transition_state(run_id, self.user_id, "ROADMAP_CREATED")
        OrchestrationService.transition_state(run_id, self.user_id, "LEVEL_UNLOCKED")
        OrchestrationService.transition_state(run_id, self.user_id, "LEVEL_ENTERED")
        OrchestrationService.transition_state(run_id, self.user_id, "READY_FOR_LEVEL_RESEARCH")
        OrchestrationService.transition_state(run_id, self.user_id, "AYAN_THINKING")
        OrchestrationService.transition_state(run_id, self.user_id, "THINKING_COMPLETED")
        OrchestrationService.transition_state(run_id, self.user_id, "KIRA_APPLICATION")
        OrchestrationService.transition_state(run_id, self.user_id, "APPLICATION_COMPLETED")
        OrchestrationService.transition_state(run_id, self.user_id, "ZAYN_QUIZ")
        OrchestrationService.transition_state(run_id, self.user_id, "QUIZ_COMPLETED")

        # 3. Mock Elara LLM output
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"
        mock_response = ElaraEvaluationResponse(
            evaluation_id=eval_id,
            session_id=self.session_id,
            level_id=self.level_id,
            overall_evaluation="Excellent grasp of search algorithms.",
            concept_evaluations=[
                ConceptEvaluation(
                    concept="BFS",
                    understanding="Accurate FIFO queue understanding",
                    reasoning="Solid step-by-step logic",
                    application="Successfully implemented queue-based search",
                    assessment="100% on BFS questions",
                    mastery_score=0.92,
                    strengths=["Queue implementation", "Shortest path guarantees"],
                    weaknesses=[],
                    mistakes=[],
                    evidence=["teaching_1", "quiz_response_1"]
                )
            ],
            global_strengths=["Algorithmic rigor"],
            global_weaknesses=[],
            evidence_summary="All 4 agents provided positive evidence."
        )
        mock_generate.return_value = mock_response

        # 4. Call evaluation endpoint
        resp = self.client.post(f"/evaluation/levels/{self.level_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["evaluation_id"], eval_id)
        self.assertEqual(len(data["concept_evaluations"]), 1)
        self.assertEqual(data["concept_evaluations"][0]["concept"], "BFS")
        self.assertEqual(data["concept_evaluations"][0]["mastery_score"], 0.92)

        # 5. Verify database persistence in clario_ai.db
        with get_clario_ai_db() as ai_db:
            saved_eval = ai_db.execute("SELECT * FROM elara_evaluations WHERE evaluation_id = ?", (eval_id,)).fetchone()
            self.assertIsNotNone(saved_eval)
            self.assertEqual(saved_eval["overall_evaluation"], "Excellent grasp of search algorithms.")

            saved_concept = ai_db.execute("SELECT * FROM concept_evaluations WHERE evaluation_id = ?", (eval_id,)).fetchone()
            self.assertIsNotNone(saved_concept)
            self.assertEqual(saved_concept["concept_name"], "BFS")
            self.assertEqual(saved_concept["mastery_score"], 0.92)

            # 6. Verify orchestration stage transitioned to EVALUATION_COMPLETED
            current_run = OrchestrationService.get_current_state(run_id)
            self.assertEqual(current_run["current_stage"], "EVALUATION_COMPLETED")

        # 7. Test GET /evaluation/levels/{level_id}
        get_level_resp = self.client.get(f"/evaluation/levels/{self.level_id}?session_id={self.session_id}")
        self.assertEqual(get_level_resp.status_code, 200)
        self.assertEqual(get_level_resp.json()["evaluation_id"], eval_id)

        # 8. Test GET /evaluation/{evaluation_id}
        get_id_resp = self.client.get(f"/evaluation/{eval_id}")
        self.assertEqual(get_id_resp.status_code, 200)
        self.assertEqual(get_id_resp.json()["evaluation_id"], eval_id)


class TestRegressionSessions(unittest.TestCase):
    def setUp(self):
        init_all_databases()
        self.client = TestClient(app)
        self.user_id = f"user-{uuid.uuid4().hex[:8]}"
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"

        app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        with get_user_db() as u_db:
            u_db.execute("INSERT INTO users (id, email) VALUES (?, ?)", (self.user_id, f"{self.user_id}@regression.com"))
            u_db.execute("INSERT INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'CREATED')", (self.session_id, self.user_id))

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_user_sessions_regression(self):
        """Verifies GET /users/{user_id}/sessions remains fully functional."""
        resp = self.client.get(f"/users/{self.user_id}/sessions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], self.session_id)
        self.assertEqual(data[0]["user_id"], self.user_id)

    def test_get_user_sessions_unauthorized_mismatch(self):
        """Verifies accessing another user's sessions returns 403."""
        other_user = "other-user-456"
        resp = self.client.get(f"/users/{other_user}/sessions")
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
