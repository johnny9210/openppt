"""
Phase 3: Code Synthesizer (3-Pass Architecture) — HTML Edition
Pass 1 (Vision): Design image → HTML+CSS layout (structure only, no text)
Pass 2 (Code):   Layout HTML + text content → Final HTML with text
Pass 3 (Code):   Fit to 1280×720 container and adjust CSS

Each slide outputs a scoped HTML snippet:
  <style>.slide_NNN { ... }</style>
  <div class="slide-container slide_NNN"> ... </div>
"""

import asyncio
import json
import logging
import os
import re

from langchain_core.messages import SystemMessage, HumanMessage

from core.config import get_llm
from core.state import PPTState

logger = logging.getLogger(__name__)

# Limit concurrent LLM calls to avoid Bedrock throttling.
# Each slide makes 3 sequential LLM calls (pass1→pass2→pass3),
# so MAX_CONCURRENT_SLIDES=3 means up to 3 LLM calls at any moment.
MAX_CONCURRENT_SLIDES = int(os.getenv("MAX_CONCURRENT_SLIDES", "3"))
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_SLIDES)
    return _semaphore


# ── Pass 1: Layout Generation (Vision → HTML+CSS) ─────────────────

LAYOUT_SYSTEM_PROMPT = """당신은 디자인 이미지를 HTML + CSS 코드로 변환하는 전문 개발자입니다.

★ 핵심 임무: 디자인 이미지의 시각적 구조를 HTML + CSS로 정확히 재현합니다.
텍스트 콘텐츠는 렌더링하지 않습니다 — 텍스트가 들어갈 구조만 잡아둡니다.

<output_rules>
★ 최우선 규칙: <style>과 <div>로 구성된 순수 HTML 코드만 출력하세요.
코드 외의 모든 텍스트(설명, 마크다운, 사고 과정)를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<output_format>
## ★ 반드시 이 형식으로 출력

<style>
  .slide_NNN { /* 컨테이너 기본 스타일 */ }
  .slide_NNN .내부요소 { /* 내부 요소 스타일 */ }
</style>
<div class="slide-container slide_NNN">
  <!-- 슬라이드 콘텐츠 구조 -->
</div>

★ 모든 CSS 선택자는 반드시 해당 슬라이드의 클래스(.slide_001 등)로 시작 (스타일 충돌 방지)
★ slide_NNN 부분은 유저 프롬프트에서 제공하는 실제 slide_id로 교체하세요
</output_format>

<styling_rules>
## 스타일링 규칙

### CSS 작성 원칙
- 모든 커스텀 스타일은 <style> 블록에 작성
- 모든 선택자는 해당 슬라이드 클래스로 스코핑 (예: .slide_001 .card { ... })
- 인라인 style 속성은 최소화

### 슬라이드 컨테이너 기본 (반드시 포함)
.slide_NNN {
  width: 1280px;
  height: 720px;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  position: relative;
  overflow: hidden;
  font-family: 'Noto Sans KR', sans-serif;
}

### Tailwind 유틸리티 클래스 (HTML class 속성에서 사용 가능)
- 레이아웃: flex, grid, gap-*, items-center, justify-center
- 간격: p-*, m-*, px-*, py-*, mb-*, mt-*
- 텍스트: text-xs ~ text-5xl, font-light ~ font-black, leading-*
- 색상: text-white, text-gray-*, bg-white, bg-gray-*
- 둥근 모서리: rounded, rounded-lg, rounded-xl, rounded-2xl, rounded-full
- 그림자: shadow-sm, shadow-md, shadow-lg, shadow-xl
- 테두리: border, border-gray-200

### 사용 가능한 커스텀 Tailwind 색상 (tailwind.config에 정의됨)
- bg-primary, text-primary, border-primary: 주 브랜드 색상
- bg-accent, text-accent, border-accent: 보조 색상
- text-heading: 제목 텍스트
- text-body: 본문 텍스트 (#64748B)
- bg-card, border-card-border: 카드 스타일
- bg-slide-bg: 슬라이드 배경색

### 디자인 패턴
- 카드: bg-white, border-radius 16px, box-shadow 0 2px 8px rgba(0,0,0,0.06), border 1px solid #E2E8F0
- 아이콘 배지: 56px 원형, 브랜드 색상 배경, 중앙 정렬, text-white
- 장식 원: position absolute, border-radius 50%, 반투명 배경색, z-index 0
- 하단 바: height 8-12px, 전체 너비, 브랜드 색상
- 액센트 라인: width 48px, height 4px, 브랜드 색상, border-radius
- FontAwesome 아이콘: <i class="fas fa-icon-name"></i>
</styling_rules>

<task>
## 재현할 요소
1. **레이아웃**: flex/grid 배치, 간격, 패딩 — 이미지와 최대한 동일
2. **카드**: 배경, 둥근 모서리, 그림자, 테두리
3. **아이콘/배지**: 원형 배지 구조 (내용은 비워둠)
4. **장식**: 배경 원, 그라디언트, 구분선, 하단 컬러 바
5. **색상**: 테마 컬러 적용

## 텍스트 처리 규칙
- 텍스트가 들어갈 자리에 적절한 높이/여백의 빈 영역만 만드세요
- 배열 데이터는 요소 개수만큼 반복 구조를 만드세요 (텍스트는 비움)
- 아이콘 배지 안에 콘텐츠를 넣지 마세요 (Pass 2에서 삽입)
</task>

<constraints>
- <style> + <div> 형식만 출력
- 모든 CSS 선택자는 슬라이드 클래스(.slide_NNN)로 시작
- class="slide-container slide_NNN" 최상위 컨테이너 필수
- JavaScript 사용 금지
- <img> 태그 사용 금지
- 텍스트 콘텐츠 직접 삽입 금지
- 외부 이미지 URL 참조 금지
</constraints>"""


