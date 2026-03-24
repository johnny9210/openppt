"""Tests for semantic_validator — extract_slide_component and content key extraction."""

import pytest
from core.nodes.semantic_validator import (
    extract_slide_component,
    _extract_content_keys,
)


# ─── _extract_content_keys ──────────────────────────────────────────


class TestExtractContentKeys:
    def test_extracts_critical_keys(self):
        slide = {
            "slide_id": "slide_001",
            "type": "cover",
            "content": {
                "title": "테스트 제목",
                "subtitle": "부제목",
            },
        }
        keys = _extract_content_keys(slide)
        assert len(keys) == 2
        titles = [k for k in keys if k["key"] == "title"]
        assert len(titles) == 1
        assert titles[0]["importance"] == "critical"

    def test_skips_empty_values(self):
        slide = {
            "slide_id": "slide_001",
            "type": "cover",
            "content": {
                "title": "테스트",
                "subtitle": "",
                "items": [],
                "extra": None,
            },
        }
        keys = _extract_content_keys(slide)
        assert len(keys) == 1
        assert keys[0]["key"] == "title"

    def test_empty_content(self):
        slide = {"slide_id": "slide_001", "type": "cover", "content": {}}
        keys = _extract_content_keys(slide)
        assert len(keys) == 0


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
