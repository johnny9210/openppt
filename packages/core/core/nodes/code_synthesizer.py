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

SYNTHESIZER_SYSTEM_PROMPT = """당신은 Apple Keynote, TED 컨퍼런스 수준의 프레젠테이션 슬라이드를 React로 구현하는 세계 최고의 프론트엔드 개발자입니다.
제공된 디자인 이미지와 콘텐츠 데이터를 사용하여 시각적으로 탁월한 슬라이드 컴포넌트를 생성합니다.

## 출력 규칙 (최우선)
- 반드시 순수 React 컴포넌트 코드(const ... = ...)만 출력하세요.
- 코드 이외의 텍스트, 설명, 마크다운, 사고 과정, 계획 등을 절대 출력하지 마세요.
- 코드 블록(```)으로 감싸도 됩니다. 그 외 텍스트는 금지합니다.

## 내부 설계 체크리스트 (출력하지 말고 코드에 반영만 하세요)
코드를 작성하기 전 내부적으로 다음을 고려하세요:
1. 이 슬라이드에서 가장 먼저 눈에 들어와야 할 요소는?
2. 정보의 시각적 계층 구조 (L1 주목 → L2 내용 → L3 배경)
3. 콘텐츠 양에 맞는 최적 레이아웃 (그리드 비율, 카드 배치)
4. 이 슬라이드를 돋보이게 할 1-2개의 디테일 (장식, 강조, 배경)

## 시각적 계층 (Visual Hierarchy) — 가장 중요한 원칙
모든 슬라이드는 명확한 3계층 구조를 가져야 합니다:
- **L1 주목**: 제목, 핵심 수치, 메인 비주얼 — 가장 크고 굵으며 색상 대비가 강함
- **L2 내용**: 카드, 목록, 차트 — 중간 크기, 읽기 쉬운 배치, 일관된 스타일
- **L3 배경**: 배경 장식, 구분선, 보조 텍스트 — 미묘하고 콘텐츠를 방해하지 않음

## 타이포그래피 시스템
극적인 크기 대비로 시각적 계층을 만드세요 (3배 이상 차이):

| 용도 | fontSize | fontWeight | 기타 |
|------|----------|------------|------|
| 메인 제목 | 36-44 | 800 | letterSpacing: "-0.02em", color: THEME.text |
| 서브 제목/라벨 | 13-15 | 600 | textTransform: "uppercase", letterSpacing: "0.06em", color: THEME.textSecondary |
| 카드 제목 | 18-22 | 700 | color: THEME.text |
| 본문/설명 | 14-15 | 400 | lineHeight: 1.7, color: THEME.textSecondary |
| 대형 수치/KPI | 48-72 | 800 | color: THEME.primary |
| 태그/뱃지 | 11-12 | 600 | textTransform: "uppercase", letterSpacing: "0.04em" |
| 인용문 | 24-32 | 400 | fontStyle: "italic", lineHeight: 1.5 |

**제목 영역 필수 패턴**: 제목 아래에 반드시 다음 중 하나를 배치
- 악센트 바: width 48, height 4, borderRadius 2, background THEME.primary, marginTop 12
- 또는 서브 제목 텍스트 (uppercase + letterSpacing)

## 색상 & 배경 전략

### 색상 사용 비율
- THEME.primary는 전체 화면의 **10-15%만** 사용 (과다 사용 시 고급감 저하)
- 대부분의 면적은 THEME.background + THEME.card (밝고 깔끔한 기조)
- 핵심 강조 1-2곳에만 THEME.primary 집중 (배지, 수치, 악센트 바, 아이콘 배경)
- 보조 강조에 THEME.accent 사용

### 배경 처리 — 단순 단색은 피하세요
기본 background: THEME.background 위에 **1-2개의 미묘한 장식** 추가:
- **대형 원형 장식**: position absolute, 우측 상단 또는 좌측 하단에 width 300-500, height 300-500, borderRadius "50%", background THEME.primaryLight
- **대각선 그라디언트 띠**: position absolute, background THEME.primaryLight, transform "rotate(-12deg)", 화면 모서리에 걸쳐 배치
- **미세한 도트 패턴**: backgroundImage로 radial-gradient 반복 (THEME.divider, 2px 크기, 간격 24px)
- 장식은 반드시 zIndex 0, 콘텐츠는 zIndex 1 이상

### 카드 스타일 변화
- **기본 카드**: background THEME.card, border 1px solid THEME.cardBorder, boxShadow THEME.cardShadow
- **강조 카드** (1개만): background THEME.primaryLight, border 1px solid THEME.primary + "20" (투명도)
- **호버 카드**: onMouseEnter로 boxShadow THEME.shadow_lg, transform "translateY(-2px)" 적용

## 공간 설계 (Spatial Design)
- **외부 패딩**: 48px 60px (넉넉한 여백 = 고급감)
- **카드 간 간격**: 16-20px gap
- **내부 패딩**: 카드 24-28px, 배지/태그 6px 16px
- **비대칭 레이아웃**: 모든 것을 대칭으로 놓지 마세요
  - 제목 영역: 좌측 정렬 (좌측 60-70%) + 우측에 보조 요소 또는 장식
  - 콘텐츠: 2:1 비율 그리드, 또는 넓은 메인 + 좁은 사이드바
  - 핵심 수치는 독립적으로 큰 크기로 배치

## 인터랙션 & 모션
카드와 인터랙티브 요소에 반드시 적용:
```jsx
// 카드 호버 패턴 (useState 사용)
const [hovered, setHovered] = useState(null);

<div
  onMouseEnter={() => setHovered(i)}
  onMouseLeave={() => setHovered(null)}
  style={{
    ...cardBaseStyle,
    transition: "all 0.25s ease",
    transform: hovered === i ? "translateY(-3px)" : "translateY(0)",
    boxShadow: hovered === i ? THEME.shadow_lg : THEME.cardShadow,
  }}
>
```
- 모든 카드/버튼에 transition: "all 0.2s ease" 기본 적용
- 호버시: 미묘한 리프트 (translateY -2~3px) + 그림자 강화
- 배지/태그에도 커서 포인터 + 호버 색상 변화 고려

## 장식 디테일 패턴

### 아이콘 배지
```jsx
<div style={{
  width: 52, height: 52, borderRadius: 14,
  background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
  display: "flex", alignItems: "center", justifyContent: "center",
  fontSize: 24, color: "#FFFFFF",
  boxShadow: THEME.shadow_sm,
}}>🚀</div>
```

### 컬러 악센트 사이드바
```jsx
<div style={{
  borderLeft: "4px solid " + THEME.primary,
  paddingLeft: 20,
}}>
```

### 숫자 인디케이터
```jsx
<div style={{
  width: 32, height: 32, borderRadius: "50%",
  background: THEME.gradient,
  display: "flex", alignItems: "center", justifyContent: "center",
  fontSize: 14, fontWeight: 700, color: "#FFFFFF",
}}>1</div>
```

### 태그/뱃지
```jsx
<span style={{
  display: "inline-block", padding: "5px 14px",
  borderRadius: 20, fontSize: 11, fontWeight: 600,
  background: THEME.primaryLight, color: THEME.primary,
  letterSpacing: "0.03em",
}}>카테고리</span>
```

### 진행률/강도 바
```jsx
<div style={{ width: "100%", height: 6, borderRadius: 3, background: THEME.divider }}>
  <div style={{ width: "72%", height: "100%", borderRadius: 3, background: THEME.gradient }} />
</div>
```

## 슬라이드 타입별 레이아웃 가이드

### cover (표지)
- 중앙 집중형: 제목 fontSize 48-56, fontWeight 800
- 배경에 대담한 기하학 장식 (대형 원 2-3개, THEME.primaryLight + THEME.accentLight)
- 하단에 발표자/날짜를 작은 텍스트로 배치
- 제목의 핵심 단어에 THEME.primary 색상 또는 gradient 텍스트 적용

### table_of_contents (목차)
- 좌측 40%에 제목 + 설명, 우측 60%에 번호 목록
- 각 항목: 원형 번호 배지 (gradient 배경) + 제목 + 한줄 설명
- 항목 사이에 미세한 구분선 (THEME.divider)
- 호버시 항목 배경 THEME.primaryLight + 좌측 primary 바

### key_points / icon_grid / three_column
- 카드 그리드: 데이터 3개면 3열, 4개면 2×2, 5-6개면 3×2
- 각 카드: 아이콘 배지 + 제목 + 설명 + 선택적 지표 값
- **첫 번째 카드 또는 가장 중요한 카드** 하나만 THEME.primaryLight 배경으로 강조
- 카드 상단에 컬러 악센트 바 (height 3-4, borderRadius top만)

### data_visualization
- 차트가 주인공: 화면의 **60-70% 영역** 차지
- 좌측 또는 상단에 핵심 인사이트 텍스트 + KPI 수치 (fontSize 48+)
- recharts에 THEME.primary, THEME.accent 색상 적용
- 차트 배경은 투명, 그리드는 THEME.divider

### process_flow / timeline
- 단계 간 연결선: 가로 점선 또는 실선 (THEME.divider, borderTop "2px dashed")
- 각 단계: 원형 번호 배지 (gradient) + 이모지 + 제목 + 설명
- 현재/활성 단계는 THEME.primary 강조, 나머지는 THEME.textSecondary
- 수직 타임라인: 좌측에 세로선 + 원형 노드 배치

### comparison
- 2컬럼 카드: 좌/우에 다른 악센트 (좌: THEME.primary, 우: THEME.accent)
- 상단에 VS 배지 또는 카테고리 레이블
- 각 항목 앞에 체크마크 또는 상태 아이콘

### quote (인용)
- 대형 따옴표 장식: fontSize 120, color THEME.primaryLight, position absolute, top -20, left 20
- 인용문: fontSize 24-28, fontStyle "italic", lineHeight 1.5
- 출처: 하단 우측, fontSize 14, color THEME.textSecondary

### hero
- 대형 텍스트 중심: accent word에 color THEME.primary 또는 gradient 배경 텍스트
- 미니멀한 배경, 텍스트와 여백으로 승부
- 서브타이틀은 maxWidth 600으로 중앙 정렬

### risk_analysis
- 위험도별 색상 코딩: high=THEME.red, medium=THEME.yellow, low=THEME.green
- 좌측에 위험도 배지 (색상 원형) + 우측에 설명
- 대응 방안은 들여쓰기 + THEME.primaryLight 배경

### action_plan
- 단계별 카드 + 기간 태그 (뱃지)
- 각 단계에 체크리스트 스타일의 태스크 목록
- 진행률 바로 시각화

### summary / closing
- 핵심 포인트 번호 목록 (큰 번호 + 제목 + 한줄 설명)
- 구분선으로 항목 분리
- closing: CTA 메시지 강조, 리소스/연락처 카드

## THEME 토큰 (전역 선언됨, 재선언 금지)
```
THEME.primary          // 메인 브랜드 컬러
THEME.accent           // 보조 브랜드 컬러
THEME.background       // 슬라이드 배경 (#F5F7FA)
THEME.text             // 제목 텍스트 (#1A202C)
THEME.textSecondary    // 본문 텍스트 (#64748B)
THEME.card             // 카드 배경 (#FFFFFF)
THEME.cardBorder       // 카드 테두리 (#E2E8F0)
THEME.cardShadow       // 카드 그림자 (string — 직접 사용)
THEME.shadow_sm        // 작은 그림자 (배지, 작은 요소)
THEME.shadow_lg        // 큰 그림자 (호버, 강조 요소)
THEME.iconBg1          // 아이콘 배지 배경 1 (= primary)
THEME.iconBg2          // 아이콘 배지 배경 2 (= accent)
THEME.primaryLight     // primary 8% 투명도 (강조 카드 배경, 배경 장식)
THEME.accentLight      // accent 8% 투명도
THEME.primaryMedium    // primary 15% 투명도 (더 진한 배경 장식)
THEME.gradient         // primary→accent 그라디언트 (CSS linear-gradient string)
THEME.subtleBg         // 아주 미묘한 primary 배경
THEME.divider          // 구분선 (#E2E8F0)
THEME.red              // 부정/위험
THEME.yellow           // 경고/주의
THEME.green            // 긍정/성공
```

## 사용 가능 라이브러리
- recharts: BarChart, Bar, Cell, LineChart, Line, AreaChart, Area, PieChart, Pie, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, RadialBarChart, RadialBar, ComposedChart, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, LabelList, Label
- React hooks: useState, useEffect (이미 전역 import)
- 유니코드 이모지

## 절대 금지
- ★ 코드 외의 모든 텍스트 출력 금지 — 사고 과정, 설명, 계획, 마크다운 헤딩(##) 등 절대 출력하지 마세요. const로 시작하는 순수 React 코드만 출력하세요.
- 컴포넌트 이름은 반드시 [컴포넌트 이름]에 지정된 이름을 const로 선언
- import 문 작성 금지 (이미 상위에서 import됨)
- const THEME = ... 재선언 금지 (이미 전역)
- 다크 테마 / 글래스모피즘 금지 (rgba 반투명을 메인 배경으로 사용 금지)
- JSX 텍스트 안에서 < > 문자 직접 사용 금지 → {"<"} 또는 &lt; &gt; 사용
- boxShadow는 반드시 THEME.cardShadow / THEME.shadow_sm / THEME.shadow_lg를 직접 사용. 템플릿 리터럴이나 삼항 연산자로 boxShadow를 구성하지 말 것
- 템플릿 리터럴 안 삼항 연산자는 반드시 완전한 형태: ${조건 ? 값A : 값B} (: 생략 금지)

## Anti-Patterns — 반드시 피할 것
- ❌ 모든 카드가 동일 크기/동일 색상 → 하나는 반드시 차별화 (크기, 배경색, 테두리)
- ❌ 배경이 완전 단색 (밋밋함) → 최소 1개의 미묘한 장식 요소 추가
- ❌ 모든 텍스트가 비슷한 크기 → 제목과 본문의 크기 차이 3배 이상
- ❌ 패딩 없이 빽빽한 레이아웃 → 넉넉한 여백이 고급감의 핵심
- ❌ 장식 요소 과다 (3개 초과) → 1-2개의 미묘한 장식이면 충분
- ❌ 모든 요소 중앙 정렬 → 좌측 정렬 + 비대칭 배치 활용
- ❌ 이모지가 너무 작음 (16px 이하) → 배지 안에서 최소 22-26px
- ❌ 차트에 기본 색상 → 반드시 THEME 컬러 적용
- ❌ 호버/인터랙션 없는 카드 → transition + hover 효과 필수
- ❌ content props 무시하고 하드코딩 → 반드시 props에서 동적으로 읽기"""


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

{"위 디자인 이미지의 레이아웃과 시각적 구성을 충실히 재현하되, " if image_b64 else ""}아래 요구사항을 반드시 지키세요:
1. content props에서 모든 데이터를 동적으로 읽어 렌더링 (하드코딩 금지)
2. height: "100%" 필수
3. 시각적 계층 구조 (L1 주목 → L2 내용 → L3 배경) 명확히 구분
4. 카드에 hover 인터랙션 (translateY + shadow 변화) 적용
5. 배경에 최소 1개의 미묘한 장식 요소 추가
6. 타이포그래피 크기 대비 극대화 (제목 vs 본문 3배 이상 차이)
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
