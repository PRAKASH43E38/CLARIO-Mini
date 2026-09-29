import unittest
from unittest.mock import patch, MagicMock
import json
import uuid
import asyncio

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.end_to_end_loop_service import EndToEndLoopService, end_to_end_loop_service
from backend.services.orchestration_service import OrchestrationService
from backend.services.adaptive_decision_service import adaptive_decision_service
from backend.database.connection import get_user_db, get_clario_ai_db, init_all_databases
from backend.auth.session import get_current_user_id


class TestPhase13EndToEndLoop(unittest.TestCase):
    def setUp(self):
        init_all_databases()
        self.client = TestClient(app)
        self.user_id = f"user-{uuid.uuid4().hex[:8]}"
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"

        # Override user authentication dependency
        app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        # Seed full user profile, 5 mind questions, 4 session inputs
        with get_user_db() as u_db:
            u_db.execute(
                "INSERT INTO users (id, email) VALUES (?, ?)",
                (self.user_id, f"{self.user_id}@clario.ai")
            )
            u_db.execute(
                "INSERT INTO user_profiles (user_id, display_name, preferences_json) VALUES (?, 'Test User', '{\"learning_style\": \"visual\"}')",
                (self.user_id,)
            )
            # 5 Mind Questions
            mind_answers = [
                "I prefer visual diagrams and structured breakdowns.",
                "I have high intrinsic motivation to build real-world AI applications.",
                "I can dedicate 45 minutes per day in focused blocks.",
                "I have intermediate background in Python and mathematics.",
                "I learn fastest by doing hands-on challenges and scenario puzzles."
            ]
            u_db.execute(
                "INSERT INTO mind_profiles (user_id, answers_json) VALUES (?, ?)",
                (self.user_id, json.dumps(mind_answers))
            )
            # Session & 4 Session Inputs
            u_db.execute(
                "INSERT INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
                (self.session_id, self.user_id)
            )
            u_db.execute(
                """
                INSERT INTO session_inputs (session_id, task, goal, learner_state, interest)
                VALUES (?, 'Build Graph Neural Networks from scratch', 'Master Graph Neural Networks', 'beginner', 'Deep Learning')
                """,
                (self.session_id,)
            )

        # Mirror session to clario_ai.db
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT OR REPLACE INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
                (self.session_id, self.user_id)
            )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_01_journey_initialization(self):
        """
        Verify: USER -> AUTH -> 5 MIND -> 4 SESSION INPUTS -> CALA -> ROADMAP -> CLARIO-AI -> LEVEL 1 UNLOCK
        """
        response = self.client.post("/orchestration/loop/initialize", json={"session_id": self.session_id})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()

        self.assertIn("run_id", data)
        self.assertEqual(data["session_id"], self.session_id)
        self.assertEqual(data["stage"], "LEVEL_UNLOCKED")
        self.assertGreaterEqual(data["roadmap_levels_count"], 1)
        self.assertIsNotNone(data["current_level_id"])

        # Check in DB that Level 1 is UNLOCKED
        with get_clario_ai_db() as ai_db:
            lvl1 = ai_db.execute(
                "SELECT * FROM roadmap_levels WHERE level_id = ?",
                (data["current_level_id"],)
            ).fetchone()
            self.assertIsNotNone(lvl1)
            self.assertEqual(lvl1["status"], "UNLOCKED")
            self.assertEqual(lvl1["level_number"], 1)

    def test_02_level_entry(self):
        """
        Verify: LEVEL ENTRY -> READY_FOR_LEVEL_RESEARCH
        """
        init_res = self.client.post("/orchestration/loop/initialize", json={"session_id": self.session_id})
        level_1_id = init_res.json()["current_level_id"]

        entry_res = self.client.post(f"/orchestration/loop/enter-level/{level_1_id}")
        self.assertEqual(entry_res.status_code, 200, entry_res.text)
        data = entry_res.json()

        self.assertEqual(data["level_id"], level_1_id)
        self.assertEqual(data["status"], "READY_FOR_LEVEL_RESEARCH")
        self.assertTrue(len(data["title"]) > 0)

    def test_03_successful_level_completion_and_unlock_next(self):
        """
        Verify: NOVA -> MIRA -> AYAN -> KIRA -> ZAYN -> ELARA -> CLARIO-AI DECISION -> LEVEL COMPLETE -> UNLOCK NEXT LEVEL
        """
        init_res = self.client.post("/orchestration/loop/initialize", json={"session_id": self.session_id})
        level_1_id = init_res.json()["current_level_id"]

        # Run level flow with high mastery scores (passing >= 0.80)
        run_res = self.client.post(
            f"/orchestration/loop/run-level/{level_1_id}",
            json={
                "session_id": self.session_id,
                "simulated_answers": {
                    "concept_scores": {"Graph Foundations": 0.95, "Adjacency Matrix": 0.88}
                }
            }
        )
        self.assertEqual(run_res.status_code, 200, run_res.text)
        data = run_res.json()

        # Check all agents executed in strict order
        expected_agents = ["nova", "mira", "ayan", "kira", "zayn", "elara", "clario_ai"]
        self.assertEqual(data["executed_agents"], expected_agents)

        # Decision should be COMPLETE_LEVEL
        self.assertEqual(data["stage"], "COMPLETE_LEVEL")
        self.assertEqual(data["decision"]["decision_type"], "COMPLETE_LEVEL")

        # Verify next level is unlocked in database
        with get_clario_ai_db() as ai_db:
            lvl1 = ai_db.execute("SELECT status FROM roadmap_levels WHERE level_id = ?", (level_1_id,)).fetchone()
            self.assertEqual(lvl1["status"], "COMPLETED")

            lvl2 = ai_db.execute(
                """
                SELECT rl.status FROM roadmap_levels rl
                JOIN roadmaps r ON rl.roadmap_id = r.roadmap_id
                WHERE r.session_id = ? AND rl.level_number = 2
                """,
                (self.session_id,)
            ).fetchone()
            if lvl2:
                self.assertEqual(lvl2["status"], "UNLOCKED")

    def test_04_remediation_branch_and_retest(self):
        """
        Verify: ELARA (<0.80) -> CLARIO-AI (REMEDIATE) -> MIRA RETEACH -> RETEST -> ELARA -> CLARIO-AI
        """
        init_res = self.client.post("/orchestration/loop/initialize", json={"session_id": self.session_id})
        level_1_id = init_res.json()["current_level_id"]

        # Fetch concept for Level 1
        with get_clario_ai_db() as ai_db:
            lvl_row = ai_db.execute("SELECT title FROM roadmap_levels WHERE level_id = ?", (level_1_id,)).fetchone()
            target_concept = lvl_row["title"]

        # 1. Run Level Flow with low score on target_concept
        run_res = self.client.post(
            f"/orchestration/loop/run-level/{level_1_id}",
            json={
                "session_id": self.session_id,
                "simulated_answers": {
                    "concept_scores": {target_concept: 0.55},
                    f"mistakes_{target_concept}": ["Inverted directed edge causality"]
                }
            }
        )
        self.assertEqual(run_res.status_code, 200, run_res.text)
        data = run_res.json()

        # Decision must be RETEACH / REMEDIATE
        self.assertIn(data["stage"], ["RETEACH", "REMEDIATE"])
        self.assertIn(data["decision"]["decision_type"], ["RETEACH", "REMEDIATE"])
        self.assertEqual(data["decision"]["target_concept"], target_concept)

        # 2. Trigger Remediation Cycle
        rem_res = self.client.post(
            f"/orchestration/loop/remediate-cycle/{level_1_id}",
            json={
                "session_id": self.session_id,
                "concept": target_concept,
                "simulated_retest_score": 0.95
            }
        )
        self.assertEqual(rem_res.status_code, 200, rem_res.text)
        rem_data = rem_res.json()

        self.assertEqual(rem_data["status"], "remediation_cycle_completed")
        self.assertEqual(rem_data["remediation_package"]["concept"], target_concept)
        self.assertIn("reteaching_content", rem_data["remediation_package"])
        self.assertIn("retest_task", rem_data["remediation_package"])

        # Post-retest decision should now advance towards level completion
        post_decision = rem_data["decision"]
        self.assertEqual(post_decision["decision_type"], "COMPLETE_LEVEL")

    def test_05_journey_status_endpoint(self):
        """
        Verify: GET /orchestration/loop/status/{session_id} tracks full learning journey
        """
        # Initialize
        self.client.post("/orchestration/loop/initialize", json={"session_id": self.session_id})

        # Fetch status
        res = self.client.get(f"/orchestration/loop/status/{self.session_id}")
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()

        self.assertEqual(data["session_id"], self.session_id)
        self.assertEqual(data["current_stage"], "LEVEL_UNLOCKED")
        self.assertIn("roadmap", data)
        self.assertGreater(len(data["roadmap"]["levels"]), 0)

    def test_06_goal_completion_on_final_level(self):
        """
        Verify: When completing the final level of a roadmap, CLARIO-AI triggers COMPLETE_GOAL.
        """
        init_res = self.client.post("/orchestration/loop/initialize", json={"session_id": self.session_id})
        level_1_id = init_res.json()["current_level_id"]

        # Mark all other levels as already completed except the last one, or test single-level completion
        with get_clario_ai_db() as ai_db:
            # Find roadmap_id
            rm_row = ai_db.execute("SELECT roadmap_id FROM roadmaps WHERE session_id = ?", (self.session_id,)).fetchone()
            roadmap_id = rm_row["roadmap_id"]

            # Remove extra levels so level 1 is the ONLY and FINAL level
            ai_db.execute("DELETE FROM roadmap_levels WHERE roadmap_id = ? AND level_number > 1", (roadmap_id,))

        # Run level 1 to mastery
        run_res = self.client.post(
            f"/orchestration/loop/run-level/{level_1_id}",
            json={
                "session_id": self.session_id,
                "simulated_answers": {
                    "concept_scores": {"Graph Foundations": 0.95}
                }
            }
        )
        self.assertEqual(run_res.status_code, 200, run_res.text)
        data = run_res.json()

        # Decision should be COMPLETE_GOAL since there are no more levels
        self.assertEqual(data["stage"], "COMPLETE_GOAL")
        self.assertEqual(data["decision"]["decision_type"], "COMPLETE_GOAL")

        # Session in clario_ai.db should now be marked GOAL_COMPLETED
        with get_clario_ai_db() as ai_db:
            sess = ai_db.execute("SELECT status FROM learning_sessions WHERE session_id = ?", (self.session_id,)).fetchone()
            self.assertEqual(sess["status"], "GOAL_COMPLETED")


if __name__ == "__main__":
    unittest.main()
