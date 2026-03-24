"""Tests for slide_dispatcher — _find_failed_slide_ids and _build_per_slide_fix_prompt.

Uses sys.modules mock to avoid importing langgraph (not installed in test env).
"""

import sys
import types
import pytest

# Mock langgraph.types before importing slide_dispatcher
_mock_lg_types = types.ModuleType("langgraph.types")
_mock_lg_types.Send = type("Send", (), {"__init__": lambda self, *a, **kw: None})
_mock_lg_types.Command = type("Command", (), {"__init__": lambda self, *a, **kw: None})
sys.modules.setdefault("langgraph", types.ModuleType("langgraph"))
sys.modules.setdefault("langgraph.types", _mock_lg_types)

from core.nodes.slide_dispatcher import (
    _find_failed_slide_ids,
    _build_per_slide_fix_prompt,
)


# ─── _find_failed_slide_ids ─────────────────────────────────────────


class TestFindFailedSlideIds:
    def test_single_failed_slide(self):
        slides = [
            {"slide_id": "slide_001", "slots": {"title_size": "...", "background": "..."}},
            {"slide_id": "slide_003", "slots": {"chart_renderer": "...", "bar_highlight": "..."}},
            {"slide_id": "slide_005", "slots": {"severity_badge": "..."}},
        ]
        missing_slots = ["chart_renderer"]
        result = _find_failed_slide_ids(slides, missing_slots)
        assert result == {"slide_003"}

    def test_multiple_failed_slides(self):
        slides = [
            {"slide_id": "slide_001", "slots": {"title_size": "..."}},
            {"slide_id": "slide_003", "slots": {"chart_renderer": "..."}},
            {"slide_id": "slide_005", "slots": {"severity_badge": "..."}},
        ]
        missing_slots = ["chart_renderer", "severity_badge"]
        result = _find_failed_slide_ids(slides, missing_slots)
        assert result == {"slide_003", "slide_005"}

    def test_no_missing_slots(self):
        slides = [
            {"slide_id": "slide_001", "slots": {"title_size": "..."}},
        ]
        result = _find_failed_slide_ids(slides, [])
        assert result == set()

    def test_slot_in_multiple_slides(self):
        """If the same slot name exists in multiple slides, all are flagged."""
        slides = [
            {"slide_id": "slide_001", "slots": {"grid_layout": "..."}},
            {"slide_id": "slide_004", "slots": {"grid_layout": "..."}},
        ]
        missing_slots = ["grid_layout"]
        result = _find_failed_slide_ids(slides, missing_slots)
        assert result == {"slide_001", "slide_004"}

    def test_no_slots_key(self):
        slides = [
            {"slide_id": "slide_001"},
        ]
        result = _find_failed_slide_ids(slides, ["chart_renderer"])
        assert result == set()


# ─── _build_per_slide_fix_prompt ─────────────────────────────────────


class TestBuildPerSlideFixPrompt:
    SAMPLE_FIX_PROMPT = """이전에 생성한 React 코드에서 아래 슬롯이 누락되었습니다.
Reference Component를 다시 참고하여 누락된 슬롯만 추가하세요.

[누락된 슬롯 목록]
- [slide_003] 'chart_renderer' 슬롯 누락.
  지시사항: chart_type에 따라 차트 컴포넌트 선택
  Reference Component의 해당 슬롯 위치를 참고하여 반드시 구현할 것.
- [slide_005] 'severity_badge' 슬롯 누락.
  지시사항: severity에 따라 뱃지 색상 적용
  Reference Component의 해당 슬롯 위치를 참고하여 반드시 구현할 것.

[원칙]
- 누락된 슬롯이 있는 컴포넌트만 수정할 것
- Reference Component의 전체 구조는 변경하지 말 것
- 슬롯 지시사항의 의도를 코드로 정확히 반영할 것
"""

    def test_filter_to_slide_003(self):
        result = _build_per_slide_fix_prompt("slide_003", self.SAMPLE_FIX_PROMPT)
        assert "[slide_003]" in result
        assert "chart_renderer" in result
        # Should NOT contain slide_005 entry
        assert "[slide_005]" not in result
        # Should contain header and footer
        assert "누락된 슬롯 목록" in result
        assert "원칙" in result

    def test_filter_to_slide_005(self):
        result = _build_per_slide_fix_prompt("slide_005", self.SAMPLE_FIX_PROMPT)
        assert "[slide_005]" in result
        assert "severity_badge" in result
        assert "[slide_003]" not in result

    def test_no_matching_slide_returns_full(self):
        """If no entries match the slide_id, return the full prompt as fallback."""
        result = _build_per_slide_fix_prompt("slide_999", self.SAMPLE_FIX_PROMPT)
        # Should get the full prompt since no matching entries were found
        assert "slide_003" in result
        assert "slide_005" in result

    def test_empty_fix_prompt(self):
        result = _build_per_slide_fix_prompt("slide_003", "")
        assert result == ""

    def test_none_fix_prompt(self):
        result = _build_per_slide_fix_prompt("slide_003", None)
        assert result == ""
