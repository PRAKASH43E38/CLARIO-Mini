import uuid
import json
from datetime import datetime, timezone
from backend.database.connection import get_clario_ai_db, get_user_db
from backend.schemas.contracts import Roadmap, RoadmapLevel
from backend.providers.service import provider_service


class RoadmapService:
    """
    Personalized Roadmap Engine.
    Generates a structured learning path based on Mind Profile, Session Inputs, and CALA result.
    """

    @staticmethod
    def generate_roadmap(user_id: str, session_id: str) -> Roadmap:
        # 1. Load context
        mind_profile = RoadmapService._get_mind_profile(user_id)
        session_inputs = RoadmapService._get_session_inputs(session_id)
        cala_result = RoadmapService._get_cala_result(session_id)

        # 2. Construct prompt for CLARIO-AI (via LLM provider)
        prompt = RoadmapService._build_prompt(mind_profile, session_inputs, cala_result)

        # 3. Phase 0 placeholder — generate a deterministic roadmap
        # Full LLM-driven generation is reserved for subsequent phases.
        topic = session_inputs.get("task", "General Learning")
        raw_roadmap = Roadmap(
            session_id=session_id,
            topic=topic,
            levels=[
                RoadmapLevel(
                    level_number=1,
                    title="Foundations",
                    description=f"Introduction to core concepts of {topic}",
                    key_concepts=["Basic terminology", "Core principles"],
                    estimated_duration_minutes=30,
                ),
                RoadmapLevel(
                    level_number=2,
                    title="Application",
                    description=f"Applying {topic} concepts in practice",
                    key_concepts=["Practical usage", "Common patterns"],
                    estimated_duration_minutes=45,
                ),
                RoadmapLevel(
                    level_number=3,
                    title="Mastery",
                    description=f"Advanced {topic} and synthesis",
                    key_concepts=["Advanced techniques", "Problem solving"],
                    estimated_duration_minutes=60,
                ),
            ],
        )

        # 4. Persist Roadmap and Levels in clario_ai.db
        roadmap_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with get_clario_ai_db() as conn:
            # Store Roadmap
            conn.execute(
                "INSERT INTO roadmaps (roadmap_id, session_id, topic, created_at) VALUES (?, ?, ?, ?)",
                (roadmap_id, session_id, raw_roadmap.topic, now)
            )

            # Store Levels
            for i, level in enumerate(raw_roadmap.levels):
                level_id = str(uuid.uuid4())
                status = 'UNLOCKED' if i == 0 else 'LOCKED'

                conn.execute(
                    "INSERT INTO roadmap_levels (level_id, roadmap_id, level_number, title, objective, difficulty, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (level_id, roadmap_id, level.level_number, level.title, level.description, 'medium', status, now)
                )

        return raw_roadmap

    @staticmethod
    def _get_mind_profile(user_id: str) -> dict:
        with get_user_db() as conn:
            row = conn.execute("SELECT answers_json FROM mind_profiles WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                raise ValueError("Mind profile not found.")
            return json.loads(row["answers_json"])

    @staticmethod
    def _get_session_inputs(session_id: str) -> dict:
        with get_user_db() as conn:
            row = conn.execute("SELECT task, goal, learner_state, interest FROM session_inputs WHERE session_id = ?", (session_id,)).fetchone()
            if not row:
                raise ValueError("Session inputs not found.")
            return dict(row)

    @staticmethod
    def _get_cala_result(session_id: str) -> dict:
        with get_user_db() as conn:
            row = conn.execute("SELECT result_json FROM cala_results WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", (session_id,)).fetchone()
            if not row:
                raise ValueError("CALA analysis not found. Please run analysis first.")
            return json.loads(row["result_json"])

    @staticmethod
    def _build_prompt(mind_profile: dict, session_inputs: dict, cala_result: dict) -> str:
        return f"""
        You are the CLARIO-AI Roadmap Engine.
        Create a personalized, structured learning roadmap.

        LEARNER CONTEXT:
        - Mind Profile: {json.dumps(mind_profile)}
        - Session Inputs: {json.dumps(session_inputs)}
        - CALA Analysis: {json.dumps(cala_result)}

        REQUIREMENTS:
        1. Topic: Derived from the Task and Goal.
        2. Levels: Create a variable number of levels (usually 3-7) that logically progress from the recommended starting level to the final goal.
        3. Content: Each level must have a title, a clear objective, and a list of key concepts to master.
        4. Structure:
           - Level 1 must be an accessible entry point based on the CALA starting level.
           - Subsequent levels must build on prerequisites.
           - The final level must directly achieve the learner's goal.
        5. Logic: Do NOT generate lesson content, only the high-level structural roadmap.

        Output the response as a structured Roadmap object.
        """
