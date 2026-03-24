"""Tests for core.nodes.code_assembly — import/THEME removal, component reordering."""

import pytest
from core.nodes.code_assembly import (
    _remove_imports,
    _remove_theme_declaration,
    _reorder_components,
    _clean_slide_code,
    _extract_component_names,
    _split_components,
    code_assembly,
    TYPE_COMPONENT_MAP,
)


# ─── _remove_imports ────────────────────────────────────────────────


class TestRemoveImports:
    def test_single_line_named_import(self):
        code = 'import { useState } from "react";\nconst x = 1;'
        result = _remove_imports(code)
        assert "import" not in result
        assert "const x = 1;" in result

    def test_single_line_default_import(self):
        code = 'import React from "react";\nconst x = 1;'
        result = _remove_imports(code)
        assert "import" not in result
        assert "const x = 1;" in result

    def test_namespace_import(self):
        code = 'import * as React from "react";\nconst x = 1;'
        result = _remove_imports(code)
        assert "import" not in result

    def test_side_effect_import(self):
        code = 'import "polyfill";\nconst x = 1;'
        result = _remove_imports(code)
        assert "import" not in result

    def test_multi_line_import(self):
        code = '''import {
  BarChart,
  Bar,
  Cell
} from "recharts";
const x = 1;'''
        result = _remove_imports(code)
        assert "import" not in result
        assert "BarChart" not in result
        assert "Bar" not in result
        assert "const x = 1;" in result

    def test_multiple_imports(self):
        code = '''import { useState } from "react";
import {
  BarChart,
  Bar
} from "recharts";
import styles from "./styles.css";

const MyComponent = () => <div />;'''
        result = _remove_imports(code)
        assert "import" not in result
        assert "MyComponent" in result

    def test_no_imports(self):
        code = "const x = 1;\nconst y = 2;"
        result = _remove_imports(code)
        assert result == code

    def test_type_import(self):
        code = 'import type { FC } from "react";\nconst x = 1;'
        result = _remove_imports(code)
        assert "import" not in result


# ─── _remove_theme_declaration ──────────────────────────────────────


class TestRemoveThemeDeclaration:
    def test_simple_flat_theme(self):
        code = '''const THEME = {
  primary: "#1a1a2e",
  accent: "#e94560",
};
const x = 1;'''
        result = _remove_theme_declaration(code)
        assert "THEME" not in result
        assert "const x = 1;" in result

    def test_nested_theme(self):
        """CRITICAL: The old regex couldn't handle nested braces."""
        code = '''const THEME = {
  primary: "#1a1a2e",
  derived: {
    light: "#2a2a3e",
    dark: "#0a0a1e"
  },
  accent: "#e94560"
};
const x = 1;'''
        result = _remove_theme_declaration(code)
        assert "THEME" not in result
        assert "derived" not in result
        assert "const x = 1;" in result

    def test_deeply_nested_theme(self):
        code = '''const THEME = {
  a: { b: { c: { d: "#000" } } }
};
const x = 1;'''
        result = _remove_theme_declaration(code)
        assert "THEME" not in result

    def test_theme_with_strings_containing_braces(self):
        code = '''const THEME = {
  primary: "color{test}",
  accent: "#e94560"
};
const x = 1;'''
        result = _remove_theme_declaration(code)
        assert "THEME" not in result

    def test_no_theme(self):
        code = "const x = 1;\nconst y = 2;"
        result = _remove_theme_declaration(code)
        assert result == code

    def test_single_line_theme(self):
        code = 'const THEME = { primary: "#1a1a2e" };\nconst x = 1;'
        result = _remove_theme_declaration(code)
        assert "THEME" not in result

    def test_multiple_theme_declarations(self):
        code = '''const THEME = { a: 1 };
const other = 2;
const THEME = { b: 2 };
const x = 1;'''
        result = _remove_theme_declaration(code)
        assert "THEME" not in result
        assert "const other = 2;" in result
        assert "const x = 1;" in result


# ─── _extract_component_names ───────────────────────────────────────


class TestExtractComponentNames:
    def test_const_arrow(self):
        code = "const MyComponent = () => <div />;"
        names = _extract_component_names(code)
        assert "MyComponent" in names

    def test_function_declaration(self):
        code = "function MyComponent() { return <div />; }"
        names = _extract_component_names(code)
        assert "MyComponent" in names

    def test_const_function_expression(self):
        code = "const MyComponent = function() { return <div />; }"
        names = _extract_component_names(code)
        assert "MyComponent" in names

    def test_ignores_lowercase(self):
        code = "const myHelper = () => 1;\nconst MyComponent = () => <div />;"
        names = _extract_component_names(code)
        assert "MyComponent" in names
        assert "myHelper" not in names

    def test_multiple_components(self):
        code = """const DataVizSlide = ({ content }) => <div />;
const BarChartRenderer = ({ chart }) => <div />;"""
        names = _extract_component_names(code)
        assert "DataVizSlide" in names
        assert "BarChartRenderer" in names


# ─── _reorder_components ────────────────────────────────────────────