# ── Pass 2: Text Insertion ─────────────────────────────────────────

TEXT_INSERT_SYSTEM_PROMPT = """당신은 HTML 슬라이드에 텍스트 콘텐츠를 삽입하는 전문 개발자입니다.

★ 핵심 임무: 주어진 HTML 레이아웃의 빈 영역에 텍스트 콘텐츠를 삽입하고 스타일을 미세 조정합니다.

<output_rules>
★ 최우선 규칙: <style>과 <div>로 구성된 순수 HTML 코드만 출력하세요.
코드 외의 모든 텍스트를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<task>
## 해야 할 것
1. **레이아웃 유지**: 기존 CSS, 카드 배치, 색상 그대로 유지
2. **텍스트 삽입**: 빈 영역에 콘텐츠 데이터의 실제 텍스트 값을 삽입
3. **아이콘/이모지**: 빈 아이콘 배지에 실제 이모지 또는 FontAwesome 아이콘 삽입
   - FontAwesome: <i class="fas fa-icon-name"></i>
   - 이모지: 유니코드 이모지 직접 사용
4. **가독성**: 배경 대비 텍스트 가독성 보장
5. **반복 요소**: 배열 데이터 수만큼 카드/항목 유지, 각각에 해당 텍스트 삽입

## 텍스트 스타일 가이드
- 메인 제목: font-size 2.5~3.5rem, font-weight 800-900, color 진한 색상
- 부제목/설명: font-size 1~1.2rem, font-weight 400-500, color #64748B 계열
- 카드 제목: font-size 1~1.1rem, font-weight 600-700, color 진한 색상
- 카드 설명: font-size 0.8~0.9rem, color #64748B, line-height 1.6
- 강조 수치: font-size 1.2~1.5rem, font-weight 700, 브랜드 색상
- 태그/라벨: font-size 0.75rem, font-weight 600, 브랜드 색상 배경 + padding + border-radius
</task>

<data_visualization>
## 데이터 시각화 (data_visualization 타입인 경우)
차트 데이터가 제공되면 인라인 SVG로 시각화하세요:
- 바 차트: <svg> 안에 <rect> 요소 배치, 높이로 값 표현
- 파이 차트: <svg> 안에 <circle> + stroke-dasharray 또는 <path>
- 라인 차트: <svg> 안에 <polyline> 또는 <path>
- 범례, 축 라벨 포함
- 브랜드 색상 사용
</data_visualization>

<do_not>
## 하지 말 것
- 레이아웃 구조 변경 (카드 수, 그리드 컬럼 수, 전체 패딩)
- 새로운 시각 요소 추가 (카드, 아이콘 배지 등 추가 금지)
- 기존 CSS 클래스/속성 대폭 변경
- CSS 선택자 스코핑 변경
- JavaScript 추가
</do_not>"""


