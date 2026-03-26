"""
Phase 3: Code Synthesizer (2-Pass Architecture)
Pass 1 (Vision): Design image -> React/CSS layout code (structure only, no text)
Pass 2 (Code):   Layout code + text content -> Final React component with text

Separates layout generation from text insertion to eliminate text
positioning errors. Claude Vision focuses on visual structure in Pass 1,
then Claude precisely inserts text into the established layout in Pass 2.
"""

import asyncio
import json
import logging
import re

from langchain_core.messages import SystemMessage, HumanMessage

from core.config import get_llm
from core.state import PPTState

logger = logging.getLogger(__name__)

COMPONENT_NAMES = {
    "cover": "CoverSlide",
    "table_of_contents": "TocSlide",
    "hero": "HeroSlide",
    "quote": "QuoteSlide",
    "icon_grid": "IconGridSlide",
    "key_points": "KeyPointsSlide",
    "three_column": "ThreeColumnSlide",
    "comparison": "ComparisonSlide",
    "process_flow": "ProcessFlowSlide",
    "timeline": "TimelineSlide",
    "data_visualization": "DataVizSlide",
    "risk_analysis": "RiskSlide",
    "action_plan": "ActionPlanSlide",
    "summary": "SummarySlide",
    "closing": "ClosingSlide",
}


# ── Pass 1: Layout Generation (Vision -> CSS) ─────────────────

LAYOUT_SYSTEM_PROMPT = """당신은 디자인 이미지를 React 인라인 스타일 코드로 변환하는 전문 개발자입니다.

★ 핵심 임무: 디자인 이미지의 시각적 구조를 React/CSS 코드로 정확히 재현합니다.
텍스트 콘텐츠는 렌더링하지 않습니다 — 텍스트가 들어갈 구조만 잡아둡니다.

<output_rules>
★ 최우선 규칙: const로 시작하는 순수 React 컴포넌트 코드만 출력하세요.
코드 외의 모든 텍스트(설명, 마크다운, 사고 과정)를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<task>
## 재현할 요소
1. **레이아웃 구조**: 카드 배치(grid, flex), 간격, 패딩, 마진 — 이미지와 최대한 동일하게
2. **카드 스타일**: 배경색, border-radius, box-shadow, 테두리
3. **아이콘 배지**: 원형 배지의 크기, 색상, 위치 — 이모지는 플레이스홀더("●")로
4. **장식 요소**: 액센트 바, 배경 패턴, 그라데이션, 화살표, 연결선
5. **색상**: THEME 토큰으로 이미지의 색상 팔레트를 재현

## 텍스트 처리 규칙
- content props를 구조분해하여 받되, 텍스트를 직접 렌더링하지 마세요
- 배열 데이터는 map()으로 반복 구조를 잡되, 내부에 텍스트를 렌더링하지 마세요
- 텍스트가 들어갈 자리에는 적절한 높이/여백을 가진 빈 영역을 만드세요

## 예시
```jsx
const KeyPointsSlide = ({ content }) => {
  const points = content.points || [];
  return (
    <div style={{ height: "100%", background: THEME.background, padding: "48px 60px" }}>
      {/* 제목 영역 */}
      <div style={{ textAlign: "center", marginBottom: 8 }} />
      <div style={{ width: 48, height: 4, borderRadius: 2, background: THEME.primary, margin: "0 auto 32px" }} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20, maxWidth: 800, margin: "0 auto" }}>
        {points.map((_, i) => (
          <div key={i} style={{
            background: THEME.card, borderRadius: 16, padding: "24px 20px",
            boxShadow: THEME.cardShadow, border: `1px solid ${THEME.cardBorder}`,
            display: "flex", alignItems: "flex-start", gap: 16,
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
              background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, color: "#fff",
            }}>{"●"}</div>
            <div style={{ flex: 1 }}>
              {/* 텍스트 삽입 영역 */}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```
</task>

<constraints>
- 컴포넌트 이름은 반드시 지정된 이름으로 const 선언
- import 문 작성 금지 (이미 상위에서 import됨)
- const THEME = ... 재선언 금지 (이미 전역)
- SLIDE_IMAGES 참조 금지 — 이미지를 배경으로 사용하지 않음, CSS로 직접 구현
- height: "100%" 필수
- JSX 텍스트 안에서 < > 직접 사용 금지 → {"<"} 또는 &lt; &gt;
- 템플릿 리터럴 안 삼항 연산자: ${조건 ? 값A : 값B} (: 생략 금지)
- ★ 중첩 삼항 금지. 조건부 렌더링은 단순하게
</constraints>

<theme_tokens>
THEME.primary, THEME.accent, THEME.background, THEME.text, THEME.textSecondary
THEME.card, THEME.cardBorder, THEME.cardShadow, THEME.shadow_sm, THEME.shadow_lg
THEME.iconBg1, THEME.iconBg2, THEME.primaryLight, THEME.accentLight
THEME.gradient, THEME.subtleBg, THEME.divider
THEME.red, THEME.yellow, THEME.green
</theme_tokens>"""


