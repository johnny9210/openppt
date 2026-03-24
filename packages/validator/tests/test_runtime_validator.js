/**
 * Tests for runtime-validator.js
 * Run with: node --test packages/validator/tests/test_runtime_validator.js
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { validateRuntime } from "../src/runtime-validator.js";

// ── Helper: minimal valid presentation code ─────────────────────────

const VALID_CODE = `
import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const THEME = {
  primary: "#1a1a2e",
  accent: "#e94560",
  background: "#16213e",
  text: "#eaeaea",
};

const CoverSlide = ({ content }) => (
  <div style={{ background: THEME.background, padding: 32 }}>
    <h1 style={{ color: THEME.text }}>{content.title}</h1>
  </div>
);

const SlideFactory = ({ slide }) => {
  const map = { cover: CoverSlide };
  const Component = map[slide.type];
  return Component ? <Component {...slide} /> : null;
};

export default function Presentation({ spec }) {
  const [current, setCurrent] = useState(0);
  const slides = spec.ppt_state.presentation.slides;
  return (
    <div>
      <SlideFactory slide={slides[current]} />
      {slides.map((_, i) => (
        <button key={i} onClick={() => setCurrent(i)}>dot</button>
      ))}
    </div>
  );
}
`;

const VALID_SPEC = {
  ppt_state: {
    presentation: {
      slides: [
        { slide_id: "slide_001", type: "cover", content: { title: "Test" } },
      ],
    },
  },
};


// ── Test: Valid code passes ──────────────────────────────────────────

describe("validateRuntime", () => {
  it("should pass valid code with correct slide count", async () => {
    const result = await validateRuntime(VALID_CODE, 1, VALID_SPEC);
    assert.equal(result.valid, true, `Expected valid=true, got errors: ${JSON.stringify(result.errors)}`);
    assert.equal(result.errors.length, 0);
    assert.ok(result.html_length > 0);
  });

  it("should detect slide count mismatch", async () => {
    const result = await validateRuntime(VALID_CODE, 3, VALID_SPEC);
    const slideCountErrors = result.errors.filter(e => e.type === "slide_count");
    assert.ok(slideCountErrors.length > 0, "Expected a slide_count error");
  });

  // ── Transpile errors ────────────────────────────────────────────

  it("should catch syntax errors", async () => {
    const brokenCode = "const x = {;";
    const result = await validateRuntime(brokenCode, 1, VALID_SPEC);
    assert.equal(result.valid, false);
    const transpileErrors = result.errors.filter(e => e.type === "transpile");
    assert.ok(transpileErrors.length > 0, "Expected a transpile error");
  });

  // ── Missing component detection ─────────────────────────────────

  it("should detect missing component definitions", async () => {
    const codeWithMissingComponent = `
import { useState } from "react";

const SlideFactory = ({ slide }) => {
  return <MissingComponent />;
};

export default function Presentation({ spec }) {
  return <SlideFactory slide={{}} />;
}
`;
    const result = await validateRuntime(codeWithMissingComponent, 1, VALID_SPEC);
    const missingErrors = result.errors.filter(e => e.type === "missing_component");
    assert.ok(missingErrors.length > 0, "Expected a missing_component error");
  });

  // ── No default export ───────────────────────────────────────────

  it("should fail when no default export exists", async () => {
    const noExportCode = `
import { useState } from "react";
const NotExported = () => <div>hello</div>;
`;
    const result = await validateRuntime(noExportCode, 1, VALID_SPEC);
    assert.equal(result.valid, false);
  });

  // ── Recharts prop validation ────────────────────────────────────

  it("should detect missing BarChart data prop", async () => {
    const codeWithBadChart = `
import { useState } from "react";
import { BarChart, Bar, ResponsiveContainer } from "recharts";

export default function Presentation({ spec }) {
  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart>
          <Bar dataKey="value" />
        </BarChart>
      </ResponsiveContainer>
      {spec.ppt_state.presentation.slides.map((_, i) => (
        <button key={i}>dot</button>
      ))}
    </div>
  );
}
`;
    const result = await validateRuntime(codeWithBadChart, 1, VALID_SPEC);
    const propErrors = result.errors.filter(e => e.type === "missing_prop");
    assert.ok(propErrors.length > 0, `Expected missing_prop errors for BarChart data, got: ${JSON.stringify(result.errors)}`);
    assert.ok(
      propErrors.some(e => e.component === "BarChart" && e.prop === "data"),
      "Expected error about BarChart missing data prop"
    );
  });

  it("should detect non-array data passed to BarChart", async () => {
    const codeWithWrongType = `
import { useState } from "react";
import { BarChart, Bar, ResponsiveContainer } from "recharts";

export default function Presentation({ spec }) {
  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data="not an array">
          <Bar dataKey="value" />
        </BarChart>
      </ResponsiveContainer>
      {spec.ppt_state.presentation.slides.map((_, i) => (
        <button key={i}>dot</button>
      ))}
    </div>
  );
}
`;
    const result = await validateRuntime(codeWithWrongType, 1, VALID_SPEC);
    const propErrors = result.errors.filter(
      e => e.type === "missing_prop" && e.component === "BarChart"
    );
    assert.ok(propErrors.length > 0, "Expected error about BarChart data being non-array");
  });

  it("should detect missing Bar dataKey prop", async () => {
    const codeWithBadBar = `
import { useState } from "react";
import { BarChart, Bar, ResponsiveContainer } from "recharts";

export default function Presentation({ spec }) {
  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={[{value: 1}]}>
          <Bar />
        </BarChart>
      </ResponsiveContainer>
      {spec.ppt_state.presentation.slides.map((_, i) => (
        <button key={i}>dot</button>
      ))}
    </div>
  );
}
`;
    const result = await validateRuntime(codeWithBadBar, 1, VALID_SPEC);
    const propErrors = result.errors.filter(
      e => e.type === "missing_prop" && e.component === "Bar" && e.prop === "dataKey"
    );
    assert.ok(propErrors.length > 0, "Expected error about Bar missing dataKey prop");
  });

  // ── Runtime errors ──────────────────────────────────────────────

  it("should catch runtime errors in component code", async () => {
    const codeWithRuntimeError = `
import { useState } from "react";

export default function Presentation({ spec }) {
  const x = null;
  return <div>{x.toString()}</div>;
}
`;
    const result = await validateRuntime(codeWithRuntimeError, 1, VALID_SPEC);
    assert.equal(result.valid, false);
    const runtimeErrors = result.errors.filter(e => e.type === "runtime");
    assert.ok(runtimeErrors.length > 0, "Expected a runtime error");
  });
});
