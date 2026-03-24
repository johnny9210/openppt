import express from "express";
import { validateAST } from "./ast-validator.js";
import { validateRuntime } from "./runtime-validator.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// Health check
app.get("/health", (_, res) => res.json({ status: "ok" }));

// AST Validation endpoint
app.post("/validate/ast", (req, res) => {
  const { code } = req.body;
  if (!code) return res.status(400).json({ error: "code is required" });

  const result = validateAST(code);
  res.json(result);
});

// Runtime Validation endpoint
app.post("/validate/runtime", async (req, res) => {
  const { code, expected_slide_count, spec } = req.body;
  if (!code) return res.status(400).json({ error: "code is required" });

  const result = await validateRuntime(code, expected_slide_count, spec);
  res.json(result);
});

const PORT = process.env.PORT || 8001;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Validator service running on port ${PORT}`);
});
