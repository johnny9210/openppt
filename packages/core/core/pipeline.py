"""
LangGraph Pipeline - PPT Code Generation
Architecture: Scoping -> Web Research -> Cover-First Design -> Parallel (Text + Remaining Design) -> Synthesis -> Validation

Uses LangGraph v1.0.10 API:
- StateGraph with conditional edges
- Send API for parallel text + design generation
- Cover slide generated first for style reference
- Checkpointer for state persistence
- get_stream_writer for SSE progress
- Token tracking via get_usage_metadata_callback (deep_research pattern)
- Cancel support via asyncio.Event (deep_research pattern)
- Web search via Tavily API (deep_research pattern)
"""

import logging



from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer

from core.state import PPTState
from core.config import MAX_REVISIONS

logger = logging.getLogger(__name__)

# Import nodes
from core.nodes.scoping import scoping
from core.nodes.web_researcher import web_researcher
from core.nodes.text_generator import text_generator
from core.nodes.design_generator import cover_design_generator, design_generator
from core.nodes.code_synthesizer import code_synthesizer
from core.nodes.code_assembly import code_assembly
from core.nodes.ast_validator import ast_validator
from core.nodes.runtime_validator import runtime_validator


# --- Phase 2a: Cover + Text dispatch ---

def cover_and_text_dispatcher(state: PPTState) -> Command:
    """Fan-out: dispatch cover design (single) + ALL text generators in parallel.

    Cover design runs separately so its output image can be used as a style
    reference for remaining slides. Text generators all run in parallel.
    """
    brief = state["research_brief"]
    slide_plan = brief.get("slide_plan", [])

    sends = []

    for slide in slide_plan:
        payload = {
            "slide_plan": slide,
            "research_brief": brief,
        }
        # ALL text generators run in parallel
        sends.append(Send("text_generator", payload))

        # Cover design generator runs separately (first slide)
        if slide["type"] == "cover":
            sends.append(Send("cover_design_generator", payload))

    return Command(goto=sends)


# --- Phase 2b: Remaining design dispatch (after cover completes) ---

def remaining_design_dispatcher(state: PPTState) -> Command:
    """Fan-out: dispatch remaining (non-cover) design generators with cover image as reference.

    This node runs AFTER all text_generators and cover_design_generator complete.
    It reads cover_design_image from state and passes it to each remaining design generator.
    """
    brief = state["research_brief"]
    slide_plan = brief.get("slide_plan", [])
    cover_image = state.get("cover_design_image") or ""

    sends = []
    for slide in slide_plan:
        if slide["type"] == "cover":
            continue  # Already generated in Phase 2a

        payload = {
            "slide_plan": slide,
            "research_brief": brief,
            "reference_image_b64": cover_image,
        }
        sends.append(Send("design_generator", payload))

    if not sends:
        # Edge case: only cover slide
        return Command(goto="code_synthesizer")

    return Command(goto=sends)


# --- Routing functions ---

def route_ast_result(state: PPTState) -> str:
    """AST fail -> re-run code_assembly."""
    result = state.get("validation_result", {})
    revision_count = state.get("revision_count", 0)
    if (
        result.get("layer") == "ast"
        and result.get("status") == "fail"
        and revision_count < MAX_REVISIONS
    ):
        return "code_assembly"
    return "runtime_validator"


def route_runtime_result(
    state: PPTState,
) -> str:
    """Runtime fail -> re-synthesize code. Pass -> END."""
    result = state.get("validation_result", {})
    revision_count = state.get("revision_count", 0)
    if (
        result.get("layer") == "runtime"
        and result.get("status") == "fail"
        and revision_count < MAX_REVISIONS
    ):
        return "code_synthesizer"
    return END


# --- Progress wrapper nodes ---

async def progress_scoping(state: PPTState, config) -> dict:
    writer = get_stream_writer()
    writer({"phase": 1, "step": "scoping", "message": "요청 분석 중..."})
    result = await scoping(state, config)
    slide_count = len(result.get("research_brief", {}).get("slide_plan", []))
    writer({
        "phase": 1,
        "step": "scoping",
        "message": f"분석 완료: {slide_count}장 슬라이드 기획",
        "done": True,
    })
    return result


