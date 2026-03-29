"""
Phase 2-A: Text Generator
Generates detailed text content for each slide in parallel via Send API.
"""

import asyncio
import json
import logging
import os

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.runnables import RunnableConfig

from core.config import get_llm, LLM_TIMEOUT
from core.state import TextGeneratorState
from core.utils import robust_parse_json, LLMJSONParseError

logger = logging.getLogger(__name__)

# Limit concurrent Bedrock calls from parallel text generators.
MAX_CONCURRENT_TEXT_GEN = int(os.getenv("MAX_CONCURRENT_TEXT_GEN", "5"))
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_TEXT_GEN)
    return _semaphore

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

### hero
```json
{{
    "title": "강조할 핵심 메시지",
    "subtitle": "보조 설명 (1~2문장)",
    "accent_word": "제목에서 강조할 단어"
}}
```

### quote
```json
{{
    "quote": "인용구 또는 핵심 문구",
    "attribution": "출처 또는 설명 (선택)",
    "context": "부연 설명 (선택)"
}}
```

### icon_grid
```json
{{
    "title": "섹션 제목",
    "description": "섹션 설명",
    "items": [
        {{"emoji": "🔔", "label": "항목명", "description": "간단한 설명"}}
    ]
}}
```

### process_flow
```json
{{
    "title": "프로세스 제목",
    "description": "프로세스 설명",
    "steps": [
        {{"step": 1, "emoji": "⏰", "title": "단계명", "description": "단계 설명"}}
    ]
}}
```

### comparison
```json
{{
    "title": "비교 제목",
    "left": {{"label": "Before / 문제", "items": ["항목1", "항목2", "항목3"]}},
    "right": {{"label": "After / 해결", "items": ["항목1", "항목2", "항목3"]}}
}}
```

### three_column
```json
{{
    "title": "섹션 제목",
    "description": "섹션 설명",
    "columns": [
        {{"emoji": "📧", "title": "칼럼 제목", "description": "칼럼 설명", "metric": "수치 (선택)"}}
    ]
}}
```

### timeline
```json
{{
    "title": "타임라인 제목",
    "description": "타임라인 설명",
    "events": [
        {{"time": "시점 (예: 오전 7시, Phase 1)", "emoji": "🌅", "title": "이벤트명", "description": "이벤트 설명"}}
    ]
}}
```

### summary
```json
{{
    "title": "정리 제목",
    "points": [
        {{"number": 1, "title": "핵심 포인트", "description": "부연 설명"}}
    ]
}}
```

### closing
```json
{{
    "title": "마무리 제목",
    "message": "마무리 메시지 (감사, CTA 등)",
    "resources": [
        {{"emoji": "📚", "label": "자료 유형", "description": "설명 또는 링크"}}
    ]
}}
```

반드시 해당 슬라이드 타입에 맞는 JSON 형식으로만 응답하세요.
콘텐츠는 구체적이고 전문적으로 작성하세요."""


async def text_generator(state: TextGeneratorState, config: RunnableConfig) -> dict:
    """Generate detailed text content for a single slide."""
    cancel_event = (config.get("configurable") or {}).get("cancel_event")
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

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

    # Append web research context if available (from web_researcher node)
    web_research = slide.get("web_research")
    if web_research:
        research_lines = ["\n\n## 웹 리서치 참고 자료 (실제 데이터를 활용하세요)"]
        for i, r in enumerate(web_research, 1):
            research_lines.append(f"\n[{i}] {r.get('title', '')}")
            research_lines.append(f"    {r.get('content', '')}")
            if r.get("url"):
                research_lines.append(f"    출처: {r['url']}")
        prompt += "\n".join(research_lines)

    input_tokens = 0
    output_tokens = 0

    async with _get_semaphore():
        with get_usage_metadata_callback() as cb:
            response = await asyncio.wait_for(
                llm.ainvoke([{"role": "user", "content": prompt}]),
                timeout=LLM_TIMEOUT,
            )
            if cb.usage_metadata:
                for _, usage in cb.usage_metadata.items():
                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)

    try:
        content = robust_parse_json(response.content)
    except LLMJSONParseError as exc:
        logger.error("text_generator [%s]: %s", slide["slide_id"], exc)
        content = {"title": slide["topic"], "error": str(exc)}

    logger.info("[TextGen] %s tokens: in=%d out=%d", slide["slide_id"], input_tokens, output_tokens)

    return {
        "slide_contents": [{
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "content": content,
        }],
        "token_usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
