"""
PPTState - LangGraph State Definition
Architecture: Scoping -> Parallel (Text + Design) -> Synthesis -> Validation
"""

from typing import TypedDict, Annotated
import operator


class PPTState(TypedDict):
    """LangGraph state for PPT code generation pipeline."""

    # Phase 0: Input
    user_request: str

    # Phase 1: Scoping (dee_research pattern)
    research_brief: dict

    # Phase 2: Parallel Generation
    slide_contents: Annotated[list[dict], operator.add]   # Text branch
    slide_designs: Annotated[list[dict], operator.add]     # Design branch (images)
    cover_design_image: str  # Cover slide image for style reference

    # Phase 3: Synthesis
    generated_slides: Annotated[list[dict], operator.add]  # Vision -> code
    react_code: str

    # Phase 3-B: PPTX Layout (React → PptxGenJS JSON, parallel with validation)
    pptx_layouts: Annotated[list[dict], operator.add]

    # Phase 4: Validation
    slide_spec: dict  # backward-compatible spec for validators
    validation_result: dict
    revision_count: int
    error_log: Annotated[list[dict], operator.add]


class TextGeneratorState(TypedDict):
    """State for text generation Send nodes."""

    slide_plan: dict
    research_brief: dict


class DesignGeneratorState(TypedDict):
    """State for design generation Send nodes."""

    slide_plan: dict
    research_brief: dict
    reference_image_b64: str  # Cover image for style consistency
