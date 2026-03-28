"""
Phase 3-B: Runtime Validator (HTML Edition)
Validates HTML slide count and structural integrity.

Replaces the React sandbox rendering approach — HTML doesn't have
the same runtime failure modes as JSX (no compilation, no component
mounting errors). We check slide count match and basic structure.
"""

import logging
import re

from core.state import PPTState

logger = logging.getLogger(__name__)


async def runtime_validator(state: PPTState) -> dict:
    """Validate HTML presentation structure and slide count."""
    html_code = state.get("react_code", "")
    spec_slides = state["slide_spec"]["ppt_state"]["presentation"]["slides"]
    expected_slides = len(spec_slides)
    expected_ids = {s.get("slide_id") for s in spec_slides}

    logger.info(
        "[RuntimeValidator] expected_slides=%d, slide_ids=%s",
        expected_slides,
        sorted(expected_ids),
    )

    errors = []

    # Count slide containers
    container_matches = re.findall(
        r'class="slide-container[^"]*\b(slide_\d+)\b', html_code
    )
    actual_count = len(container_matches)
    found_ids = set(container_matches)

    if actual_count != expected_slides:
        errors.append({
            "type": "slide_count_mismatch",
            "message": f"Expected {expected_slides} slides, found {actual_count}",
        })

    # Check that each expected slide_id has a container
    missing_ids = expected_ids - found_ids
    if missing_ids:
        errors.append({
            "type": "missing_slides",
            "message": f"Missing slide containers for: {', '.join(sorted(missing_ids))}",
        })

    # Check that the document has basic structure
    if "<!DOCTYPE html>" not in html_code and "<html" not in html_code:
        errors.append({
            "type": "incomplete_document",
            "message": "HTML document is missing <!DOCTYPE html> or <html> tag",
        })

    if "<script>" not in html_code:
        errors.append({
            "type": "missing_navigation",
            "message": "No <script> block found — navigation may be missing",
        })

    is_valid = len(errors) == 0

    if is_valid:
        logger.info("[RuntimeValidator] PASS - %d slides found", actual_count)
    else:
        for err in errors:
            logger.error(
                "[RuntimeValidator] FAIL: type=%s message=%s",
                err.get("type", "?"),
                err.get("message", "?"),
            )

    update: dict = {
        "validation_result": {
            "layer": "runtime",
            "status": "pass" if is_valid else "fail",
            "errors": errors,
        },
    }
    if not is_valid:
        update["revision_count"] = state.get("revision_count", 0) + 1
    return update
