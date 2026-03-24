"""
Shared utilities for the core pipeline.

- robust_parse_json: Multi-strategy JSON parser for LLM responses
- retry_async: Async retry decorator with exponential backoff
"""

import asyncio
import json
import logging
import re
from functools import wraps

logger = logging.getLogger(__name__)


class LLMJSONParseError(Exception):
    """Raised when all JSON parsing strategies fail on LLM output."""

    def __init__(self, raw_text: str, attempts: list[str]):
        self.raw_text = raw_text
        self.attempts = attempts
        summary = "; ".join(attempts)
        super().__init__(
            f"Failed to parse JSON from LLM response. Tried: {summary}. "
            f"Raw text (first 200 chars): {raw_text[:200]!r}"
        )


def robust_parse_json(content: str) -> dict | list:
    """Parse JSON from an LLM response using multiple strategies.

    Strategies (tried in order):
    1. Direct json.loads
    2. Strip markdown code fences then json.loads
    3. Find first { or [ and matching closing } or ], then json.loads
    4. Same as (3) but also remove trailing commas before } and ]

    Returns the parsed object on success.
    Raises LLMJSONParseError with diagnostic info on failure.
    """
    attempts: list[str] = []

    # --- Strategy 1: direct parse ---
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        attempts.append(f"direct: {exc}")

    # --- Strategy 2: strip markdown fences ---
    stripped = content.strip()
    # Remove opening ```json or ``` and closing ```
    cleaned = re.sub(
        r"^```(?:json|JSON)?\s*\n?", "", stripped
    )
    cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    if cleaned != stripped:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            attempts.append(f"fence-strip: {exc}")
    else:
        attempts.append("fence-strip: no fences detected, skipped")

    # --- Strategy 3: find first/last balanced JSON object or array ---
    text = cleaned  # work on fence-stripped version
    json_str = _extract_json_substring(text)
    if json_str is not None:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            attempts.append(f"extract-balanced: {exc}")

        # --- Strategy 4: remove trailing commas and retry ---
        no_trailing = _remove_trailing_commas(json_str)
        if no_trailing != json_str:
            try:
                return json.loads(no_trailing)
            except json.JSONDecodeError as exc:
                attempts.append(f"trailing-commas: {exc}")
        else:
            attempts.append("trailing-commas: none found, skipped")
    else:
        attempts.append("extract-balanced: no JSON structure found")
        attempts.append("trailing-commas: skipped (no structure)")

    raise LLMJSONParseError(content, attempts)


def _extract_json_substring(text: str) -> str | None:
    """Find the first top-level JSON object or array in *text*.

    Returns the substring from the opening brace/bracket to its matching
    closing brace/bracket, or None if not found.
    """
    openers = {"{": "}", "[": "]"}

    # Find the first { or [
    start = None
    for i, ch in enumerate(text):
        if ch in openers:
            start = i
            break

    if start is None:
        return None

    target_close = openers[text[start]]
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            if in_string:
                escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == text[start]:
            depth += 1
        elif ch == target_close:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # Unbalanced -- return everything from start to end as best effort
    return text[start:]


def _remove_trailing_commas(json_str: str) -> str:
    """Remove trailing commas before } and ] (common LLM mistake)."""
    return re.sub(r",\s*([}\]])", r"\1", json_str)


# ---------------------------------------------------------------------------
# Retry decorator for async functions (used by validator service calls)
# ---------------------------------------------------------------------------

def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
):
    """Decorator factory for async retry with exponential backoff.

    Usage::

        @retry_async(max_attempts=3, base_delay=1.0,
                     retryable_exceptions=(httpx.HTTPStatusError, httpx.ConnectError))
        async def call_service(...):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = base_delay * (backoff_factor ** (attempt - 1))
                        logger.warning(
                            "%s attempt %d/%d failed (%s). "
                            "Retrying in %.1fs ...",
                            fn.__name__,
                            attempt,
                            max_attempts,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts. Last error: %s",
                            fn.__name__,
                            max_attempts,
                            exc,
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
