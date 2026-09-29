import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from backend.core.config import BASE_DIR, settings


def _database_path(configured_path: str | Path) -> Path:
    """Resolve relative SQLite paths from the project root and create their parent."""
    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_data_directory() -> None:
    """Ensure configured SQLite database directories exist."""
    for configured_path in (
        settings.USER_DB_PATH,
        settings.NOVA_DB_PATH,
        settings.CLARIO_AI_DB_PATH,
        settings.SESSION_DB_PATH,
    ):
        _database_path(configured_path)


@contextmanager
def get_user_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a connection to user.db (User identity and session inputs)."""
    ensure_data_directory()
    conn = sqlite3.connect(_database_path(settings.USER_DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_nova_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a connection to nova.db (Web research and source-related info)."""
    ensure_data_directory()
    conn = sqlite3.connect(_database_path(settings.NOVA_DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_clario_ai_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a connection to clario_ai.db (Orchestration, learning state, agent records, evaluations, decisions)."""
    ensure_data_directory()
    conn = sqlite3.connect(_database_path(settings.CLARIO_AI_DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_user_db() -> None:
    """Initialize schema for user.db."""
    with get_user_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                target_topic TEXT,
                learning_goals TEXT,
                preferences_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS mind_profiles (
                user_id TEXT PRIMARY KEY,
                answers_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cala_results (
                cala_result_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );
        """)
        profile_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(user_profiles)")
        }
        if "updated_at" not in profile_columns:
            conn.execute("ALTER TABLE user_profiles ADD COLUMN updated_at TIMESTAMP")
            conn.execute(
                "UPDATE user_profiles SET updated_at = created_at WHERE updated_at IS NULL"
            )
        _init_learning_session_tables(conn)


def _init_learning_session_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'CREATED',
                    'INPUTS_PENDING',
                    'INPUTS_COMPLETED',
                    'READY_FOR_CALA'
                )
            ),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    existing = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'session_inputs'"
    ).fetchone()
    if existing:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(session_inputs)")
        }
        required_columns = {
            "session_id",
            "task",
            "goal",
            "learner_state",
            "interest",
            "created_at",
            "updated_at",
        }
        if not required_columns.issubset(columns):
            legacy_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'legacy_session_inputs_phase0'"
            ).fetchone()
            if legacy_exists:
                raise RuntimeError(
                    "Both legacy and current session-input tables exist; "
                    "manual migration is required to avoid data loss."
                )
            conn.execute(
                "ALTER TABLE session_inputs RENAME TO legacy_session_inputs_phase0"
            )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_inputs (
            session_id TEXT PRIMARY KEY,
            task TEXT NOT NULL CHECK (length(trim(task)) BETWEEN 1 AND 2000),
            goal TEXT NOT NULL CHECK (length(trim(goal)) BETWEEN 1 AND 2000),
            learner_state TEXT NOT NULL CHECK (length(trim(learner_state)) BETWEEN 1 AND 2000),
            interest TEXT NOT NULL CHECK (length(trim(interest)) BETWEEN 1 AND 2000),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
        )
    """)


def init_nova_db() -> None:
    """Initialize schema for nova.db."""
    with get_nova_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS research_queries (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                query_text TEXT NOT NULL,
                requested_by TEXT DEFAULT 'nova',
                parameters_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS research_sources (
                id TEXT PRIMARY KEY,
                query_id TEXT NOT NULL,
                title TEXT,
                url TEXT,
                snippet TEXT,
                raw_content TEXT,
                reliability_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES research_queries (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS research_summaries (
                id TEXT PRIMARY KEY,
                query_id TEXT NOT NULL,
                summary_text TEXT,
                key_findings_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES research_queries (id) ON DELETE CASCADE
            );
        """)


