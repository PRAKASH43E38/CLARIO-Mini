import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json
import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.adaptive_decision_service import (
    AdaptiveDecisionService,
    adaptive_decision_service,
    REMEDIATION_APPROACHES
)
from backend.services.orchestration_service import OrchestrationService
from backend.schemas.contracts import (
    AdaptiveDecision,
    ConceptPerformance,
    ElaraEvaluationResponse,
    ConceptEvaluation
)
from backend.database.connection import get_user_db, get_clario_ai_db, init_all_databases
from backend.auth.session import get_current_user_id


class TestPhase12AdaptiveEngine(unittest.TestCase):
    def setUp(self):
        init_all_databases()
        self.client = TestClient(app)
        self.user_id = f"user-{uuid.uuid4().hex[:8]}"
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self.level_1_id = f"lvl1-{uuid.uuid4().hex[:8]}"
        self.level_2_id = f"lvl2-{uuid.uuid4().hex[:8]}"
        self.roadmap_id = f"rm-{uuid.uuid4().hex[:8]}"

        # Override user authentication dependency
        app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        # Seed user database
        with get_user_db() as u_db:
            u_db.execute("INSERT INTO users (id, email) VALUES (?, ?)", (self.user_id, f"{self.user_id}@clario.ai"))
            u_db.execute("INSERT INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')", (self.session_id, self.user_id))

        # Seed clario_ai database
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                "INSERT OR REPLACE INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
                (self.session_id, self.user_id)
            )
            ai_db.execute("INSERT INTO roadmaps (roadmap_id, session_id, topic) VALUES (?, ?, 'Algorithms')", (self.roadmap_id, self.session_id))
            # Level 1 (current)
            ai_db.execute(
                "INSERT INTO roadmap_levels (level_id, roadmap_id, level_number, title, objective, difficulty, status) VALUES (?, ?, 1, 'Graph Search', 'Master BFS and DFS', 'Medium', 'UNLOCKED')",
                (self.level_1_id, self.roadmap_id)
            )
            # Level 2 (next)
            ai_db.execute(
                "INSERT INTO roadmap_levels (level_id, roadmap_id, level_number, title, objective, difficulty, status) VALUES (?, ?, 2, 'Shortest Path', 'Master Dijkstra and A*', 'Medium', 'LOCKED')",
                (self.level_2_id, self.roadmap_id)
            )

    def tearDown(self):
        app.dependency_overrides.clear()

    def _seed_elara_evaluation(self, level_id: str, concept_evals: list[dict], overall: str = "Evaluation summary"):
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"
        with get_clario_ai_db() as ai_db:
            ai_db.execute(
                """
                INSERT INTO elara_evaluations
                (evaluation_id, session_id, level_id, overall_evaluation, global_strengths, global_weaknesses, evidence_summary)
                VALUES (?, ?, ?, ?, '["strength"]', '["weakness"]', 'Summary evidence')
                """,
                (eval_id, self.session_id, level_id, overall)
            )
            for ce in concept_evals:
                ai_db.execute(
                    """
                    INSERT INTO concept_evaluations
                    (concept_eval_id, evaluation_id, concept_name, understanding, reasoning, application, assessment, mastery_score, strengths, weaknesses, mistakes, evidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        eval_id,
                        ce["concept"],
                        ce.get("understanding", "Good grasp"),
                        ce.get("reasoning", "Clear deductive logic"),
                        ce.get("application", "Applied correctly"),
                        ce.get("assessment", "Quiz 90%"),
                        ce.get("mastery_score", 0.9),
                        json.dumps(ce.get("strengths", [])),
                        json.dumps(ce.get("weaknesses", [])),
                        json.dumps(ce.get("mistakes", [])),
                        json.dumps(ce.get("evidence", []))
                    )
                )
        return eval_id

    # -------------------------------------------------------------------------
    # Scenario 1: Strong level → COMPLETE_LEVEL & UNLOCK_NEXT_LEVEL
    # -------------------------------------------------------------------------
    def test_strong_level_completes_level_and_unlocks_next(self):
        self._seed_elara_evaluation(
            self.level_1_id,
            [
                {"concept": "BFS", "mastery_score": 0.92, "mistakes": []},
                {"concept": "DFS", "mastery_score": 0.88, "mistakes": []}
            ]
        )

        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        decision = data["decision"]
        self.assertEqual(decision["decision_type"], "COMPLETE_LEVEL")
        self.assertIn("unlocked", decision["reason"].lower())

        # Check database: level 1 is COMPLETED, level 2 is UNLOCKED
        with get_clario_ai_db() as ai_db:
            lvl1 = ai_db.execute("SELECT status FROM roadmap_levels WHERE level_id = ?", (self.level_1_id,)).fetchone()
            self.assertEqual(lvl1["status"], "COMPLETED")

            lvl2 = ai_db.execute("SELECT status FROM roadmap_levels WHERE level_id = ?", (self.level_2_id,)).fetchone()
            self.assertEqual(lvl2["status"], "UNLOCKED")

    # -------------------------------------------------------------------------
    # Scenario 2 & 3: Weak concept → RETEACH and REDUCE_DIFFICULTY
    # -------------------------------------------------------------------------
    def test_weak_concept_triggers_reteach_and_reduces_difficulty(self):
        # Concept BFS is strong (0.90), Concept DFS is weak (0.55)
        self._seed_elara_evaluation(
            self.level_1_id,
            [
                {"concept": "BFS", "mastery_score": 0.90, "mistakes": []},
                {"concept": "DFS", "mastery_score": 0.55, "mistakes": ["Infinite recursion on cyclic graph"]}
            ]
        )

        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        decision = data["decision"]
        self.assertEqual(decision["decision_type"], "RETEACH")
        self.assertEqual(decision["target_concept"], "DFS")
        self.assertEqual(decision["target_agent"], "mira")
        self.assertEqual(decision["new_difficulty"], "Easy")

    # -------------------------------------------------------------------------
    # Scenario 4: Retest after remediation
    # -------------------------------------------------------------------------
    def test_retest_after_remediation(self):
        self._seed_elara_evaluation(
            self.level_1_id,
            [
                {"concept": "BFS", "mastery_score": 0.95, "mistakes": []},
                {"concept": "DFS", "mastery_score": 0.60, "mistakes": ["Missed visited set"]}
            ]
        )
        self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")

        # Trigger remediation for DFS
        rem_resp = self.client.post(f"/adaptive/remediate/{self.level_1_id}?session_id={self.session_id}")
        self.assertEqual(rem_resp.status_code, 200)
        rem_data = rem_resp.json()

        self.assertEqual(rem_data["concept"], "DFS")
        self.assertIn("retest_task", rem_data)
        self.assertTrue(rem_data["retest_task"]["is_retest"])
        self.assertEqual(rem_data["retest_task"]["concept"], "DFS")
        self.assertEqual(rem_data["status"], "ready_for_retest")

    # -------------------------------------------------------------------------
    # Scenario 5: Strong concepts remain untouched (Concept Isolation)
    # -------------------------------------------------------------------------
    def test_concept_isolation_strong_concepts_remain_untouched(self):
        # A = mastered, B = weak, C = mastered
        self._seed_elara_evaluation(
            self.level_1_id,
            [
                {"concept": "Concept A", "mastery_score": 0.95, "mistakes": []},
                {"concept": "Concept B", "mastery_score": 0.50, "mistakes": ["Fundamental misunderstanding"]},
                {"concept": "Concept C", "mastery_score": 0.91, "mistakes": []}
            ]
        )

        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 200)

        concept_perfs = {cp["concept"]: cp for cp in resp.json()["concept_performances"]}

        # Concept A and C are mastered and NOT in remediation
        self.assertEqual(concept_perfs["Concept A"]["status"], "mastered")
        self.assertEqual(concept_perfs["Concept C"]["status"], "mastered")

        # ONLY Concept B enters remediation
        self.assertEqual(concept_perfs["Concept B"]["status"], "remediating")

        # Decision specifically isolates Concept B
        decision = resp.json()["decision"]
        self.assertEqual(decision["target_concept"], "Concept B")

    # -------------------------------------------------------------------------
    # Scenario 6: Concept-specific difficulty change
    # -------------------------------------------------------------------------
    def test_concept_specific_difficulty_change(self):
        # Initial evaluation: Concept A (0.95) advances, Concept B (0.50) drops
        self._seed_elara_evaluation(
            self.level_1_id,
            [
                {"concept": "Concept A", "mastery_score": 0.95, "mistakes": []},
                {"concept": "Concept B", "mastery_score": 0.50, "mistakes": ["Syntax error"]}
            ]
        )

        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")
        concept_perfs = {cp["concept"]: cp for cp in resp.json()["concept_performances"]}

        # Concept A moved up to Hard
        self.assertEqual(concept_perfs["Concept A"]["difficulty"], "Hard")
        # Concept B reduced to Easy
        self.assertEqual(concept_perfs["Concept B"]["difficulty"], "Easy")

    # -------------------------------------------------------------------------
    # Scenario 7: Different remediation path (Approach rotation)
    # -------------------------------------------------------------------------
    def test_remediation_uses_different_approach_on_subsequent_attempts(self):
        self._seed_elara_evaluation(
            self.level_1_id,
            [{"concept": "Recursion", "mastery_score": 0.50, "mistakes": ["Stack overflow"]}]
        )
        self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")

        # First remediation
        rem1 = self.client.post(f"/adaptive/remediate/{self.level_1_id}?session_id={self.session_id}&concept=Recursion").json()
        approach_1 = rem1["approach"]

        # Second remediation
        rem2 = self.client.post(f"/adaptive/remediate/{self.level_1_id}?session_id={self.session_id}&concept=Recursion").json()
        approach_2 = rem2["approach"]

        self.assertNotEqual(approach_1, approach_2, "Remediation approach must rotate and be different!")

    # -------------------------------------------------------------------------
    # Scenario 8: Mastery threshold handling (80-90% range)
    # -------------------------------------------------------------------------
    def test_mastery_threshold_handling(self):
        # 0.79 is below 0.80 -> remediating
        self._seed_elara_evaluation(
            self.level_1_id,
            [{"concept": "ThresholdConcept", "mastery_score": 0.79, "mistakes": []}]
        )
        resp1 = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}").json()
        self.assertEqual(resp1["decision"]["decision_type"], "RETEACH")

        # 0.82 with 0 mistakes -> mastered
        self._seed_elara_evaluation(
            self.level_1_id,
            [{"concept": "ThresholdConcept", "mastery_score": 0.82, "mistakes": []}]
        )
        resp2 = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}&force=true", json={"force": True}).json()
        self.assertEqual(resp2["decision"]["decision_type"], "COMPLETE_LEVEL")

    # -------------------------------------------------------------------------
    # Scenario 9: Repeated mistakes block completion even near threshold
    # -------------------------------------------------------------------------
    def test_repeated_mistakes_prevent_completion(self):
        # 0.81 but with 3 repeated mistakes -> requires remediation
        self._seed_elara_evaluation(
            self.level_1_id,
            [{"concept": "TrickyConcept", "mastery_score": 0.81, "mistakes": ["Off-by-one", "Memory leak", "Sign error"]}]
        )
        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}").json()
        self.assertEqual(resp["decision"]["decision_type"], "RETEACH")
        self.assertEqual(resp["decision"]["target_concept"], "TrickyConcept")

    # -------------------------------------------------------------------------
    # Scenario 10: Meaningful struggle detection
    # -------------------------------------------------------------------------
    def test_meaningful_struggle_detection(self):
        self._seed_elara_evaluation(
            self.level_1_id,
            [{"concept": "ComplexTopic", "mastery_score": 0.45, "mistakes": ["Misconception A", "Misconception B"]}]
        )
        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}").json()

        struggle = resp.get("struggle_intervention")
        self.assertIsNotNone(struggle)
        self.assertTrue(struggle["struggle_detected"])
        self.assertIn("explain it another way", struggle["intervention_message"].lower())
        self.assertIn("Explain Differently", struggle["options"])

    # -------------------------------------------------------------------------
    # Scenario 11: Invalid state transition
    # -------------------------------------------------------------------------
    def test_invalid_state_transition_rejected(self):
        run_id = OrchestrationService.create_orchestration_state(self.session_id, self.user_id)
        # Attempt illegal jump directly from SESSION_CREATED to COMPLETE_LEVEL
        with self.assertRaises(ValueError):
            OrchestrationService.transition_state(run_id, self.user_id, "COMPLETE_LEVEL")

    # -------------------------------------------------------------------------
    # Scenario 12: Duplicate decision prevention (Idempotency)
    # -------------------------------------------------------------------------
    def test_duplicate_decision_prevention_idempotency(self):
        self._seed_elara_evaluation(
            self.level_1_id,
            [{"concept": "BFS", "mastery_score": 0.95, "mistakes": []}]
        )

        resp1 = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}").json()
        dec_id_1 = resp1["decision"]["decision_id"]
        self.assertFalse(resp1.get("idempotent", False))

        # Repeated request without force
        resp2 = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}").json()
        dec_id_2 = resp2["decision"]["decision_id"]
        self.assertTrue(resp2.get("idempotent", True))
        self.assertEqual(dec_id_1, dec_id_2, "Subsequent calls must return the identical decision idempotently")

    # -------------------------------------------------------------------------
    # Scenario 13: Authentication required
    # -------------------------------------------------------------------------
    def test_adaptive_endpoints_require_authentication(self):
        # Clear override
        app.dependency_overrides.clear()
        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 401)

    # -------------------------------------------------------------------------
    # Scenario 14: Ownership check
    # -------------------------------------------------------------------------
    def test_adaptive_endpoints_enforce_session_ownership(self):
        app.dependency_overrides[get_current_user_id] = lambda: "unauthorized-intruder"
        resp = self.client.post(f"/adaptive/evaluate/{self.level_1_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 403)

    # -------------------------------------------------------------------------
    # Scenario 15: Final level completion triggers COMPLETE_GOAL
    # -------------------------------------------------------------------------
    def test_final_level_completion_triggers_complete_goal(self):
        # Evaluate Level 2 (the final level in the roadmap)
        self._seed_elara_evaluation(
            self.level_2_id,
            [{"concept": "Dijkstra", "mastery_score": 0.95, "mistakes": []}]
        )

        resp = self.client.post(f"/adaptive/evaluate/{self.level_2_id}?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"]["decision_type"], "COMPLETE_GOAL")
        self.assertIn("completed successfully", data["decision"]["reason"])


if __name__ == "__main__":
    unittest.main()
