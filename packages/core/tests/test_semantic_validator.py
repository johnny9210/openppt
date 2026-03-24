"""Tests for semantic_validator — extract_slide_component and slot classification."""

import pytest
from core.nodes.semantic_validator import (
    extract_slide_component,
    extract_slots,
    _classify_importance,
)


# ─── _classify_importance ───────────────────────────────────────────


class TestClassifyImportance:
    def test_critical_slots(self):
        assert _classify_importance("chart_renderer") == "critical"
        assert _classify_importance("grid_layout") == "critical"
        assert _classify_importance("list_layout") == "critical"

    def test_major_slots(self):
        assert _classify_importance("severity_badge") == "major"
        assert _classify_importance("metric_color") == "major"
        assert _classify_importance("bar_highlight") == "major"

    def test_minor_slots(self):
        assert _classify_importance("title_size") == "minor"
        assert _classify_importance("subtitle") == "minor"
        assert _classify_importance("background") == "minor"


# ─── extract_slots ──────────────────────────────────────────────────


class TestExtractSlots:
    def test_extract_multiple_slots(self):
        spec = {
            "ppt_state": {
                "presentation": {
                    "slides": [
                        {
                            "slide_id": "slide_001",
                            "type": "cover",
                            "slots": {
                                "title_size": "제목 글자 크기 조정",
                                "background": "배경색 설정",
                            },
                        },
                        {
                            "slide_id": "slide_003",
                            "type": "data_visualization",
                            "slots": {
                                "chart_renderer": "차트 타입에 따라 렌더링",
                            },
                        },
                    ]
                }
            }
        }
        slots = extract_slots(spec)
        assert len(slots) == 3
        keys = {s.slot_key for s in slots}
        assert keys == {"title_size", "background", "chart_renderer"}

    def test_empty_slots(self):
        spec = {
            "ppt_state": {
                "presentation": {
                    "slides": [
                        {"slide_id": "slide_001", "type": "cover", "slots": {}},
                    ]
                }
            }
        }
        slots = extract_slots(spec)
        assert len(slots) == 0

    def test_no_slots_key(self):
        spec = {
            "ppt_state": {
                "presentation": {
                    "slides": [
                        {"slide_id": "slide_001", "type": "cover"},
                    ]
                }
            }
        }
        slots = extract_slots(spec)
        assert len(slots) == 0


# ─── extract_slide_component ────────────────────────────────────────


class TestExtractSlideComponent:
    def test_section_marker_extraction(self):
        """PRIMARY: Uses section markers to extract component + sub-components."""
        code = """import { useState } from "react";

// ── [slide_001] cover ─────────────
const CoverSlide = ({ content }) => {
  return <div>{content.title}</div>;
};

// ── [slide_003] data_visualization ─────────────
const DataVizSlide = ({ content }) => {
  return <BarChartRenderer data={content.data} />;
};

const BarChartRenderer = ({ data }) => {
  return <div>chart</div>;
};

// ── SlideFactory: type → 컴포넌트 dispatch ────────────
const SlideFactory = ({ slide }) => null;

export default function Presentation({ spec }) {
  return <div />;
}"""
        result = extract_slide_component(code, "slide_003", "data_visualization")
        # Should include BOTH DataVizSlide AND BarChartRenderer
        assert "DataVizSlide" in result
        assert "BarChartRenderer" in result
        # Should NOT include CoverSlide
        assert "CoverSlide" not in result
        # Should NOT include SlideFactory
        assert "SlideFactory" not in result

    def test_section_marker_first_slide(self):
        code = """// ── [slide_001] cover ─────────────
const CoverSlide = ({ content }) => <div />;

// ── [slide_002] table_of_contents ─────────────
const TocSlide = ({ content }) => <div />;"""

        result = extract_slide_component(code, "slide_001", "cover")
        assert "CoverSlide" in result
        assert "TocSlide" not in result

    def test_fallback_regex_when_no_markers(self):
        """FALLBACK: When section markers are absent, uses const-based regex."""
        code = """const CoverSlide = ({ content }) => <div>{content.title}</div>;

const TocSlide = ({ content }) => <div>toc</div>;

export default function Presentation({ spec }) {
  return <div />;
}"""
        result = extract_slide_component(code, "slide_001", "cover")
        assert "CoverSlide" in result

    def test_unknown_type_returns_full_code(self):
        code = "const Foo = () => <div />;"
        result = extract_slide_component(code, "slide_001", "unknown_type")
        assert result == code

    def test_last_section_before_export(self):
        code = """// ── [slide_006] action_plan ─────────────
const ActionPlanSlide = ({ content }) => <div>plan</div>;

export default function Presentation({ spec }) {
  return <div />;
}"""
        result = extract_slide_component(code, "slide_006", "action_plan")
        assert "ActionPlanSlide" in result
        assert "export default" not in result
