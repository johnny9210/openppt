"""
Phase 1-C: Design System Loader
Loads Reference Components based on slide types.
LLM generates code based on these references (slot filling, not free generation).
"""

import json
from pathlib import Path
from core.state import PPTState

DESIGN_SYSTEM_DIR = Path(__file__).parent.parent.parent / "design-system" / "templates"


def design_system_loader(state: PPTState) -> dict:
    """Load reference components for each slide type in the spec."""
    slides = state["slide_spec"]["ppt_state"]["presentation"]["slides"]
    reference_components = {}

    for slide in slides:
        slide_type = slide["type"]
        if slide_type in reference_components:
            continue

        ref_path = DESIGN_SYSTEM_DIR / slide_type / "reference.jsx"
        if ref_path.exists():
            reference_components[slide_type] = ref_path.read_text(encoding="utf-8")

    return {"reference_components": reference_components}
