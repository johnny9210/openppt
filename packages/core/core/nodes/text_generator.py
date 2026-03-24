"""
Phase 2-A: Text Generator
Generates detailed text content for each slide in parallel via Send API.
"""

import json
import logging

from core.config import get_llm
from core.state import TextGeneratorState
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)

TEXT_GEN_PROMPT = """당신은 프레젠테이션 콘텐츠 작성 전문가입니다.
주어진 슬라이드 기획 정보를 바탕으로 실제 슬라이드에 들어갈 상세 텍스트 콘텐츠를 작성합니다.

## 프레젠테이션 정보
목적: {purpose}
대상: {audience}
핵심 메시지: {key_message}

## 슬라이드 정보
slide_id: {slide_id}
type: {slide_type}
주제: {topic}
핵심 포인트: {key_points}
추가 데이터: {data}

## 슬라이드 타입별 출력 형식

### cover
```json
{{
    "title": "메인 제목",
    "subtitle": "부제목",
    "presenter": "발표자 이름 또는 팀명",
    "date": "2024"
}}
```

### table_of_contents
```json
{{
    "title": "목차",
    "items": [
        {{"number": 1, "title": "섹션명", "description": "간단한 설명"}}
    ]
}}
```

### data_visualization
```json
{{
    "title": "차트 제목",
    "description": "데이터 설명",
    "chart_type": "bar | line | pie",
    "data": [{{"name": "항목", "value": 100}}],
    "insight": "핵심 인사이트"
}}
```

### key_points
```json
{{
    "title": "섹션 제목",
    "description": "섹션 설명",
    "points": [
        {{"emoji": "⚡", "title": "포인트 제목", "description": "상세 설명", "metric": "수치 (선택)"}}
    ]
}}
```

### risk_analysis
```json
{{
    "title": "리스크 분석",
    "description": "분석 개요",
    "risks": [
        {{"level": "high | medium | low", "title": "리스크명", "description": "설명", "mitigation": "대응 방안"}}
    ]
}}
```

### action_plan
```json
{{
    "title": "실행 계획",
    "description": "계획 개요",
    "actions": [
        {{"phase": "Phase 1", "title": "단계명", "period": "기간", "tasks": ["태스크1", "태스크2"]}}
    ]
}}
```

반드시 해당 슬라이드 타입에 맞는 JSON 형식으로만 응답하세요.
콘텐츠는 구체적이고 전문적으로 작성하세요."""


async def text_generator(state: TextGeneratorState) -> dict:
    """Generate detailed text content for a single slide."""
    llm = get_llm()
    slide = state["slide_plan"]
    brief = state["research_brief"]

    prompt = TEXT_GEN_PROMPT.format(
        purpose=brief.get("purpose", ""),
        audience=brief.get("audience", ""),
        key_message=brief.get("key_message", ""),
        slide_id=slide["slide_id"],
        slide_type=slide["type"],
        topic=slide["topic"],
        key_points=json.dumps(slide.get("key_points", []), ensure_ascii=False),
        data=json.dumps(slide.get("data"), ensure_ascii=False) if slide.get("data") else "없음",
    )

    response = await llm.ainvoke([
        {"role": "user", "content": prompt},
    ])

    try:
        content = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("text_generator [%s]: %s", slide["slide_id"], exc)
        content = {"title": slide["topic"], "error": str(exc)}

    return {
        "slide_contents": [{
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "content": content,
        }]
    }