def init_clario_ai_db() -> None:
    """Initialize schema for clario_ai.db."""
    with get_clario_ai_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS roadmaps (
                roadmap_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS roadmap_levels (
                level_id TEXT PRIMARY KEY,
                roadmap_id TEXT NOT NULL,
                level_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                objective TEXT,
                difficulty TEXT,
                status TEXT DEFAULT 'LOCKED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (roadmap_id) REFERENCES roadmaps (roadmap_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS level_concepts (
                concept_id TEXT PRIMARY KEY,
                level_id TEXT NOT NULL,
                concept_name TEXT NOT NULL,
                prerequisites_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (level_id) REFERENCES roadmap_levels (level_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS research_orchestration (
                request_id TEXT PRIMARY KEY,
                level_id TEXT,
                status TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS orchestration_runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                current_stage TEXT NOT NULL,
                status TEXT NOT NULL,
                state_snapshot_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_executions (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                input_payload_json TEXT,
                output_payload_json TEXT,
                execution_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES orchestration_runs (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learner_progress (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                concept_id TEXT NOT NULL,
                mastery_score REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                evaluation_type TEXT NOT NULL,
                score REAL,
                feedback_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS adaptive_decisions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                rationale TEXT,
                decision_payload_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS teaching_interactions (
                interaction_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                request_payload_json TEXT,
                response_payload_json TEXT,
                user_feedback TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS thinking_challenges (
                challenge_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                questions_json TEXT NOT NULL,
                rationale TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS thinking_responses (
                response_id TEXT PRIMARY KEY,
                challenge_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                user_answer TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (challenge_id) REFERENCES thinking_challenges (challenge_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS application_scenarios (
                scenario_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                scenarios_json TEXT NOT NULL,
                rationale TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS application_responses (
                response_id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                user_response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scenario_id) REFERENCES application_scenarios (scenario_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS quizzes (
                quiz_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                questions_json TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS quiz_responses (
                response_id TEXT PRIMARY KEY,
                quiz_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                user_answer TEXT NOT NULL,
                response_time_seconds REAL,
                is_timeout BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes (quiz_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS elara_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                overall_evaluation TEXT,
                global_strengths TEXT,
                global_weaknesses TEXT,
                evidence_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS concept_evaluations (
                concept_eval_id TEXT PRIMARY KEY,
                evaluation_id TEXT NOT NULL,
                concept_name TEXT NOT NULL,
                understanding TEXT,
                reasoning TEXT,
                application TEXT,
                assessment TEXT,
                mastery_score REAL,
                strengths TEXT,
                weaknesses TEXT,
                mistakes TEXT,
                evidence TEXT,
                FOREIGN KEY (evaluation_id) REFERENCES elara_evaluations (evaluation_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS concept_performance (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                concept TEXT NOT NULL,
                understanding TEXT,
                reasoning TEXT,
                application TEXT,
                assessment TEXT,
                mastery_score REAL DEFAULT 0.0,
                difficulty TEXT DEFAULT 'Medium',
                attempts INTEGER DEFAULT 1,
                mistakes_json TEXT,
                status TEXT DEFAULT 'learning',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, level_id, concept),
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS remediation_history (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                concept TEXT NOT NULL,
                decision_id TEXT,
                approach TEXT,
                old_difficulty TEXT,
                new_difficulty TEXT,
                remediation_content TEXT,
                retest_content TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                level_id TEXT,
                event_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                payload_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, event_type, entity_id)
            );

            CREATE TABLE IF NOT EXISTS xp_transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                xp_amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES learning_events (event_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_streaks (
                user_id TEXT PRIMARY KEY,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_learning_date TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_badges (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                badge_key TEXT NOT NULL,
                badge_name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_key)
            );

            CREATE TABLE IF NOT EXISTS final_reports (
                report_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                total_levels INTEGER NOT NULL,
                completed_levels INTEGER NOT NULL,
                total_xp INTEGER NOT NULL,
                mastered_concepts_json TEXT NOT NULL,
                remediations_count INTEGER DEFAULT 0,
                executive_summary TEXT NOT NULL,
                strengths_json TEXT,
                growth_areas_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id) ON DELETE CASCADE
            );
        """)

        # Ensure adaptive_decisions has all Phase 12 columns
        decision_cols = {row["name"] for row in conn.execute("PRAGMA table_info(adaptive_decisions)")}
        for col_name, col_type in [
            ("level_id", "TEXT"),
            ("reason", "TEXT"),
            ("target_concept", "TEXT"),
            ("target_agent", "TEXT"),
            ("old_difficulty", "TEXT"),
            ("new_difficulty", "TEXT"),
            ("mastery_score", "REAL"),
        ]:
            if col_name not in decision_cols:
                conn.execute(f"ALTER TABLE adaptive_decisions ADD COLUMN {col_name} {col_type}")


def init_all_databases() -> None:
    """Initialize all 3 SQLite databases."""
    ensure_data_directory()
    init_user_db()
    init_nova_db()
    init_clario_ai_db()
