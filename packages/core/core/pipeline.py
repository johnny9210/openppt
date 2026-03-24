"""
LangGraph Pipeline - PPT Code Generation
4 Phases: Preprocessing → Model Inference → Multi-layer Validation

Uses LangGraph v1.0.10 API:
- StateGraph with conditional edges
- Send API for parallel slide generation (via Command(goto=list[Send]))
- interrupt() for human-in-the-loop (inside node functions only)
- get_stream_writer for SSE progress
"""

from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer

from core.state import PPTState
from core.config import MAX_REVISIONS

# Import all nodes
from core.nodes.mode_router import mode_router
from core.nodes.intent_parser import intent_parser
from core.nodes.schema_abstractor import schema_abstractor
from core.nodes.design_system_loader import design_system_loader
from core.nodes.json_validator import json_validator
from core.nodes.slide_dispatcher import slide_dispatcher
from core.nodes.slide_generator import slide_generator
from core.nodes.code_assembly import code_assembly
from core.nodes.ast_validator import ast_validator
from core.nodes.runtime_validator import runtime_validator
from core.nodes.semantic_validator import semantic_validator


# --- Routing functions (must return string node names) ---

def route_after_mode(state: PPTState) -> Literal["intent_parser", "slide_dispatcher"]:
    """Edit mode skips preprocessing — slide_spec already exists in state."""
    if state.get("mode") == "edit":
        return "slide_dispatcher"
    return "intent_parser"


def route_json_validation(state: PPTState) -> Literal["design_system_loader", "intent_parser"]:
    """Route after JSON validation: pass → continue, fail → retry intent_parser."""
    result = state.get("validation_result", {})
    if result.get("status") == "pass":
        return "design_system_loader"
    return "intent_parser"


def route_ast_result(state: PPTState) -> Literal["runtime_validator", "code_assembly"]:
    """AST fail → Code Assembly re-execution (max MAX_REVISIONS retries)."""
    result = state.get("validation_result", {})
    revision_count = state.get("revision_count", 0)
    if result.get("layer") == "ast" and result.get("status") == "fail" and revision_count < MAX_REVISIONS:
        return "code_assembly"
    return "runtime_validator"


def route_runtime_result(state: PPTState) -> Literal["semantic_validator", "slide_dispatcher"]:
    """Runtime fail → re-dispatch slide generation (max MAX_REVISIONS retries)."""
    result = state.get("validation_result", {})
    revision_count = state.get("revision_count", 0)
    if result.get("layer") == "runtime" and result.get("status") == "fail" and revision_count < MAX_REVISIONS:
        return "slide_dispatcher"
    return "semantic_validator"


# --- Semantic decision node (uses interrupt + Command, must be a node) ---

def semantic_decision(state: PPTState) -> Command:
    """
    Post-semantic-validation decision node.
    - pass → END
    - fail + revision_count < MAX → auto regeneration (goto slide_dispatcher)
    - fail + revision_count >= MAX → human-in-the-loop via interrupt()
    """
    result = state.get("validation_result", {})

    if result.get("layer") == "semantic" and result.get("status") == "pass":
        return Command(goto=END)

    revision_count = state.get("revision_count", 0)

    if revision_count >= MAX_REVISIONS:
        # Human-in-the-loop: interrupt() is called inside a node
        decision = interrupt({
            "message": f"{revision_count}회 검증 실패. 계속 재생성하시겠습니까?",
            "validation_result": result,
            "options": ["retry", "approve", "abort"],
        })

        if decision == "approve":
            return Command(goto=END)
        elif decision == "abort":
            return Command(goto=END, update={"validation_result": {
                "layer": "semantic",
                "status": "aborted",
                "reason": "User aborted after max revisions",
            }})
        # retry: fall through to regeneration

    # Auto regeneration: go back to slide_dispatcher
    return Command(goto="slide_dispatcher")


# --- Progress wrapper nodes ---

async def progress_mode_router(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 0, "step": "mode_router", "message": "모드 분석 중..."})
    result = await mode_router(state)
    writer({"phase": 0, "step": "mode_router", "message": f"모드: {result['mode']}", "done": True})
    return result


async def progress_intent_parser(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 1, "step": "intent_parser", "message": "의도 추출 중..."})
    result = await intent_parser(state)
    writer({"phase": 1, "step": "intent_parser", "message": "의도 추출 완료", "done": True})
    return result


async def progress_schema_abstractor(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 1, "step": "schema_abstractor", "message": "PPTState JSON 생성 중..."})
    result = await schema_abstractor(state)
    writer({"phase": 1, "step": "schema_abstractor", "message": "스키마 생성 완료", "done": True})
    return result


