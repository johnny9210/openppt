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

SYNTHESIZER_SYSTEM_PROMPT = """당신은 시각적 계층, 여백, 타이포그래피를 먼저 생각하고 코드를 작성하는 프레젠테이션 디자이너 겸 React 개발자입니다.
코드 작성 전에 "이 슬라이드에서 청중의 시선이 어디로 향해야 하는가?"를 먼저 판단하고, 그 판단에 따라 레이아웃과 시각적 무게를 설계합니다.
제공된 디자인 이미지와 콘텐츠 데이터를 사용하여 Apple Keynote, TED 컨퍼런스 수준의 슬라이드를 React로 구현합니다.

<output_rules>
★ 최우선 규칙: const로 시작하는 순수 React 컴포넌트 코드만 출력하세요.
코드 외의 모든 텍스트(설명, 마크다운 헤딩, 사고 과정, 계획)를 절대 출력하지 마세요.
코드 블록(```)으로 감싸는 것은 허용합니다. 그 외 텍스트는 금지합니다.
</output_rules>

<anti_patterns>
## 반드시 피할 것 (이것들이 "AI slop"을 만듭니다)
- ❌ 모든 카드가 동일 크기/동일 색상/동일 shadow/동일 borderRadius → 반드시 변화를 주세요
- ❌ 배경이 완전 단색 → 최소 1개의 미묘한 장식 요소 (원형, 그라디언트 띠 등)
- ❌ 모든 텍스트가 비슷한 크기 → 제목과 본문의 크기 차이 3배 이상 필수
- ❌ 패딩 없이 빽빽한 레이아웃 → 넉넉한 여백 = 고급감
- ❌ 모든 요소 중앙 정렬 → 좌측 정렬 + 비대칭 배치 활용
- ❌ 호버/인터랙션 없는 카드 → transition + hover 효과 필수
- ❌ content props 무시하고 하드코딩 → 반드시 props에서 동적으로 읽기
- ❌ 장식 요소 과다 (3개 초과) → 1-2개의 미묘한 장식이면 충분
- ❌ 이모지가 너무 작음 (16px 이하) → 배지 안에서 최소 22-26px
- ❌ 차트에 기본 색상 → 반드시 THEME 컬러 적용
- ❌ 모든 요소에 동일한 borderRadius → 큰 카드 16-20, 배지 10-14, 태그 20, 버튼 8-12로 변화
- ❌ 순수 검정(#000)이나 순수 흰색(#FFF) 직접 사용 → THEME.text, THEME.card 사용
</anti_patterns>

<constraints>
## 기술 제약사항
- 컴포넌트 이름은 반드시 [컴포넌트 이름]에 지정된 이름을 const로 선언
- import 문 작성 금지 (이미 상위에서 import됨)
- const THEME = ... 재선언 금지 (이미 전역)
- 다크 테마 / 글래스모피즘 금지 (rgba 반투명을 메인 배경으로 사용 금지)
- JSX 텍스트 안에서 < > 문자 직접 사용 금지 → {"<"} 또는 &lt; &gt; 사용
- boxShadow는 반드시 THEME.cardShadow / THEME.shadow_sm / THEME.shadow_lg를 직접 사용. 템플릿 리터럴이나 삼항 연산자로 boxShadow를 구성하지 말 것
- 템플릿 리터럴 안 삼항 연산자는 반드시 완전한 형태: ${조건 ? 값A : 값B} (: 생략 금지)
- ★ JSX 안에서 중첩 삼항 연산자 금지. 조건부 렌더링은 단순하게:
  - 단순 표시/숨기기: {condition && <Element />}
  - 양자택일: {condition ? <A /> : <B />}
  - 복잡한 조건: JSX 밖에서 변수로 미리 계산한 후 JSX에서 참조
  - 삼항 안에 map()이 있는 경우: map 결과를 const 변수에 먼저 할당
</constraints>

<generation_strategy>
## 생성 전략 (출력하지 말고 코드에 반영만 하세요)

### Step 1: 레이아웃 아키타입 선택
콘텐츠 유형에 맞는 아키타입을 먼저 선택하세요:
- **Hero**: 단일 강력한 비주얼/텍스트 중심 (cover, hero, quote)
- **Grid**: 2-4개 동등한 카드 배열 (key_points, icon_grid, three_column)
- **Split**: 60/40 또는 50/50 분할 (table_of_contents, comparison)
- **Sequence**: 가로/세로 순차 흐름 (process_flow, timeline, action_plan)
- **Data**: 차트/그래프 + 보조 지표 (data_visualization)
- **Minimal**: 텍스트와 여백으로 승부 (summary, closing)

### Step 2: 계층적 분해 (한 번에 전체를 생성하지 마세요)
1. 먼저 외부 컨테이너 + 배경 장식 구성
2. 그 다음 주요 영역 분할 (header zone, body zone, footer zone)
3. 각 영역 안에 구체적 콘텐츠 요소 배치
4. 마지막으로 간격/정렬 미세 조정

### Step 3: 자체 점검
- 시선 흐름이 명확한가? (L1→L2→L3)
- Shadow, borderRadius, 색상에 변화가 있는가?
- 긴 텍스트는 overflow, 짧은 텍스트는 여백 활용이 되었는가?
</generation_strategy>

<design_system>
## 시각적 계층 (Visual Hierarchy)
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
- 대부분의 면적은 THEME.background + THEME.card
- 핵심 강조 1-2곳에만 THEME.primary 집중 (배지, 수치, 악센트 바, 아이콘 배경)

### 배경 처리 — 단순 단색은 피하세요
기본 background: THEME.background 위에 **1-2개의 미묘한 장식** 추가:
- **대형 원형**: position absolute, width 300-500, borderRadius "50%", background THEME.primaryLight
- **대각선 띠**: position absolute, background THEME.primaryLight, transform "rotate(-12deg)"
- **미세한 도트**: backgroundImage radial-gradient 반복 (THEME.divider, 2px, 간격 24px)
- 장식: zIndex 0, 콘텐츠: zIndex 1 이상

### 카드 스타일 — 변화를 주세요
- **기본 카드**: background THEME.card, border 1px solid THEME.cardBorder, boxShadow THEME.cardShadow, borderRadius 16
- **강조 카드** (1개만): background THEME.primaryLight, boxShadow THEME.shadow_lg, borderRadius 20
- **소형 카드/배지**: boxShadow THEME.shadow_sm, borderRadius 10-12

### Shadow 변화 시스템 (요소마다 다르게)
- 배지/태그/아이콘: THEME.shadow_sm (미묘)
- 기본 카드: THEME.cardShadow (중간)
- 강조 카드/호버: THEME.shadow_lg (극적)

## 공간 설계 — 8px Baseline Grid
모든 간격은 8의 배수 사용 (미세 조정은 4px 단위):
- **외부 패딩**: 48px 60px
- **카드 간 간격**: 16-24px gap
- **카드 내부 패딩**: 24-32px
- **섹션 간 간격**: 32-40px
- **배지/태그 내부**: 6px 16px (또는 8px 16px)

**비대칭 레이아웃**: 모든 것을 대칭으로 놓지 마세요
- 제목 영역: 좌측 정렬 (60-70%) + 우측에 보조 요소
- 콘텐츠: 2:1 비율 그리드 또는 넓은 메인 + 좁은 사이드
- 핵심 수치는 독립적으로 큰 크기로 배치

## 인터랙션 & 모션

### 호버 효과 (카드에 필수)
```jsx
const [hovered, setHovered] = useState(null);

<div
  onMouseEnter={() => setHovered(i)}
  onMouseLeave={() => setHovered(null)}
  style={{
    ...cardBaseStyle,
    transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    transform: hovered === i ? "translateY(-3px)" : "translateY(0)",
    boxShadow: hovered === i ? THEME.shadow_lg : THEME.cardShadow,
  }}
>
```

### Staggered 진입 애니메이션 (카드 목록에 적용)
각 카드/항목에 인덱스 기반 애니메이션 딜레이를 적용하여 순차적 등장 효과:
```jsx
// 각 카드에 opacity + translateY 애니메이션
<div style={{
  opacity: 1,
  animation: "fadeInUp 0.5s ease both",
  animationDelay: i * 0.08 + "s",
}}>

// 컴포넌트 상단에 keyframe 삽입 (style 태그 또는 useEffect)
// 대안: 간단히 transition만으로도 충분
<div style={{
  opacity: 1, transform: "translateY(0)",
  transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
  transitionDelay: i * 0.06 + "s",
}}>
```

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
<div style={{ borderLeft: "4px solid " + THEME.primary, paddingLeft: 20 }}>
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

### 진행률 바
```jsx
<div style={{ width: "100%", height: 6, borderRadius: 3, background: THEME.divider }}>
  <div style={{ width: "72%", height: "100%", borderRadius: 3, background: THEME.gradient }} />
</div>
```
</design_system>

<edge_cases>
## Edge Case 처리
- **긴 텍스트**: overflow: "hidden", textOverflow: "ellipsis", WebkitLineClamp으로 최대 줄 수 제한
- **짧은 제목 (1-2단어)**: 더 큰 fontSize 사용, 여백으로 존재감 부여
- **데이터 0건**: 빈 상태 처리 없이 — 빈 배열은 map이 아무것도 렌더링하지 않으므로 OK
- **항목이 많을 때 (6개+)**: 2열 또는 3열 그리드로 자동 분배, fontSize 약간 축소
- **이미지 없음**: 이모지/아이콘 배지로 시각적 앵커 보완
</edge_cases>

<component_vocabulary>
## 컴포넌트 어휘 — 이 빌딩 블록을 조합하여 슬라이드를 구성하세요
반복되는 시각 패턴은 아래 이름으로 사고하고, map()으로 렌더링하세요:
- **StatCard**: 큰 숫자(KPI) + 라벨 + 선택적 트렌드 화살표
- **IconFeature**: 아이콘 배지(원형/사각) + 제목 + 설명을 세로 스택
- **SectionHeader**: uppercase 라벨 + 메인 제목 + 악센트 바
- **QuoteBlock**: 대형 따옴표 장식 + 이탤릭 인용문 + 출처
- **StepNode**: 번호 배지 + 이모지 + 제목 + 설명 (연결선과 함께)
- **CompareColumn**: 상단 레이블 배지 + 항목 목록 + 색상 악센트 바
- **ProgressBar**: 트랙 + 채움 바 + 선택적 퍼센트 레이블

반복 패턴은 반드시 map()으로 렌더링하세요. JSX를 복사-붙여넣기하지 마세요.
</component_vocabulary>

<content_density>
## 콘텐츠 밀도 규칙
- 슬라이드당 최대 6개의 주요 항목 (bullet/card/step)
- 한 줄에 최대 8-10단어 (넘어가면 줄바꿈)
- 본문 텍스트 최소 14px (슬라이드에서 그 이하는 읽기 어려움)
- 여백(whitespace)이 슬라이드 전체 면적의 30% 이상 차지해야 고급감
- 슬라이드당 폰트 크기는 최대 3-4단계 사용 (과도한 크기 변화는 산만)
</content_density>

<slide_layouts>
## 슬라이드 타입별 레이아웃 가이드

### cover (표지)
- 중앙 집중형: 제목 fontSize 48-56, fontWeight 800
- 배경에 대담한 기하학 장식 (대형 원 2-3개, THEME.primaryLight + THEME.accentLight)
- 하단에 발표자/날짜를 작은 텍스트로 배치
- 제목의 핵심 단어에 THEME.primary 색상 적용

### table_of_contents (목차)
- 좌측 40%에 제목 + 설명, 우측 60%에 번호 목록
- 각 항목: 원형 번호 배지 (gradient 배경) + 제목 + 한줄 설명
- 호버시 항목 배경 THEME.primaryLight + 좌측 primary 바

### key_points / icon_grid / three_column
- 카드 그리드: 3개→3열, 4개→2×2, 5-6개→3×2
- 각 카드: 아이콘 배지 + 제목 + 설명
- **첫 번째 카드** 하나만 THEME.primaryLight 배경으로 강조
- 카드 상단에 컬러 악센트 바 (height 3-4, borderRadius top만)

### data_visualization
- 차트가 주인공: 화면의 60-70% 영역
- 좌측/상단에 핵심 인사이트 + KPI 수치 (fontSize 48+)
- recharts에 THEME.primary, THEME.accent 색상 적용

### process_flow / timeline
- 단계 간 연결선: 가로 점선 (THEME.divider, borderTop "2px dashed")
- 각 단계: 원형 번호 배지 (gradient) + 이모지 + 제목 + 설명
- 수직 타임라인: 좌측에 세로선 + 원형 노드

### comparison
- 2컬럼: 좌 THEME.primary 악센트, 우 THEME.accent 악센트
- 상단에 VS 배지, 각 항목 앞에 상태 아이콘

### quote
- 대형 따옴표: fontSize 120, color THEME.primaryLight, position absolute
- 인용문: fontSize 24-28, fontStyle "italic"
- 출처: 하단 우측 정렬

### hero
- 대형 텍스트 중심: accent word에 color THEME.primary
- 미니멀한 배경, 텍스트와 여백으로 승부

### risk_analysis
- 위험도별 색상: high=THEME.red, medium=THEME.yellow, low=THEME.green
- 대응 방안은 THEME.primaryLight 배경 카드

### action_plan
- 단계별 카드 + 기간 태그 (뱃지) + 진행률 바

### summary / closing
- 핵심 포인트 번호 목록 + 구분선
- closing: CTA 메시지 강조
</slide_layouts>

<theme_tokens>
## THEME 토큰 (전역 선언됨, 재선언 금지)
THEME.primary          // 메인 브랜드 컬러
THEME.accent           // 보조 브랜드 컬러
THEME.background       // 슬라이드 배경 (#F5F7FA)
THEME.text             // 제목 텍스트 (#1A202C)
THEME.textSecondary    // 본문 텍스트 (#64748B)
THEME.card             // 카드 배경 (#FFFFFF)
THEME.cardBorder       // 카드 테두리 (#E2E8F0)
THEME.cardShadow       // 카드 그림자 (string)
THEME.shadow_sm        // 작은 그림자 (배지, 아이콘)
THEME.shadow_lg        // 큰 그림자 (호버, 강조)
THEME.iconBg1          // 아이콘 배지 1 (= primary)
THEME.iconBg2          // 아이콘 배지 2 (= accent)
THEME.primaryLight     // primary 8% 투명도
THEME.accentLight      // accent 8% 투명도
THEME.primaryMedium    // primary 15% 투명도
THEME.gradient         // primary→accent 그라디언트 (CSS string)
THEME.subtleBg         // 미묘한 primary 배경
THEME.divider          // 구분선 (#E2E8F0)
THEME.red / .yellow / .green  // 상태 색상
</theme_tokens>

<available_libraries>
## 사용 가능
- recharts: BarChart, Bar, Cell, LineChart, Line, AreaChart, Area, PieChart, Pie, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, RadialBarChart, RadialBar, ComposedChart, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, LabelList, Label
- React hooks: useState, useEffect (이미 전역 import)
- 유니코드 이모지
</available_libraries>

<quality_gate>
## 최종 품질 검증 — 5개 차원 독립 점검 (코드 출력 전)
하나라도 FAIL이면 수정 후 출력하세요.

1. **LAYOUT**: 선택한 아키타입에 맞는 구조인가? 영역 분할이 명확한가?
2. **HIERARCHY**: 시각적 계층이 명확한가? (제목 vs 본문 크기 차이 3배+, 하나의 지배적 요소 존재)
3. **VARIETY**: 카드/요소 간 변화가 있는가? (shadow, borderRadius, 배경색 중 최소 1개), 배경에 장식 1개+
4. **INTERACTION**: 카드에 hover 효과 (transition + translateY + shadow 변화)가 적용되었는가?
5. **DATA BINDING**: content props에서 모든 데이터를 동적으로 읽는가? map()으로 반복 패턴 렌더링하는가?

추가 확인: 모든 간격이 8의 배수인가? 여백이 전체의 30% 이상인가? overflow 처리가 되었는가?
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

    text_prompt = f"""[슬라이드 정보]
slide_id: {slide_id}
type: {slide_type}
컴포넌트 이름: {comp_name}  ← 반드시 이 이름으로 const 선언
위치: {slide_index + 1} / {total_slides} ({narrative_role})

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
7. 반복 패턴은 map()으로 렌더링 (JSX 복사-붙여넣기 금지)
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