# ── Pass 3: Layout Fitting ─────────────────────────────────────────

FITTING_SYSTEM_PROMPT = """당신은 HTML 슬라이드의 레이아웃을 1280×720px 컨테이너에 맞추는 전문가입니다.

★ 핵심 임무: 모든 콘텐츠가 1280×720px 안에 넘치지 않고 들어가도록 CSS를 조정합니다.

<output_rules>
★ 최우선 규칙: <style>과 <div>로 구성된 순수 HTML 코드만 출력하세요.
코드 외의 모든 텍스트를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다.
</output_rules>

<analysis>
## 분석 절차
1. 컨테이너 padding 확인 → 내부 가용 영역 계산
2. 제목 + 설명 영역의 높이 추정
3. 본문 콘텐츠 높이 추정 (그리드 행 × 카드 높이 + gap)
4. 전체 높이 합산 → 720px 초과 여부 판단
</analysis>

<adjustments>
## 넘칠 때 조정 우선순위
1. **패딩 축소**: 48px → 32px → 24px
2. **gap 축소**: 20px → 12px → 8px
3. **카드 내부 패딩 축소**: 24px → 16px → 12px
4. **폰트 크기 축소**: 한 단계씩 줄이기
5. **아이콘/배지 축소**: 56px → 40px → 36px
6. **여백 축소**: margin-bottom 32px → 16px → 12px
7. **그리드 재배치**: 2열 → 3열 (항목 5~6개인 경우)
</adjustments>

<rules>
- 디자인의 시각적 정체성(색상, 카드 스타일, 구조)은 유지
- 콘텐츠를 삭제하거나 숨기지 마세요 — CSS만 조정
- 이미 1280×720에 충분히 들어가면 수정하지 말고 그대로 출력
- CSS 선택자 스코핑 유지
</rules>"""


# ── HTML extraction helper ───────────────────────────────────────