class TestReorderComponents:
    def test_dependency_reorder(self):
        """CRITICAL: DataVizSlide uses BarChartRenderer, so BarChartRenderer must come first."""
        code = """const DataVizSlide = ({ content }) => {
  return <BarChartRenderer data={content.data} />;
};

const BarChartRenderer = ({ data }) => {
  return <div>chart</div>;
};"""
        result = _reorder_components(code)
        # BarChartRenderer should appear before DataVizSlide
        bar_pos = result.find("BarChartRenderer")
        data_pos = result.find("DataVizSlide")
        assert bar_pos < data_pos, "BarChartRenderer must come before DataVizSlide"

    def test_no_deps_preserves_order(self):
        code = """const CompA = () => <div>A</div>;

const CompB = () => <div>B</div>;"""
        result = _reorder_components(code)
        a_pos = result.find("CompA")
        b_pos = result.find("CompB")
        assert a_pos < b_pos

    def test_single_component_no_reorder(self):
        code = "const SingleComp = () => <div />;"
        result = _reorder_components(code)
        assert "SingleComp" in result

    def test_chain_dependency(self):
        """A → B → C should produce C, B, A."""
        code = """const CompA = () => <CompB />;

const CompB = () => <CompC />;

const CompC = () => <div />;"""
        result = _reorder_components(code)
        c_pos = result.find("CompC")
        b_pos = result.find("CompB")
        a_pos = result.find("CompA")
        assert c_pos < b_pos < a_pos


# ─── _clean_slide_code (integration) ────────────────────────────────


class TestCleanSlideCode:
    def test_full_cleanup(self):
        """Integration test: imports + THEME + reordering all at once."""
        code = '''import { useState } from "react";
import { BarChart, Bar } from "recharts";

const THEME = {
  primary: "#1a1a2e",
  nested: { val: "#fff" }
};

const DataVizSlide = ({ content }) => {
  return <BarChartRenderer data={content.data} />;
};

const BarChartRenderer = ({ data }) => {
  return <div>chart</div>;
};'''
        result = _clean_slide_code(code)

        # Imports removed
        assert "import" not in result
        # THEME removed
        assert "THEME" not in result
        # Both components present
        assert "DataVizSlide" in result
        assert "BarChartRenderer" in result
        # BarChartRenderer before DataVizSlide
        assert result.find("BarChartRenderer") < result.find("DataVizSlide")


# ─── code_assembly (integration) ────────────────────────────────────


class TestCodeAssembly:
    def _make_state(self, slides):
        return {
            "slide_spec": {
                "ppt_state": {
                    "presentation": {
                        "meta": {
                            "theme": {
                                "primary_color": "#1a1a2e",
                                "accent_color": "#e94560",
                                "background": "#16213e",
                                "text_color": "#eaeaea",
                            }
                        },
                        "slides": [],
                    }
                }
            },
            "generated_slides": slides,
        }

    def test_basic_assembly(self):
        state = self._make_state([
            {
                "slide_id": "slide_001",
                "type": "cover",
                "code": 'const CoverSlide = ({ content }) => (\n  <div>{content.title}</div>\n);',
            }
        ])
        result = code_assembly(state)
        code = result["react_code"]

        assert "import { useState }" in code
        assert "import {" in code  # recharts imports
        assert "const THEME =" in code
        assert "CoverSlide" in code
        assert "SlideFactory" in code
        assert "export default function Presentation" in code

    def test_deduplication_keeps_latest(self):
        """On retries, operator.add appends, so dedup must keep latest."""
        state = self._make_state([
            {"slide_id": "slide_001", "type": "cover", "code": "const CoverSlide = () => <div>v1</div>;"},
            {"slide_id": "slide_001", "type": "cover", "code": "const CoverSlide = () => <div>v2</div>;"},
        ])
        result = code_assembly(state)
        assert "v2" in result["react_code"]
        # v1 should be overwritten
        assert "v1" not in result["react_code"]

    def test_type_component_map(self):
        for slide_type, comp_name in TYPE_COMPONENT_MAP.items():
            state = self._make_state([
                {"slide_id": "slide_001", "type": slide_type, "code": f"const {comp_name} = () => <div />;"},
            ])
            result = code_assembly(state)
            assert comp_name in result["react_code"]

    def test_duplicate_type_gets_unique_names(self):
        """CRITICAL: Two slides of the same type must get unique component names."""
        state = self._make_state([
            {
                "slide_id": "slide_003",
                "type": "key_points",
                "code": "const KeyPointsSlide = ({ content }) => <div>slide3</div>;",
            },
            {
                "slide_id": "slide_005",
                "type": "key_points",
                "code": "const KeyPointsSlide = ({ content }) => <div>slide5</div>;",
            },
        ])
        result = code_assembly(state)
        code = result["react_code"]

        # Should NOT have duplicate 'const KeyPointsSlide'
        assert code.count("const KeyPointsSlide =") == 0, \
            "Original KeyPointsSlide should be renamed to avoid duplicates"
        # Should have unique names like KeyPointsSlide_003 and KeyPointsSlide_005
        assert "KeyPointsSlide_003" in code
        assert "KeyPointsSlide_005" in code
        # SlideFactory should dispatch by slide_id
        assert '"slide_003"' in code
        assert '"slide_005"' in code

    def test_single_type_no_rename(self):
        """Single slide of a type should keep the original name."""
        state = self._make_state([
            {
                "slide_id": "slide_001",
                "type": "cover",
                "code": "const CoverSlide = ({ content }) => <div>cover</div>;",
            },
            {
                "slide_id": "slide_003",
                "type": "key_points",
                "code": "const KeyPointsSlide = ({ content }) => <div>kp</div>;",
            },
        ])
        result = code_assembly(state)
        code = result["react_code"]

        # No renaming needed — each type is unique
        assert "CoverSlide" in code
        assert "KeyPointsSlide" in code
        # No suffixed versions
        assert "CoverSlide_" not in code
        assert "KeyPointsSlide_" not in code
