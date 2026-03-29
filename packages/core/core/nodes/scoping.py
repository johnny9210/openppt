"""
Phase 1: Scoping (deep_research pattern)
Analyzes user request and generates structured research brief with slide plan.
"""

import asyncio
import logging

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.runnables import RunnableConfig

from core.config import get_llm, LLM_TIMEOUT
from core.state import PPTState
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)

# ── Color Palettes (deterministic mapping — LLM picks keyword, code picks colors) ──

COLOR_PALETTES = {
    "tech": {
        "primary_color": "#2563EB",
        "accent_color": "#38BDF8",
        "background": "#EFF6FF",
    },
    "education": {
        "primary_color": "#059669",
        "accent_color": "#2DD4BF",
        "background": "#ECFDF5",
    },
    "business": {
        "primary_color": "#1E40AF",
        "accent_color": "#D97706",
        "background": "#EFF6FF",
    },
    "marketing": {
        "primary_color": "#DC2626",
        "accent_color": "#F97316",
        "background": "#FEF2F2",
    },
    "creative": {
        "primary_color": "#EA580C",
        "accent_color": "#F59E0B",
        "background": "#FFF7ED",
    },
    "lifestyle": {
        "primary_color": "#E11D48",
        "accent_color": "#F472B6",
        "background": "#FFF1F2",
    },
    "minimal": {
        "primary_color": "#475569",
        "accent_color": "#94A3B8",
        "background": "#F8FAFC",
    },
    "entertainment": {
        "primary_color": "#7C3AED",
        "accent_color": "#D946EF",
        "background": "#F5F3FF",
    },
    "medical": {
        "primary_color": "#0891B2",
        "accent_color": "#34D399",
        "background": "#ECFEFF",
    },
    "environment": {
        "primary_color": "#16A34A",
        "accent_color": "#84CC16",
        "background": "#F0FDF4",
    },
}

DEFAULT_COLOR_THEME = "minimal"

