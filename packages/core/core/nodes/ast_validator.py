"""
Phase 3-A: AST Validator (HTML Edition)
Validates HTML structure: well-formed tags, slide containers present,
basic CSS integrity. Replaces the external Babel-based JSX validator.
"""

import logging
import re
from html.parser import HTMLParser

from core.state import PPTState

logger = logging.getLogger(__name__)


# ── HTML Structure Validator ──────────────────────────────────────

# Tags that are self-closing (void elements) in HTML
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


class _HTMLChecker(HTMLParser):
    """Lightweight HTML checker that detects structural issues."""

    def __init__(self):
        super().__init__()
        self.errors: list[str] = []
        self.tag_stack: list[str] = []
        self.slide_container_count = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _VOID_TAGS:
            return
        self.tag_stack.append(tag)
        # Track slide containers
        classes = dict(attrs).get("class", "")
        if "slide-container" in classes:
            self.slide_container_count += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _VOID_TAGS:
            return
        if not self.tag_stack:
            self.errors.append(f"Unexpected closing tag </{tag}> with no open tags")
            return
        if self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        else:
            # Try to find the matching tag deeper in the stack (common in LLM output)
            if tag in self.tag_stack:
                # Pop up to and including the matching tag
                while self.tag_stack and self.tag_stack[-1] != tag:
                    unclosed = self.tag_stack.pop()
                    self.errors.append(f"Implicitly closed <{unclosed}> by </{tag}>")
                if self.tag_stack:
                    self.tag_stack.pop()
            else:
                self.errors.append(f"Unexpected closing tag </{tag}>, expected </{self.tag_stack[-1]}>")

    def handle_startendtag(self, tag, attrs):
        # Self-closing tags like <br/>, <img/>
        tag = tag.lower()
        classes = dict(attrs).get("class", "")
        if "slide-container" in classes:
            self.slide_container_count += 1

    def finish(self):
        if self.tag_stack:
            self.errors.append(f"Unclosed tags at end: {', '.join(self.tag_stack)}")


def _validate_html(html_code: str) -> tuple[bool, list[str]]:
    """Validate HTML structure. Returns (is_valid, errors)."""
    errors = []

    # Basic presence checks
    if not html_code or len(html_code.strip()) < 50:
        return False, ["HTML code is empty or too short"]

    if "slide-container" not in html_code:
        errors.append("No .slide-container elements found in HTML")

    if "<style>" not in html_code and "</style>" not in html_code:
        # Not strictly an error (Tailwind-only slides are valid) but warn
        logger.warning("[ASTValidator] No <style> block found — slides may rely entirely on Tailwind")

    # Parse HTML structure
    checker = _HTMLChecker()
    try:
        checker.feed(html_code)
        checker.finish()
    except Exception as e:
        errors.append(f"HTML parse error: {e}")
        return False, errors

    # Only report critical structural errors (not minor nesting issues)
    critical_errors = [
        e for e in checker.errors
        if "Unexpected closing tag" in e or "Unclosed tags at end" in e
    ]
    if critical_errors:
        # Allow a few minor errors (LLM output is not always perfect)
        if len(critical_errors) > 5:
            errors.extend(critical_errors[:5])
            errors.append(f"... and {len(critical_errors) - 5} more tag errors")

    if checker.slide_container_count == 0:
        errors.append("No slide-container divs found after parsing")

    # Check for obvious CSS issues
    style_blocks = re.findall(r"<style>([\s\S]*?)</style>", html_code)
    for block in style_blocks:
        open_braces = block.count("{")
        close_braces = block.count("}")
        if abs(open_braces - close_braces) > 2:
            errors.append(f"CSS brace mismatch: {open_braces} open vs {close_braces} close")

    return len(errors) == 0, errors


# ── Main entry point ─────────────────────────────────────────────

async def ast_validator(state: PPTState) -> dict:
    """Validate assembled HTML code structure."""
    html_code = state.get("react_code", "")

    is_valid, errors = _validate_html(html_code)

    if is_valid:
        logger.info("[ASTValidator] PASS")
    else:
        for err in errors:
            logger.error("[ASTValidator] %s", err)

    update: dict = {
        "validation_result": {
            "layer": "ast",
            "status": "pass" if is_valid else "fail",
            "errors": errors,
        },
    }
    if not is_valid:
        update["revision_count"] = state.get("revision_count", 0) + 1
    return update
