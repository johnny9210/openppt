"""
Phase 2-C: Code Assembly
Merges individual slide components into a single React presentation file.
"""

import json
import re
from core.state import PPTState


TEMPLATE_HEADER = '''import {{ useState, useEffect }} from "react";
import {{
  BarChart, Bar, Cell, LineChart, Line, AreaChart, Area,
  PieChart, Pie, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  RadialBarChart, RadialBar, ScatterChart, Scatter, ComposedChart,
  FunnelChart, Funnel, Treemap,
  XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, ReferenceArea, ReferenceDot, Brush, LabelList, Label, Text
}} from "recharts";

// ── Design System Theme ──────────────────────────────
const THEME = {theme_obj};
'''

TEMPLATE_FACTORY = '''
// ── SlideFactory: slide_id → 컴포넌트 dispatch ────────────
const SlideFactory = ({{ slide }}) => {{
  const map = {{
{slide_map}
  }};
  const Component = map[slide.slide_id];
  return Component ? <Component {{...slide}} /> : null;
}};
'''

TEMPLATE_ROOT = '''
// ── Presentation Root ─────────────────────────────────
export default function Presentation({ spec }) {
  const [current, setCurrent] = useState(0);
  const slides = spec.ppt_state.presentation.slides;
  const total = slides.length;

  const goTo = (i) => {
    const next = Math.max(0, Math.min(total - 1, i));
    setCurrent(next);
    try { window.parent.postMessage({ type: "slideChange", index: next }, "*"); } catch(e) {}
  };
  const goPrev = () => setCurrent((c) => { const n = Math.max(0, c - 1); try { window.parent.postMessage({ type: "slideChange", index: n }, "*"); } catch(e) {} return n; });
  const goNext = () => setCurrent((c) => { const n = Math.min(total - 1, c + 1); try { window.parent.postMessage({ type: "slideChange", index: n }, "*"); } catch(e) {} return n; });

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "ArrowLeft") goPrev();
      else if (e.key === "ArrowRight") goNext();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [total]);

  // Register goTo on global bridge for parent postMessage
  useEffect(() => {
    window.__goToSlide = goTo;
    return () => { window.__goToSlide = null; };
  });

  const arrowBtn = (direction, onClick) => (
    <button onClick={onClick} style={{
      position: "absolute", top: "50%", transform: "translateY(-50%)",
      [direction === "left" ? "left" : "right"]: 12,
      width: 36, height: 36, borderRadius: "50%", border: "none",
      background: "rgba(255,255,255,0.1)", color: "#fff",
      fontSize: 18, cursor: "pointer", display: "flex",
      alignItems: "center", justifyContent: "center",
      backdropFilter: "blur(4px)", transition: "background 0.2s",
      zIndex: 10,
    }}
    onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.25)"}
    onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.1)"}
    >{direction === "left" ? "\\u2039" : "\\u203A"}</button>
  );

  return (
    <div style={{
      background: "#050810", width: "100vw", height: "100vh",
      display: "flex", flexDirection: "column"
    }}>
      <div style={{
        flex: 1, display: "flex", position: "relative",
        alignItems: "center", justifyContent: "center", padding: 32
      }}>
        {current > 0 && arrowBtn("left", goPrev)}
        <div style={{
          width: "100%", maxWidth: 900,
          aspectRatio: "16/9", borderRadius: 16, overflow: "hidden",
          boxShadow: "0 25px 60px rgba(0,0,0,0.5)"
        }}>
          <SlideFactory slide={slides[current]} />
        </div>
        {current < total - 1 && arrowBtn("right", goNext)}
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, paddingBottom: 16 }}>
        <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 12 }}>
          {current + 1} / {total}
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          {slides.map((_, i) => (
            <button key={i} data-nav-dot="true" onClick={() => goTo(i)} style={{
              width: i === current ? 24 : 10, height: 10, borderRadius: 5,
              border: "none", transition: "all 0.2s",
              background: i === current ? THEME.accent : "rgba(255,255,255,0.2)",
              cursor: "pointer"
            }} />
          ))}
        </div>
      </div>
    </div>
  );
}
'''