async def progress_web_researcher(state: PPTState, config) -> dict:
    writer = get_stream_writer()
    from core.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        writer({"phase": 1, "step": "web_research", "message": "웹 리서치 건너뜀 (API 키 없음)", "done": True})
        return {}
    slide_plan = state.get("research_brief", {}).get("slide_plan", [])
    writer({"phase": 1, "step": "web_research", "message": f"웹 리서치 중... ({len(slide_plan)}장 슬라이드)"})
    result = await web_researcher(state, config)
    enriched = sum(1 for s in result.get("research_brief", {}).get("slide_plan", []) if s.get("web_research"))
    writer({
        "phase": 1,
        "step": "web_research",
        "message": f"웹 리서치 완료: {enriched}장 데이터 보강",
        "done": True,
    })
    return result


def progress_cover_and_text_dispatcher(state: PPTState) -> Command:
    writer = get_stream_writer()
    slide_count = len(state.get("research_brief", {}).get("slide_plan", []))
    writer({
        "phase": 2,
        "step": "cover_text_dispatch",
        "message": f"Cover 디자인 + 텍스트 {slide_count}장 생성 시작...",
    })
    result = cover_and_text_dispatcher(state)
    writer({
        "phase": 2,
        "step": "cover_text_dispatch",
        "message": "Cover + 텍스트 분배 완료",
        "done": True,
    })
    return result


def progress_remaining_design_dispatcher(state: PPTState) -> Command:
    writer = get_stream_writer()
    cover_ok = bool(state.get("cover_design_image"))
    slide_plan = state.get("research_brief", {}).get("slide_plan", [])
    remaining = sum(1 for s in slide_plan if s["type"] != "cover")
    writer({
        "phase": 2,
        "step": "remaining_design_dispatch",
        "message": f"나머지 {remaining}장 디자인 생성 (스타일 레퍼런스: {'✓' if cover_ok else '✗'})...",
    })
    result = remaining_design_dispatcher(state)
    writer({
        "phase": 2,
        "step": "remaining_design_dispatch",
        "message": "디자인 분배 완료",
        "done": True,
    })
    return result


async def progress_code_synthesizer(state: PPTState, config) -> dict:
    writer = get_stream_writer()
    designs = state.get("slide_designs", [])
    contents = state.get("slide_contents", [])
    logger.info("[Pipeline] code_synthesizer START - designs: %d, contents: %d, revision: %d",
                len(designs), len(contents), state.get("revision_count", 0))
    for d in designs:
        logger.info("[Pipeline]   design: %s has_image=%s", d["slide_id"], bool(d.get("image_b64")))
    writer({
        "phase": 3,
        "step": "code_synthesizer",
        "message": "3-Pass HTML 합성 중... (레이아웃 → 텍스트 삽입 → 크기 조정)",
    })
    result = await code_synthesizer(state, config)
    count = len(result.get("generated_slides", []))
    logger.info("[Pipeline] code_synthesizer DONE - generated %d slides", count)
    writer({
        "phase": 3,
        "step": "code_synthesizer",
        "message": f"코드 합성 완료: {count}장",
        "done": True,
    })
    return result


def progress_code_assembly(state: PPTState) -> dict:
    writer = get_stream_writer()
    logger.info("[Pipeline] code_assembly START - generated_slides: %d, slide_contents: %d",
                len(state.get("generated_slides", [])), len(state.get("slide_contents", [])))
    writer({"phase": 3, "step": "code_assembly", "message": "HTML 문서 조립 중..."})
    result = code_assembly(state)
    spec_slides = result.get("slide_spec", {}).get("ppt_state", {}).get("presentation", {}).get("slides", [])
    logger.info("[Pipeline] code_assembly DONE - react_code: %d chars, spec slides: %d",
                len(result.get("react_code", "")), len(spec_slides))
    for s in spec_slides:
        logger.info("[Pipeline]   spec slide: %s type=%s content_keys=%s",
                    s.get("slide_id"), s.get("type"), list(s.get("content", {}).keys()))
    writer({"phase": 3, "step": "code_assembly", "message": "HTML 문서 조립 완료", "done": True})
    return result




