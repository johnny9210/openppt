"""
Phase 1: Scoping (dee_research pattern)
Analyzes user request and generates structured research brief with slide plan.
"""

import logging

from core.config import get_llm
from core.state import PPTState
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)

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

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요:

```json
{
    "purpose": "프레젠테이션의 목적 (한 문장)",
    "audience": "대상 청중",
    "key_message": "전달하려는 핵심 메시지",
    "style": {
        "mood": "professional | creative | minimal | bold",
        "primary_color": "#6366F1",
        "accent_color": "#818CF8",
        "background": "#050810",
        "text_color": "#E2E8F0"
    },
    "slide_plan": [
        {
            "slide_id": "slide_001",
            "type": "cover",
            "topic": "슬라이드 주제",
            "key_points": ["핵심 포인트1", "핵심 포인트2"],
            "design_direction": "디자인 방향 설명 (레이아웃, 시각적 요소 등)",
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
- design_direction은 구체적으로 (레이아웃 패턴, 시각적 요소, 강조점 등)
- data 필드는 차트/그래프에 사용할 구체적 데이터 (없으면 null)
- 색상은 주제와 분위기에 맞게 선택 (기본: 보라/남색 계열 다크 테마)

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


async def scoping(state: PPTState) -> dict:
    """Analyze user request and generate structured research brief."""
    llm = get_llm()

    response = await llm.ainvoke([
        {"role": "system", "content": SCOPING_PROMPT},
        {"role": "user", "content": state["user_request"]},
    ])

    try:
        brief = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("scoping: %s", exc)
        raise ValueError(
            f"Scoping could not parse research brief: {exc}"
        ) from exc

    return {"research_brief": brief}
