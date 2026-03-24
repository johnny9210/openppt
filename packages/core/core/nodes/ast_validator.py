"""
Phase 3-A: AST Validator
Validates JSX syntax, import completeness, and tag pairs using Babel Parser.
Calls the validator microservice.
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
async def _call_ast_validator(code: str) -> dict:
    """POST to the AST validator endpoint with retry support."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{VALIDATOR_URL}/validate/ast",
            json={"code": code},
        )
        resp.raise_for_status()
        return resp.json()


async def ast_validator(state: PPTState) -> dict:
    """Validate React code AST via validator service."""
    try:
        result = await _call_ast_validator(state["react_code"])
    except Exception as exc:
        logger.error(
            "AST validator service unavailable after retries: %s", exc
        )
        return {
            "validation_result": {
                "layer": "ast",
                "status": "fail",
                "errors": [
                    f"Validator service unavailable: {exc}"
                ],
            },
            "revision_count": state.get("revision_count", 0) + 1,
        }

    update: dict = {
        "validation_result": {
            "layer": "ast",
            "status": "pass" if result["valid"] else "fail",
            "errors": result.get("errors", []),
        },
    }
    if not result["valid"]:
        update["revision_count"] = state.get("revision_count", 0) + 1
    return update
