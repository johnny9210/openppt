"""
Phase 1-B: Schema Abstractor
Converts parsed intent into validated PPTState JSON with slots fields.
"""

import json
import logging

from core.config import get_llm
from core.state import PPTState
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 스펙을 PPTState JSON으로 변환하는 전문가입니다.

입력된 슬라이드 스펙을 아래 구조의 JSON으로 변환하세요:

{
  "ppt_state": {
    "session_id": "sess_생성",
    "mode": "create",
    "target_slide_id": null,
    "revision_count": 0,
    "presentation": {
      "meta": {
        "title": "제목",
        "theme": {
          "primary_color": "#hex",
          "accent_color": "#hex",
          "background": "#hex",
          "text_color": "#hex"
        },
        "total_slides": N,
        "language": "ko"
      },
      "slides": [
        {
          "slide_id": "slide_001",
          "index": 0,
          "type": "cover|table_of_contents|data_visualization|key_points|risk_analysis|action_plan",
          "state": "INITIAL|NAVIGATION|DATA_HEAVY|CONTENT_RICH|ANALYTICAL|CONCLUDING",
          "content": { ... },
          "slots": {
            "slot_key": "condition → action_slot"
          }
        }
      ]
    }
  }
}

핵심 원칙:
1. 모든 조건부 로직은 slots 필드에 명시
2. slots는 "condition → action_slot" 형식
3. 미입력 데이터는 data=null 플래그 + 샘플 데이터 대체
4. 충돌 시: 명시적 > 암묵적, 구체적 > 일반적

반드시 유효한 JSON만 응답하세요.
"""


async def schema_abstractor(state: PPTState) -> dict:
    """Convert parsed intent into full PPTState JSON."""
    llm = get_llm()

    spec_str = json.dumps(state["slide_spec"], ensure_ascii=False)

    response = await llm.ainvoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": spec_str},
    ])

    try:
        slide_spec = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("schema_abstractor: %s", exc)
        raise ValueError(
            f"Schema abstractor could not parse LLM response as JSON: {exc}"
        ) from exc

    return {"slide_spec": slide_spec}
