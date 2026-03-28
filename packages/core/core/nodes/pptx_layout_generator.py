"""
PPTX Layout Generator
Transpiles React + Tailwind slide code to PptxGenJS-compatible JSON layouts.
Runs in parallel with the validation chain after code_assembly.
"""

import asyncio
import json
import logging
import re

from langchain_core.messages import SystemMessage, HumanMessage
from core.config import get_llm
from core.state import PPTState

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 React + Tailwind CSS 코드를 PowerPoint 슬라이드 레이아웃 JSON으로 변환하는 전문가입니다.

★ 핵심 임무: 주어진 React 컴포넌트 코드를 분석하여, 동일한 레이아웃을 PptxGenJS로 재현할 수 있는 구조화된 JSON을 생성합니다.

<coordinate_system>
## 좌표계 (인치 단위)
- 슬라이드 크기: 13.333 × 7.5 인치 (16:9)
- 원점: 좌상단 (0, 0)
- 모든 x, y, w, h 값은 인치(소수점 2자리)

## Tailwind → 인치 변환 규칙
- 1rem = 16px = 0.222인치
- p-1=4px=0.056", p-2=8px=0.111", p-3=12px=0.167", p-4=16px=0.222"
- p-5=20px=0.278", p-6=24px=0.333", p-8=32px=0.444", p-10=40px=0.556"
- p-12=48px=0.667", p-16=64px=0.889"
- gap-1=4px, gap-2=8px, gap-3=12px, gap-4=16px, gap-5=20px
- text-xs=12px≈9pt, text-sm=14px≈10pt, text-base=16px≈12pt
- text-lg=18px≈14pt, text-xl=20px≈15pt, text-2xl=24px≈18pt
- text-3xl=30px≈22pt, text-4xl=36px≈27pt, text-5xl=48px≈36pt
- w-10=40px=0.556", w-12=48px=0.667", w-14=56px=0.778"
- rounded-lg=8px=0.11", rounded-xl=12px=0.17", rounded-2xl=16px=0.22"
- 전체 뷰포트: 960px = 13.333인치 (1px ≈ 0.01389인치)
- max-w-[800px] = 800 × 0.01389 ≈ 11.11인치
</coordinate_system>

<output_format>
## 출력 JSON 형식
```json
{
  "elements": [
    {
      "type": "shape",
      "shape": "roundRect",
      "x": 0.7, "y": 1.8, "w": 5.5, "h": 2.0,
      "fill": "FFFFFF",
      "border": "E2E8F0",
      "borderWidth": 0.5,
      "radius": 0.22,
      "shadow": true
    },
    {
      "type": "text",
      "text": "실제 텍스트 값",
      "x": 0.7, "y": 0.4, "w": 11.9, "h": 0.7,
      "fontSize": 22,
      "bold": true,
      "italic": false,
      "color": "1A202C",
      "align": "left",
      "valign": "middle",
      "lineSpacing": 1.3
    },
    {
      "type": "shape",
      "shape": "ellipse",
      "x": 1.0, "y": 2.0, "w": 0.55, "h": 0.55,
      "fill": "6366F1"
    },
    {
      "type": "text",
      "text": "🎯",
      "x": 1.0, "y": 2.0, "w": 0.55, "h": 0.55,
      "fontSize": 14,
      "align": "center",
      "valign": "middle",
      "color": "FFFFFF"
    },
    {
      "type": "chart",
      "chartType": "bar",
      "x": 2.0, "y": 2.0, "w": 9.0, "h": 4.0,
      "data": [{"name": "Series", "labels": ["A","B"], "values": [10,20]}],
      "colors": ["6366F1", "818CF8"]
    }
  ]
}
```

