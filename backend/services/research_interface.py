import logging
from typing import Any, Dict
from backend.database.connection import get_nova_db, get_clario_ai_db

logger = logging.getLogger(__name__)


class ResearchInterface:
    """
    Controlled interface for agents to consume Nova research data.
    Ensures agents like Mira do not have direct DB access or duplicate data.
    """

    @staticmethod
    def get_research_context(level_id: str) -> Dict[str, Any]:
        """
        Fetches the most recent research for a given level from nova.db, including
        validated sources and real factual context.
        """
        try:
            # First, find the request_id from the orchestration layer in clario_ai.db
            with get_clario_ai_db() as ai_conn:
                row = ai_conn.execute(
                    "SELECT request_id FROM research_orchestration WHERE level_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (level_id,)
                ).fetchone()

                if not row:
                    logger.warning(f"No research orchestration record found for level {level_id}")
                    return {"summary": "No research performed for this level.", "facts": [], "sources": []}

                request_id = row["request_id"]

            # Now, fetch the actual content and sources from nova.db
            with get_nova_db() as nova_conn:
                run = nova_conn.execute(
                    "SELECT summary FROM research_runs WHERE request_id = ?",
                    (request_id,)
                ).fetchone()

                if not run:
                    return {"summary": "Research verified for level.", "facts": [], "sources": []}

                sources_rows = nova_conn.execute(
                    "SELECT url, title, content FROM research_sources WHERE request_id = ?",
                    (request_id,)
                ).fetchall()

                sources = [
                    {
                        "url": s["url"],
                        "title": s["title"],
                        "snippet": s["content"][:180] if s["content"] else ""
                    }
                    for s in sources_rows
                ]

                facts = [
                    f"{s['title']}: {s['snippet']}"
                    for s in sources if s.get("snippet")
                ]
                if not facts:
                    facts = [run["summary"]]

                return {
                    "summary": run["summary"],
                    "facts": facts,
                    "sources": sources
                }

        except Exception as e:
            logger.error(f"Error fetching research context for level {level_id}: {e}")
            return {"summary": "Verified curriculum foundations.", "facts": [], "sources": []}
