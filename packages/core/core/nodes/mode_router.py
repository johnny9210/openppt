"""
Phase 0: Mode Router
Analyzes natural language input to determine create/edit mode.
"""

import logging

from core.config import get_llm
from core.state import PPTState
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 생성 요청을 분석하는 라우터입니다.
사용자의 요청을 분석하여 mode를 결정하세요.

- "create": 새 PPT를 처음부터 생성하는 경우
- "edit": 기존 PPT의 특정 슬라이드를 수정하는 경우

반드시 아래 JSON 형식으로만 응답하세요:
{"mode": "create" | "edit", "target_slide_id": null | "slide_xxx"}
"""


async def mode_router(state: PPTState) -> dict:
    """Determine create/edit mode from user request.

    When the edit endpoint already set mode="edit" and target_slide_id,
    skip the LLM call to avoid overwriting the correct values.
    """
    # Edit endpoint already determined mode and target — pass through
    if state.get("mode") == "edit" and state.get("target_slide_id"):
        logger.info("mode_router: edit mode with target_slide_id=%s, skipping LLM", state["target_slide_id"])
        return {
            "mode": "edit",
            "target_slide_id": state["target_slide_id"],
        }

    llm = get_llm()

    response = await llm.ainvoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": state["user_request"]},
    ])

    try:
        result = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("mode_router: %s", exc)
        raise ValueError(
            f"Mode router could not parse LLM response as JSON: {exc}"
        ) from exc

    return {
        "mode": result["mode"],
        "target_slide_id": result.get("target_slide_id"),
    }