# ── Pass 2: Text Insertion (Code -> Code) ─────────────────────

TEXT_INSERT_SYSTEM_PROMPT = """당신은 React 슬라이드 컴포넌트에 텍스트 콘텐츠를 삽입하는 전문 개발자입니다.

★ 핵심 임무: 주어진 레이아웃 코드의 빈 영역에 텍스트 콘텐츠를 삽입하고, 스타일을 미세 조정합니다.

<output_rules>
★ 최우선 규칙: const로 시작하는 순수 React 컴포넌트 코드만 출력하세요.
코드 외의 모든 텍스트를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<task>
## 해야 할 것
1. **레이아웃 유지**: 기존 코드의 카드 배치, 그리드, 색상, 스타일을 그대로 유지
2. **텍스트 삽입**: 빈 영역 / 주석 위치에 content props의 데이터를 렌더링
3. **동적 바인딩**: 모든 텍스트는 content props에서 읽기 (하드코딩 금지)
4. **아이콘/이모지**: "●" 플레이스홀더를 실제 이모지(content에서 읽기)로 교체
5. **반복 렌더링**: 배열 데이터는 기존 map() 구조 안에서 텍스트 추가
6. **가독성 확보**: 배경 대비 텍스트 가독성 보장

## 텍스트 스타일 가이드
- 메인 제목: fontSize 28-44, fontWeight 800, color THEME.text
- 부제목/설명: fontSize 14-18, color THEME.textSecondary, lineHeight 1.5
- 카드 제목: fontSize 16-18, fontWeight 600, color THEME.text
- 카드 설명: fontSize 12-14, color THEME.textSecondary, lineHeight 1.5
- 강조 수치/메트릭: fontSize 20-24, fontWeight 700, color THEME.primary
- 라벨/태그: fontSize 11-13, fontWeight 500
</task>

<do_not>
## 하지 말 것
- 레이아웃 구조 변경 (카드 수, 그리드 컬럼 수, 전체 패딩 등)
- 새로운 시각 요소 추가 (카드, 아이콘 배지 등 추가 금지)
- 기존 CSS 스타일 대폭 변경 (색상, 그림자, border-radius 등)
- 컴포넌트 이름 변경
- import 문 추가
- const THEME 재선언
</do_not>

<constraints>
- 컴포넌트 이름 유지
- import 문 작성 금지
- const THEME = ... 재선언 금지
- height: "100%" 유지
- JSX 텍스트 안에서 < > 직접 사용 금지
- 템플릿 리터럴 안 삼항 연산자: ${조건 ? 값A : 값B} (: 생략 금지)
- ★ 중첩 삼항 금지
- 코드 블록(```)으로 감싸는 것은 허용합니다
</constraints>

<available_libraries>
- recharts: BarChart, Bar, Cell, LineChart, Line, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 등
- React hooks: useState, useEffect
- 유니코드 이모지
</available_libraries>"""


# ── Code extraction helpers ───────────────────────────────────

