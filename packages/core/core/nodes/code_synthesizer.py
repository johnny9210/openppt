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

SYNTHESIZER_SYSTEM_PROMPT = """당신은 프리미엄 프레젠테이션 슬라이드를 위한 React 컴포넌트 전문 개발자입니다.
제공된 디자인 이미지를 참고하여, 주어진 콘텐츠 데이터를 사용하는 React 컴포넌트를 생성합니다.

## 핵심 원칙
1. 디자인 이미지의 레이아웃, 색상, 시각적 구성을 최대한 충실히 재현
2. content props에서 데이터를 동적으로 읽어 렌더링
3. 인라인 스타일만 사용 (CSS 파일 없음)

## 디자인 시스템
### 글라스 카드
```jsx
<div style={{
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 16,
  padding: "24px 28px",
}}>
```

### 아이콘 배지
```jsx
<div style={{
  width: 52, height: 52, borderRadius: 16,
  background: "rgba(99,102,241,0.15)",
  display: "flex", alignItems: "center", justifyContent: "center",
  fontSize: 24,
}}>⚡</div>
```

### 타이포그래피
- 히어로 제목: fontSize 42~52, fontWeight 800, lineHeight 1.1
- 제목 내 강조 단어: color THEME.accent
- 섹션 제목: fontSize 20~24, fontWeight 700
- 카드 제목: fontSize 17~19, fontWeight 600
- 본문: fontSize 14~15, color THEME.text, opacity 0.6, lineHeight 1.5
- 대형 지표: fontSize 48~64, fontWeight 800

### 색상 규칙
- 배경: THEME.background
- 텍스트: THEME.text
- 포인트: THEME.accent
- 상태: THEME.green(긍정), THEME.red(부정), THEME.yellow(주의)
- 글라스: rgba(255,255,255,0.04~0.08) 배경 + rgba(255,255,255,0.08~0.15) 보더

## 절대 금지
- 컴포넌트 이름은 반드시 [컴포넌트 이름]에 지정된 이름 사용
- import 문 작성 금지 (이미 상위에서 import됨)
- const THEME = ... 재선언 금지 (이미 전역)
- 인라인 hex 컬러 금지 (THEME 객체 또는 rgba 사용)
- 설명, 마크다운 없이 순수 React 컴포넌트 코드만 출력
- JSX 텍스트 안에서 < > 문자 직접 사용 금지 -> {"<"} 또는 &lt; &gt; 사용

## 사용 가능
- THEME.primary, THEME.accent, THEME.background, THEME.text, THEME.red, THEME.yellow, THEME.green
- recharts: BarChart, Bar, Cell, LineChart, Line, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
- React hooks: useState (이미 전역)
- 유니코드 이모지"""


def _extract_code(text: str) -> str:
    """Extract code from LLM response, removing markdown fences."""
    code = re.sub(r"^```(?:jsx|javascript|tsx|js)?\s*\n?", "", text.strip())
    code = re.sub(r"\n?```\s*$", "", code)
    return code


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
    """Synthesize React code for one slide from design image + content."""
    content_json = json.dumps(content, ensure_ascii=False, indent=2)

    user_parts = []

    # Add design image if available
    if image_b64:
        user_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        })

    text_prompt = f"""[슬라이드]
slide_id: {slide_id}
type: {slide_type}
컴포넌트 이름: {comp_name}  <- 반드시 이 이름으로 const 선언

[테마 컬러]
primary_color: {style.get('primary_color', '#6366F1')}
accent_color: {style.get('accent_color', '#818CF8')}
background: {style.get('background', '#050810')}
text_color: {style.get('text_color', '#E2E8F0')}

[콘텐츠 데이터]
{content_json}

{"위 디자인 이미지를 참고하여 " if image_b64 else ""}프리미엄 React 슬라이드 컴포넌트를 생성하세요.
- content props에서 데이터를 읽어 동적으로 렌더링
- 디자인 이미지의 레이아웃과 시각적 구성을 충실히 재현
- height: "100%" 필수
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
