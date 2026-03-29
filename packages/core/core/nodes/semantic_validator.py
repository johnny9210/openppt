"""
Phase 3-C: Semantic Validator (HTML Edition)
Verifies that generated HTML properly reflects the slide content.

Checks each slide's HTML against its content data using LLM verification.
Uses individual slide codes from generated_slides (not extracted from assembled HTML).
"""

import asyncio
import json
import logging

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.runnables import RunnableConfig

from core.config import get_llm, LLM_TIMEOUT
from core.state import PPTState

logger = logging.getLogger(__name__)


# --- STEP 1: LLM Content Verifier ---

VERIFY_PROMPT = """당신은 HTML 프레젠테이션 슬라이드 검증 전문가입니다.

[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}

[콘텐츠 데이터 (이 데이터가 HTML에 반영되어야 함)]
{content_json}

[생성된 HTML 코드]
{generated}

위 콘텐츠 데이터가 생성된 HTML에 적절히 반영되었는지 검증하세요.

검증 기준:
1. title, items, points 등 핵심 텍스트가 HTML에 포함되어 있는가?
2. 배열 데이터의 각 항목이 개별적으로 렌더링되어 있는가?
3. 데이터 시각화가 필요한 경우 SVG 차트 또는 시각적 표현이 있는가?
4. 빈 영역이 남아있지 않고 텍스트가 삽입되어 있는가?

반드시 아래 JSON 형식으로만 응답하세요:
{{"pass": true | false, "issues": ["문제1", "문제2"], "summary": "한 문장 요약"}}
"""


async def _verify_slide(slide: dict, generated: str) -> tuple[dict, dict]:
    """Verify a single slide's content reflection with LLM.
    Returns (result, token_usage).
    """
    llm = get_llm()

    prompt = VERIFY_PROMPT.format(
        slide_id=slide["slide_id"],
        slide_type=slide["type"],
        content_json=json.dumps(slide.get("content", {}), ensure_ascii=False, indent=2),
        generated=generated,
    )

    input_tokens = 0
    output_tokens = 0

    with get_usage_metadata_callback() as cb:
        response = await asyncio.wait_for(
            llm.ainvoke([{"role": "user", "content": prompt}]),
            timeout=LLM_TIMEOUT,
        )
        if cb.usage_metadata:
            for _, usage in cb.usage_metadata.items():
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)

    tokens = {"input_tokens": input_tokens, "output_tokens": output_tokens}

    try:
        return json.loads(response.content), tokens
    except json.JSONDecodeError:
        try:
            text = response.content
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end]), tokens
        except (ValueError, json.JSONDecodeError):
            return {
                "pass": False,
                "issues": ["LLM 응답 파싱 실패"],
                "summary": "검증 응답 파싱 오류",
            }, tokens


async def _verify_all_slides(
    slides: list[dict],
    generated_map: dict[str, str],
) -> tuple[bool, list[dict], dict]:
    """Verify all slides in parallel. Returns (passed, failed_slides, token_usage)."""
    total_in = 0
    total_out = 0

    async def _check_one(slide):
        nonlocal total_in, total_out
        html_code = generated_map.get(slide["slide_id"], "")
        if not html_code:
            return {
                "slide_id": slide["slide_id"],
                "slide_type": slide["type"],
                "issues": ["슬라이드 HTML 코드가 없습니다"],
                "summary": "생성된 코드 없음",
            }

        result, tokens = await _verify_slide(slide, html_code)
        total_in += tokens.get("input_tokens", 0)
        total_out += tokens.get("output_tokens", 0)

        if not result.get("pass", False):
            return {
                "slide_id": slide["slide_id"],
                "slide_type": slide["type"],
                "issues": result.get("issues", []),
                "summary": result.get("summary", ""),
            }
        return None

    results = await asyncio.gather(*[_check_one(s) for s in slides])
    failed_slides = [r for r in results if r is not None]

    return (
        len(failed_slides) == 0,
        failed_slides,
        {"input_tokens": total_in, "output_tokens": total_out},
    )


# --- STEP 2: Fix Prompt Generator ---

def _generate_fix_prompt(failed_slides: list[dict]) -> str:
    """Generate fix prompt for regeneration."""
    descriptions = []
    for fs in failed_slides:
        issues = "\n".join(f"    - {issue}" for issue in fs["issues"])
        descriptions.append(
            f"- [{fs['slide_id']}] {fs['slide_type']}\n"
            f"  문제점:\n{issues}\n"
            f"  요약: {fs['summary']}"
        )

    return f"""이전에 생성한 HTML 코드에서 콘텐츠가 제대로 반영되지 않은 슬라이드가 있습니다.

[문제 슬라이드 목록]
{chr(10).join(descriptions)}

[수정 원칙]
- 문제가 있는 슬라이드만 수정
- 콘텐츠 데이터의 텍스트를 HTML에 올바르게 삽입
- 기존 디자인(CSS, 레이아웃, 색상)은 유지
- 빈 영역이 남지 않도록 모든 텍스트 삽입 확인
"""


# --- Main entry point ---

async def semantic_validator(state: PPTState, config: RunnableConfig) -> dict:
    """Semantic Validator - verifies content reflection in generated HTML."""
    cancel_event = (config.get("configurable") or {}).get("cancel_event")
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

    slide_spec = state["slide_spec"]
    slides = slide_spec["ppt_state"]["presentation"]["slides"]

    # Build map of slide_id → individual HTML code from generated_slides
    generated_slides = state.get("generated_slides", [])
    # Deduplicate (keep latest)
    seen = {}
    for s in generated_slides:
        seen[s["slide_id"]] = s
    generated_map = {sid: s["code"] for sid, s in seen.items()}

    # On retry, only re-verify the slides that were previously fixed
    prev_validation = state.get("validation_result", {})
    prev_failed_ids = set(prev_validation.get("failed_slide_ids", []))
    revision_count = state.get("revision_count", 0)

    if prev_failed_ids and revision_count > 0:
        slides_to_verify = [s for s in slides if s["slide_id"] in prev_failed_ids]
        logger.info(
            "[SemanticValidator] Retry mode: verifying %d/%d failed slides only",
            len(slides_to_verify),
            len(slides),
        )
    else:
        slides_to_verify = slides

    passed, failed, verify_tokens = await _verify_all_slides(slides_to_verify, generated_map)

    total = len(slides)
    passed_count = total - len(failed)

    if passed:
        logger.info("[SemanticValidator] PASS - %d/%d slides", passed_count, total)
    else:
        logger.error("[SemanticValidator] FAIL - %d/%d passed", passed_count, total)
        for fs in failed:
            logger.error(
                "[SemanticValidator]   FAILED %s (%s): %s",
                fs["slide_id"],
                fs["slide_type"],
                fs["summary"],
            )
            for issue in fs.get("issues", []):
                logger.error("[SemanticValidator]     - %s", issue[:200])

    result = {
        "layer": "semantic",
        "status": "pass" if passed else "fail",
        "total": total,
        "passed": passed_count,
        "failed_slide_ids": [fs["slide_id"] for fs in failed],
        "missing_slots": [fs["slide_id"] for fs in failed],  # backward compat
        "fix_prompt": None if passed else _generate_fix_prompt(failed),
    }

    update: dict = {
        "validation_result": result,
        "token_usage": verify_tokens,
    }
    if not passed:
        update["revision_count"] = state.get("revision_count", 0) + 1
        update["error_log"] = [
            {
                "layer": "semantic",
                "revision": state.get("revision_count", 0) + 1,
                "failed_slides": [fs["slide_id"] for fs in failed],
            }
        ]

    return update