def _extract_code(text: str) -> str:
    """Extract code from LLM response, removing markdown fences, preamble text, and fixing common errors."""
    code = text.strip()

    # If response contains a code fence, extract only the fenced block
    fence_match = re.search(r"```(?:jsx|javascript|tsx|js)?\s*\n([\s\S]*?)```", code)
    if fence_match:
        code = fence_match.group(1).strip()
    else:
        # Remove any markdown fences at boundaries
        code = re.sub(r"^```(?:jsx|javascript|tsx|js)?\s*\n?", "", code)
        code = re.sub(r"\n?```\s*$", "", code)

    # Strip any preamble text before the first const/function declaration
    # (LLM sometimes outputs thinking/planning text before code)
    code_start = re.search(r"^(?:const |function |export )", code, re.MULTILINE)
    if code_start and code_start.start() > 0:
        code = code[code_start.start():]

    code = _fix_broken_ternaries(code)
    code = _fix_bracket_balance(code)
    return code


def _fix_bracket_balance(code: str) -> str:
    """Check and warn about bracket imbalance in generated code.

    Attempts simple fixes for common LLM parenthesis errors.
    """
    # Count brackets outside of string literals
    counts = {"(": 0, ")": 0, "{": 0, "}": 0, "[": 0, "]": 0}
    in_string = None
    i = 0
    while i < len(code):
        ch = code[i]
        if in_string:
            if ch == "\\" and i + 1 < len(code):
                i += 2
                continue
            if ch == in_string:
                in_string = None
        elif ch in ("'", '"', "`"):
            in_string = ch
        elif ch in counts:
            counts[ch] += 1
        i += 1

    # Fix trailing missing closing brackets
    # e.g., missing final ");" or "};"
    paren_diff = counts["("] - counts[")"]
    brace_diff = counts["{"] - counts["}"]

    if paren_diff > 0 and paren_diff <= 3:
        code = code.rstrip().rstrip(";")
        code += ")" * paren_diff + ";"
    if brace_diff > 0 and brace_diff <= 3:
        code = code.rstrip().rstrip(";")
        code += "}" * brace_diff + ";"

    return code


def _fix_broken_ternaries(code: str) -> str:
    """Fix incomplete ternary operators in template literals.

    Common LLM error:
      ${index % 2 === 0 ? THEME.primary}20
    Should be:
      ${index % 2 === 0 ? THEME.primary : THEME.accent}20
    """
    # Pattern: ${ ... ? VALUE } — missing : branch
    code = re.sub(
        r'\$\{([^}]*?\?)\s*([A-Za-z_.]+)\}',
        lambda m: '${' + m.group(1) + ' ' + m.group(2) + ' : ' + m.group(2) + '}',
        code,
    )
    return code


# ── Pass 1: Layout Generation ────────────────────────────────

async def _generate_layout(
    llm,
    slide_id: str,
    slide_type: str,
    image_b64: str | None,
    content: dict,
    comp_name: str,
    style: dict,
) -> str:
    """Pass 1: Generate CSS layout code from design image (or from scratch if no image)."""
    user_parts = []

    # Add design image for vision
    if image_b64:
        user_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        })

    # Build content structure hint (for array sizes, field names — NOT text values)
    structure_lines = []
    for k, v in content.items():
        if isinstance(v, list):
            if v and isinstance(v[0], dict):
                structure_lines.append(f"- {k}: 배열 ({len(v)}개), 각 항목 keys: {list(v[0].keys())}")
            else:
                structure_lines.append(f"- {k}: 배열 ({len(v)}개)")
        elif isinstance(v, dict):
            structure_lines.append(f"- {k}: 객체 (keys: {list(v.keys())})")
        else:
            structure_lines.append(f"- {k}: 단일 값")
    structure_hint = "\n".join(structure_lines) if structure_lines else "없음"

    has_image = bool(image_b64)

    prompt = f"""[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}
컴포넌트 이름: {comp_name}  ← 반드시 이 이름으로 const 선언

[테마 컬러]
primary: {style.get('primary_color', '#6366F1')}
accent: {style.get('accent_color', '#818CF8')}
background: {style.get('background', '#F5F7FA')}
text: {style.get('text_color', '#1A202C')}

[콘텐츠 구조 (반복 횟수 및 필드 참고용 — 텍스트 렌더링 금지)]
{structure_hint}

{"[디자인 이미지 첨부됨]" if has_image else "[이미지 없음]"}
{"이 이미지의 시각적 구조(카드 배치, 아이콘, 색상, 간격, 장식)를 React 인라인 스타일로 정확히 재현하세요." if has_image else f"'{slide_type}' 타입에 적합한 깔끔하고 전문적인 레이아웃을 THEME 기반으로 설계하세요."}
텍스트는 넣지 마세요 — 레이아웃 구조만 코드로 만드세요."""

    user_parts.append({"type": "text", "text": prompt})

    response = await llm.ainvoke([
        SystemMessage(content=LAYOUT_SYSTEM_PROMPT),
        HumanMessage(content=user_parts),
    ])

    layout_code = _extract_code(response.content)
    logger.info("[Synth:Pass1] %s (%s) - layout: %d chars", slide_id, slide_type, len(layout_code))
    return layout_code


