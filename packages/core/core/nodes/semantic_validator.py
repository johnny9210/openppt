"""
Phase 3-C: Semantic Validator
Verifies that generated code properly reflects the slide content.

Instead of slot-based checking, this version verifies:
1. Are all key content values present in the generated component?
2. Does the component structure make sense for the slide type?
"""

import json
import re
from core.config import get_llm
from core.state import PPTState


# --- STEP 1: Content Key Extractor ---

TYPE_COMPONENT_MAP = {
    "cover": "CoverSlide",
    "table_of_contents": "TocSlide",
    "data_visualization": "DataVizSlide",
    "key_points": "KeyPointsSlide",
    "risk_analysis": "RiskSlide",
    "action_plan": "ActionPlanSlide",
}


def _extract_content_keys(slide: dict) -> list[dict]:
    """Extract key content fields that MUST be reflected in the generated code."""
    content = slide.get("content", {})
    keys = []

    for key, value in content.items():
        if value is None or value == "" or value == []:
            continue
        importance = "critical" if key in ("title", "items", "points", "data", "risks", "actions", "chart") else "major"
        keys.append({
            "key": key,
            "value": value,
            "importance": importance,
            "slide_id": slide["slide_id"],
        })

    return keys


# --- STEP 2: Slide Component Extractor ---

def extract_slide_component(react_code: str, slide_id: str, slide_type: str) -> str:
    """Extract component code block for a specific slide."""
    component_name = TYPE_COMPONENT_MAP.get(slide_type, "")
    if not component_name:
        return react_code

    # Strategy 1: section-marker boundaries
    section_pattern = (
        rf"(// ──\s*\[{re.escape(slide_id)}\][^\n]*\n"
        r"[\s\S]*?)"
        r"(?=\n// ──\s*(?:\[slide_|\S)|"
        r"\nconst SlideFactory\b|"
        r"\nconst Presentation\b|"
        r"\nexport default\b|"
        r"\Z)"
    )
    section_match = re.search(section_pattern, react_code)
    if section_match:
        return section_match.group(1)

    # Strategy 2 (fallback): component-name based extraction
    pattern = rf"(const {component_name}[\s\S]*?)(?=\n(?:const \w+|// ──|export ))"
    match = re.search(pattern, react_code)
    return match.group(1) if match else react_code


# --- STEP 3: LLM Content Verifier ---

VERIFY_PROMPT = """당신은 React 프레젠테이션 코드 검증 전문가입니다.

[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}

[콘텐츠 데이터 (이 데이터가 코드에 반영되어야 함)]
{content_json}

[생성된 컴포넌트 코드]
{generated}

위 콘텐츠 데이터가 생성된 컴포넌트에 적절히 반영되었는지 검증하세요.

검증 기준:
1. title, items, points 등 핵심 데이터가 content props에서 읽혀 렌더링되는가?
2. 데이터 구조(배열, 객체)에 맞게 map/반복 처리가 되어있는가?
3. 빈 데이터에 대한 조건부 렌더링이 적절한가?
4. 차트가 필요한 경우 recharts 컴포넌트가 올바르게 사용되었는가?

반드시 아래 JSON 형식으로만 응답하세요:
{{"pass": true | false, "issues": ["문제1", "문제2"], "summary": "한 문장 요약"}}
"""


async def _verify_slide(
    slide: dict,
    generated: str,
) -> dict:
    """Verify a single slide's content reflection with LLM."""
    llm = get_llm()

    prompt = VERIFY_PROMPT.format(
        slide_id=slide["slide_id"],
        slide_type=slide["type"],
        content_json=json.dumps(slide.get("content", {}), ensure_ascii=False, indent=2),
        generated=generated,
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        try:
            text = response.content
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"pass": False, "issues": ["LLM 응답 파싱 실패"], "summary": "검증 응답 파싱 오류"}


async def _verify_all_slides(
    slides: list[dict],
    react_code: str,
) -> tuple[bool, list[dict]]:
    """Verify all slides. Returns (passed, failed_slides)."""
    failed_slides = []

    for slide in slides:
        generated = extract_slide_component(react_code, slide["slide_id"], slide["type"])
        result = await _verify_slide(slide, generated)

        if not result.get("pass", False):
            failed_slides.append({
                "slide_id": slide["slide_id"],
                "slide_type": slide["type"],
                "issues": result.get("issues", []),
                "summary": result.get("summary", ""),
            })

    return len(failed_slides) == 0, failed_slides


# --- STEP 4: Fix Prompt Generator ---

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

    return f"""이전에 생성한 React 코드에서 콘텐츠가 제대로 반영되지 않은 슬라이드가 있습니다.

[문제 슬라이드 목록]
{chr(10).join(descriptions)}

[수정 원칙]
- 문제가 있는 컴포넌트만 수정
- content props의 데이터를 올바르게 읽어 렌더링
- 디자인 가이드라인(글라스모피즘, 타이포그래피)은 유지
- 빈 데이터 처리(조건부 렌더링) 확인
"""


# --- Main entry point ---

async def semantic_validator(state: PPTState) -> dict:
    """Semantic Validator - verifies content reflection in generated code."""
    slide_spec = state["slide_spec"]
    react_code = state["react_code"]

    slides = slide_spec["ppt_state"]["presentation"]["slides"]

    # Verify each slide's content is properly reflected
    import logging
    _logger = logging.getLogger(__name__)

    passed, failed = await _verify_all_slides(slides, react_code)

    total = len(slides)
    passed_count = total - len(failed)

    if passed:
        _logger.info("[SemanticValidator] PASS - %d/%d slides", passed_count, total)
    else:
        _logger.error("[SemanticValidator] FAIL - %d/%d passed", passed_count, total)
        for fs in failed:
            _logger.error("[SemanticValidator]   FAILED %s (%s): %s",
                          fs["slide_id"], fs["slide_type"], fs["summary"])
            for issue in fs.get("issues", []):
                _logger.error("[SemanticValidator]     - %s", issue[:200])

    result = {
        "layer": "semantic",
        "status": "pass" if passed else "fail",
        "total": total,
        "passed": passed_count,
        "failed_slide_ids": [fs["slide_id"] for fs in failed],
        "missing_slots": [fs["slide_id"] for fs in failed],  # backward compat
        "fix_prompt": None if passed else _generate_fix_prompt(failed),
    }

    update: dict = {"validation_result": result}
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
