"""
Tavily Web Research Module.
NOTE: Per CLARIO architectural constraints, Nova is the ONLY agent permitted
to interact with this service. Other agents must never access Tavily directly.
"""
from typing import Any
from backend.core.config import settings


class TavilyResearchService:
    """Service abstraction for web research via Tavily."""

    def __init__(self) -> None:
        self.api_key = settings.TAVILY_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """
        Execute web search for Nova.
        Phase 0 placeholder - full Tavily API integration reserved for future phases.
        """
        return [
            {
                "title": f"Research Result for: {query}",
                "url": "https://example.org/source-placeholder",
                "snippet": f"Placeholder research findings for query: {query}",
            }
        ]


research_service = TavilyResearchService()
