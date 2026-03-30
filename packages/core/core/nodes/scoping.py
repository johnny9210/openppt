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
            "infographic_prompt": "시각화가 필요한 슬라이드만 작성, 불필요하면 null",
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
- 마지막 슬라이드 → closing

## infographic_prompt 작성 가이드 (선택)
데이터 시각화나 개념 다이어그램이 효과적인 슬라이드에만 작성합니다.
design_prompt와는 완전히 다릅니다:
- design_prompt = 슬라이드 배경 이미지 (텍스트 없음, 장식용)
- infographic_prompt = 데이터/개념을 설명하는 독립 인포그래픽 이미지 (텍스트/수치 포함)

적합한 슬라이드 타입: data_visualization, comparison, process_flow, timeline, key_points, risk_analysis, action_plan
부적합 (infographic_prompt를 null로): cover, closing, table_of_contents, hero, quote, summary
전체 슬라이드의 30-50%만 인포그래픽 적용 (모든 슬라이드에 넣지 마세요)

### 프롬프트 필수 구조 (5개 섹션 모두 포함할 것)
infographic_prompt는 반드시 아래 5개 섹션을 영어로 작성하세요:

**## Infographic Type & Title**
인포그래픽 유형과 제목을 한 줄로 명시합니다.
유형 옵션: KPI Dashboard, Bar/Line/Pie Chart, Timeline Roadmap, Process Flow,
Comparison (Split-Screen), Funnel, Pyramid, Mind Map, Venn Diagram, Icon Grid,
Circular Cycle, Checklist, Storyboard

**## Layout**
구체적 배치 구조를 지정합니다:
- 전체 영역 분할 (예: "Header 15%, Main 70%, Footer 15%")
- 카드/항목 배치 (예: "2×2 grid of metric cards", "5-column horizontal pipeline")
- 항목 수에 맞는 레이아웃 (2개→좌우 split, 3개→1×3, 4개→2×2, 5+→vertical stack)
- 연결 요소 (화살표, 커넥터 라인, 그라디언트 전환)

**## Data & Content**
시각화할 데이터를 항목별로 구체적으로 나열합니다:
- 각 항목: "항목명: 수치/값 (아이콘, 색상 힌트)" 형식
- 전체 텍스트 400단어 이하 (텍스트 렌더링 정확도 보장)
- 구체적 수치가 없으면 예상 범위라도 기재 (웹 리서치 후 실데이터로 보강됨)

**## Visual Style**
일러스트레이션 스타일을 구체적으로 지정합니다.
스타일 옵션: Clean Corporate Minimalist, Flat 2.0 Vector, Bold Editorial,
Dark Mode Tech, Soft Pastel Educational, Hand-Drawn Sketchnote
- 카드 컨테이너 디자인 (rounded corners, subtle shadows, border)
- 아이콘 스타일 (line icons, filled badges, emoji)
- 배경 처리 (white, light gray, subtle gradient)

**## Output Spec**
"Aspect ratio: 16:9. Include data labels and numbers on all visual elements.
Keep total text under 400 words. Generate this infographic now."

### 예시 (KPI 대시보드):
```
## Infographic Type & Title
Corporate KPI Dashboard — "Q4 2025 Revenue Performance"

## Layout
- Header: Full-width title bar with accent color underline (top 12%)
- Main area: 2×2 grid of metric cards with equal spacing (70%)
  - Each card: Rounded rectangle, subtle shadow, icon badge top-left
  - Bottom of each card: Mini sparkline or trend indicator
- Footer: Full-width single-row trend line chart (18%)

## Data & Content
- Card 1: "Total Revenue $5.2M" (+20% YoY) — dollar icon, green trend arrow
- Card 2: "New Customers 1,500" (+35%) — people icon, blue badge
- Card 3: "Churn Rate 2.1%" (-0.5pp) — shield icon, green (positive)
- Card 4: "NPS Score 72" (+8pts) — star icon, gold badge
- Trend chart: Monthly revenue line Jan–Dec, highlight Q4 growth zone

## Visual Style
Clean Corporate Minimalist. Navy primary, gold accents.
Rounded card containers (16px radius), subtle drop shadows.
Sans-serif bold typography for numbers, regular for labels.
White background, no decorative patterns.

## Output Spec
Aspect ratio: 16:9. Include data labels and numbers on all visual elements.
Keep total text under 400 words. Generate this infographic now.
```

### 예시 (프로세스 플로우):
```
## Infographic Type & Title
Process Flow — "SaaS Customer Journey: Awareness to Advocacy"

## Layout
- 5-column horizontal pipeline, each stage as a rounded-rectangle card
- Connecting gradient arrows between stages
- Top: Stage title and icon badge
- Middle: 2-3 bullet points per stage
- Bottom row: Key metric per stage

## Data & Content
- Stage 1: "Awareness" — eye icon, soft blue — "Content Marketing, SEO" — 10K visitors/mo
- Stage 2: "Consideration" — magnifying glass, teal — "Free Trial, Webinars" — 15% conversion
- Stage 3: "Decision" — checkmark, green — "Demo, Case Studies" — 8% close rate
- Stage 4: "Onboarding" — rocket, orange — "Setup Wizard, Training" — 3-day avg activation
- Stage 5: "Advocacy" — heart, pink — "Referral Program, Reviews" — 40% referral rate

## Visual Style
Flat 2.0 Vector with gradient overlays between stages.
Each stage card: white background, colored top border matching stage color.
Circular icon badges (48px) with white icons on colored background.
Light gray overall background, clean sans-serif typography.

## Output Spec
Aspect ratio: 16:9. Include data labels and numbers on all visual elements.
Keep total text under 400 words. Generate this infographic now.
```"""


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