SCOPING_PROMPT = """당신은 프레젠테이션 기획 전문가입니다. 사용자의 요청을 깊이 분석하여 체계적인 프레젠테이션 기획서(Research Brief)를 작성합니다.

## 분석 절차
1. 사용자 요청의 핵심 주제와 목적을 파악합니다
2. 적절한 대상 청중을 추정합니다
3. 효과적인 슬라이드 구성을 설계합니다
4. 각 슬라이드의 콘텐츠 방향과 디자인 방향을 정합니다

## 사용 가능한 슬라이드 타입
- cover: 표지 슬라이드 (제목, 부제, 발표자/날짜)
- table_of_contents: 목차 슬라이드
- hero: 핵심 메시지 하나를 크게 강조하는 슬라이드 (짧은 한 문장 중심)
- quote: 인용구/명언/핵심 문구를 큰 따옴표와 함께 강조
- icon_grid: 5~6개 항목을 아이콘+라벨로 격자 배치 (2x3, 3x2 등)
- key_points: 2~4개 핵심 포인트를 카드로 배치
- three_column: 3개 항목을 세로 카드 3열로 배치
- comparison: 두 가지를 좌우 대비 (Before/After, 문제/해결 등)
- process_flow: 단계별 흐름을 화살표로 연결 (3~5단계)
- timeline: 시간순 흐름을 타임라인으로 표현
- data_visualization: 데이터/차트 슬라이드 (recharts 사용)
- risk_analysis: 리스크 분석 슬라이드
- action_plan: 실행 계획/로드맵 슬라이드
- summary: 핵심 내용 정리/요약 (번호 매긴 3줄 요약)
- closing: 마무리 슬라이드 (자료 안내, 감사, CTA, QR 등)

## design_prompt 작성 가이드
각 슬라이드의 design_prompt는 이미지 생성 AI에 전달되어 슬라이드 배경 이미지를 만듭니다.
이 이미지 위에 코드로 텍스트를 오버레이하므로, 이미지 자체에는 텍스트를 포함하지 않습니다.

작성 규칙:
1. "## Image Type": 슬라이드 성격 한 줄 (예: "Professional cover slide — visual structure only")
2. "## Layout": 구체적 배치 구조 (영역 비율, 카드 수와 배치, 방향)
   - 항목 수에 맞게 레이아웃 결정 (2개→좌우 분할, 3개→1×3 가로, 4개→2×2 그리드, 5+→수직 스택 등)
   - 모든 텍스트 영역은 "blank zone for overlay"로 표시
3. "## Visual Theme": 주제에 맞는 시각 요소
   - 주제 연관 아이콘/일러스트 (AI→회로/뉴럴넷, 마케팅→타겟/차트, 교육→책/연필 등)
   - 배경 장식 패턴 (주제에 맞는 미묘한 패턴, opacity 5-10%)
4. 영어로 작성 (이미지 생성 AI가 영어 프롬프트에 최적화)
5. "Generate this ... visual structure (NO TEXT) now." 로 끝낼 것

예시 (AI 기술 주제의 key_points 3개):
```
## Image Type
Professional key points slide — visual structure only (no text).

## Layout
- Top 20%: Clean blank zone for title + description overlay, accent bar
- Below: 1×3 HORIZONTAL card row with 20px gaps
  - Each card: White rounded rectangle (border-radius 16px), subtle shadow
  - Top of card: Circular icon badge (56px) with theme icon
  - Below icon: Blank area for title + description text overlay
- Cards equal width, symmetric spacing

## Visual Theme
- Icon badges: neural network node, brain circuit, robot head
- Background: Subtle circuit board trace pattern at 5% opacity
- Accent: Tech-blue connecting lines between cards suggesting data flow

Generate this key points visual structure (NO TEXT) now.
```

## 색상 테마 선택 (중요!)
프레젠테이션 주제에 가장 어울리는 color_theme을 선택하세요:
- tech: 기술, IT, AI, 소프트웨어, 데이터, 자동화
- education: 교육, 학습, 성장, 강의, 워크숍, 세미나
- business: 비즈니스, 금융, 경영, 컨설팅, 투자
- marketing: 마케팅, 광고, 브랜딩, 홍보, PR, 세일즈
- creative: 디자인, 예술, 창작, 콘텐츠 제작
- lifestyle: 뷰티, 패션, 라이프스타일, 푸드, 여행
- minimal: 미니멀, 모던, 일반 발표, 보고서
- entertainment: 엔터테인먼트, 게임, 미디어, 음악, 영상
- medical: 의료, 건강, 웰니스, 헬스케어, 제약
- environment: 환경, 지속가능성, ESG, 에너지, 농업

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요:

```json
{
    "purpose": "프레젠테이션의 목적 (한 문장)",
    "audience": "대상 청중",
    "key_message": "전달하려는 핵심 메시지",
    "style": {
        "mood": "professional | creative | minimal | bold 중 택 1",
        "color_theme": "tech | education | business | marketing | creative | lifestyle | minimal | entertainment | medical | environment 중 택 1"
    },
    "slide_plan": [
        {
            "slide_id": "slide_001",
            "type": "cover",
            "topic": "슬라이드 주제",
            "key_points": ["핵심 포인트1", "핵심 포인트2"],
            "design_prompt": "## Image Type\n...\n## Layout\n...\n## Visual Theme\n...\nGenerate this ... visual structure (NO TEXT) now.",
            "data": null
        }
    ]
}
```

## 슬라이드 구성 원칙
- 사용자가 슬라이드 구성을 직접 명시한 경우 (예: "슬라이드 1", "슬라이드 2" 등) 그 수와 순서를 그대로 따릅니다
- 사용자가 슬라이드 수를 명시하지 않은 경우 최소 4장, 최대 8장으로 구성합니다
- 최대 30장까지 허용됩니다
- 첫 슬라이드는 반드시 cover
- 두 번째 슬라이드는 table_of_contents 권장 (사용자가 별도 구성을 명시하지 않은 경우)
- data_visualization은 차트 데이터가 있을 때만
- 각 슬라이드의 key_points는 2-5개
- design_prompt는 위 가이드에 따라 영어로 구체적으로 작성 (Image Type + Layout + Visual Theme)
- data 필드는 차트/그래프에 사용할 구체적 데이터 (없으면 null)
- color_theme은 프레젠테이션 주제에 가장 어울리는 것을 선택하세요

## 슬라이드 타입 선택 가이드 (중요!)
연속으로 같은 타입을 사용하지 마세요. 슬라이드마다 콘텐츠 특성에 맞는 타입을 선택하세요:
- 핵심 메시지 하나 → hero 또는 quote
- 항목 5~6개 나열 → icon_grid
- 항목 2~4개 설명 → key_points
- 항목 정확히 3개 → three_column
- 대비/비교 → comparison
- 단계별 흐름 → process_flow
- 시간 순서 → timeline
- 내용 정리 → summary
- 마지막 슬라이드 → closing"""


async def scoping(state: PPTState, config: RunnableConfig) -> dict:
    """Analyze user request and generate structured research brief."""
    cancel_event = (config.get("configurable") or {}).get("cancel_event")
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

    llm = get_llm()

    input_tokens = 0
    output_tokens = 0

    with get_usage_metadata_callback() as cb:
        response = await asyncio.wait_for(
            llm.ainvoke([
                {"role": "system", "content": SCOPING_PROMPT},
                {"role": "user", "content": state["user_request"]},
            ]),
            timeout=LLM_TIMEOUT,
        )
        if cb.usage_metadata:
            for _, usage in cb.usage_metadata.items():
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)

    try:
        brief = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("scoping: %s", exc)
        raise ValueError(
            f"Scoping could not parse research brief: {exc}"
        ) from exc

    # ── Apply color palette from theme keyword ──
    style = brief.get("style", {})
    color_theme = style.get("color_theme", DEFAULT_COLOR_THEME)
    palette = COLOR_PALETTES.get(color_theme, COLOR_PALETTES[DEFAULT_COLOR_THEME])
    style["primary_color"] = palette["primary_color"]
    style["accent_color"] = palette["accent_color"]
    style["background"] = palette["background"]
    style["text_color"] = "#1A202C"
    brief["style"] = style
    logger.info("[Scoping] color_theme=%s → primary=%s", color_theme, palette["primary_color"])

    logger.info("[Scoping] tokens: in=%d out=%d", input_tokens, output_tokens)

    return {
        "research_brief": brief,
        "token_usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
