"""
Phase 2-A': Infographic Generator
Generates data-rich infographic images using Nano Banana (Gemini).

Unlike design images (decorative slide backgrounds with NO text),
infographics are information-dense visuals containing data labels,
numbers, charts, and diagrams. They are shown in the UI Infograph tab
for reference only — NOT embedded in the final PPT slides.
"""

import asyncio
import logging

from langchain_core.runnables import RunnableConfig

from core.state import InfographicGeneratorState
from core.services.nano_banana import generate_slide_image

logger = logging.getLogger(__name__)


# ── Infographic Visual Rules (common to all themes) ──────

INFOGRAPHIC_RULES = """## Infographic Rendering Rules (MUST apply)

## Image Specification
- Aspect ratio: 16:9 widescreen (960×540 proportions)
- High resolution, crisp edges on all elements

## CRITICAL: This is a DATA INFOGRAPHIC (not a slide background)
- INCLUDE data labels, numbers, axis labels, metric values on ALL visual elements
- Every chart bar, pie slice, card, and icon MUST have its label/value visible
- Data accuracy and readability are the #1 priority
- Total text in the image must stay under 400 words (ensures legible rendering)

## Color Palette (MUST use these exact colors)
- Primary: {primary_color} — use for main data elements, headings, key metrics
- Accent: {accent_color} — use for secondary elements, highlights, trend indicators
- Use gradient between primary → accent for progressive elements (funnels, timelines)
- Positive indicators: #22C55E (green arrows, growth)
- Negative indicators: #EF4444 (red arrows, decline)
- Neutral/background: white or #F8FAFC

## Typography Rules
- Title: Bold sans-serif, largest size, primary color
- Metric numbers: Extra-bold sans-serif, 1.5× body size, primary or accent color
- Labels: Regular sans-serif, body size, #64748B (slate gray)
- All text in English only

## Container & Card Design
- Card containers: white background, rounded corners (12-16px), subtle shadow (0 2px 8px rgba(0,0,0,0.08))
- Icon badges: 40-56px circular, colored background with white icon inside
- Dividers: 1px #E2E8F0 lines or subtle spacing
- Generous padding inside cards (16-24px) and between elements (12-20px gap)

## Layout Quality
- Maximum 60% content density — leave 40% as breathing space
- Clear visual hierarchy: title zone → main content → supporting details
- Symmetric alignment and consistent spacing
- Connecting elements (arrows, lines) should be subtle, not dominant

## DO NOT
- NO decorative background patterns or textures
- NO 3D effects, extreme drop shadows, or neon glows
- NO photorealistic style (use flat vector / minimalist instead)
- NO overcrowded layouts — if too many items, use grid or multi-row
- NO Korean text"""


def _format_research_data(web_research: list[dict]) -> str:
    """Format web research results as structured context for infographic generation.

    Extracts key facts and data points in a scannable format
    so Gemini can incorporate real numbers into the infographic.
    """
    lines = []
    for i, r in enumerate(web_research[:5], 1):
        title = r.get("title", "")
        content = r.get("content", "")[:400]
        lines.append(f"Source [{i}]: {title}")
        lines.append(f"Key facts: {content}")
        lines.append("")
    lines.append(
        "IMPORTANT: Use the actual numbers and facts above in your infographic. "
        "Replace any placeholder data in the prompt with these real values."
    )
    return "\n".join(lines)


async def infographic_generator(
    state: InfographicGeneratorState, config: RunnableConfig
) -> dict:
    """Generate an infographic image for a single slide.

    Skips slides without infographic_prompt (returns empty list).
    Uses web_research data when available to enrich the prompt.
    """
    cancel_event = (config.get("configurable") or {}).get("cancel_event")
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

    from core.config import GEMINI_THINKING_BUDGET

    slide = state["slide_plan"]
    brief = state["research_brief"]

    infographic_prompt = slide.get("infographic_prompt")
    if not infographic_prompt:
        return {"slide_infographics": []}

    # Enrich prompt with web research data if available
    web_research = slide.get("web_research", [])
    if web_research:
        data_context = _format_research_data(web_research)
        enriched_prompt = (
            f"{infographic_prompt}\n\n"
            f"## Real Data (use actual numbers from this research):\n{data_context}"
        )
    else:
        enriched_prompt = infographic_prompt

    # Apply theme colors and infographic rules
    style = brief.get("style", {})
    primary = style.get("primary_color", "#6366F1")
    accent = style.get("accent_color", "#818CF8")

    rules = INFOGRAPHIC_RULES.format(
        primary_color=primary,
        accent_color=accent,
    )

    final_prompt = f"{enriched_prompt}\n\n{rules}"

    logger.info(
        "[InfographGen] START %s (%s) - prompt: %d chars",
        slide["slide_id"], slide["type"], len(final_prompt),
    )

    # Always use thinking mode for data accuracy
    image_b64 = await generate_slide_image(
        final_prompt,
        aspect_ratio="16:9",
        thinking_budget=GEMINI_THINKING_BUDGET,
    )

    if image_b64:
        logger.info(
            "[InfographGen] SUCCESS %s - image size: %d bytes",
            slide["slide_id"], len(image_b64),
        )
    else:
        logger.warning(
            "[InfographGen] FAILED %s - no image", slide["slide_id"],
        )

    return {
        "slide_infographics": [{
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "image_b64": image_b64,
        }]
    }
