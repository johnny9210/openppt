"""
Phase 3: Code Synthesizer
Merges design images + text content -> React components via Claude vision.
Runs after both text_generator and design_generator fan-in.
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

SYNTHESIZER_SYSTEM_PROMPT = """당신은 디자인 이미지를 배경으로 사용하고 텍스트를 오버레이하는 React 슬라이드 컴포넌트를 만드는 전문 개발자입니다.

★ 핵심: 디자인 이미지가 모든 시각적 요소(카드, 아이콘, 장식, 색상)를 담당합니다.
당신은 CSS로 시각 디자인을 재현하지 않습니다.
당신은 이미지 위에 텍스트만 정확한 위치에 오버레이합니다.

<output_rules>
★ 최우선 규칙: const로 시작하는 순수 React 컴포넌트 코드만 출력하세요.
코드 외의 모든 텍스트(설명, 마크다운, 사고 과정)를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<architecture>
## 컴포넌트 구조

모든 슬라이드 컴포넌트는 이 구조를 따릅니다:

```jsx
const SlideComponent = ({ content, slide_id, designImage }) => {
  // designImage: SLIDE_IMAGES[slide_id] (base64 data URL, 전역에서 전달)
  const bgImage = designImage || SLIDE_IMAGES[slide_id];

  return (
    <div style={{
      width: "100%", height: "100%", position: "relative",
      backgroundImage: bgImage ? `url(${bgImage})` : undefined,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundColor: bgImage ? undefined : THEME.background,
    }}>
      {/* 텍스트 오버레이만 여기에 배치 */}
    </div>
  );
};
```

### 텍스트 오버레이 원칙
1. 모든 텍스트는 `position: "absolute"` 또는 부모 flex 안에서 배치
2. 디자인 이미지의 레이아웃을 보고, 빈 공간에 텍스트를 정확히 위치시킴
3. 텍스트 가독성: `textShadow: "0 1px 3px rgba(0,0,0,0.1)"` 또는 반투명 배경 사용 가능
4. content props에서 모든 데이터를 동적으로 읽기 (하드코딩 금지)
5. 반복 패턴은 map()으로 렌더링
</architecture>

<constraints>
## 기술 제약사항
- 컴포넌트 이름은 반드시 [컴포넌트 이름]에 지정된 이름을 const로 선언
- import 문 작성 금지 (이미 상위에서 import됨)
- const THEME = ... 재선언 금지 (이미 전역)
- SLIDE_IMAGES는 전역 상수 (재선언 금지) — slide_id로 이미지 조회
- JSX 텍스트 안에서 < > 직접 사용 금지 → {"<"} 또는 &lt; &gt;
- 템플릿 리터럴 안 삼항 연산자: ${조건 ? 값A : 값B} (: 생략 금지)
- ★ 중첩 삼항 금지. 조건부 렌더링은 단순하게
</constraints>

<text_positioning>
## 슬라이드 타입별 텍스트 위치 가이드

이미지를 보고 빈 공간의 위치를 판단하세요. 일반적인 배치:

### cover
- 제목: left 5-8%, top 20-30%, fontSize 40-48, fontWeight 800, color THEME.text
- 부제목: left 5-8%, top 45-50%, fontSize 18, color THEME.textSecondary
- 발표자/날짜: left 5-8%, bottom 10-15%, fontSize 13, color THEME.textSecondary

### table_of_contents
- 제목: center-top, top 5-8%, fontSize 28-32, fontWeight 800
- 항목: 이미지의 카드 위치에 맞춰 절대 좌표로 배치

### key_points / icon_grid / three_column
- 제목: center-top, top 4-6%, fontSize 28-32, fontWeight 800
- 카드 텍스트: 이미지의 카드 영역 안에 배치 (카드 좌측 40%는 아이콘, 우측 60%에 텍스트)

### hero
- 메인 텍스트: center, top 30-40%, fontSize 48-56, fontWeight 800

### quote
- 인용문: center, top 30-45%, fontSize 24-28, fontWeight 600

### process_flow / timeline
- 제목: center-top
- 단계 텍스트: 이미지의 각 카드 위치에 맞춰 배치

### data_visualization
- ★ 특수 케이스: 이미지 배경 없이 recharts로 직접 렌더링할 수 있음
- 이미지가 있으면: 제목 + 인사이트만 오버레이, 차트는 이미지에 포함
- 이미지가 없으면: THEME 기반으로 직접 차트 렌더링 (기존 방식)

### comparison
- 제목: center-top
- 좌측/우측 카드 내부에 텍스트 배치

### risk_analysis
- 제목: center-top
- 각 카드 내부에 severity + title + description 배치

### summary / closing
- 제목: center-top
- 항목 텍스트: 이미지의 카드 영역에 맞춰 배치
</text_positioning>

<fallback>
## 이미지 없을 때 (fallback)
designImage가 없으면 기존 방식으로 React CSS 기반 슬라이드를 생성하세요:
- backgroundColor: THEME.background
- THEME 토큰 활용한 카드, 배지, 타이포그래피
- 인라인 스타일로 전체 디자인
</fallback>