def _remove_imports(code: str) -> str:
    """Remove all forms of import statements, including multi-line imports.

    Handles:
      - import x from "y";
      - import { x } from "y";
      - import { \\n  x, \\n  y \\n } from "y";
      - import * as x from "y";
      - import "side-effect";
      - import type { x } from "y";
    """
    lines = code.split('\n')
    result = []
    in_import = False

    for line in lines:
        stripped = line.strip()

        if in_import:
            # We're inside a multi-line import; consume lines until we see
            # a line containing 'from' followed by a string literal and semicolon,
            # or a bare closing that ends the statement.
            if re.search(r'''from\s+['"].*['"]\s*;?\s*$''', stripped):
                # This line closes the multi-line import
                in_import = False
                continue
            if stripped.endswith(';'):
                # Fallback: a semicolon ends any dangling import statement
                in_import = False
                continue
            # Still inside the import block; skip the line
            continue

        # Detect start of an import statement
        if re.match(r'^\s*import\s', stripped):
            # Check if the import is complete on this single line
            # A complete import has 'from "..."' or is a side-effect import like import "x";
            if re.search(r'''from\s+['"].*['"]\s*;?\s*$''', stripped):
                # Single-line import with from clause
                continue
            if re.match(r'''^\s*import\s+['"].*['"]\s*;?\s*$''', stripped):
                # Side-effect import: import "polyfill";
                continue
            # The import is incomplete (multi-line) — start consuming
            in_import = True
            continue

        result.append(line)

    return '\n'.join(result)


def _remove_theme_declaration(code: str) -> str:
    """Remove `const THEME = { ... };` declarations by counting brace depth.

    Handles nested braces such as:
      const THEME = { primary: "#1a1a2e", derived: { light: "#2a2a3e" } };
    """
    # Find the start of a THEME declaration
    pattern = re.compile(r'^\s*const\s+THEME\s*=\s*\{', re.MULTILINE)
    match = pattern.search(code)
    if not match:
        return code

    # Walk forward from the opening brace to find the matching close
    start = match.start()
    brace_pos = code.index('{', match.start() + len('const'))
    depth = 0
    i = brace_pos
    end = None

    while i < len(code):
        ch = code[i]

        # Skip string literals to avoid counting braces inside strings
        if ch in ('"', "'", '`'):
            quote = ch
            i += 1
            while i < len(code):
                if code[i] == '\\':
                    i += 2  # skip escaped character
                    continue
                if code[i] == quote:
                    break
                i += 1
            i += 1
            continue

        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                # Found the matching closing brace
                end = i + 1
                # Consume optional trailing semicolon and whitespace on the same line
                rest = code[end:]
                trail = re.match(r'\s*;?[^\S\n]*', rest)
                if trail:
                    end += trail.end()
                break
        i += 1

    if end is None:
        # Malformed — couldn't find matching brace; return as-is
        return code

    # Remove from start-of-line to end of declaration
    # Walk back to start of the line containing the declaration
    line_start = code.rfind('\n', 0, start)
    line_start = line_start + 1 if line_start != -1 else 0

    # Walk forward past any trailing newline
    if end < len(code) and code[end] == '\n':
        end += 1

    cleaned = code[:line_start] + code[end:]

    # Recursively remove any additional THEME declarations (unlikely but safe)
    return _remove_theme_declaration(cleaned)


def _extract_component_names(code: str) -> list[str]:
    """Extract all top-level const component/function names from a code block.

    Matches patterns like:
      const FooBar = (...) => { ... }
      const FooBar = (...) => (
      const FooBar = function(...) {
      function FooBar(...) {
    """
    names = []
    # const Name = ... (arrow or function expression)
    for m in re.finditer(
        r'(?:^|\n)\s*(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*=',
        code,
    ):
        names.append(m.group(1))
    # function Name(...)
    for m in re.finditer(
        r'(?:^|\n)\s*(?:export\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(',
        code,
    ):
        names.append(m.group(1))
    return names


