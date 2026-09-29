"""
CLARIO Gamification & Reward Service (Phase 15)

Deterministic XP, streaks, badges, and learning events engine.
All gamification state lives strictly in clario_ai.db.
Events and rewards are idempotent and authenticated.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from backend.database.connection import get_clario_ai_db


# Deterministic XP values per learning event type
XP_TABLE = {
    "TEACHING_COMPLETED": (25, "Completed Mira Concept Teaching"),
    "THINKING_COMPLETED": (25, "Completed Ayan Socratic Challenge"),
    "APPLICATION_COMPLETED": (35, "Completed Kira Practical Project"),
    "QUIZ_COMPLETED": (40, "Completed Zayn Assessment Quiz"),
    "MASTERY_ACHIEVED": (50, "Achieved Concept Mastery"),
    "LEVEL_COMPLETED": (100, "Completed Learning Level"),
    "REMEDIATION_SUCCESS": (50, "Successfully Completed Remediation"),
    "GOAL_COMPLETED": (250, "Achieved Complete Learning Goal"),
}

# Catalog of deterministic badges
BADGE_CATALOG = {
    "first_step": {
        "name": "First Step",
        "description": "Completed your first learning activity in CLARIO",
        "icon": "🌱",
    },
    "critical_thinker": {
        "name": "Critical Thinker",
        "description": "Successfully solved an Ayan critical thinking challenge",
        "icon": "🧠",
    },
    "practical_learner": {
        "name": "Practical Learner",
        "description": "Completed a Kira hands-on practical application project",
        "icon": "🛠️",
    },
    "quiz_finisher": {
        "name": "Quiz Finisher",
        "description": "Completed a Zayn assessment quiz",
        "icon": "📝",
    },
    "first_mastery": {
        "name": "First Mastery",
        "description": "Achieved mastery on a core academic concept",
        "icon": "⭐",
    },
    "first_level_complete": {
        "name": "First Level Complete",
        "description": "Completed your first roadmap level",
        "icon": "🏆",
    },
    "remediation_success": {
        "name": "Remediation Success",
        "description": "Overcame a learning struggle through targeted remediation",
        "icon": "🔄",
    },
    "goal_complete": {
        "name": "Goal Complete",
        "description": "Mastered all levels in your personalized roadmap",
        "icon": "👑",
    },
    "streak_starter": {
        "name": "Streak Starter",
        "description": "Started your learning streak",
        "icon": "🔥",
    },
    "streak_three": {
        "name": "Consistent Learner",
        "description": "Maintained a 3-day consecutive learning streak",
        "icon": "⚡",
    },
    "streak_week": {
        "name": "Streak Master",
        "description": "Maintained a 7-day consecutive learning streak",
        "icon": "🌟",
    },
}


class RewardService:
    """Central engine for recording learning events and awarding XP, streaks, and badges."""

    @classmethod
    def record_learning_event(
        cls,
        user_id: str,
        session_id: str,
        event_type: str,
        entity_id: str,
        level_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        current_date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a deterministic learning event idempotently.
        Awards XP, updates streak, and evaluates badges.
        """
        payload_json = json.dumps(payload or {})
        event_id = str(uuid.uuid4())
        xp_awarded = 0
        newly_awarded_badges: List[Dict[str, Any]] = []

        with get_clario_ai_db() as conn:
            # 1. Check if this exact event was already recorded (idempotency)
            existing = conn.execute(
                "SELECT event_id FROM learning_events WHERE user_id = ? AND event_type = ? AND entity_id = ?",
                (user_id, event_type, entity_id),
            ).fetchone()

            if existing:
                # Already processed — return current state without duplicating rewards
                return cls.get_user_rewards(user_id)

            # Insert learning event
            conn.execute(
                """
                INSERT INTO learning_events (event_id, user_id, session_id, level_id, event_type, entity_id, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, user_id, session_id, level_id, event_type, entity_id, payload_json),
            )

            # 2. Award XP if event type is recognized
            if event_type in XP_TABLE:
                amount, reason = XP_TABLE[event_type]
                tx_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO xp_transactions (transaction_id, user_id, event_id, xp_amount, reason)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (tx_id, user_id, event_id, amount, reason),
                )
                xp_awarded = amount

            # 3. Update Streak
            cls._update_streak(conn, user_id, current_date_str)

            # 4. Evaluate and award badges
            newly_awarded_badges = cls._evaluate_badges(conn, user_id, event_type)

        return {
            "event_id": event_id,
            "event_type": event_type,
            "xp_awarded": xp_awarded,
            "new_badges": newly_awarded_badges,
            "rewards": cls.get_user_rewards(user_id),
        }

    @classmethod
    def _update_streak(cls, conn, user_id: str, custom_date_str: Optional[str] = None) -> None:
        """Update consecutive learning day streak idempotently."""
        today_str = custom_date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today = datetime.strptime(today_str, "%Y-%m-%d").date()

        row = conn.execute(
            "SELECT current_streak, longest_streak, last_learning_date FROM user_streaks WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            conn.execute(
                """
                INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_learning_date)
                VALUES (?, 1, 1, ?)
                """,
                (user_id, today_str),
            )
            return

        last_date_str = row["last_learning_date"]
        current_streak = row["current_streak"]
        longest_streak = row["longest_streak"]

        if not last_date_str:
            new_current = 1
            new_longest = max(longest_streak, 1)
        else:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            diff_days = (today - last_date).days

            if diff_days == 0:
                # Same calendar day — do not duplicate increment
                return
            elif diff_days == 1:
                # Consecutive day — increment streak
                new_current = current_streak + 1
                new_longest = max(longest_streak, new_current)
            elif diff_days > 1:
                # Gap in learning — reset streak to 1
                new_current = 1
                new_longest = max(longest_streak, 1)
            else:
                # Event from past date — do not alter future streak
                return

        conn.execute(
            """
            UPDATE user_streaks
            SET current_streak = ?, longest_streak = ?, last_learning_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (new_current, new_longest, today_str, user_id),
        )

    @classmethod
    def _evaluate_badges(cls, conn, user_id: str, trigger_event: str) -> List[Dict[str, Any]]:
        """Evaluate deterministic badge criteria and award newly qualified badges."""
        awarded_keys = {
            r["badge_key"]
            for r in conn.execute("SELECT badge_key FROM user_badges WHERE user_id = ?", (user_id,)).fetchall()
        }

        new_badges = []

        def award(badge_key: str):
            if badge_key not in awarded_keys and badge_key in BADGE_CATALOG:
                meta = BADGE_CATALOG[badge_key]
                badge_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO user_badges (id, user_id, badge_key, badge_name, description, icon)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (badge_id, user_id, badge_key, meta["name"], meta["description"], meta["icon"]),
                )
                awarded_keys.add(badge_key)
                new_badges.append({"key": badge_key, **meta})

        # "First Step" badge: Any completed activity
        award("first_step")

        # Specific activity badges
        if trigger_event == "THINKING_COMPLETED":
            award("critical_thinker")
        elif trigger_event == "APPLICATION_COMPLETED":
            award("practical_learner")
        elif trigger_event == "QUIZ_COMPLETED":
            award("quiz_finisher")
        elif trigger_event == "MASTERY_ACHIEVED":
            award("first_mastery")
        elif trigger_event == "LEVEL_COMPLETED":
            award("first_level_complete")
        elif trigger_event == "REMEDIATION_SUCCESS":
            award("remediation_success")
        elif trigger_event == "GOAL_COMPLETED":
            award("goal_complete")

        # Streak badges
        streak_row = conn.execute(
            "SELECT current_streak FROM user_streaks WHERE user_id = ?", (user_id,)
        ).fetchone()
        if streak_row:
            current_streak = streak_row["current_streak"]
            if current_streak >= 1:
                award("streak_starter")
            if current_streak >= 3:
                award("streak_three")
            if current_streak >= 7:
                award("streak_week")

        return new_badges

    @classmethod
    def get_user_rewards(cls, user_id: str) -> Dict[str, Any]:
        """Fetch overall rewards summary for an authenticated user."""
        with get_clario_ai_db() as conn:
            # Total XP
            xp_row = conn.execute(
                "SELECT COALESCE(SUM(xp_amount), 0) as total_xp FROM xp_transactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            total_xp = xp_row["total_xp"] if xp_row else 0

            # Level calculation: 100 XP per level
            level = (total_xp // 100) + 1

            # Streak
            streak_row = conn.execute(
                "SELECT current_streak, longest_streak, last_learning_date FROM user_streaks WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            streak = {
                "current_streak": streak_row["current_streak"] if streak_row else 0,
                "longest_streak": streak_row["longest_streak"] if streak_row else 0,
                "last_learning_date": streak_row["last_learning_date"] if streak_row else None,
            }

            # Badges
            badges_rows = conn.execute(
                "SELECT badge_key, badge_name, description, icon, awarded_at FROM user_badges WHERE user_id = ? ORDER BY awarded_at ASC",
                (user_id,),
            ).fetchall()
            earned_badges = [dict(r) for r in badges_rows]

            # Recent transactions
            tx_rows = conn.execute(
                "SELECT transaction_id, xp_amount, reason, created_at FROM xp_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
                (user_id,),
            ).fetchall()
            recent_xp = [dict(r) for r in tx_rows]

        return {
            "user_id": user_id,
            "total_xp": total_xp,
            "level": level,
            "streak": streak,
            "earned_badges": earned_badges,
            "badge_count": len(earned_badges),
            "recent_xp": recent_xp,
        }

    @classmethod
    def get_user_xp(cls, user_id: str) -> Dict[str, Any]:
        """Fetch XP summary and transaction history for an authenticated user."""
        with get_clario_ai_db() as conn:
            xp_row = conn.execute(
                "SELECT COALESCE(SUM(xp_amount), 0) as total_xp FROM xp_transactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            total_xp = xp_row["total_xp"] if xp_row else 0
            level = (total_xp // 100) + 1

            tx_rows = conn.execute(
                "SELECT transaction_id, xp_amount, reason, created_at FROM xp_transactions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

        return {
            "user_id": user_id,
            "total_xp": total_xp,
            "level": level,
            "transactions": [dict(r) for r in tx_rows],
        }

    @classmethod
    def get_user_streak(cls, user_id: str) -> Dict[str, Any]:
        """Fetch streak details for an authenticated user."""
        with get_clario_ai_db() as conn:
            streak_row = conn.execute(
                "SELECT current_streak, longest_streak, last_learning_date FROM user_streaks WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        return {
            "user_id": user_id,
            "current_streak": streak_row["current_streak"] if streak_row else 0,
            "longest_streak": streak_row["longest_streak"] if streak_row else 0,
            "last_learning_date": streak_row["last_learning_date"] if streak_row else None,
        }

    @classmethod
    def get_user_badges(cls, user_id: str) -> Dict[str, Any]:
        """Fetch earned badges and full badge catalog with completion status."""
        with get_clario_ai_db() as conn:
            badges_rows = conn.execute(
                "SELECT badge_key, badge_name, description, icon, awarded_at FROM user_badges WHERE user_id = ? ORDER BY awarded_at ASC",
                (user_id,),
            ).fetchall()
            earned_map = {r["badge_key"]: dict(r) for r in badges_rows}

        catalog = []
        for key, meta in BADGE_CATALOG.items():
            earned = key in earned_map
            catalog.append({
                "badge_key": key,
                "badge_name": meta["name"],
                "description": meta["description"],
                "icon": meta["icon"],
                "earned": earned,
                "awarded_at": earned_map[key]["awarded_at"] if earned else None,
            })

        return {
            "user_id": user_id,
            "earned_count": len(earned_map),
            "total_available": len(BADGE_CATALOG),
            "badges": catalog,
        }
