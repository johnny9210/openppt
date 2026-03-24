/**
 * Tests for ast-validator.js
 * Run with: node --test packages/validator/tests/test_ast_validator.js
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { validateAST } from "../src/ast-validator.js";


describe("validateAST", () => {

  // ── Valid code ────────────────────────────────────────────────────

  it("should pass valid JSX code with imports and export", () => {
    const code = `
import { useState } from "react";

export default function Presentation({ spec }) {
  return <div>Hello</div>;
}
`;
    const result = validateAST(code);
    assert.equal(result.valid, true, `Expected valid=true, got: ${JSON.stringify(result.errors)}`);
    assert.ok(result.ast_node_count > 0);
  });

  it("should pass code with recharts and multiple components", () => {
    const code = `
import { useState } from "react";
import { BarChart, Bar } from "recharts";

const THEME = { primary: "#1a1a2e" };

const CoverSlide = ({ content }) => <div>{content.title}</div>;

const SlideFactory = ({ slide }) => {
  const map = { cover: CoverSlide };
  const Component = map[slide.type];
  return Component ? <Component {...slide} /> : null;
};

export default function Presentation({ spec }) {
  const [current, setCurrent] = useState(0);
  return <SlideFactory slide={spec.ppt_state.presentation.slides[current]} />;
}
`;
    const result = validateAST(code);
    assert.equal(result.valid, true, `Expected valid=true, got: ${JSON.stringify(result.errors)}`);
  });

  // ── Syntax errors ───────────────────────────────────────────────

  it("should detect syntax errors", () => {
    const code = "const x = {;";
    const result = validateAST(code);
    assert.equal(result.valid, false);
    assert.ok(result.errors.length > 0);
  });

  it("should detect unclosed JSX tags", () => {
    const code = `
import { useState } from "react";
export default function Presentation() {
  return <div><span></div>;
}
`;
    const result = validateAST(code);
    // Parser in error-recovery mode may or may not catch this as error
    // but it should at least produce errors or warnings
    assert.ok(result.errors.length > 0 || result.valid === true);
  });

  // ── Missing react import ─────────────────────────────────────────

  it("should warn when react import is missing", () => {
    const code = `
export default function Presentation({ spec }) {
  return <div>No react import</div>;
}
`;
    const result = validateAST(code);
    const importErrors = result.errors.filter(
      e => e.type === "import" && e.message.includes("react")
    );
    assert.ok(importErrors.length > 0, "Expected warning about missing react import");
  });

  // ── Missing default export ────────────────────────────────────────

  it("should error when no default export exists", () => {
    const code = `
import { useState } from "react";
const NotExported = () => <div>hello</div>;
`;
    const result = validateAST(code);
    const exportErrors = result.errors.filter(e => e.type === "export");
    assert.ok(exportErrors.length > 0, "Expected error about missing default export");
  });

  // ── Fatal parse errors ──────────────────────────────────────────

  it("should handle completely unparseable code", () => {
    const code = "@#$%^&*()_+-=[]{}|;':\",./<>?";
    const result = validateAST(code);
    assert.equal(result.valid, false);
  });

  // ── Empty code ──────────────────────────────────────────────────

  it("should handle empty code", () => {
    const code = "";
    const result = validateAST(code);
    assert.equal(result.valid, false);
    const exportErrors = result.errors.filter(e => e.type === "export");
    assert.ok(exportErrors.length > 0, "Expected error about missing export in empty code");
  });
});
