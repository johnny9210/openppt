"""
Tavily Web Search — simplified from aidx deep_research pattern.
Provides direct search function for web_researcher node.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazy-init TavilyClient singleton."""
    global _client
    if _client is None:
        from tavily import TavilyClient

        key = os.getenv("TAVILY_API_KEY", "")
        if not key:
            raise ValueError("TAVILY_API_KEY not set")
        _client = TavilyClient(api_key=key)
        logger.info("[Tavily] Client initialized")
    return _client


def tavily_search_sync(query: str, max_results: int = 5) -> list[dict]:
    """Synchronous Tavily web search."""
    client = _get_client()
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
    )
    return [
        {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "content": r.get("content", "")[:500],
        }
        for r in response.get("results", [])
    ]


async def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Async wrapper for Tavily web search."""
    return await asyncio.to_thread(tavily_search_sync, query, max_results)
