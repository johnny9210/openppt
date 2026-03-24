# =============================================================
# Task 3: Semantic Validator — Pseudo Code
# 핵심 모듈: Design System 기반 LLM 전담 검증
# =============================================================

# ─────────────────────────────────────────────────
# 데이터 구조 정의
# ─────────────────────────────────────────────────

class Slot:
    slot_key:    str     # "chart_renderer"
    instruction: str     # "chart_type=bar → BarChart_slot"
    slide_id:    str     # "slide_003"
    importance:  Literal["critical", "major", "minor"]
    # critical: 구조적 슬롯 (레이아웃, 차트 타입)
    # major:    시각적 슬롯 (색상, 배지)
    # minor:    보조 슬롯 (텍스트 크기 조정 등)

class SlotVerifyResult:
    slot_key:     str
    filled:       bool   # 슬롯이 올바르게 채워졌는가
    reason:       str    # LLM의 판단 근거
    code_snippet: str    # 관련 코드 조각

class ValidationResult:
    status:       Literal["pass", "fail"]
    total_slots:  int
    passed_slots: int
    missing_slots: list[Slot]
    fix_prompt:   str | None


# ─────────────────────────────────────────────────
# STEP 1: Slot List Extractor
# slide_spec의 slots 필드를 순회하여 검증 대상 Slot 목록 생성
# ─────────────────────────────────────────────────

FUNCTION extract_slots(slide_spec) -> list[Slot]:

    slots = []

    FOR each slide IN slide_spec.slides:
        FOR each slot_key, instruction IN slide.slots:

            # 중요도 분류
            # slot_key에 "renderer", "layout" 포함 → critical (구조 슬롯)
            # slot_key에 "color", "badge" 포함     → major   (스타일 슬롯)
            # 그 외                                → minor
            importance = classify_slot_importance(slot_key)

            slots.append(Slot(
                slot_key    = slot_key,
                instruction = instruction,
                slide_id    = slide.slide_id,
                importance  = importance
            ))

    RETURN slots


# ─────────────────────────────────────────────────
# STEP 2: Slide Component Extractor
# react_code에서 슬라이드별 컴포넌트 코드만 분리
# LLM에 전체 코드를 넘기지 않아 토큰 절감 + 판단 노이즈 제거
# ─────────────────────────────────────────────────

FUNCTION extract_slide_component(react_code, slide_id) -> str:

    component_name_map = {
        "slide_001": "CoverSlide",
        "slide_002": "TocSlide",
        "slide_003": "DataVizSlide",
        "slide_004": "KeyPointsSlide",
        "slide_005": "RiskSlide",
        "slide_006": "ActionPlanSlide",
    }

    target_component = component_name_map[slide_id]

    # react_code에서 해당 컴포넌트 함수 블록만 추출
    # "const {ComponentName}" 시작부터 해당 함수 종료까지
    component_code = extract_function_block(react_code, target_component)

    RETURN component_code


# ─────────────────────────────────────────────────
# STEP 3: LLM Slot Verifier
# Reference Component의 슬롯 정의 vs 생성 코드를 LLM에 전달
# 슬롯이 올바르게 채워졌는지 판단
# ─────────────────────────────────────────────────

FUNCTION verify_slot(slot, reference_component, generated_component) -> SlotVerifyResult:

    prompt = f"""
당신은 React 컴포넌트 코드 검증 전문가입니다.

[검증 대상 슬롯]
슬롯 이름: {slot.slot_key}
슬롯 지시사항: {slot.instruction}

[Reference Component (기준)]
{reference_component}

[생성된 Component (검증 대상)]
{generated_component}

위 슬롯이 생성된 컴포넌트에 올바르게 구현되었는지 판단하세요.
- Reference의 슬롯 위치에 지시사항에 맞는 코드가 있어야 합니다.
- 구현 방식(className, style, 변수명 등)은 자유이나 의도는 충족해야 합니다.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "filled": true | false,
  "reason": "판단 근거를 한 문장으로",
  "code_snippet": "관련 코드 조각 (없으면 null)"
}}
"""

    response = call_llm(
        prompt     = prompt,
        model      = "claude-sonnet",
        temperature = 0,        # 판단 일관성을 위해 고정
        max_tokens = 300,
        format     = "json"
    )

    RETURN parse_json(response)


