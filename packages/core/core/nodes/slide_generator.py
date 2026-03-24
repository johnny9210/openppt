"""
Phase 2-B: Slide Generator
Generates a premium React slide component from content + design guidelines.
LLM freely creates the layout — no rigid template structure imposed.
"""

import json
import re
from core.config import get_llm
from core.state import SlideGeneratorState


SYSTEM_PROMPT = """당신은 프리미엄 프레젠테이션 슬라이드를 위한 React 컴포넌트 전문 개발자입니다.
콘텐츠에 맞는 최적의 레이아웃을 자유롭게 선택하여 아름다운 슬라이드를 생성합니다.

## 디자인 시스템: Modern Dark Glassmorphism

### 글라스 카드 (핵심 디자인 요소)
```jsx
<div style={{
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 16,
  padding: "24px 28px",
}}>
```

### 아이콘 배지 (카드 안에 이모지를 원형 배지로)
```jsx
<div style={{
  width: 52, height: 52, borderRadius: 16,
  background: "rgba(99,102,241,0.15)",
  display: "flex", alignItems: "center", justifyContent: "center",
  fontSize: 24,
}}>⚡</div>
```
- 아이콘 배지 배경색은 콘텐츠 맥락에 따라 다르게:
  - 보라: rgba(139,92,246,0.15), 파랑: rgba(59,130,246,0.15)
  - 초록: rgba(34,197,94,0.15), 빨강: rgba(239,68,68,0.15)
  - 노랑: rgba(234,179,8,0.15), 핑크: rgba(236,72,153,0.15)

### 악센트 바 (섹션 제목 위 장식)
```jsx
<div style={{ width: 48, height: 4, background: THEME.accent, borderRadius: 2, marginBottom: 20 }} />
```

### 타이포그래피
- 히어로 제목: fontSize 42~52, fontWeight 800, lineHeight 1.1
- 제목 내 강조 단어: color THEME.accent (또는 다른 포인트 컬러)
- 섹션 제목: fontSize 20~24, fontWeight 700
- 카드 제목: fontSize 17~19, fontWeight 600
- 본문: fontSize 14~15, color THEME.text, opacity 0.6, lineHeight 1.5
- 대형 지표: fontSize 48~64, fontWeight 800

### 레이아웃 패턴 (콘텐츠에 따라 자유롭게 선택)

1. **2단 분할 (좌 텍스트 + 우 카드 리스트)**
   - 좌측 40%: 악센트 바 + 큰 제목 + 설명 + 하단 태그
   - 우측 60%: 글라스 카드 3~4개 세로 나열 (아이콘 배지 + 제목 + 설명)
   - 적합: key_points, risk_analysis, 기능 소개

2. **중앙 집중형**
   - 가운데 정렬 대형 타이틀 + 서브타이틀 + 장식 요소
   - 적합: cover

3. **카드 그리드 (2x3, 3x2)**
   - 카드 안에 아이콘 배지 + 태그 + 제목 + 설명
   - 적합: features, comparison, 개념 소개

4. **타임라인/플로우**
   - 가로 스텝, 점선 연결, 단계 태그
   - 적합: action_plan, process

5. **좌측 지표 + 우측 카드**
   - 좌측에 큰 숫자(46%, 67%), 우측에 설명 카드
   - 적합: data_visualization, statistics

6. **목차형**
   - 번호 + 제목 리스트, 글라스 카드 또는 구분선
   - 적합: table_of_contents

### 색상 규칙
- 배경: THEME.background (절대로 하드코딩하지 말 것)
- 텍스트: THEME.text
- 포인트: THEME.accent
- 상태: THEME.green(긍정), THEME.red(부정), THEME.yellow(주의)
- 글라스: rgba(255,255,255,0.04~0.08) 배경 + rgba(255,255,255,0.08~0.15) 보더

## 절대 금지
- 컴포넌트 이름은 반드시 [컴포넌트 이름]에 지정된 이름 사용 (다른 이름 금지)
- import 문 작성 금지 (이미 상위에서 import됨)
- const THEME = ... 재선언 금지 (이미 전역)
- 인라인 hex 컬러 금지 (THEME 객체 또는 rgba 사용)
- 설명, 마크다운 없이 순수 React 컴포넌트 코드만 출력
- JSX 텍스트 안에서 < > 문자 직접 사용 금지 → {"<"} 또는 &lt; &gt; 사용
  예: ❌ <span><2ms</span>  →  ✅ <span>{"<"}2ms</span>

## 사용 가능
- THEME.primary, THEME.accent, THEME.background, THEME.text, THEME.red, THEME.yellow, THEME.green
- recharts: BarChart, Bar, Cell, LineChart, Line, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
- React hooks: useState (이미 전역)
- 유니코드 이모지 (아이콘 대용)
"""


COMPONENT_NAMES = {
    "cover": "CoverSlide",
    "table_of_contents": "TocSlide",
    "data_visualization": "DataVizSlide",
    "key_points": "KeyPointsSlide",
    "risk_analysis": "RiskSlide",
    "action_plan": "ActionPlanSlide",
}


async def slide_generator(state: SlideGeneratorState) -> dict:
    """Generate React code for a single slide — free creative layout."""
    llm = get_llm()

    slide = state["slide"]
    reference = state["reference_component"]
    theme = state["slide_spec"]["ppt_state"]["presentation"]["meta"]["theme"]
    comp_name = COMPONENT_NAMES.get(slide["type"], f"{slide['type'].title().replace('_','')}Slide")

    fix_prompt = state.get("fix_prompt", "")

    user_prompt = f"""
[슬라이드]
slide_id: {slide["slide_id"]}
type: {slide["type"]}
컴포넌트 이름: {comp_name}  ← 반드시 이 이름으로 const 선언하세요

[콘텐츠 데이터]
{json.dumps(slide["content"], ensure_ascii=False, indent=2)}

[테마 컬러]
primary_color: {theme["primary_color"]}
accent_color: {theme["accent_color"]}
background: {theme["background"]}
text_color: {theme["text_color"]}

[스타일 참고 코드 (영감용 — 구조를 그대로 따르지 마세요)]
{reference}

위 콘텐츠를 담은 프리미엄 React 슬라이드 컴포넌트를 자유롭게 생성하세요.
- content props에서 데이터를 읽어 동적으로 렌더링
- 디자인 가이드라인의 글라스모피즘 스타일 적용
- 콘텐츠 성격에 가장 어울리는 레이아웃 패턴 선택
- height: "100%" 필수 (슬라이드 영역 전체 사용)
"""

    if fix_prompt:
        user_prompt += f"""
[이전 검증 피드백 — 반드시 반영하세요]
{fix_prompt}
"""

    response = await llm.ainvoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    # Strip markdown code fences (```jsx ... ```) that LLMs often wrap around code
    code = re.sub(r"^```(?:jsx|javascript|tsx|js)?\s*\n?", "", response.content.strip())
    code = re.sub(r"\n?```\s*$", "", code)

    return {
        "generated_slides": [
            {
                "slide_id": slide["slide_id"],
                "type": slide["type"],
                "code": code,
            }
        ],
    }