def _split_components(code: str) -> list[tuple[str, str]]:
    """Split a code block into individual component definitions.

    Returns a list of (component_name, component_code) tuples.
    Components are identified by top-level `const Name = ` or `function Name(`
    declarations where Name starts with an uppercase letter.
    """
    # Pattern that matches the start of a component definition at top level
    component_start = re.compile(
        r'^(?:export\s+)?(?:const\s+([A-Z][A-Za-z0-9_]*)\s*=|function\s+([A-Z][A-Za-z0-9_]*)\s*\()',
        re.MULTILINE,
    )

    matches = list(component_start.finditer(code))
    if len(matches) <= 1:
        # Zero or one component — no reordering needed
        return []

    components = []
    for idx, match in enumerate(matches):
        name = match.group(1) or match.group(2)
        start = match.start()
        # Walk back to capture any comments immediately preceding the component
        line_start = code.rfind('\n', 0, start)
        line_start = line_start + 1 if line_start != -1 else 0
        # Check for preceding comment lines
        prefix_start = line_start
        lines_before = code[:line_start].split('\n')
        while lines_before and lines_before[-1].strip().startswith('//'):
            prefix_start -= len(lines_before[-1]) + 1  # +1 for newline
            lines_before.pop()
        if prefix_start < 0:
            prefix_start = 0

        if idx + 1 < len(matches):
            end = matches[idx + 1].start()
            # Walk back to the start of that next match's line
            nl = code.rfind('\n', 0, end)
            if nl != -1:
                # Check for comment lines preceding next component
                check_lines = code[:nl + 1].split('\n')
                while check_lines and check_lines[-1].strip().startswith('//'):
                    nl = code.rfind('\n', 0, nl)
                    check_lines.pop()
                end = nl + 1 if nl != -1 else end
        else:
            end = len(code)

        component_code = code[prefix_start:end].strip()
        components.append((name, component_code))

    return components


def _reorder_components(code: str) -> str:
    """Reorder component definitions so that dependencies come before dependents.

    If component A references component B, B must appear before A in the output.
    This fixes the Temporal Dead Zone issue with `const` declarations.
    """
    components = _split_components(code)
    if len(components) <= 1:
        return code

    # Build dependency graph: for each component, find which other components it references
    comp_names = {name for name, _ in components}
    deps: dict[str, set[str]] = {name: set() for name, _ in components}

    for name, comp_code in components:
        for other_name in comp_names:
            if other_name == name:
                continue
            # Check if this component references the other (as an identifier, not in a string)
            # Use word boundary to avoid partial matches
            if re.search(r'\b' + re.escape(other_name) + r'\b', comp_code):
                deps[name].add(other_name)

    # Topological sort (Kahn's algorithm) — components with no deps come first
    in_degree = {name: len(d) for name, d in deps.items()}
    queue = [name for name in in_degree if in_degree[name] == 0]
    sorted_names = []

    while queue:
        # Sort the queue to ensure deterministic ordering
        queue.sort()
        node = queue.pop(0)
        sorted_names.append(node)
        for name in deps:
            if node in deps[name]:
                deps[name].discard(node)
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)

    # If there's a cycle, append any remaining components in original order
    for name, _ in components:
        if name not in sorted_names:
            sorted_names.append(name)

    # Rebuild the code block with components in sorted order
    comp_map = {name: comp_code for name, comp_code in components}
    reordered_parts = [comp_map[name] for name in sorted_names if name in comp_map]

    # Collect any non-component code (standalone statements, comments not attached to components)
    # by checking what's left after removing all component code
    remaining = code
    for _, comp_code in components:
        remaining = remaining.replace(comp_code, '', 1)
    remaining = remaining.strip()

    parts = []
    if remaining:
        parts.append(remaining)
    parts.extend(reordered_parts)

    return '\n\n'.join(parts)


def _clean_slide_code(code: str) -> str:
    """Remove import statements and THEME re-declarations from LLM-generated slide code,
    then reorder components to prevent Temporal Dead Zone issues."""
    # Remove all import statements (single-line and multi-line)
    code = _remove_imports(code)
    # Remove const THEME = { ... }; declarations (handles nested braces)
    code = _remove_theme_declaration(code)
    # Reorder components so dependencies come before dependents
    code = _reorder_components(code)
    # Clean up excessive blank lines
    code = re.sub(r'\n{3,}', '\n\n', code).strip()
    return code


# Map slide types to component names
TYPE_COMPONENT_MAP = {
    "cover": "CoverSlide",
    "table_of_contents": "TocSlide",
    "hero": "HeroSlide",
    "quote": "QuoteSlide",
    "icon_grid": "IconGridSlide",
    "key_points": "KeyPointsSlide",
    "three_column": "ThreeColumnSlide",
    "comparison": "ComparisonSlide",
    "process_flow": "ProcessFlowSlide",
    "timeline": "TimelineSlide",
    "data_visualization": "DataVizSlide",
    "risk_analysis": "RiskSlide",
    "action_plan": "ActionPlanSlide",
    "summary": "SummarySlide",
    "closing": "ClosingSlide",
}