# ─────────────────────────────────────────────────
# STEP 3 메인 루프: 슬롯 목록 순회 검증
# critical 슬롯 실패 시 즉시 종료 (Fail Fast)
# ─────────────────────────────────────────────────

FUNCTION verify_all_slots(slots, reference_components, react_code) -> (bool, list[Slot]):

    missing_slots = []

    FOR slot IN slots:

        reference = reference_components[get_slide_type(slot.slide_id)]
        generated = extract_slide_component(react_code, slot.slide_id)
        result    = verify_slot(slot, reference, generated)

        IF NOT result.filled:
            missing_slots.append(slot)

            # critical 슬롯 실패 → 즉시 종료
            IF slot.importance == "critical":
                RETURN (False, missing_slots)

    # major 이상 누락 시 fail, minor만 누락 시 pass
    critical_major_missing = [
        s FOR s IN missing_slots
        IF s.importance IN ["critical", "major"]
    ]

    RETURN (len(critical_major_missing) == 0, missing_slots)


# ─────────────────────────────────────────────────
# STEP 4: Verdict Generator
# 최종 판정 + 재생성용 fix_prompt 생성
# ─────────────────────────────────────────────────

FUNCTION generate_verdict(passed, missing_slots, slide_spec) -> ValidationResult:

    IF passed:
        RETURN ValidationResult(
            status        = "pass",
            total_slots   = count_all_slots(slide_spec),
            passed_slots  = count_all_slots(slide_spec) - len(missing_slots),
            missing_slots = missing_slots,
            fix_prompt    = None
        )

    ELSE:
        missing_descriptions = []

        FOR slot IN missing_slots:
            IF slot.importance IN ["critical", "major"]:
                missing_descriptions.append(
                    f"- [{slot.slide_id}] '{slot.slot_key}' 슬롯 누락.\n"
                    f"  지시사항: {slot.instruction}\n"
                    f"  Reference Component의 해당 슬롯 위치를 참고하여 반드시 구현할 것."
                )

        fix_prompt = f"""
이전에 생성한 React 코드에서 아래 슬롯이 누락되었습니다.
Reference Component를 다시 참고하여 누락된 슬롯만 추가하세요.

[누락된 슬롯 목록]
{chr(10).join(missing_descriptions)}

[원칙]
- 누락된 슬롯이 있는 컴포넌트만 수정할 것
- Reference Component의 전체 구조는 변경하지 말 것
- 슬롯 지시사항의 의도를 코드로 정확히 반영할 것
"""

        RETURN ValidationResult(
            status        = "fail",
            total_slots   = count_all_slots(slide_spec),
            passed_slots  = count_all_slots(slide_spec) - len(missing_slots),
            missing_slots = missing_slots,
            fix_prompt    = fix_prompt
        )


# ─────────────────────────────────────────────────
# 메인 진입점: Semantic Validator
# ─────────────────────────────────────────────────

FUNCTION semantic_validator(state: PPTState) -> PPTState:

    slide_spec           = state.slide_spec
    reference_components = state.reference_components
    react_code           = state.react_code

    # STEP 1: 슬롯 목록 추출
    slots = extract_slots(slide_spec)

    # STEP 2+3: 슬롯별 LLM 검증
    passed, missing = verify_all_slots(slots, reference_components, react_code)

    # STEP 4: 최종 판정
    result = generate_verdict(passed, missing, slide_spec)

    state.validation_result = {
        "layer":         "semantic",
        "status":        result.status,
        "total":         result.total_slots,
        "passed":        result.passed_slots,
        "missing_slots": [s.slot_key for s in result.missing_slots],
        "fix_prompt":    result.fix_prompt
    }

    IF result.status == "fail":
        state.revision_count += 1

    RETURN state