async def progress_ast_validator(state: PPTState, config) -> dict:
    writer = get_stream_writer()
    writer({"phase": 4, "step": "ast_validator", "message": "AST 검증 중..."})
    result = await ast_validator(state)
    status = result["validation_result"]["status"]
    writer({"phase": 4, "step": "ast_validator", "message": f"AST 검증: {status}", "done": True})
    return result


async def progress_runtime_validator(state: PPTState, config) -> dict:
    writer = get_stream_writer()
    writer({"phase": 4, "step": "runtime_validator", "message": "런타임 검증 중..."})
    result = await runtime_validator(state)
    status = result["validation_result"]["status"]
    writer({
        "phase": 4,
        "step": "runtime_validator",
        "message": f"런타임 검증: {status}",
        "done": True,
    })
    return result


# --- Build Pipeline ---

def build_pipeline():
    """Build the LangGraph StateGraph pipeline.

    Flow:
      scoping
        → web_researcher (Tavily search, enriches research_brief)
          → cover_and_text_dispatcher (Send: all text_generators + cover_design_generator)
            → [text_generator x N] + [cover_design_generator x 1] (parallel)
              → remaining_design_dispatcher (reads cover image, Send: design_generator x N-1)
                → [design_generator x N-1] (parallel, with cover as style reference)
                  → code_synthesizer
                    → code_assembly → ast_validator → runtime_validator → END
    """
    graph = StateGraph(PPTState)

    # Phase 1: Scoping
    graph.add_node("scoping", progress_scoping)

    # Phase 1.5: Web Research (Tavily)
    graph.add_node("web_researcher", progress_web_researcher)

    # Phase 2a: Cover + Text parallel dispatch
    graph.add_node("cover_and_text_dispatcher", progress_cover_and_text_dispatcher)
    graph.add_node("text_generator", text_generator)
    graph.add_node("cover_design_generator", cover_design_generator)

    # Phase 2b: Remaining design dispatch (with cover as reference)
    graph.add_node("remaining_design_dispatcher", progress_remaining_design_dispatcher)
    graph.add_node("design_generator", design_generator)

    # Phase 3: Synthesis + Assembly
    graph.add_node("code_synthesizer", progress_code_synthesizer)
    graph.add_node("code_assembly", progress_code_assembly)


    # Phase 4: Validation
    graph.add_node("ast_validator", progress_ast_validator)
    graph.add_node("runtime_validator", progress_runtime_validator)

    # --- Edges ---

    # Phase 1: Scoping → Web Research → Dispatch
    graph.add_edge(START, "scoping")
    graph.add_edge("scoping", "web_researcher")
    graph.add_edge("web_researcher", "cover_and_text_dispatcher")
    # cover_and_text_dispatcher returns Command(goto=list[Send])

    # Phase 2a: Fan-in after text + cover design complete
    graph.add_edge("text_generator", "remaining_design_dispatcher")
    graph.add_edge("cover_design_generator", "remaining_design_dispatcher")
    # remaining_design_dispatcher returns Command(goto=list[Send]) or Command(goto="code_synthesizer")

    # Phase 2b: Fan-in after remaining designs complete
    graph.add_edge("design_generator", "code_synthesizer")

    # Phase 3: Synthesis -> Assembly -> Validation + PPTX Layout (parallel)
    graph.add_edge("code_synthesizer", "code_assembly")
    graph.add_edge("code_assembly", "ast_validator")

    # Phase 4: Validation chain
    graph.add_conditional_edges("ast_validator", route_ast_result)
    graph.add_conditional_edges("runtime_validator", route_runtime_result)

    # Compile with checkpointer (required for interrupt)
    checkpointer = InMemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Singleton pipeline instance
_pipeline = None


def get_pipeline():
    """Get or create the pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline
