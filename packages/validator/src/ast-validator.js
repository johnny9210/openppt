/**
 * AST Validator - Phase 3-A
 * Uses @babel/parser to validate JSX syntax, imports, and tag pairs.
 */

import { parse } from "@babel/parser";

export function validateAST(code) {
  const errors = [];

  // 1. Parse with error recovery
  try {
    const ast = parse(code, {
      sourceType: "module",
      plugins: ["jsx"],
      errorRecovery: true,
    });

    // Collect recovered errors
    if (ast.errors && ast.errors.length > 0) {
      for (const err of ast.errors) {
        errors.push({
          type: "syntax",
          message: err.message,
          line: err.loc?.line,
          column: err.loc?.column,
          code: err.reasonCode,
        });
      }
    }

    // 2. Verify imports
    const imports = ast.program.body.filter(
      (node) => node.type === "ImportDeclaration"
    );
    const importedModules = imports.map((imp) => imp.source.value);

    // Check required imports
    const hasReact = importedModules.some((m) => m === "react");
    if (!hasReact) {
      errors.push({
        type: "import",
        message: 'Missing "react" import',
        severity: "warning",
      });
    }

    // 3. Check for default export
    const hasDefaultExport = ast.program.body.some(
      (node) =>
        node.type === "ExportDefaultDeclaration" ||
        (node.type === "ExportNamedDeclaration" &&
          node.specifiers?.some((s) => s.exported?.name === "default"))
    );
    if (!hasDefaultExport) {
      errors.push({
        type: "export",
        message: "Missing default export (Presentation component)",
        severity: "error",
      });
    }

    return {
      valid: errors.filter((e) => e.severity === "error" || e.type === "syntax").length === 0,
      errors,
      ast_node_count: countNodes(ast),
    };
  } catch (e) {
    // Unrecoverable parse error
    return {
      valid: false,
      errors: [
        {
          type: "fatal",
          message: e.message,
          line: e.loc?.line,
          column: e.loc?.column,
        },
      ],
    };
  }
}

function countNodes(ast) {
  let count = 0;
  function walk(node) {
    if (!node || typeof node !== "object") return;
    if (node.type) count++;
    for (const key of Object.keys(node)) {
      if (key === "parent") continue;
      const child = node[key];
      if (Array.isArray(child)) child.forEach(walk);
      else if (child && typeof child === "object" && child.type) walk(child);
    }
  }
  walk(ast.program);
  return count;
}
