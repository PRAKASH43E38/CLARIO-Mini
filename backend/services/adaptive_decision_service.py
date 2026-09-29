import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.database.connection import get_clario_ai_db, get_user_db
from backend.schemas.contracts import (
    AdaptiveDecision,
    ConceptPerformance,
    ElaraEvaluationResponse,
    ConceptEvaluation,
    AgentTask,
)
from backend.services.orchestration_service import OrchestrationService
from backend.agents.mira.agent import mira_agent
from backend.agents.zayn.agent import zayn_agent

logger = logging.getLogger(__name__)

# Pedagogy approaches rotated during remediation
REMEDIATION_APPROACHES = [
    "First-principles decomposition and step-by-step causal derivation",
    "Analogy-driven intuitive model with everyday experiential metaphors",
    "Contrastive analysis with common counter-examples and non-examples",
    "Visual scaffolding breakdown and schematic mental model"
]

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]


class AdaptiveDecisionService:
    """
    Deterministic CLARIO-AI Adaptive Decision Layer.
    Responsible for deciding WHAT SHOULD HAPPEN NEXT based on Elara's evaluation,
    enforcing strict concept isolation, concept-specific difficulty adaptation,
    and safe remediation loops without circular runaway.
    """

    MASTERY_THRESHOLD = 0.80
    ADVANCED_MASTERY_THRESHOLD = 0.90
    MAX_REMEDIATION_ATTEMPTS = 3

    @classmethod
    def make_decision(
        cls,
        session_id: str,
        level_id: str,
        user_id: str,
        force_reevaluate: bool = False
    ) -> Dict[str, Any]:
        """
        Determines the next pedagogical step deterministically.
        Idempotent: returns existing decision if already created for the latest evaluation.
        """
        # 1. Fetch the latest Elara evaluation
        evaluation_data = cls._get_latest_evaluation(session_id, level_id)
        if not evaluation_data:
            raise ValueError(f"No Elara evaluation found for level {level_id}. Evaluation must precede decision.")

        eval_id = evaluation_data["evaluation_id"]

        # 2. Check Idempotency: Has an adaptive decision already been recorded for this evaluation?
        if not force_reevaluate:
            existing_decision = cls._get_existing_decision(session_id, level_id, eval_id)
            if existing_decision:
                concept_perfs = cls.get_concept_performances(session_id, level_id)
                struggle = cls.detect_meaningful_struggle(session_id, level_id)
                return {
                    "decision": existing_decision,
                    "concept_performances": [cp.model_dump() for cp in concept_perfs],
                    "struggle_intervention": struggle,
                    "idempotent": True
                }

        # 3. Process Concept Evaluations with Strict Concept Isolation
        concept_evals = evaluation_data.get("concept_evaluations", [])
        if not concept_evals:
            raise ValueError(f"Evaluation {eval_id} contains no concept evaluations.")

        updated_performances: List[ConceptPerformance] = []
        weak_concepts: List[ConceptPerformance] = []
        mastered_concepts: List[ConceptPerformance] = []

        with get_clario_ai_db() as ai_db:
            for c_eval in concept_evals:
                concept_name = c_eval["concept"]
                mastery_score = float(c_eval.get("mastery_score", 0.0))
                mistakes = c_eval.get("mistakes", [])
                if isinstance(mistakes, str):
                    try:
                        mistakes = json.loads(mistakes)
                    except Exception:
                        mistakes = [mistakes]

                # Fetch prior performance if any
                prior_row = ai_db.execute(
                    "SELECT * FROM concept_performance WHERE session_id = ? AND level_id = ? AND concept = ?",
                    (session_id, level_id, concept_name)
                ).fetchone()

                prior_attempts = prior_row["attempts"] if prior_row else 0
                prior_difficulty = prior_row["difficulty"] if prior_row else "Medium"
                prior_status = prior_row["status"] if prior_row else "learning"

                current_attempts = prior_attempts + 1

                # Deterministic mastery judgment:
                # 80-90% target, taking into account mistake density
                has_critical_mistakes = len(mistakes) >= 2
                is_mastered = (mastery_score >= cls.MASTERY_THRESHOLD) and not (has_critical_mistakes and mastery_score < 0.85)

                if is_mastered:
                    new_status = "mastered"
                    # Appropriate difficulty adaptation for strong concept
                    if mastery_score >= cls.ADVANCED_MASTERY_THRESHOLD and prior_difficulty != "Hard":
                        new_diff = "Hard" if prior_difficulty == "Medium" else "Medium"
                    else:
                        new_diff = prior_difficulty
                else:
                    new_status = "remediating"
                    # Concept-specific difficulty reduction
                    if prior_difficulty == "Hard":
                        new_diff = "Medium"
                    else:
                        new_diff = "Easy"

                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                # Upsert into concept_performance
                ai_db.execute(
                    """
                    INSERT INTO concept_performance
                    (id, session_id, level_id, concept, understanding, reasoning, application, assessment,
                     mastery_score, difficulty, attempts, mistakes_json, status, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, level_id, concept) DO UPDATE SET
                        understanding = excluded.understanding,
                        reasoning = excluded.reasoning,
                        application = excluded.application,
                        assessment = excluded.assessment,
                        mastery_score = excluded.mastery_score,
                        difficulty = excluded.difficulty,
                        attempts = excluded.attempts,
                        mistakes_json = excluded.mistakes_json,
                        status = excluded.status,
                        last_updated = excluded.last_updated
                    """,
                    (
                        str(uuid.uuid4()),
                        session_id,
                        level_id,
                        concept_name,
                        c_eval.get("understanding", ""),
                        c_eval.get("reasoning", ""),
                        c_eval.get("application", ""),
                        c_eval.get("assessment", ""),
                        mastery_score,
                        new_diff,
                        current_attempts,
                        json.dumps(mistakes),
                        new_status,
                        now_str
                    )
                )

                perf = ConceptPerformance(
                    session_id=session_id,
                    level_id=level_id,
                    concept=concept_name,
                    understanding=c_eval.get("understanding"),
                    reasoning=c_eval.get("reasoning"),
                    application=c_eval.get("application"),
                    assessment=c_eval.get("assessment"),
                    mastery_score=mastery_score,
                    difficulty=new_diff,
                    attempts=current_attempts,
                    mistakes=mistakes,
                    status=new_status,
                    last_updated=datetime.now(timezone.utc)
                )
                updated_performances.append(perf)

                if new_status == "mastered":
                    mastered_concepts.append(perf)
                else:
                    weak_concepts.append(perf)

        # 4. Synthesize Level Decision
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        now_dt = datetime.now(timezone.utc)

        if len(weak_concepts) == 0:
            # BRANCH A: All concepts mastered! Complete level and check for roadmap unlock
            decision_type, reason, target_agent = cls._handle_level_completion(session_id, level_id, user_id)
            target_concept = None
            old_diff = None
            new_diff = None
            avg_mastery = sum(cp.mastery_score for cp in updated_performances) / len(updated_performances)

            decision = AdaptiveDecision(
                decision_id=decision_id,
                session_id=session_id,
                level_id=level_id,
                decision_type=decision_type,
                reason=reason,
                target_concept=None,
                target_agent=target_agent,
                old_difficulty=None,
                new_difficulty=None,
                mastery_score=round(avg_mastery, 3),
                created_at=now_dt
            )
        else:
            # BRANCH B: Concept Isolation — Only weak concept(s) enter remediation
            # Pick the most critical weak concept (lowest mastery score)
            target_weak = min(weak_concepts, key=lambda cp: cp.mastery_score)
            target_concept = target_weak.concept
            old_diff = prior_difficulty if 'prior_difficulty' in locals() else "Medium"
            new_diff = target_weak.difficulty

            # Check safe attempt limit (avoid infinite runaway loops)
            if target_weak.attempts > cls.MAX_REMEDIATION_ATTEMPTS:
                decision_type = "RETEACH"
                reason = (
                    f"Concept '{target_concept}' has reached {target_weak.attempts} attempts with mastery {target_weak.mastery_score:.2f}. "
                    f"Applying alternative scaffolding and struggle intervention rather than repeating identical loops."
                )
            else:
                decision_type = "RETEACH"
                reason = (
                    f"Concept '{target_concept}' achieved mastery of {target_weak.mastery_score:.2f} (< {cls.MASTERY_THRESHOLD:.2f}) "
                    f"with {len(target_weak.mistakes)} recorded mistakes. "
                    f"Reducing difficulty to {new_diff} and targeting solely this concept for differentiated reteach."
                )

            decision = AdaptiveDecision(
                decision_id=decision_id,
                session_id=session_id,
                level_id=level_id,
                decision_type=decision_type,
                reason=reason,
                target_concept=target_concept,
                target_agent="mira",
                old_difficulty=old_diff,
                new_difficulty=new_diff,
                mastery_score=target_weak.mastery_score,
                created_at=now_dt
            )

            # Advance state machine
            cls._transition_state_safe(session_id, user_id, "ADAPTIVE_DECISION")
            cls._transition_state_safe(session_id, user_id, "REMEDIATE")
            cls._transition_state_safe(session_id, user_id, "REDUCE_DIFFICULTY")

        # 5. Persist Adaptive Decision to clario_ai.db
        cls._persist_decision(decision, eval_id)

        # 6. Check for Meaningful Struggle Intervention
        struggle = cls.detect_meaningful_struggle(session_id, level_id)

        return {
            "decision": decision.model_dump(),
            "concept_performances": [cp.model_dump() for cp in updated_performances],
            "struggle_intervention": struggle,
            "idempotent": False
        }

    @classmethod
    def remediate_concept(
        cls,
        session_id: str,
        level_id: str,
        user_id: str,
        concept: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a targeted, differentiated remediation package for ONLY the weak concept.
        Strong concepts remain completely untouched.
        Uses a DIFFERENT pedagogical explanation approach and DIFFERENT retest task.
        """
        with get_clario_ai_db() as ai_db:
            # 1. Determine target weak concept
            if concept:
                target_concept_name = concept
            else:
                # Find most recent weak concept marked remediating
                weak_row = ai_db.execute(
                    """
                    SELECT concept FROM concept_performance
                    WHERE session_id = ? AND level_id = ? AND status = 'remediating'
                    ORDER BY mastery_score ASC, last_updated DESC LIMIT 1
                    """,
                    (session_id, level_id)
                ).fetchone()
                if not weak_row:
                    raise ValueError(f"No concept in level {level_id} currently requires remediation.")
                target_concept_name = weak_row["concept"]

            perf_row = ai_db.execute(
                "SELECT * FROM concept_performance WHERE session_id = ? AND level_id = ? AND concept = ?",
                (session_id, level_id, target_concept_name)
            ).fetchone()

            if not perf_row:
                raise ValueError(f"Concept '{target_concept_name}' not found in performance registry.")

            current_difficulty = perf_row["difficulty"]
            mistakes = json.loads(perf_row["mistakes_json"]) if perf_row["mistakes_json"] else []

            # 2. Select a DIFFERENT remediation approach from history
            prior_history = ai_db.execute(
                "SELECT approach FROM remediation_history WHERE session_id = ? AND level_id = ? AND concept = ?",
                (session_id, level_id, target_concept_name)
            ).fetchall()
            used_approaches = {r["approach"] for r in prior_history}

            available_approaches = [a for a in REMEDIATION_APPROACHES if a not in used_approaches]
            chosen_approach = available_approaches[0] if available_approaches else REMEDIATION_APPROACHES[0]

            # 3. Create Differentiated Remediation Content (Mira leaf delegation)
            remediation_explanation = (
                f"### Differentiated Remediation: {target_concept_name}\n"
                f"**Pedagogical Angle**: {chosen_approach}\n\n"
                f"Let's break down {target_concept_name} from a fresh perspective. "
                f"Previously, you encountered difficulty with: {', '.join(mistakes) if mistakes else 'core foundational logic'}.\n\n"
                f"#### Core Principle:\n"
                f"{target_concept_name} can be understood intuitively when we strip away extraneous parameters. "
                f"Focus on the primary invariants and observe how the fundamental state transforms."
            )

            # 4. Create Targeted Retest Task (Zayn leaf delegation)
            retest_question_id = f"retest-q-{uuid.uuid4().hex[:8]}"
            retest_task = {
                "question_id": retest_question_id,
                "concept": target_concept_name,
                "difficulty": current_difficulty,
                "question_text": f"Apply {target_concept_name} using the fresh perspective: What is the primary invariant condition under transformation?",
                "expected_answer": f"The fundamental invariant state of {target_concept_name}",
                "is_retest": True
            }

            # 5. Persist to remediation_history
            remediation_id = f"rem-{uuid.uuid4().hex[:12]}"
            ai_db.execute(
                """
                INSERT INTO remediation_history
                (id, session_id, level_id, concept, decision_id, approach, old_difficulty, new_difficulty,
                 remediation_content, retest_content, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """,
                (
                    remediation_id,
                    session_id,
                    level_id,
                    target_concept_name,
                    None,
                    chosen_approach,
                    "Medium" if current_difficulty == "Easy" else "Hard",
                    current_difficulty,
                    remediation_explanation,
                    json.dumps(retest_task)
                )
            )

        # 6. Advance state machine safely outside the db context manager
        cls._transition_state_safe(session_id, user_id, "MIRA_RETEACH")
        cls._transition_state_safe(session_id, user_id, "TARGETED_RETEST")

        return {
            "remediation_id": remediation_id,
            "concept": target_concept_name,
            "approach": chosen_approach,
            "difficulty": current_difficulty,
            "reteaching_content": remediation_explanation,
            "retest_task": retest_task,
            "status": "ready_for_retest"
        }

    @classmethod
    def detect_meaningful_struggle(
        cls,
        session_id: str,
        level_id: str,
        concept: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Identifies signals of meaningful struggle (repeated mistakes, multiple attempts with low mastery,
        timeouts, confusion) and returns an actionable intervention.
        """
        with get_clario_ai_db() as ai_db:
            query = "SELECT * FROM concept_performance WHERE session_id = ? AND level_id = ?"
            params = [session_id, level_id]
            if concept:
                query += " AND concept = ?"
                params.append(concept)

            rows = ai_db.execute(query, params).fetchall()
            for r in rows:
                mistakes = json.loads(r["mistakes_json"]) if r["mistakes_json"] else []
                attempts = r["attempts"]
                mastery = r["mastery_score"]

                struggle_signals = []
                if len(mistakes) >= 2:
                    struggle_signals.append(f"Repeated mistakes on {r['concept']} ({len(mistakes)} recorded)")
                if attempts >= 2 and mastery < 0.70:
                    struggle_signals.append(f"Multiple attempts ({attempts}) with mastery at {mastery:.2f}")

                # Check quiz timeout signals
                timeout_row = ai_db.execute(
                    """
                    SELECT COUNT(*) as timeout_cnt FROM quiz_responses qr
                    JOIN quizzes q ON qr.quiz_id = q.quiz_id
                    WHERE q.session_id = ? AND q.level_id = ? AND qr.is_timeout = 1
                    """,
                    (session_id, level_id)
                ).fetchone()

                if timeout_row and timeout_row["timeout_cnt"] > 0:
                    struggle_signals.append("Response timeouts detected during assessment")

                if struggle_signals:
                    return {
                        "struggle_detected": True,
                        "target_concept": r["concept"],
                        "intervention_message": "I noticed this part may be difficult. Would you like me to explain it another way?",
                        "options": [
                            "Explain Differently",
                            "Continue",
                            "Tell CLARIO what's difficult"
                        ],
                        "signals": struggle_signals
                    }

        return None

    @classmethod
    def get_concept_performances(cls, session_id: str, level_id: str) -> List[ConceptPerformance]:
        """Retrieves current concept performances for a level."""
        with get_clario_ai_db() as ai_db:
            rows = ai_db.execute(
                "SELECT * FROM concept_performance WHERE session_id = ? AND level_id = ? ORDER BY concept ASC",
                (session_id, level_id)
            ).fetchall()

            results = []
            for r in rows:
                mistakes = json.loads(r["mistakes_json"]) if r["mistakes_json"] else []
                results.append(
                    ConceptPerformance(
                        session_id=r["session_id"],
                        level_id=r["level_id"],
                        concept=r["concept"],
                        understanding=r["understanding"],
                        reasoning=r["reasoning"],
                        application=r["application"],
                        assessment=r["assessment"],
                        mastery_score=r["mastery_score"],
                        difficulty=r["difficulty"],
                        attempts=r["attempts"],
                        mistakes=mistakes,
                        status=r["status"],
                        last_updated=datetime.fromisoformat(r["last_updated"]) if isinstance(r["last_updated"], str) else r["last_updated"]
                    )
                )
            return results

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    @classmethod
    def _get_latest_evaluation(cls, session_id: str, level_id: str) -> Optional[Dict[str, Any]]:
        with get_clario_ai_db() as ai_db:
            eval_row = ai_db.execute(
                """
                SELECT * FROM elara_evaluations
                WHERE session_id = ? AND level_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT 1
                """,
                (session_id, level_id)
            ).fetchone()

            if not eval_row:
                return None

            concept_rows = ai_db.execute(
                "SELECT * FROM concept_evaluations WHERE evaluation_id = ?",
                (eval_row["evaluation_id"],)
            ).fetchall()

            concepts = []
            for cr in concept_rows:
                concepts.append({
                    "concept": cr["concept_name"],
                    "understanding": cr["understanding"],
                    "reasoning": cr["reasoning"],
                    "application": cr["application"],
                    "assessment": cr["assessment"],
                    "mastery_score": cr["mastery_score"],
                    "strengths": json.loads(cr["strengths"]) if cr["strengths"] else [],
                    "weaknesses": json.loads(cr["weaknesses"]) if cr["weaknesses"] else [],
                    "mistakes": json.loads(cr["mistakes"]) if cr["mistakes"] else [],
                    "evidence": json.loads(cr["evidence"]) if cr["evidence"] else []
                })

            return {
                "evaluation_id": eval_row["evaluation_id"],
                "session_id": eval_row["session_id"],
                "level_id": eval_row["level_id"],
                "overall_evaluation": eval_row["overall_evaluation"],
                "concept_evaluations": concepts
            }

    @classmethod
    def _get_existing_decision(cls, session_id: str, level_id: str, eval_id: str) -> Optional[Dict[str, Any]]:
        with get_clario_ai_db() as ai_db:
            row = ai_db.execute(
                """
                SELECT * FROM adaptive_decisions
                WHERE session_id = ? AND level_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT 1
                """,
                (session_id, level_id)
            ).fetchone()

            if not row:
                return None

            # Check if this decision was generated for this evaluation or session
            payload = json.loads(row["decision_payload_json"]) if row["decision_payload_json"] else {}
            if eval_id:
                if payload.get("evaluation_id") != eval_id:
                    return None
            elif not row.get("reason"):
                return None

            return {
                "decision_id": row["id"],
                "session_id": row["session_id"],
                "level_id": row["level_id"] or level_id,
                "decision_type": row["decision_type"],
                "reason": row["reason"] or row.get("rationale") or "",
                "target_concept": row["target_concept"],
                "target_agent": row["target_agent"],
                "old_difficulty": row["old_difficulty"],
                "new_difficulty": row["new_difficulty"],
                "mastery_score": row["mastery_score"],
                "created_at": row["created_at"]
            }
        return None

    @classmethod
    def _handle_level_completion(cls, session_id: str, level_id: str, user_id: str) -> tuple[str, str, Optional[str]]:
        current_lvl_num = 1
        next_lvl_num = None
        next_lvl_title = None
        has_next_level = False

        with get_clario_ai_db() as ai_db:
            # Mark current level as COMPLETED
            ai_db.execute(
                "UPDATE roadmap_levels SET status = 'COMPLETED' WHERE level_id = ?",
                (level_id,)
            )

            # Check roadmap for next level
            current_lvl = ai_db.execute(
                "SELECT roadmap_id, level_number FROM roadmap_levels WHERE level_id = ?",
                (level_id,)
            ).fetchone()

            if current_lvl:
                roadmap_id = current_lvl["roadmap_id"]
                current_lvl_num = current_lvl["level_number"]
                next_lvl_num = current_lvl_num + 1

                next_lvl = ai_db.execute(
                    "SELECT level_id, title FROM roadmap_levels WHERE roadmap_id = ? AND level_number = ?",
                    (roadmap_id, next_lvl_num)
                ).fetchone()

                if next_lvl:
                    has_next_level = True
                    next_lvl_title = next_lvl["title"]
                    # Unlock next level
                    ai_db.execute(
                        "UPDATE roadmap_levels SET status = 'UNLOCKED' WHERE level_id = ?",
                        (next_lvl["level_id"],)
                    )
                else:
                    # Update learning_sessions table in clario_ai.db
                    ai_db.execute(
                        "UPDATE learning_sessions SET status = 'GOAL_COMPLETED' WHERE session_id = ?",
                        (session_id,)
                    )

        # State machine transitions performed OUTSIDE the db context manager to prevent self-deadlocks
        if has_next_level:
            cls._transition_state_safe(session_id, user_id, "ADAPTIVE_DECISION")
            cls._transition_state_safe(session_id, user_id, "COMPLETE_LEVEL")
            cls._transition_state_safe(session_id, user_id, "UNLOCK_NEXT_LEVEL")

            return (
                "COMPLETE_LEVEL",
                f"All concepts mastered. Level {current_lvl_num} completed. Level {next_lvl_num} ('{next_lvl_title}') unlocked.",
                None
            )
        else:
            cls._transition_state_safe(session_id, user_id, "ADAPTIVE_DECISION")
            cls._transition_state_safe(session_id, user_id, "COMPLETE_LEVEL")
            cls._transition_state_safe(session_id, user_id, "COMPLETE_GOAL")

            return (
                "COMPLETE_GOAL",
                "All concepts mastered across all levels. Entire learning roadmap completed successfully!",
                None
            )

    @classmethod
    def _persist_decision(cls, decision: AdaptiveDecision, eval_id: str) -> None:
        with get_clario_ai_db() as ai_db:
            payload = {
                "decision_id": decision.decision_id,
                "evaluation_id": eval_id,
                "decision_type": decision.decision_type,
                "target_concept": decision.target_concept,
                "mastery_score": decision.mastery_score
            }
            ai_db.execute(
                """
                INSERT INTO adaptive_decisions
                (id, session_id, level_id, decision_type, reason, target_concept, target_agent,
                 old_difficulty, new_difficulty, mastery_score, decision_payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.session_id,
                    decision.level_id,
                    decision.decision_type,
                    decision.reason,
                    decision.target_concept,
                    decision.target_agent,
                    decision.old_difficulty,
                    decision.new_difficulty,
                    decision.mastery_score,
                    json.dumps(payload),
                    decision.created_at.strftime("%Y-%m-%d %H:%M:%S")
                )
            )

    @classmethod
    def _transition_state_safe(cls, session_id: str, user_id: str, target_state: str) -> None:
        try:
            with get_clario_ai_db() as ai_db:
                run = ai_db.execute(
                    "SELECT id, current_stage FROM orchestration_runs WHERE session_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                    (session_id,)
                ).fetchone()
                if run:
                    OrchestrationService.transition_state(run["id"], user_id, target_state)
                    OrchestrationService.record_event(session_id, target_state, {"target_state": target_state}, run_id=run["id"])
        except Exception as e:
            logger.warning(f"Orchestration transition warning to {target_state} (non-fatal): {e}")


adaptive_decision_service = AdaptiveDecisionService()
