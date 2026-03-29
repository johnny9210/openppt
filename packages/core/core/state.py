"""
PPTState - LangGraph State Definition
Architecture: Scoping -> Web Research -> Parallel (Text + Design) -> Synthesis -> Validation
"""

from typing import TypedDict, Annotated
import operator


def _merge_token_usage(left: dict, right: dict) -> dict:
    """Reducer: accumulate token usage across nodes (including parallel Send nodes)."""
    if not left:
        return right or {}
    if not right:
        return left
    return {
        "input_tokens": left.get("input_tokens", 0) + right.get("input_tokens", 0),
        "output_tokens": left.get("output_tokens", 0) + right.get("output_tokens", 0),
    }


class PPTState(TypedDict):
    """LangGraph state for PPT code generation pipeline."""

    # Phase 0: Input
    user_request: str

    # Phase 1: Scoping (deep_research pattern)
    research_brief: dict

    # Phase 2: Parallel Generation
    slide_contents: Annotated[list[dict], operator.add]   # Text branch
    slide_designs: Annotated[list[dict], operator.add]     # Design branch (images)
    cover_design_image: str  # Cover slide image for style reference

    # Phase 3: Synthesis
    generated_slides: Annotated[list[dict], operator.add]  # Vision -> code
    react_code: str

    # Phase 4: Validation
    slide_spec: dict  # backward-compatible spec for validators
    validation_result: dict
    revision_count: int

    # Cross-cutting: Token tracking (accumulated across all nodes)
    token_usage: Annotated[dict, _merge_token_usage]


class TextGeneratorState(TypedDict):
    """State for text generation Send nodes."""

    slide_plan: dict
    research_brief: dict


class DesignGeneratorState(TypedDict):
    """State for design generation Send nodes."""

    slide_plan: dict
    research_brief: dict
    reference_image_b64: str  # Cover image for style consistency
