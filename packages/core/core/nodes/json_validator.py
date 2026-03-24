"""
Phase 1-D: JSON Schema Validator
Validates PPTState JSON against the schema.
On failure, routes back to intent_parser (max 2 retries).
"""

import json
from pathlib import Path

import jsonschema
from core.state import PPTState

SCHEMA_PATH = Path(__file__).parent.parent.parent / "shared" / "schemas" / "ppt_state.schema.json"


def json_validator(state: PPTState) -> dict:
    """Validate slide_spec against JSON Schema."""
    if SCHEMA_PATH.exists():
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        try:
            jsonschema.validate(state["slide_spec"], schema)
        except jsonschema.ValidationError as e:
            return {
                "validation_result": {
                    "layer": "json_schema",
                    "status": "fail",
                    "error": str(e.message),
                    "path": list(e.absolute_path),
                },
            }

    return {
        "validation_result": {
            "layer": "json_schema",
            "status": "pass",
        },
    }
