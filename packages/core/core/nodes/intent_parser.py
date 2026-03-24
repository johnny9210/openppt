"""
Phase 1-A: Intent Parser
Extracts slide types, theme, content keywords, and mode from natural language.
3-step refinement: intent extraction -> missing value handling -> conflict resolution
"""

import logging

from core.config import get_llm
from core.state import PPTState
from core.prompts.intent_parser import INTENT_PARSER_PROMPT
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)


async def intent_parser(state: PPTState) -> dict:
    """Extract structured intent from natural language request."""
    llm = get_llm()

    response = await llm.ainvoke([
        {"role": "system", "content": INTENT_PARSER_PROMPT},
        {"role": "user", "content": state["user_request"]},
    ])

    try:
        parsed = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("intent_parser: %s", exc)
        raise ValueError(
            f"Intent parser could not parse LLM response as JSON: {exc}"
        ) from exc

    return {
        "slide_spec": parsed,
    }