def _extract_html(text: str) -> str:
    """Extract HTML from LLM response, removing markdown fences and preamble."""
    text = text.strip()

    # Extract from code fence
    fence = re.search(r"```(?:html)?\s*\n([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    else:
        # Remove any markdown fences at boundaries
        text = re.sub(r"^```(?:html)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    # Strip any preamble text before the first HTML tag
    html_start = re.search(r"<(?:style|div|section|!DOCTYPE|!--)", text, re.IGNORECASE)
    if html_start and html_start.start() > 0:
        text = text[html_start.start():]

    return text.strip()


# ── Pass 1: Layout Generation ────────────────────────────────────

async def _generate_layout(
    llm,
    slide_id: str,
    slide_type: str,
    image_b64: str | None,
    content: dict,
    style: dict,
) -> str:
    """Pass 1: Generate HTML+CSS layout from design image (structure only, no text)."""
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

[테마 컬러]
primary: {style.get('primary_color', '#6366F1')}
accent: {style.get('accent_color', '#818CF8')}
background: {style.get('background', '#F5F7FA')}
text: {style.get('text_color', '#1A202C')}

[콘텐츠 구조 (반복 횟수 및 필드 참고용 — 텍스트 렌더링 금지)]
{structure_hint}

{"[디자인 이미지 첨부됨]" if has_image else "[이미지 없음]"}
{"이 이미지의 시각적 구조(카드 배치, 아이콘, 색상, 간격, 장식)를 HTML + CSS로 정확히 재현하세요." if has_image else f"'{slide_type}' 타입에 적합한 깔끔하고 전문적인 레이아웃을 HTML + CSS로 설계하세요."}
텍스트는 넣지 마세요 — 레이아웃 구조만 코드로 만드세요.

★ CSS 선택자는 .{slide_id} 로 스코핑하세요.
★ 컨테이너: <div class="slide-container {slide_id}">"""

    user_parts.append({"type": "text", "text": prompt})

    response = await llm.ainvoke([
        SystemMessage(content=LAYOUT_SYSTEM_PROMPT),
        HumanMessage(content=user_parts),
    ])

    layout_code = _extract_html(response.content)
    logger.info("[Synth:Pass1] %s (%s) - layout: %d chars", slide_id, slide_type, len(layout_code))
    return layout_code


# ── Pass 2: Text Insertion ────────────────────────────────────────

async def _insert_text(
    llm,
    layout_code: str,
    slide_id: str,
    slide_type: str,
    content: dict,
    fix_prompt: str = "",
) -> str:
    """Pass 2: Insert text content into HTML layout. No vision needed."""
    content_json = json.dumps(content, ensure_ascii=False, indent=2)

    prompt = f"""[레이아웃 HTML — 구조를 유지하면서 텍스트를 삽입하세요]
```html
{layout_code}
```

[삽입할 콘텐츠 데이터]
{content_json}

[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}

위 HTML 레이아웃의 빈 영역에 콘텐츠 데이터의 실제 텍스트를 삽입하세요.
레이아웃 구조(CSS, 카드 배치, 색상)는 그대로 유지하고 텍스트와 아이콘만 추가하세요."""

    if fix_prompt:
        prompt += f"""

[이전 검증 피드백 — 반드시 반영]
{fix_prompt}"""

    response = await llm.ainvoke([
        SystemMessage(content=TEXT_INSERT_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    final_code = _extract_html(response.content)
    logger.info("[Synth:Pass2] %s (%s) - final: %d chars", slide_id, slide_type, len(final_code))
    return final_code


# ── Pass 3: Layout Fitting (1280×720 컨테이너 맞춤) ──────────────

async def _fit_layout(
    llm,
    code: str,
    slide_id: str,
    slide_type: str,
) -> str:
    """Pass 3: Check if HTML fits in 1280×720 container and adjust CSS if needed."""
    prompt = f"""[슬라이드 HTML — 1280×720px 컨테이너에 맞는지 확인하고 조정하세요]
```html
{code}
```

[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}

이 HTML의 모든 요소가 1280×720px 안에 들어가는지 분석하세요.
넘칠 가능성이 있으면 CSS(padding, gap, font-size 등)를 축소하여 맞추세요.
이미 충분히 들어가면 코드를 그대로 출력하세요."""

    response = await llm.ainvoke([
        SystemMessage(content=FITTING_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    fitted_code = _extract_html(response.content)
    logger.info("[Synth:Pass3] %s (%s) - fitted: %d chars", slide_id, slide_type, len(fitted_code))
    return fitted_code


# ── Slide synthesis (3-pass) ─────────────────────────────────────

async def _synthesize_slide(
    llm,
    slide_id: str,
    slide_type: str,
    image_b64: str | None,
    content: dict,
    style: dict,
    fix_prompt: str = "",
) -> dict:
    """Synthesize HTML code for one slide using 3-pass architecture.

    Pass 1 (Vision): Design image → HTML+CSS layout (structure only)
    Pass 2 (Code):   Layout HTML + content → Final HTML with text
    Pass 3 (Code):   Verify 1280×720 fit and adjust CSS if needed

    Uses a semaphore to limit concurrent LLM calls and avoid throttling.
    """
    async with _get_semaphore():
        # Pass 1: Generate layout from design image
        layout_code = await _generate_layout(
            llm, slide_id, slide_type, image_b64, content, style,
        )

        # Pass 2: Insert text content into layout
        text_code = await _insert_text(
            llm, layout_code, slide_id, slide_type, content, fix_prompt,
        )

        # Pass 3: Fit to 1280×720 container
        final_code = await _fit_layout(
            llm, text_code, slide_id, slide_type,
        )

    return {
        "slide_id": slide_id,
        "type": slide_type,
        "code": final_code,
    }


# ── Main entry point ─────────────────────────────────────────────

async def code_synthesizer(state: PPTState) -> dict:
    """Merge design images + text content → HTML code via 3-pass synthesis.

    Pass 1: Vision sees design image → generates HTML+CSS layout
    Pass 2: Reads layout HTML + content → inserts text precisely
    Pass 3: Fits to 1280×720 container

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

        tasks.append(
            _synthesize_slide(
                llm=llm,
                slide_id=sid,
                slide_type=slide_type,
                image_b64=design_data.get("image_b64"),
                content=content_data.get("content", {}),
                style=style,
                fix_prompt=fix_prompt,
            )
        )

    results = await asyncio.gather(*tasks)
    return {"generated_slides": list(results)}