<theme_tokens>
## THEME 토큰 (전역, 재선언 금지)
THEME.primary, THEME.accent, THEME.background, THEME.text, THEME.textSecondary
THEME.card, THEME.cardBorder, THEME.cardShadow, THEME.shadow_sm, THEME.shadow_lg
THEME.iconBg1, THEME.iconBg2, THEME.primaryLight, THEME.accentLight
THEME.gradient, THEME.subtleBg, THEME.divider
THEME.red, THEME.yellow, THEME.green
</theme_tokens>

<available_libraries>
## 사용 가능
- recharts (data_visualization용): BarChart, Bar, Cell, LineChart, Line, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 등
- React hooks: useState, useEffect
- 유니코드 이모지
</available_libraries>

<quality_gate>
## 최종 품질 검증
1. **BACKGROUND**: designImage가 있으면 backgroundImage로 설정했는가? 없으면 THEME.background 사용?
2. **POSITIONING**: 텍스트가 이미지의 빈 공간에 정확히 배치되었는가?
3. **READABILITY**: 텍스트가 배경 위에서 읽기 쉬운가? (색상 대비, 크기)
4. **DATA BINDING**: content props에서 모든 데이터를 동적으로 읽는가?
5. **NO CSS RECREATION**: 이미지가 있는데 카드/아이콘/장식을 CSS로 다시 만들지 않았는가?
</quality_gate>"""


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


async def _synthesize_slide(
    llm,
    slide_id: str,
    slide_type: str,
    image_b64: str | None,
    content: dict,
    comp_name: str,
    style: dict,
    slide_index: int = 0,
    total_slides: int = 1,
    fix_prompt: str = "",
) -> dict:
    """Synthesize React code for one slide from design image + content."""
    content_json = json.dumps(content, ensure_ascii=False, indent=2)

    user_parts = []

    # Add design image if available
    if image_b64:
        user_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        })

    # Determine slide role in narrative
    if slide_index == 0:
        narrative_role = "오프닝 — 청중의 주의를 끄는 강렬한 첫인상"
    elif slide_index == total_slides - 1:
        narrative_role = "클로징 — 핵심 메시지 정리 및 행동 유도"
    elif slide_index == 1:
        narrative_role = "도입부 — 전체 구조를 안내하는 가이드"
    else:
        narrative_role = "본론 — 핵심 콘텐츠 전달"

    has_image = bool(image_b64)

    text_prompt = f"""[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}
컴포넌트 이름: {comp_name}  ← 반드시 이 이름으로 const 선언

[테마 컬러]
primary: {style.get('primary_color', '#6366F1')}
accent: {style.get('accent_color', '#818CF8')}
background: {style.get('background', '#F5F7FA')}
text: {style.get('text_color', '#1A202C')}

[콘텐츠 데이터 — content props에서 동적으로 읽어 렌더링]
{content_json}

[이미지 배경 사용: {"YES" if has_image else "NO"}]
{"위 디자인 이미지가 이 슬라이드의 배경으로 사용됩니다." if has_image else "디자인 이미지가 없으므로 THEME 기반으로 직접 디자인하세요."}

{"★ 핵심 지시:" if has_image else ""}
{"1. SLIDE_IMAGES[slide_id]를 backgroundImage로 사용 (designImage prop 또는 SLIDE_IMAGES[slide.slide_id])" if has_image else ""}
{"2. 이미지의 빈 공간을 보고 텍스트를 position absolute로 정확히 배치" if has_image else ""}
{"3. CSS로 카드/아이콘/장식을 다시 만들지 마세요 — 이미지에 이미 있습니다" if has_image else ""}
{"4. content props에서 데이터를 읽어 텍스트만 오버레이" if has_image else ""}

{"이미지 없이 THEME 기반 디자인:" if not has_image else ""}
{"1. backgroundColor: THEME.background" if not has_image else ""}
{"2. 카드, 아이콘 배지, 타이포그래피를 직접 구현" if not has_image else ""}
{"3. 시각적 계층 (제목 > 내용 > 배경) 명확히 구분" if not has_image else ""}

공통 요구사항:
- content props에서 모든 데이터를 동적으로 읽어 렌더링 (하드코딩 금지)
- height: "100%" 필수
- 반복 패턴은 map()으로 렌더링
"""
    if fix_prompt:
        text_prompt += f"""
[이전 검증 피드백 - 반드시 반영]
{fix_prompt}
"""

    user_parts.append({"type": "text", "text": text_prompt})

    response = await llm.ainvoke([
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
        HumanMessage(content=user_parts),
    ])

    code = _extract_code(response.content)

    return {
        "slide_id": slide_id,
        "type": slide_type,
        "code": code,
    }


async def code_synthesizer(state: PPTState) -> dict:
    """Merge design images + text content -> React code via Claude vision.

    Runs after all text_generator and design_generator Send instances complete.
    Uses asyncio.gather for parallel LLM calls within this node.
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

    total_slides = len(all_slide_ids)
    tasks = []
    for idx, sid in enumerate(all_slide_ids):
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
                slide_index=idx,
                total_slides=total_slides,
                fix_prompt=fix_prompt,
            )
        )

    results = await asyncio.gather(*tasks)
    return {"generated_slides": list(results)}
