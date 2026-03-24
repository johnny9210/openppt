"""
Phase 2-B: Slide Generator
Generates React component code for a single slide using slot filling.
"Reference Component의 {{slot}} 부분을 slots 필드를 참조하여 채워라. 구조는 변경 금지."
"""

import json
import re
from core.config import get_llm
from core.state import SlideGeneratorState


SYSTEM_PROMPT = """당신은 React PPT 슬라이드 컴포넌트 코드 생성 전문가입니다.

Reference Component가 주어집니다. 이 컴포넌트의 구조를 유지하면서
slots 필드의 지시사항에 따라 슬롯을 채우세요.

규칙:
1. Reference Component의 전체 구조(컴포넌트명, props, 레이아웃)는 변경 금지
2. slots 필드의 각 지시사항을 코드로 정확히 구현
3. THEME 객체를 사용하여 색상 참조 (인라인 hex 코드 금지)
4. recharts 라이브러리로 차트 구현 (chart_type이 있는 경우)
5. 조건부 렌더링은 slots의 condition을 코드로 변환

중요 금지사항:
- import 문을 절대 작성하지 마세요 (이미 상위에서 import됨)
- const THEME = ... 을 절대 재선언하지 마세요 (이미 전역으로 선언됨)
- THEME.primary, THEME.accent, THEME.background, THEME.text 키를 사용하세요
- 컴포넌트 함수 정의만 출력하세요

React 컴포넌트 코드만 출력하세요. 설명이나 마크다운 없이 순수 코드만.
"""


async def slide_generator(state: SlideGeneratorState) -> dict:
    """Generate React code for a single slide based on reference + slots."""
    llm = get_llm()

    slide = state["slide"]
    reference = state["reference_component"]
    theme = state["slide_spec"]["ppt_state"]["presentation"]["meta"]["theme"]

    fix_prompt = state.get("fix_prompt", "")

    user_prompt = f"""
[슬라이드 정보]
slide_id: {slide["slide_id"]}
type: {slide["type"]}
state: {slide["state"]}

[콘텐츠]
{json.dumps(slide["content"], ensure_ascii=False, indent=2)}

[슬롯 지시사항]
{json.dumps(slide["slots"], ensure_ascii=False, indent=2)}

[테마]
{json.dumps(theme, ensure_ascii=False, indent=2)}

[Reference Component]
{reference}

위 Reference Component의 슬롯을 채워서 완성된 React 컴포넌트 코드를 생성하세요.
"""

    if fix_prompt:
        user_prompt += f"""
[이전 검증 피드백 - 반드시 반영하세요]
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