# ── Pass 2: Text Insertion ────────────────────────────────────

async def _insert_text(
    llm,
    layout_code: str,
    slide_id: str,
    slide_type: str,
    content: dict,
    comp_name: str,
    fix_prompt: str = "",
) -> str:
    """Pass 2: Insert text content into layout code. No vision needed."""
    content_json = json.dumps(content, ensure_ascii=False, indent=2)

    prompt = f"""[레이아웃 코드 — 구조를 유지하면서 텍스트를 삽입하세요]
```jsx
{layout_code}
```

[삽입할 콘텐츠 데이터 — content props에서 동적으로 읽어 렌더링]
{content_json}

[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}
컴포넌트 이름: {comp_name}

위 레이아웃 코드의 빈 영역에 콘텐츠 데이터를 삽입하세요.
레이아웃 구조(카드 배치, 색상, 스타일)는 그대로 유지하고 텍스트와 이모지만 추가하세요."""

    if fix_prompt:
        prompt += f"""

[이전 검증 피드백 — 반드시 반영]
{fix_prompt}"""

    response = await llm.ainvoke([
        SystemMessage(content=TEXT_INSERT_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    final_code = _extract_code(response.content)
    logger.info("[Synth:Pass2] %s (%s) - final: %d chars", slide_id, slide_type, len(final_code))
    return final_code


# ── Pass 3: Layout Fitting (16:9 컨테이너 맞춤) ──────────────

FITTING_SYSTEM_PROMPT = """당신은 React 슬라이드 컴포넌트의 레이아웃을 16:9 컨테이너에 맞추는 전문가입니다.

★ 핵심 임무: 주어진 코드가 16:9 비율(약 960×540px) 컨테이너 안에 모든 요소가 들어가도록 크기를 조정합니다.

<output_rules>
★ 최우선 규칙: const로 시작하는 순수 React 컴포넌트 코드만 출력하세요.
코드 외의 모든 텍스트를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<analysis>
## 분석 절차
1. 최상위 컨테이너의 padding을 확인 → 사용 가능한 내부 영역 계산
2. 제목+설명 영역의 높이 추정 (fontSize, marginBottom 등)
3. 본문 콘텐츠 영역의 높이 추정:
   - grid/flex 레이아웃의 행 수 × (카드 높이 + gap)
   - 카드 높이 = padding-top + 아이콘 높이 + 텍스트 줄 수 × lineHeight + padding-bottom
4. 전체 높이 합산 → 540px(16:9 기준) 초과 여부 판단
</analysis>

<adjustments>
## 넘칠 때 조정 우선순위 (위에서부터 적용)
1. **padding 축소**: 외부 padding "48px 60px" → "32px 40px" 또는 "24px 32px"
2. **gap 축소**: 카드 간 gap 20 → 12~16
3. **카드 내부 padding 축소**: "24px 20px" → "16px 14px" 또는 "12px 10px"
4. **fontSize 축소**: 제목 32→26, 카드제목 17→14, 설명 13→11
5. **아이콘 배지 축소**: 52px → 40px 또는 36px
6. **marginBottom 축소**: 제목 아래 여백 줄이기
7. **그리드 재배치**: 항목 5~6개인데 2열이면 3열로 변경 고려
</adjustments>

<rules>
## 규칙
- 디자인의 시각적 정체성(색상, 카드 스타일, 구조)은 유지
- 콘텐츠를 삭제하거나 숨기지 마세요 — 크기만 조정
- 이미 16:9에 충분히 들어가는 코드는 수정하지 말고 그대로 출력
- 컴포넌트 이름, import, THEME 재선언 금지 등 기존 제약 유지
</rules>"""


async def _fit_layout(
    llm,
    code: str,
    slide_id: str,
    slide_type: str,
    comp_name: str,
) -> str:
    """Pass 3: Check if code fits in 16:9 container and adjust sizing if needed."""
    prompt = f"""[슬라이드 코드 — 16:9 컨테이너(약 960×540px)에 맞는지 확인하고 조정하세요]
```jsx
{code}
```

[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}
컴포넌트 이름: {comp_name}

이 코드의 모든 요소가 960×540px(16:9) 안에 들어가는지 분석하세요.
넘칠 가능성이 있으면 padding, gap, fontSize 등을 축소하여 맞추세요.
이미 충분히 들어가면 코드를 그대로 출력하세요."""

    response = await llm.ainvoke([
        SystemMessage(content=FITTING_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    fitted_code = _extract_code(response.content)
    logger.info("[Synth:Pass3] %s (%s) - fitted: %d chars", slide_id, slide_type, len(fitted_code))
    return fitted_code


# ── Slide synthesis (3-pass) ─────────────────────────────────

async def _synthesize_slide(
    llm,
    slide_id: str,
    slide_type: str,
    image_b64: str | None,
    content: dict,
    comp_name: str,
    style: dict,
    fix_prompt: str = "",
) -> dict:
    """Synthesize React code for one slide using 3-pass architecture.

    Pass 1 (Vision): Design image -> CSS layout code (structure only)
    Pass 2 (Code):   Layout code + content -> Final component with text
    Pass 3 (Code):   Verify 16:9 fit and adjust sizing if needed
    """
    # Pass 1: Generate layout from design image
    layout_code = await _generate_layout(
        llm, slide_id, slide_type, image_b64, content, comp_name, style,
    )

    # Pass 2: Insert text content into layout
    text_code = await _insert_text(
        llm, layout_code, slide_id, slide_type, content, comp_name, fix_prompt,
    )

    # Pass 3: Fit to 16:9 container
    final_code = await _fit_layout(
        llm, text_code, slide_id, slide_type, comp_name,
    )

    return {
        "slide_id": slide_id,
        "type": slide_type,
        "code": final_code,
    }


# ── Main entry point ─────────────────────────────────────────

async def code_synthesizer(state: PPTState) -> dict:
    """Merge design images + text content -> React code via 2-pass synthesis.

    Pass 1: Claude Vision sees design image -> generates CSS layout code
    Pass 2: Claude reads layout code + content -> inserts text precisely

    Runs after all text_generator and design_generator Send instances complete.
    Uses asyncio.gather for parallel synthesis across slides.
    """
    llm = get_llm()
    brief = state.get("research_brief", {})
    style = brief.get("style", {})

    # Build maps by slide_id
    contents_map = {c["slide_id"]: c for c in state.get("slide_contents", [])}
    designs_map = {d["slide_id"]: d for d in state.get("slide_designs", [])}

    # Get fix_prompt if retrying
    validation = state.get("validation_result", {})
    fix_prompt = validation.get("fix_prompt", "") or ""

    # Determine which slides to synthesize
    all_slide_ids = sorted(set(list(contents_map.keys()) + list(designs_map.keys())))

    # On retry, only re-synthesize failed slides
    failed_ids = validation.get("failed_slide_ids", [])
    if failed_ids and fix_prompt:
        all_slide_ids = [sid for sid in all_slide_ids if sid in set(failed_ids)]

    tasks = []
    for sid in all_slide_ids:
        content_data = contents_map.get(sid, {})
        design_data = designs_map.get(sid, {})
        slide_type = content_data.get("type") or design_data.get("type", "unknown")
        comp_name = COMPONENT_NAMES.get(
            slide_type, f"{slide_type.title().replace('_', '')}Slide"
        )

        tasks.append(
            _synthesize_slide(
                llm=llm,
                slide_id=sid,
                slide_type=slide_type,
                image_b64=design_data.get("image_b64"),
                content=content_data.get("content", {}),
                comp_name=comp_name,
                style=style,
                fix_prompt=fix_prompt,
            )
        )

    results = await asyncio.gather(*tasks)
    return {"generated_slides": list(results)}
