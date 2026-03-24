"""
Phase 3-B: Runtime Validator
Validates by rendering React code in a sandboxed environment.
Checks for runtime errors and slide count match.
"""

import logging

import httpx
from core.config import VALIDATOR_URL
from core.state import PPTState
from core.utils import retry_async

logger = logging.getLogger(__name__)

# Retryable httpx exceptions: connection errors and 5xx server errors
_RETRYABLE = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


@retry_async(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,
    retryable_exceptions=_RETRYABLE,
)
async def _call_runtime_validator(code: str, expected_slide_count: int, spec: dict) -> dict:
    """POST to the runtime validator endpoint with retry support."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{VALIDATOR_URL}/validate/runtime",
            json={
                "code": code,
                "expected_slide_count": expected_slide_count,
                "spec": spec,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def runtime_validator(state: PPTState) -> dict:
    """Validate React code runtime via validator service sandbox."""
    spec_slides = state["slide_spec"]["ppt_state"]["presentation"]["slides"]
    expected_slides = len(spec_slides)
    logger.info("[RuntimeValidator] expected_slides=%d, slide_ids=%s",
                expected_slides, [s.get("slide_id") for s in spec_slides])
    logger.info("[RuntimeValidator] react_code length=%d", len(state.get("react_code", "")))

    try:
        result = await _call_runtime_validator(
            state["react_code"], expected_slides, state["slide_spec"]
        )
    except Exception as exc:
        logger.error(
            "Runtime validator service unavailable after retries: %s", exc
        )
        return {
            "validation_result": {
                "layer": "runtime",
                "status": "fail",
                "errors": [
                    f"Validator service unavailable: {exc}"
                ],
            },
            "revision_count": state.get("revision_count", 0) + 1,
        }

    if result["valid"]:
        logger.info("[RuntimeValidator] PASS")
    else:
        for err in result.get("errors", []):
            logger.error("[RuntimeValidator] FAIL: type=%s message=%s",
                         err.get("type", "?"), err.get("message", "?")[:300])

    update: dict = {
        "validation_result": {
            "layer": "runtime",
            "status": "pass" if result["valid"] else "fail",
            "errors": result.get("errors", []),
        },
    }
    if not result["valid"]:
        update["revision_count"] = state.get("revision_count", 0) + 1
    return update
