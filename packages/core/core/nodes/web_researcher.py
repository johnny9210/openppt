"""
Phase 1.5: Web Researcher (deep_research pattern)
Searches the web for relevant data to enrich slide content.
Runs after scoping, before parallel generation.

Enriches research_brief.slide_plan with web_research data per slide.
Gracefully skips if TAVILY_API_KEY is not set.
"""

import asyncio
import logging

from langchain_core.runnables import RunnableConfig

from core.config import TAVILY_API_KEY, LLM_TIMEOUT
from core.state import PPTState

logger = logging.getLogger(__name__)

# Slide types that benefit from web research
_RESEARCH_TYPES = {
    "hero", "key_points", "three_column", "comparison",
    "data_visualization", "risk_analysis", "action_plan",
    "process_flow", "timeline", "icon_grid", "summary",
    "quote",
}

# Max concurrent Tavily searches
_MAX_CONCURRENT = 3


def _get_cancel_event(config: RunnableConfig) -> asyncio.Event | None:
    configurable = config.get("configurable", {}) if config else {}
    return configurable.get("cancel_event")


async def web_researcher(state: PPTState, config: RunnableConfig) -> dict:
    """Enrich research_brief with web search results for content-heavy slides.

    For each slide that benefits from research, generates a search query
    from the slide topic + presentation context, runs Tavily search,
    and attaches results as slide["web_research"].

    Skips gracefully if TAVILY_API_KEY is not configured.
    """
    cancel_event = _get_cancel_event(config)
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

    if not TAVILY_API_KEY:
        logger.info("[WebResearch] TAVILY_API_KEY not set — skipping web research")
        return {}

    brief = state["research_brief"]
    slide_plan = brief.get("slide_plan", [])
    purpose = brief.get("purpose", "")
    key_message = brief.get("key_message", "")

    # Collect slides that need research
    search_tasks: list[tuple[str, str]] = []
    for slide in slide_plan:
        if slide["type"] not in _RESEARCH_TYPES:
            continue
        topic = slide.get("topic", "")
        # Build search query: purpose + topic for context
        query = f"{key_message} {topic}".strip()
        if not query:
            continue
        search_tasks.append((slide["slide_id"], query))

    if not search_tasks:
        logger.info("[WebResearch] No slides need research")
        return {}

    logger.info("[WebResearch] Searching %d slides...", len(search_tasks))

    from core.tools.tavily_tool import tavily_search

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    total_searches = 0

    async def _search_one(slide_id: str, query: str) -> tuple[str, list[dict]]:
        nonlocal total_searches
        if cancel_event and cancel_event.is_set():
            raise asyncio.CancelledError()
        async with semaphore:
            try:
                results = await asyncio.wait_for(
                    tavily_search(query, max_results=5),
                    timeout=LLM_TIMEOUT,
                )
                total_searches += 1
                logger.info(
                    "[WebResearch] %s: %d results for '%s'",
                    slide_id, len(results), query[:60],
                )
                return slide_id, results
            except asyncio.TimeoutError:
                logger.warning("[WebResearch] Timeout for %s", slide_id)
                return slide_id, []
            except Exception as e:
                logger.warning("[WebResearch] Failed for %s: %s", slide_id, e)
                return slide_id, []

    raw_results = await asyncio.gather(*[
        _search_one(sid, q) for sid, q in search_tasks
    ])

    # Build lookup
    research_map = {sid: data for sid, data in raw_results if data}

    # Enrich slide_plan with web_research
    enriched_plan = []
    for slide in slide_plan:
        sid = slide["slide_id"]
        if sid in research_map:
            slide = {**slide, "web_research": research_map[sid]}
        enriched_plan.append(slide)

    enriched_brief = {**brief, "slide_plan": enriched_plan}

    logger.info(
        "[WebResearch] Done: %d/%d slides enriched, %d total searches",
        len(research_map), len(search_tasks), total_searches,
    )

    return {"research_brief": enriched_brief}
