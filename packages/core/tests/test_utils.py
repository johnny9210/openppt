"""Tests for core.utils — robust_parse_json and retry_async."""

import asyncio
import pytest
from core.utils import robust_parse_json, LLMJSONParseError, retry_async


# ─── robust_parse_json ──────────────────────────────────────────────


class TestRobustParseJSON:
    """Strategy 1: Direct JSON.loads"""

    def test_direct_valid_json(self):
        result = robust_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_direct_valid_array(self):
        result = robust_parse_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_direct_nested_json(self):
        result = robust_parse_json('{"a": {"b": {"c": 1}}}')
        assert result == {"a": {"b": {"c": 1}}}


class TestFenceStripping:
    """Strategy 2: Strip markdown code fences"""

    def test_json_fence(self):
        text = '```json\n{"key": "value"}\n```'
        assert robust_parse_json(text) == {"key": "value"}

    def test_plain_fence(self):
        text = '```\n{"key": "value"}\n```'
        assert robust_parse_json(text) == {"key": "value"}

    def test_fence_with_whitespace(self):
        text = '  ```json\n  {"key": "value"}\n  ```  '
        assert robust_parse_json(text) == {"key": "value"}

    def test_JSON_uppercase_fence(self):
        text = '```JSON\n{"key": "value"}\n```'
        assert robust_parse_json(text) == {"key": "value"}


class TestBalancedExtraction:
    """Strategy 3: Find first balanced { } or [ ]"""

    def test_json_with_leading_text(self):
        text = 'Here is the result:\n{"key": "value"}'
        assert robust_parse_json(text) == {"key": "value"}

    def test_json_with_trailing_text(self):
        text = '{"key": "value"}\nHope this helps!'
        assert robust_parse_json(text) == {"key": "value"}

    def test_json_surrounded_by_text(self):
        text = 'The JSON is:\n{"mode": "create", "target_slide_id": null}\nLet me know.'
        result = robust_parse_json(text)
        assert result == {"mode": "create", "target_slide_id": None}

    def test_nested_braces(self):
        text = 'Response: {"a": {"b": 1}, "c": [1, {"d": 2}]}'
        result = robust_parse_json(text)
        assert result["a"]["b"] == 1
        assert result["c"][1]["d"] == 2

    def test_array_extraction(self):
        text = 'Here: [{"a": 1}, {"b": 2}] done'
        result = robust_parse_json(text)
        assert len(result) == 2

    def test_strings_with_braces(self):
        """Braces inside string values should not confuse the parser."""
        text = 'Result: {"content": "use { and } carefully"}'
        result = robust_parse_json(text)
        assert result["content"] == "use { and } carefully"


class TestTrailingCommas:
    """Strategy 4: Remove trailing commas"""

    def test_trailing_comma_object(self):
        text = '{"key": "value", "extra": 1,}'
        result = robust_parse_json(text)
        assert result == {"key": "value", "extra": 1}

    def test_trailing_comma_array(self):
        text = '[1, 2, 3,]'
        result = robust_parse_json(text)
        assert result == [1, 2, 3]

    def test_trailing_comma_nested(self):
        text = '{"items": [1, 2,], "nested": {"a": 1,},}'
        result = robust_parse_json(text)
        assert result["items"] == [1, 2]
        assert result["nested"]["a"] == 1

    def test_trailing_comma_in_fence(self):
        text = '```json\n{"key": "value",}\n```'
        result = robust_parse_json(text)
        assert result == {"key": "value"}


class TestParseFailure:
    """All strategies fail → LLMJSONParseError"""

    def test_no_json_at_all(self):
        with pytest.raises(LLMJSONParseError):
            robust_parse_json("This is just plain text with no JSON.")

    def test_incomplete_json(self):
        with pytest.raises(LLMJSONParseError):
            robust_parse_json('{"key": ')

    def test_empty_string(self):
        with pytest.raises(LLMJSONParseError):
            robust_parse_json("")

    def test_error_contains_attempts(self):
        with pytest.raises(LLMJSONParseError) as exc_info:
            robust_parse_json("no json here")
        assert len(exc_info.value.attempts) > 0
        assert exc_info.value.raw_text == "no json here"


# ─── retry_async ────────────────────────────────────────────────────


class TestRetryAsync:
    def test_success_on_first_try(self):
        call_count = 0

        @retry_async(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = asyncio.get_event_loop().run_until_complete(succeed())
        assert result == "ok"
        assert call_count == 1

    def test_success_after_retries(self):
        call_count = 0

        @retry_async(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        result = asyncio.get_event_loop().run_until_complete(fail_twice())
        assert result == "ok"
        assert call_count == 3

    def test_failure_after_max_retries(self):
        call_count = 0

        @retry_async(max_attempts=2, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            asyncio.get_event_loop().run_until_complete(always_fail())
        assert call_count == 2

    def test_non_retryable_exception_not_retried(self):
        call_count = 0

        @retry_async(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            asyncio.get_event_loop().run_until_complete(raise_type_error())
        assert call_count == 1
