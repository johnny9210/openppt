/**
 * Runtime Validator - Phase 3-B
 * Renders React code in jsdom sandbox to detect runtime errors.
 * Uses @babel/core (NOT @babel/standalone which is browser-only).
 *
 * Environment gap: We use Node.js + jsdom + React SSR, but the browser uses
 * React 18 CSR + Recharts 2.15.0 UMD. The stubs below validate props that
 * the real Recharts library would require, catching errors before they hit
 * the browser.
 */

import { JSDOM } from "jsdom";
import { transformSync } from "@babel/core";
import React from "react";
import ReactDOMServer from "react-dom/server";

export async function validateRuntime(code, expectedSlideCount, spec) {
  const errors = [];

  // ── Phase 0: Pre-execution code analysis ──────────────────────────
  const codeAnalysisErrors = analyzeCodeBeforeExecution(code);
  errors.push(...codeAnalysisErrors);

  // ── Phase 1: Transpile JSX → CJS ─────────────────────────────────
  let transpiledCode;
  try {
    const result = transformSync(code, {
      presets: ["@babel/preset-env", "@babel/preset-react"],
      filename: "presentation.jsx",
    });
    transpiledCode = result.code;
  } catch (e) {
    return {
      valid: false,
      errors: [
        ...errors,
        {
          type: "transpile",
          message: e.message,
          line: e.loc?.line,
        },
      ],
    };
  }

  // ── Phase 2: Execute in controlled scope ──────────────────────────
  // preset-env converts imports → require() and export → exports.*
  const rechartsValidationErrors = [];
  try {
    const moduleExports = {};
    const moduleObj = { exports: moduleExports };

    const mockRequire = (name) => {
      if (name === "react") return React;
      if (name === "react-dom/server") return ReactDOMServer;
      if (name === "recharts") return createRechartsStub(rechartsValidationErrors);
      throw new Error(`Module not found: ${name}`);
    };

    const fn = new Function(
      "React",
      "require",
      "exports",
      "module",
      "useState",
      transpiledCode
    );
    fn(React, mockRequire, moduleExports, moduleObj, React.useState);

    // preset-env produces: exports.default = ... OR module.exports = ...
    const Presentation =
      moduleExports.default || moduleObj.exports?.default || moduleExports;

    if (!Presentation || typeof Presentation !== "function") {
      errors.push({
        type: "missing_component",
        message: "No default export function found after execution",
      });
      return { valid: false, errors };
    }

    // ── Phase 3: Render to string ─────────────────────────────────
    const html = ReactDOMServer.renderToString(
      React.createElement(Presentation, { spec })
    );

    // Collect any recharts prop-validation errors that fired during render
    errors.push(...rechartsValidationErrors);

    // ── Phase 4: Slide count validation ───────────────────────────
    if (expectedSlideCount) {
      const dom = new JSDOM(html);
      const doc = dom.window.document;

      // Strategy A: count navigation dots (buttons with data-nav-dot attribute only)
      const navDots = doc.querySelectorAll('button[data-nav-dot]');
      const dotCount = navDots.length;

      // Strategy B: count slide wrapper divs via data attributes or class patterns
      const slideWrappers = doc.querySelectorAll(
        '[data-slide], [class*="slide"], [data-recharts="SlideFactory"]'
      );

      // Strategy C: check for SlideFactory marker in rendered output
      const hasSlideFactory =
        html.includes("SlideFactory") ||
        html.includes("data-slide-factory") ||
        html.includes("slide-factory");

      if (!hasSlideFactory && dotCount === 0 && slideWrappers.length === 0) {
        errors.push({
          type: "slide_count",
          message:
            `Could not detect slide navigation in rendered output. ` +
            `Expected ${expectedSlideCount} slides but found no navigation dots, ` +
            `no slide wrappers, and no SlideFactory marker. ` +
            `SSR with useState only renders initial state — verify slide structure is present.`,
          expected: expectedSlideCount,
          actual: 0,
        });
      } else if (dotCount > 0 && dotCount !== expectedSlideCount) {
        errors.push({
          type: "slide_count",
          message: `Expected ${expectedSlideCount} slides, found ${dotCount} navigation dots`,
          expected: expectedSlideCount,
          actual: dotCount,
        });
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      html_length: html.length,
    };
  } catch (e) {
    // Merge any recharts validation errors collected before the crash
    errors.push(...rechartsValidationErrors);
    errors.push({
      type: "runtime",
      message: e.message,
      stack: e.stack?.split("\n").slice(0, 3).join("\n"),
    });
    return {
      valid: false,
      errors,
    };
  }
}

// ─────────────────────────────────────────────────────────────────────
// Pre-execution code analysis
// ─────────────────────────────────────────────────────────────────────

/**
 * Static analysis of the source code BEFORE transpilation/execution.
 * Catches missing component definitions and structural issues that would
 * cause runtime errors in the browser but might silently pass in SSR.
 */
function analyzeCodeBeforeExecution(code) {
  const errors = [];

  // 1. Detect component references in JSX and verify they have definitions
  //    Match <ComponentName (uppercase first letter) but skip HTML elements
  const jsxComponentUsages = new Set();
  const jsxUsageRegex = /<([A-Z][A-Za-z0-9]+)[\s/>]/g;
  let match;
  while ((match = jsxUsageRegex.exec(code)) !== null) {
    jsxComponentUsages.add(match[1]);
  }

  // Components that are imported (from recharts, react, etc.) — not locally defined
  const importedComponents = new Set();

  // Detect named imports: import { Foo, Bar } from "..."
  const namedImportRegex = /import\s*\{([^}]+)\}\s*from\s*["'][^"']+["']/g;
  while ((match = namedImportRegex.exec(code)) !== null) {
    match[1].split(",").forEach((name) => {
      const trimmed = name.trim().split(/\s+as\s+/).pop().trim();
      if (trimmed) importedComponents.add(trimmed);
    });
  }

  // Detect default imports: import Foo from "..."
  const defaultImportRegex = /import\s+([A-Z][A-Za-z0-9]*)\s+from\s*["'][^"']+["']/g;
  while ((match = defaultImportRegex.exec(code)) !== null) {
    importedComponents.add(match[1]);
  }

  // Detect locally defined components:
  //   function Foo(         const Foo = (         const Foo = function
  //   class Foo extends
  const definedComponents = new Set();

  const funcDeclRegex = /function\s+([A-Z][A-Za-z0-9]*)\s*\(/g;
  while ((match = funcDeclRegex.exec(code)) !== null) {
    definedComponents.add(match[1]);
  }

  const constFuncRegex = /(?:const|let|var)\s+([A-Z][A-Za-z0-9]*)\s*=\s*(?:\(|function|\({)/g;
  while ((match = constFuncRegex.exec(code)) !== null) {
    definedComponents.add(match[1]);
  }

  // Arrow functions: const Foo = ({ ... }) =>  OR  const Foo = (props) =>  OR  const Foo = () =>
  const arrowRegex = /(?:const|let|var)\s+([A-Z][A-Za-z0-9]*)\s*=\s*(?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)\s*=>/g;
  while ((match = arrowRegex.exec(code)) !== null) {
    definedComponents.add(match[1]);
  }

  const classRegex = /class\s+([A-Z][A-Za-z0-9]*)\s+extends/g;
  while ((match = classRegex.exec(code)) !== null) {
    definedComponents.add(match[1]);
  }

  // Detect dynamic component variables:
  //   const Component = map[x]   or   const Component = condition ? A : B
  //   These are local variables assigned at runtime, not component definitions
  const dynamicComponents = new Set();
  const dynamicVarRegex = /(?:const|let|var)\s+([A-Z][A-Za-z0-9]*)\s*=\s*(?:\w+\[|.+\?)/g;
  while ((match = dynamicVarRegex.exec(code)) !== null) {
    dynamicComponents.add(match[1]);
  }

  // Known globals that don't need definitions
  const knownGlobals = new Set([
    "React", "Fragment", "Suspense", "StrictMode",
    "Array", "Object", "Map", "Set", "Promise",
    "Math", "JSON", "Date", "Number", "String", "Boolean",
  ]);

  // Check each JSX usage for a definition or import
  for (const component of jsxComponentUsages) {
    if (
      !definedComponents.has(component) &&
      !importedComponents.has(component) &&
      !knownGlobals.has(component) &&
      !dynamicComponents.has(component)
    ) {
      errors.push({
        type: "missing_component",
        message:
          `Component <${component}> is used in JSX but has no visible definition or import. ` +
          `This will cause a ReferenceError in the browser.`,
        component,
      });
    }
  }

  // 2. Check for SlideFactory or slide-management pattern
  //    This is informational — not a hard error
  const hasSlidePattern =
    code.includes("SlideFactory") ||
    code.includes("slides") ||
    /slide[A-Z]|Slide[A-Z]/.test(code) ||
    /currentSlide|activeSlide|slideIndex/.test(code);

  if (!hasSlidePattern) {
    // Not necessarily an error, but worth noting for the caller
    errors.push({
      type: "missing_component",
      message:
        "No slide management pattern detected (SlideFactory, slides array, currentSlide state). " +
        "The presentation may not render slides correctly.",
    });
  }

  return errors;
}

// ─────────────────────────────────────────────────────────────────────
// Smart Recharts Stubs
// ─────────────────────────────────────────────────────────────────────

/**
 * Create recharts stub components for SSR validation.
 * Unlike the old dumb stubs, these validate that required props match what
 * the real Recharts 2.15.0 library expects, catching misuse before the
 * code reaches the browser.
 *
 * @param {Array} validationErrors - Mutable array; stubs push errors here
 *   instead of throwing, so rendering can continue and collect ALL issues.
 */
function createRechartsStub(validationErrors) {
  // ── Prop requirements per component ──────────────────────────────
  const propRules = {
    BarChart: {
      required: { data: "array" },
      message: "BarChart requires a `data` prop (array of objects)",
    },
    LineChart: {
      required: { data: "array" },
      message: "LineChart requires a `data` prop (array of objects)",
    },
    PieChart: {
      required: {},
      message: null,
    },
    Bar: {
      required: { dataKey: "string" },
      message: "Bar requires a `dataKey` prop (string) identifying the data field",
    },
    Line: {
      required: { dataKey: "string" },
      message: "Line requires a `dataKey` prop (string) identifying the data field",
    },
    Pie: {
      required: { data: "array", dataKey: "string" },
      message: "Pie requires `data` (array) and `dataKey` (string) props",
    },
    Cell: {
      required: { fill: "string" },
      message: "Cell requires a `fill` prop (string) for the cell color",
    },
    ResponsiveContainer: {
      recommended: { width: "any", height: "any" },
      message:
        "ResponsiveContainer should have `width` and `height` props for reliable rendering",
    },
    XAxis: { required: {} },
    YAxis: { required: {} },
    CartesianGrid: { required: {} },
    Tooltip: { required: {} },
    Legend: { required: {} },
    AreaChart: {
      required: { data: "array" },
      message: "AreaChart requires a `data` prop (array of objects)",
    },
    Area: {
      required: { dataKey: "string" },
      message: "Area requires a `dataKey` prop (string) identifying the data field",
    },
    RadarChart: { required: {} },
    Radar: {
      required: { dataKey: "string" },
      message: "Radar requires a `dataKey` prop (string)",
    },
    RadialBarChart: { required: {} },
    RadialBar: { required: {} },
    ScatterChart: { required: {} },
    Scatter: {
      required: { data: "array" },
      message: "Scatter requires a `data` prop (array)",
    },
    Treemap: {
      required: { data: "array" },
      message: "Treemap requires a `data` prop (array)",
    },
    Funnel: {
      required: { data: "array" },
      message: "Funnel requires a `data` prop (array)",
    },
    FunnelChart: { required: {} },
    ComposedChart: {
      required: { data: "array" },
      message: "ComposedChart requires a `data` prop (array of objects)",
    },
    ReferenceLine: { required: {} },
    ReferenceArea: { required: {} },
    ReferenceDot: { required: {} },
    Brush: { required: {} },
    ErrorBar: { required: {} },
    Label: { required: {} },
    LabelList: { required: {} },
  };

  /**
   * Build a validating stub for a single Recharts component.
   */
  const createValidatingStub = (name) => {
    const rules = propRules[name] || { required: {} };

    const component = ({ children, ...props }) => {
      // ── Validate required props ────────────────────────────────
      if (rules.required) {
        for (const [propName, expectedType] of Object.entries(rules.required)) {
          const value = props[propName];

          if (value === undefined || value === null) {
            validationErrors.push({
              type: "missing_prop",
              message:
                `Recharts <${name}>: missing required prop \`${propName}\`. ` +
                (rules.message || `The real Recharts library will fail or render incorrectly.`),
              component: name,
              prop: propName,
            });
          } else if (expectedType === "array" && !Array.isArray(value)) {
            validationErrors.push({
              type: "missing_prop",
              message:
                `Recharts <${name}>: prop \`${propName}\` must be an array, ` +
                `received ${typeof value}. Chart will not render data.`,
              component: name,
              prop: propName,
            });
          } else if (
            expectedType === "string" &&
            typeof value !== "string"
          ) {
            validationErrors.push({
              type: "missing_prop",
              message:
                `Recharts <${name}>: prop \`${propName}\` must be a string, ` +
                `received ${typeof value}.`,
              component: name,
              prop: propName,
            });
          }
        }
      }

      // ── Validate recommended props (warnings, not hard errors) ─
      if (rules.recommended) {
        for (const propName of Object.keys(rules.recommended)) {
          if (props[propName] === undefined || props[propName] === null) {
            validationErrors.push({
              type: "missing_prop",
              message:
                `Recharts <${name}>: recommended prop \`${propName}\` is missing. ` +
                (rules.message || "This may cause layout issues in the browser."),
              component: name,
              prop: propName,
              severity: "warning",
            });
          }
        }
      }

      // ── Render a div placeholder (same as before, but with validation) ─
      return React.createElement(
        "div",
        { "data-recharts": name, ...filterProps(props) },
        children
      );
    };

    component.displayName = name;
    return component;
  };

  const filterProps = (props) => {
    const safe = {};
    for (const [k, v] of Object.entries(props)) {
      if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
        safe[`data-${k}`] = String(v);
      }
    }
    return safe;
  };

  // Build the stub module — covers every component the real recharts exports
  const stub = {};
  for (const name of Object.keys(propRules)) {
    stub[name] = createValidatingStub(name);
  }
  return stub;
}
