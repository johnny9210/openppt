"""
Phase 3-C: Semantic Validator
Core module from the assignment. Verifies that generated code fulfills
slot instructions from the PPTState JSON.

Implements the pseudo code from semantic_validator_pseudo.py exactly.
"""

import json
import re
from typing import Literal

from core.config import get_llm
from core.state import PPTState


# --- Data structures ---

class Slot:
    def __init__(
        self,
        slot_key: str,
        instruction: str,
        slide_id: str,
        importance: Literal["critical", "major", "minor"],
    ):
        self.slot_key = slot_key
        self.instruction = instruction
        self.slide_id = slide_id
        self.importance = importance


# --- STEP 1: Slot List Extractor ---

def extract_slots(slide_spec: dict) -> list[Slot]:
    """Extract verification target slots from slide_spec."""
    slots = []
    slides = slide_spec["ppt_state"]["presentation"]["slides"]

    for slide in slides:
        for slot_key, instruction in slide.get("slots", {}).items():
            importance = _classify_importance(slot_key)
            slots.append(
                Slot(
                    slot_key=slot_key,
                    instruction=instruction,
                    slide_id=slide["slide_id"],
                    importance=importance,
                )
            )

    return slots


def _classify_importance(slot_key: str) -> Literal["critical", "major", "minor"]:
    """Classify slot importance based on key name."""
    if any(k in slot_key for k in ("renderer", "layout", "grid")):
        return "critical"
    if any(k in slot_key for k in ("color", "badge", "highlight")):
        return "major"
    return "minor"


# --- STEP 2: Slide Component Extractor ---

TYPE_COMPONENT_MAP = {
    "cover": "CoverSlide",
    "table_of_contents": "TocSlide",
    "data_visualization": "DataVizSlide",
    "key_points": "KeyPointsSlide",
    "risk_analysis": "RiskSlide",
    "action_plan": "ActionPlanSlide",
}


def extract_slide_component(react_code: str, slide_id: str, slide_type: str) -> str:
    """Extract component code block for a specific slide.

    Uses section markers (``// ── [slide_id] ...``) as boundaries so that
    sub-components defined within the same slide section (e.g.
    ``BarChartRenderer`` inside the ``DataVizSlide`` section) are included.
    Falls back to a component-name based regex when markers are absent.
    """
    component_name = TYPE_COMPONENT_MAP.get(slide_type, "")
    if not component_name:
        return react_code

    # --- Strategy 1: section-marker boundaries ---
    # Matches the section header for the given slide_id, then captures
    # everything up to the next section header or a major boundary
    # (SlideFactory / Presentation root / top-level export).
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

    # --- Strategy 2 (fallback): component-name based extraction ---
    pattern = rf"(const {component_name}[\s\S]*?)(?=\n(?:const \w+|// ──|export ))"
    match = re.search(pattern, react_code)
    return match.group(1) if match else react_code


# --- STEP 3: LLM Slot Verifier ---

VERIFY_PROMPT = """당신은 React 컴포넌트 코드 검증 전문가입니다.

[검증 대상 슬롯]
슬롯 이름: {slot_key}
슬롯 지시사항: {instruction}

[Reference Component (기준)]
{reference}

[생성된 Component (검증 대상)]
{generated}

위 슬롯이 생성된 컴포넌트에 올바르게 구현되었는지 판단하세요.
- Reference의 슬롯 위치에 지시사항에 맞는 코드가 있어야 합니다.
- 구현 방식(className, style, 변수명 등)은 자유이나 의도는 충족해야 합니다.

반드시 아래 JSON 형식으로만 응답하세요:
{{"filled": true | false, "reason": "판단 근거를 한 문장으로", "code_snippet": "관련 코드 조각 (없으면 null)"}}
"""


async def _verify_slot(
    slot: Slot,
    reference: str,
    generated: str,
) -> dict:
    """Verify a single slot with LLM."""
    llm = get_llm()

    prompt = VERIFY_PROMPT.format(
        slot_key=slot.slot_key,
        instruction=slot.instruction,
        reference=reference,
        generated=generated,
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"filled": False, "reason": "LLM response parse error", "code_snippet": None}


async def _verify_all_slots(
    slots: list[Slot],
    reference_components: dict,
    react_code: str,
    slide_spec: dict,
) -> tuple[bool, list[Slot]]:
    """Verify all slots. Fail fast on critical slot failure."""
    missing_slots = []
    slides = {s["slide_id"]: s for s in slide_spec["ppt_state"]["presentation"]["slides"]}

    for slot in slots:
        slide = slides.get(slot.slide_id, {})
        slide_type = slide.get("type", "")

        reference = reference_components.get(slide_type, "")
        generated = extract_slide_component(react_code, slot.slide_id, slide_type)

        result = await _verify_slot(slot, reference, generated)

        if not result.get("filled", False):
            missing_slots.append(slot)
            if slot.importance == "critical":
                return False, missing_slots

    critical_major_missing = [
        s for s in missing_slots if s.importance in ("critical", "major")
    ]
    return len(critical_major_missing) == 0, missing_slots


# --- STEP 4: Verdict Generator ---

def _generate_fix_prompt(missing_slots: list[Slot]) -> str:
    """Generate fix prompt for regeneration."""
    descriptions = []
    for slot in missing_slots:
        if slot.importance in ("critical", "major"):
            descriptions.append(
                f"- [{slot.slide_id}] '{slot.slot_key}' 슬롯 누락.\n"
                f"  지시사항: {slot.instruction}\n"
                f"  Reference Component의 해당 슬롯 위치를 참고하여 반드시 구현할 것."
            )

    return f"""이전에 생성한 React 코드에서 아래 슬롯이 누락되었습니다.
Reference Component를 다시 참고하여 누락된 슬롯만 추가하세요.

[누락된 슬롯 목록]
{chr(10).join(descriptions)}

[원칙]
- 누락된 슬롯이 있는 컴포넌트만 수정할 것
- Reference Component의 전체 구조는 변경하지 말 것
- 슬롯 지시사항의 의도를 코드로 정확히 반영할 것
"""


# --- Main entry point ---

async def semantic_validator(state: PPTState) -> dict:
    """Semantic Validator - verifies intent fulfillment."""
    slide_spec = state["slide_spec"]
    reference_components = state["reference_components"]
    react_code = state["react_code"]

    # STEP 1: Extract slots
    slots = extract_slots(slide_spec)

    # STEP 2+3: Verify each slot
    passed, missing = await _verify_all_slots(
        slots, reference_components, react_code, slide_spec
    )

    total = len(slots)
    passed_count = total - len(missing)

    result = {
        "layer": "semantic",
        "status": "pass" if passed else "fail",
        "total": total,
        "passed": passed_count,
        "missing_slots": [s.slot_key for s in missing],
        "fix_prompt": None if passed else _generate_fix_prompt(missing),
    }

    update: dict = {"validation_result": result}
    if not passed:
        update["revision_count"] = state.get("revision_count", 0) + 1
        update["error_log"] = [
            {
                "layer": "semantic",
                "revision": state.get("revision_count", 0) + 1,
                "missing": [s.slot_key for s in missing],
            }
        ]

    return update
