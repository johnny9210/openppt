"""
PPTState - LangGraph State Definition
Follows the assignment report's state structure exactly.
"""

from typing import Literal, TypedDict, Annotated
import operator


class PPTState(TypedDict):
    """LangGraph state for PPT code generation pipeline."""

    # Phase 0: Input
    user_request: str
    mode: Literal["create", "edit"]
    target_slide_id: str | None

    # Phase 1: Preprocessing
    slide_spec: dict  # Validated PPTState JSON
    reference_components: dict  # {slide_type: reference_code}

    # Phase 2: Generation
    generated_slides: Annotated[list[dict], operator.add]  # Parallel slide results
    react_code: str

    # Phase 3: Validation
    validation_result: dict
    revision_count: int
    error_log: Annotated[list[dict], operator.add]  # Revision history


class SlideGeneratorState(TypedDict):
    """State for individual slide generation nodes (used with Send API)."""

    slide_spec: dict
    slide: dict  # Single slide from slides array
    reference_component: str
    generated_code: str
    fix_prompt: str  # Semantic validation feedback for retries
    edit_request: str  # User's edit instruction (edit mode only)
