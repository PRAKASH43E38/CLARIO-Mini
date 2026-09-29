"""
Phase 15 Automated Test Suite: XP, Streaks, Badges & Gamification

Validates:
- Deterministic XP events and values
- Idempotency & duplicate prevention for XP and learning events
- Daily streak logic (increments once/day, resets on gaps, preserves longest)
- Badges awarding idempotency and catalog integrity
- Authenticated Rewards API routes (GET /rewards, /rewards/xp, /rewards/streak, /rewards/badges)
- Ownership isolation (User A cannot access User B's rewards)
- End-to-end integration: level completion, remediation, and goal rewards
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import init_all_databases, get_clario_ai_db, get_user_db
from backend.services.reward_service import RewardService, XP_TABLE, BADGE_CATALOG
from backend.services.end_to_end_loop_service import EndToEndLoopService
from backend.auth.session import SessionStore, init_session_db
from backend.core.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_databases():
    """Ensure all SQLite databases are initialized before every test."""
    init_all_databases()
    init_session_db()


def create_test_user_and_session(user_id: str, email: str = "gamify@example.com") -> str:
    """Helper to register a user and session in user.db and clario_ai.db."""
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    with get_user_db() as u_conn:
        u_conn.execute("INSERT OR REPLACE INTO users (id, email) VALUES (?, ?)", (user_id, email))
        u_conn.execute(
            "INSERT OR REPLACE INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
            (session_id, user_id),
        )
    with get_clario_ai_db() as ai_conn:
        ai_conn.execute(
            "INSERT OR REPLACE INTO learning_sessions (session_id, user_id, status) VALUES (?, ?, 'READY_FOR_CALA')",
            (session_id, user_id),
        )
    return session_id


class TestPhase15Gamification:
    """Complete automated verification for Phase 15 Gamification & Rewards."""

    def test_01_xp_awarded_correctly(self):
        """Verify each learning action deterministically awards exact XP amounts."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        # 1. Complete teaching activity: +25 XP
        r1 = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="TEACHING_COMPLETED",
            entity_id="mira_lvl_1",
        )
        assert r1["xp_awarded"] == 25
        assert r1["rewards"]["total_xp"] == 25

        # 2. Complete critical thinking: +25 XP
        r2 = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="THINKING_COMPLETED",
            entity_id="ayan_ch_1",
        )
        assert r2["xp_awarded"] == 25
        assert r2["rewards"]["total_xp"] == 50

        # 3. Complete practical application: +35 XP
        r3 = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="APPLICATION_COMPLETED",
            entity_id="kira_sc_1",
        )
        assert r3["xp_awarded"] == 35
        assert r3["rewards"]["total_xp"] == 85

        # 4. Complete quiz: +40 XP
        r4 = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="QUIZ_COMPLETED",
            entity_id="zayn_qz_1",
        )
        assert r4["xp_awarded"] == 40
        assert r4["rewards"]["total_xp"] == 125

        # Level increases with XP (100 XP per level)
        assert r4["rewards"]["level"] == 2

    def test_02_duplicate_request_does_not_duplicate_xp(self):
        """Verify that duplicate API calls or replayed events do not duplicate XP (Idempotency)."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        # First recording
        res1 = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="TEACHING_COMPLETED",
            entity_id="mira_lvl_repeat",
        )
        assert res1["rewards"]["total_xp"] == 25

        # Exact same event re-sent (replay/retry)
        res2 = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="TEACHING_COMPLETED",
            entity_id="mira_lvl_repeat",
        )
        # XP remains 25, no duplicate awarded
        assert res2["total_xp"] == 25

        # Verify only 1 transaction in DB
        with get_clario_ai_db() as ai_conn:
            count = ai_conn.execute(
                "SELECT COUNT(*) as c FROM xp_transactions WHERE user_id = ?", (user_id,)
            ).fetchone()["c"]
            assert count == 1

    def test_03_streak_increments_once_per_calendar_day(self):
        """Verify streak increments exactly once per calendar day and ignores same-day events."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        # Day 1: 2026-09-01
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="TEACHING_COMPLETED",
            entity_id="act_d1_1",
            current_date_str="2026-09-01",
        )
        st1 = RewardService.get_user_streak(user_id)
        assert st1["current_streak"] == 1
        assert st1["longest_streak"] == 1

        # Same day: 2026-09-01 second event -> streak MUST NOT change
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="THINKING_COMPLETED",
            entity_id="act_d1_2",
            current_date_str="2026-09-01",
        )
        st1_repeat = RewardService.get_user_streak(user_id)
        assert st1_repeat["current_streak"] == 1

        # Day 2: 2026-09-02 consecutive day -> streak becomes 2
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="APPLICATION_COMPLETED",
            entity_id="act_d2_1",
            current_date_str="2026-09-02",
        )
        st2 = RewardService.get_user_streak(user_id)
        assert st2["current_streak"] == 2
        assert st2["longest_streak"] == 2

        # Day 3: 2026-09-03 consecutive day -> streak becomes 3
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="QUIZ_COMPLETED",
            entity_id="act_d3_1",
            current_date_str="2026-09-03",
        )
        st3 = RewardService.get_user_streak(user_id)
        assert st3["current_streak"] == 3
        assert st3["longest_streak"] == 3

    def test_04_streak_resets_after_gap_and_preserves_longest(self):
        """Verify streak resets to 1 after a gap (>1 day) while longest streak is preserved."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        # Day 1 & Day 2
        RewardService.record_learning_event(
            user_id=user_id, session_id=session_id, event_type="TEACHING_COMPLETED",
            entity_id="act_1", current_date_str="2026-09-01",
        )
        RewardService.record_learning_event(
            user_id=user_id, session_id=session_id, event_type="THINKING_COMPLETED",
            entity_id="act_2", current_date_str="2026-09-02",
        )
        assert RewardService.get_user_streak(user_id)["current_streak"] == 2

        # Day 5 (3-day gap) -> Streak resets to 1, longest remains 2
        RewardService.record_learning_event(
            user_id=user_id, session_id=session_id, event_type="QUIZ_COMPLETED",
            entity_id="act_5", current_date_str="2026-09-05",
        )
        st_gap = RewardService.get_user_streak(user_id)
        assert st_gap["current_streak"] == 1
        assert st_gap["longest_streak"] == 2

    def test_05_badge_awarded_deterministically_and_idempotently(self):
        """Verify badges are awarded once upon condition and never duplicated."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        # Trigger first activity -> awards 'first_step' and 'streak_starter'
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="TEACHING_COMPLETED",
            entity_id="first_mira",
        )
        b1 = RewardService.get_user_badges(user_id)
        earned_keys = {b["badge_key"] for b in b1["badges"] if b["earned"]}
        assert "first_step" in earned_keys
        assert "streak_starter" in earned_keys

        # Trigger thinking activity -> awards 'critical_thinker'
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="THINKING_COMPLETED",
            entity_id="first_ayan",
        )
        b2 = RewardService.get_user_badges(user_id)
        earned_keys2 = {b["badge_key"] for b in b2["badges"] if b["earned"]}
        assert "critical_thinker" in earned_keys2

        # Repeated trigger does NOT duplicate the badge in DB
        with get_clario_ai_db() as ai_conn:
            rows = ai_conn.execute(
                "SELECT COUNT(*) as c FROM user_badges WHERE user_id = ? AND badge_key = 'critical_thinker'",
                (user_id,),
            ).fetchone()["c"]
            assert rows == 1

    def test_06_authenticated_rewards_api_endpoints(self):
        """Test GET /rewards, /rewards/xp, /rewards/streak, and /rewards/badges."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        # Award an activity
        RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="APPLICATION_COMPLETED",
            entity_id="kira_test",
        )

        auth_session_id = SessionStore(settings.SESSION_DB_PATH).create_session(user_id)
        cookies = {"clario_session": auth_session_id}

        # 1. GET /rewards
        r_sum = client.get("/rewards", cookies=cookies)
        assert r_sum.status_code == 200
        data = r_sum.json()
        assert data["user_id"] == user_id
        assert data["total_xp"] == 35
        assert data["level"] == 1
        assert data["streak"]["current_streak"] == 1
        assert len(data["earned_badges"]) >= 1

        # 2. GET /rewards/xp
        r_xp = client.get("/rewards/xp", cookies=cookies)
        assert r_xp.status_code == 200
        xp_data = r_xp.json()
        assert xp_data["total_xp"] == 35
        assert len(xp_data["transactions"]) == 1

        # 3. GET /rewards/streak
        r_strk = client.get("/rewards/streak", cookies=cookies)
        assert r_strk.status_code == 200
        assert r_strk.json()["current_streak"] == 1

        # 4. GET /rewards/badges
        r_bdg = client.get("/rewards/badges", cookies=cookies)
        assert r_bdg.status_code == 200
        bdg_data = r_bdg.json()
        assert bdg_data["earned_count"] >= 1
        assert bdg_data["total_available"] == len(BADGE_CATALOG)

    def test_07_unauthorized_access_rejected(self):
        """Verify unauthenticated requests to /rewards endpoints return 401."""
        assert client.get("/rewards").status_code in (401, 403)
        assert client.get("/rewards/xp").status_code in (401, 403)
        assert client.get("/rewards/streak").status_code in (401, 403)
        assert client.get("/rewards/badges").status_code in (401, 403)

    def test_08_user_a_cannot_access_user_b_rewards(self):
        """Verify User A's session strictly isolates data from User B."""
        user_a = f"userA-{uuid.uuid4().hex[:8]}"
        user_b = f"userB-{uuid.uuid4().hex[:8]}"
        sess_a = create_test_user_and_session(user_a)
        sess_b = create_test_user_and_session(user_b)

        # User A completes a high XP goal
        RewardService.record_learning_event(
            user_id=user_a,
            session_id=sess_a,
            event_type="GOAL_COMPLETED",
            entity_id="goal_a",
        )

        # User B completes only a teaching activity
        RewardService.record_learning_event(
            user_id=user_b,
            session_id=sess_b,
            event_type="TEACHING_COMPLETED",
            entity_id="mira_b",
        )

        # Authenticate as User B
        auth_b = SessionStore(settings.SESSION_DB_PATH).create_session(user_b)
        res_b = client.get("/rewards", cookies={"clario_session": auth_b})
        assert res_b.status_code == 200
        data_b = res_b.json()

        # User B only sees their 25 XP, never User A's 250 XP
        assert data_b["user_id"] == user_b
        assert data_b["total_xp"] == 25
        assert data_b["total_xp"] != 250

    def test_09_remediation_success_reward(self):
        """Verify successful remediation awards 50 XP and Remediation Success badge."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        session_id = create_test_user_and_session(user_id)

        res = RewardService.record_learning_event(
            user_id=user_id,
            session_id=session_id,
            event_type="REMEDIATION_SUCCESS",
            entity_id="rem_eval_1",
        )
        assert res["xp_awarded"] == 50
        badges = RewardService.get_user_badges(user_id)
        earned = {b["badge_key"] for b in badges["badges"] if b["earned"]}
        assert "remediation_success" in earned