## element 타입
1. **shape**: 도형 (rect, roundRect, ellipse, line)
   - fill: 색상 hex (# 없음)
   - border: 테두리 색상 (선택)
   - borderWidth: 테두리 두께 (선택, 기본 0.5)
   - radius: roundRect 코너 반경 인치 (선택)
   - shadow: true면 카드 그림자 (선택)
2. **text**: 텍스트 박스
   - text: 실제 텍스트 값 (content에서 읽어 삽입)
   - fontSize: pt 단위
   - bold, italic: boolean
   - color: hex (# 없음)
   - align: left/center/right
   - valign: top/middle/bottom
   - lineSpacing: 줄간격 배수 (선택)
3. **chart**: 차트 (recharts → PptxGenJS 차트)
   - chartType: bar/pie/line/doughnut
   - data: [{name, labels, values}]
   - colors: 색상 배열
</output_format>

<rules>
## 변환 규칙
1. React 코드의 각 JSX 요소를 순서대로 PptxGenJS element로 변환
2. Tailwind 클래스를 인치 단위 좌표와 스타일로 매핑
3. className의 색상 클래스 → hex 값 (bg-primary → THEME primary hex)
4. flex/grid 레이아웃은 절대좌표로 계산
   - grid-cols-2 gap-5 + padding → 각 카드의 x, y, w, h 계산
5. 텍스트는 content 데이터의 실제 값을 삽입 (하드코딩)
6. map() 반복문은 배열 데이터 수만큼 요소 반복 생성
7. 모든 좌표는 슬라이드 범위 안에 있어야 함 (x+w ≤ 13.333, y+h ≤ 7.5)
8. 색상은 항상 # 없는 6자리 hex
9. recharts 차트는 chart element로 변환 (Bar→bar, Pie→pie, Line→line)

## 주의사항
- JSON만 출력. 설명이나 마크다운 금지
- 코드 블록(```)으로 감싸는 것은 허용
- THEME 참조 → 제공된 테마 색상의 실제 hex 값으로 치환
</rules>"""


def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response."""
    text = text.strip()

    # Try to extract from code fence
    fence = re.search(r"```(?:json)?\s*\n([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    # Try to parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
    return None


def _validate_layout(layout: dict) -> bool:
    """Validate that layout JSON has correct structure and coordinates."""
    elements = layout.get("elements")
    if not isinstance(elements, list) or len(elements) == 0:
        return False

    for el in elements:
        if not isinstance(el, dict):
            return False
        el_type = el.get("type")
        if el_type not in ("shape", "text", "chart"):
            return False
        # Check coordinates are within slide bounds
        x = el.get("x", 0)
        y = el.get("y", 0)
        w = el.get("w", 0)
        h = el.get("h", 0)
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            return False
        if x + w > 14 or y + h > 8:  # slight tolerance
            return False

    return True


async def _generate_slide_layout(
    llm,
    slide_id: str,
    slide_type: str,
    react_code: str,
    content: dict,
    style: dict,
) -> dict | None:
    """Generate PptxGenJS layout JSON for one slide."""
    content_json = json.dumps(content, ensure_ascii=False, indent=2)

    primary = style.get("primary_color", "#6366F1").replace("#", "")
    accent = style.get("accent_color", "#818CF8").replace("#", "")
    background = style.get("background", "#F5F7FA").replace("#", "")
    text_color = style.get("text_color", "#1A202C").replace("#", "")

    prompt = f"""[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}

[테마 색상 (# 없는 hex)]
primary: {primary}
accent: {accent}
background: {background}
heading: {text_color}
body: 64748B
card: FFFFFF
cardBorder: E2E8F0
red: E53E3E
yellow: F59E0B
green: 38A169

[React + Tailwind 코드 — 이 코드를 PptxGenJS JSON으로 변환하세요]
```jsx
{react_code}
```

[콘텐츠 데이터 — text element의 실제 값으로 사용]
```json
{content_json}
```

위 React 코드의 레이아웃을 동일하게 재현하는 PptxGenJS JSON을 생성하세요.
각 JSX 요소를 순서대로 shape/text/chart element로 변환하세요.
텍스트는 콘텐츠 데이터의 실제 값을 넣으세요."""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    layout = _extract_json(response.content)
    if layout and _validate_layout(layout):
        logger.info("[PptxLayout] %s (%s) - %d elements", slide_id, slide_type, len(layout["elements"]))
        return layout
    else:
        logger.warning("[PptxLayout] %s (%s) - invalid JSON, skipping", slide_id, slide_type)
        return None


async def pptx_layout_generator(state: PPTState) -> dict:
    """Generate PptxGenJS layout JSON for all slides.

    Transpiles React + Tailwind code → PptxGenJS element JSON.
    Runs in parallel with the validation chain.
    """
    llm = get_llm()
    style = state.get("research_brief", {}).get("style", {})

    # Build maps
    contents_map = {c["slide_id"]: c for c in state.get("slide_contents", [])}

    # Get individual slide codes from generated_slides
    generated_slides = state.get("generated_slides", [])
    # Deduplicate (keep latest)
    seen = {}
    for slide in generated_slides:
        seen[slide["slide_id"]] = slide
    generated_slides = sorted(seen.values(), key=lambda s: s["slide_id"])

    tasks = []
    for slide in generated_slides:
        sid = slide["slide_id"]
        slide_type = slide.get("type", "unknown")
        react_code = slide.get("code", "")
        content = contents_map.get(sid, {}).get("content", {})

        tasks.append(
            _generate_slide_layout(llm, sid, slide_type, react_code, content, style)
        )

    results = await asyncio.gather(*tasks)

    layouts = []
    for slide, layout in zip(generated_slides, results):
        layouts.append({
            "slide_id": slide["slide_id"],
            "type": slide.get("type", "unknown"),
            "layout": layout,  # None if failed
        })

    success = sum(1 for l in layouts if l["layout"] is not None)
    logger.info("[PptxLayout] Done: %d/%d slides converted", success, len(layouts))

    return {"pptx_layouts": layouts}
