import asyncio
import logging
from typing import List, Dict, Any
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Graceful import of the optional tavily dependency
try:
    from tavily import TavilyClient
    _TAVILY_AVAILABLE = True
except ImportError:
    _TAVILY_AVAILABLE = False
    TavilyClient = None


class TavilyResearchService:
    """
    Wrapper for the Tavily API.
    Nova is the only component allowed to use this service.
    """

    def __init__(self) -> None:
        api_key = settings.TAVILY_API_KEY
        if not api_key or not _TAVILY_AVAILABLE:
            if not _TAVILY_AVAILABLE:
                logger.warning("tavily-python package is not installed; research is unavailable.")
            else:
                logger.warning("TAVILY_API_KEY is not configured; research is unavailable.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=api_key)

    async def search(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Performs search across multiple queries.
        Returns a list of search results.
        """
        if not self.client:
            return []

        try:
            all_results = []
            for query in queries:
                response = await asyncio.to_thread(
                    self.client.search,
                    query=query,
                    search_depth="advanced",
                    max_results=3,
                )
                all_results.extend(response.get("results", []))

            # Deduplicate results by URL
            seen_urls: set[str] = set()
            unique_results = []
            for res in all_results:
                url = res.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(res)

            return unique_results

        except Exception as e:
            logger.error(f"Tavily API error: {e}")
            return []