def code_assembly(state: PPTState) -> dict:
    """Assemble individual slide codes into a complete React component."""
    # Read theme from research_brief.style (new architecture)
    style = state.get("research_brief", {}).get("style", {})
    generated_slides = state["generated_slides"]

    # Build theme object with glass design tokens
    theme_obj = json.dumps(
        {
            "primary": style.get("primary_color", "#6366F1"),
            "accent": style.get("accent_color", "#818CF8"),
            "background": style.get("background", "#050810"),
            "text": style.get("text_color", "#E2E8F0"),
            "red": "#E53E3E",
            "yellow": "#F6C90E",
            "green": "#38A169",
            "glass": "rgba(255,255,255,0.04)",
            "glassBorder": "rgba(255,255,255,0.08)",
            "glassBright": "rgba(255,255,255,0.08)",
            "glassBorderBright": "rgba(255,255,255,0.15)",
        },
        indent=2,
    )

    # Build header
    header = TEMPLATE_HEADER.format(theme_obj=theme_obj)

    # Deduplicate by slide_id (keep latest on retries, since operator.add appends)
    seen = {}
    for slide in generated_slides:
        seen[slide["slide_id"]] = slide
    generated_slides = sorted(seen.values(), key=lambda s: s["slide_id"])

    # Count occurrences of each type to detect duplicates (e.g., two key_points slides)
    type_counts: dict[str, int] = {}
    for slide in generated_slides:
        t = slide["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    # Assign unique component names when the same type appears multiple times
    type_index: dict[str, int] = {}
    slide_component_names: dict[str, str] = {}  # slide_id → unique component name
    for slide in generated_slides:
        t = slide["type"]
        base_name = TYPE_COMPONENT_MAP.get(t, f"{t}Slide")
        if type_counts[t] > 1:
            idx = type_index.get(t, 0) + 1
            type_index[t] = idx
            # e.g., KeyPointsSlide → KeyPointsSlide_003 (using slide number)
            slide_num = slide["slide_id"].split("_")[-1]
            unique_name = f"{base_name}_{slide_num}"
        else:
            unique_name = base_name
        slide_component_names[slide["slide_id"]] = unique_name

    slide_codes = []
    for slide in generated_slides:
        code = _clean_slide_code(slide["code"])
        # Rename component if this type has duplicates
        base_name = TYPE_COMPONENT_MAP.get(slide["type"], f"{slide['type']}Slide")
        unique_name = slide_component_names[slide["slide_id"]]
        if unique_name != base_name:
            # Replace the component name declaration and any self-references
            code = re.sub(
                r'\b' + re.escape(base_name) + r'\b',
                unique_name,
                code,
            )
        slide_codes.append(f"// ── [{slide['slide_id']}] {slide['type']} ─────────────")
        slide_codes.append(code)

    # Build slide_id → component map for SlideFactory
    slide_lines = []
    for slide in generated_slides:
        comp_name = slide_component_names[slide["slide_id"]]
        slide_lines.append(f'    "{slide["slide_id"]}": {comp_name},')

    factory = TEMPLATE_FACTORY.format(slide_map="\n".join(slide_lines))

    # Assemble
    full_code = "\n".join([
        header,
        "\n\n".join(slide_codes),
        factory,
        TEMPLATE_ROOT,
    ])

    # Build backward-compatible slide_spec for validators
    contents_map = {c["slide_id"]: c for c in state.get("slide_contents", [])}
    slides_for_spec = []
    for slide in generated_slides:
        content = contents_map.get(slide["slide_id"], {}).get("content", {})
        slides_for_spec.append({
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "content": content,
        })

    slide_spec = {
        "ppt_state": {
            "presentation": {
                "meta": {
                    "title": state.get("research_brief", {}).get("purpose", ""),
                    "theme": {
                        "primary_color": style.get("primary_color", "#6366F1"),
                        "accent_color": style.get("accent_color", "#818CF8"),
                        "background": style.get("background", "#050810"),
                        "text_color": style.get("text_color", "#E2E8F0"),
                    },
                },
                "slides": slides_for_spec,
            }
        }
    }

    return {"react_code": full_code, "slide_spec": slide_spec}