def progress_design_system_loader(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 1, "step": "design_system_loader", "message": "Reference Component 로드 중..."})
    result = design_system_loader(state)
    writer({"phase": 1, "step": "design_system_loader", "message": "디자인 시스템 로드 완료", "done": True})
    return result


def progress_json_validator(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 1, "step": "json_validator", "message": "JSON 스키마 검증 중..."})
    result = json_validator(state)
    writer({"phase": 1, "step": "json_validator", "message": "JSON 검증 완료", "done": True})
    return result


def progress_slide_dispatcher(state: PPTState) -> Command:
    writer = get_stream_writer()
    writer({"phase": 2, "step": "slide_dispatcher", "message": "슬라이드 분배 중..."})
    result = slide_dispatcher(state)
    writer({"phase": 2, "step": "slide_dispatcher", "message": "슬라이드 분배 완료", "done": True})
    return result


def progress_code_assembly(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 2, "step": "code_assembly", "message": "코드 조립 중..."})
    result = code_assembly(state)
    writer({"phase": 2, "step": "code_assembly", "message": "코드 조립 완료", "done": True})
    return result


async def progress_ast_validator(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 3, "step": "ast_validator", "message": "AST 검증 중..."})
    result = await ast_validator(state)
    status = result["validation_result"]["status"]
    writer({"phase": 3, "step": "ast_validator", "message": f"AST 검증: {status}", "done": True})
    return result


async def progress_runtime_validator(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 3, "step": "runtime_validator", "message": "런타임 검증 중..."})
    result = await runtime_validator(state)
    status = result["validation_result"]["status"]
    writer({"phase": 3, "step": "runtime_validator", "message": f"런타임 검증: {status}", "done": True})
    return result


async def progress_semantic_validator(state: PPTState) -> dict:
    writer = get_stream_writer()
    writer({"phase": 3, "step": "semantic_validator", "message": "시맨틱 검증 중..."})
    result = await semantic_validator(state)
    status = result["validation_result"]["status"]
    writer({"phase": 3, "step": "semantic_validator", "message": f"시맨틱 검증: {status}", "done": True})
    return result


# --- Build Pipeline ---

def build_pipeline():
    """Build the LangGraph StateGraph pipeline."""
    graph = StateGraph(PPTState)

    # Phase 0: Mode Router
    graph.add_node("mode_router", progress_mode_router)

    # Phase 1: Preprocessing
    graph.add_node("intent_parser", progress_intent_parser)
    graph.add_node("schema_abstractor", progress_schema_abstractor)
    graph.add_node("design_system_loader", progress_design_system_loader)
    graph.add_node("json_validator", progress_json_validator)

    # Phase 2: Model Inference
    # slide_dispatcher returns Command(goto=list[Send]) for fan-out
    graph.add_node("slide_dispatcher", progress_slide_dispatcher)
    graph.add_node("slide_generator", slide_generator)
    graph.add_node("code_assembly", progress_code_assembly)

    # Phase 3: Multi-layer Validation
    graph.add_node("ast_validator", progress_ast_validator)
    graph.add_node("runtime_validator", progress_runtime_validator)
    graph.add_node("semantic_validator", progress_semantic_validator)
    # semantic_decision handles interrupt() + Command routing
    graph.add_node("semantic_decision", semantic_decision)

    # --- Edges ---

    # Phase 0 → conditional routing based on mode
    graph.add_edge(START, "mode_router")
    # Edit mode skips preprocessing (slide_spec already in state)
    graph.add_conditional_edges("mode_router", route_after_mode)
    graph.add_edge("intent_parser", "schema_abstractor")
    graph.add_edge("schema_abstractor", "json_validator")

    # JSON validation routing
    graph.add_conditional_edges("json_validator", route_json_validation)

    # Phase 1 → Phase 2
    graph.add_edge("design_system_loader", "slide_dispatcher")
    # slide_dispatcher returns Command(goto=list[Send]) — no outgoing edge needed

    # Fan-in: all slide_generator instances must complete before code_assembly
    graph.add_edge("slide_generator", "code_assembly")

    # Phase 2 → Phase 3: Validation chain
    graph.add_edge("code_assembly", "ast_validator")
    graph.add_conditional_edges("ast_validator", route_ast_result)
    graph.add_conditional_edges("runtime_validator", route_runtime_result)

    # Semantic validator → decision node (handles Command routing)
    graph.add_edge("semantic_validator", "semantic_decision")
    # semantic_decision returns Command(goto=END|"slide_dispatcher") — no outgoing edge needed

    # InMemorySaver — sessions lost on restart, but edit endpoint handles 404 gracefully
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
