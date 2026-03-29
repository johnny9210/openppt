"""
Phase 2-B: Design Generator
Generates PPT slide design images using Nano Banana (Gemini) via Send API.

Uses LLM-generated design_prompt from scoping phase (ICS framework)
with shared VISUAL_IDENTITY guardrails for consistent styling.
"""

import asyncio
import logging

from langchain_core.runnables import RunnableConfig

from core.state import DesignGeneratorState
from core.services.nano_banana import generate_slide_image

logger = logging.getLogger(__name__)


# ── Shared Visual Identity (prepended to all prompts) ──────

VISUAL_IDENTITY = """## Visual Identity (MUST apply to every slide)
- Aspect ratio: 16:9 widescreen (960×540 proportions)
- Background: Clean light gray (#F5F7FA), NOT white, NOT dark
- Card elements: Pure white (#FFFFFF), border-radius 16px, subtle shadow, thin border (#E2E8F0)
- Icon badges: Circular, 50-60px, solid color fill ({primary_color} or {accent_color}), white emoji inside
- Accent bar: Thin colored line (width 48px, height 4px) using {primary_color}
- Decorations: Subtle geometric network pattern (thin lines + small dots), opacity 10-15%
- Overall mood: McKinsey consulting deck meets Apple Keynote — clean, confident, premium

## CRITICAL: Text-Free Image Rule
This image will be used as a BACKGROUND with text overlaid by code later.
- DO NOT render any Korean or English text in the image
- Leave title areas as clean blank zones (light background, no text)
- Leave body/description areas empty within cards and containers
- Cards should show visual structure (borders, shadows, icons) but NO text labels
- Icon badges may contain emoji symbols but NO text words
- The image provides ONLY visual structure, decorations, colors, and layout — ALL text comes from code overlay

## Whitespace & Density Rules
- Maximum 6 visual elements per slide (cards, badges, decorations)
- At least 30% of slide area must be empty for text overlay space
- Generous padding inside cards (24-28px) and between cards (20px gaps)
- Title zone: Leave clean open area at top 15-25% of slide for title overlay

## DO NOT (Negative Instructions)
- NO text of any kind (Korean, English, numbers) — except emoji symbols in icon badges
- NO dark mode, NO glassmorphism, NO gradient backgrounds
- NO 3D effects, NO extreme drop shadows, NO bevels
- NO neon or overly saturated colors
- NO overcrowded layouts"""


def _build_design_prompt(
    slide: dict,
    brief: dict,
    reference_image: bool = False,
) -> str:
    """Build Nano Banana prompt for slide design generation.

    Uses LLM-generated design_prompt from scoping phase + visual identity guardrails.
    """
    style = brief.get("style", {})
    primary = style.get("primary_color", "#6366F1")
    accent = style.get("accent_color", "#818CF8")

    visual_identity = VISUAL_IDENTITY.format(
        primary_color=primary,
        accent_color=accent,
    )

    # Add style reference instruction when a reference image is attached
    if reference_image:
        visual_identity = """## Style Reference (CRITICAL)
The attached image is the COVER slide of this presentation.
You MUST match its visual style exactly: same color palette, typography weight,
card corner radius, shadow depth, background color, and decorative elements.
Maintain this consistent look while adapting the layout to the current slide type.

""" + visual_identity

    design_prompt = slide.get("design_prompt")
    if not design_prompt:
        raise ValueError(
            f"Slide {slide.get('slide_id')} missing design_prompt from scoping"
        )

    logger.info("[DesignGen] Using LLM-generated design_prompt for %s", slide.get("slide_id"))
    return f"{design_prompt}\n\n{visual_identity}"


# Slide types that benefit from Gemini's Thinking mode (complex layouts)
COMPLEX_SLIDE_TYPES = {
    "data_visualization", "process_flow", "comparison",
    "risk_analysis", "action_plan", "timeline", "cover",
}


async def cover_design_generator(state: DesignGeneratorState, config: RunnableConfig) -> dict:
    """Generate cover slide design FIRST — its image becomes the style reference for all other slides."""
    cancel_event = (config.get("configurable") or {}).get("cancel_event")
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

    from core.config import GEMINI_THINKING_BUDGET

    slide = state["slide_plan"]
    brief = state["research_brief"]

    prompt = _build_design_prompt(slide, brief, reference_image=False)

    logger.info("[DesignGen:Cover] START %s - prompt: %d chars", slide["slide_id"], len(prompt))
    image_b64 = await generate_slide_image(
        prompt,
        aspect_ratio="16:9",
        thinking_budget=GEMINI_THINKING_BUDGET,
    )

    if image_b64:
        logger.info("[DesignGen:Cover] SUCCESS - image size: %d bytes", len(image_b64))
    else:
        logger.warning("[DesignGen:Cover] FAILED - no image")

    return {
        "slide_designs": [{
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "image_b64": image_b64,
            "design_prompt": prompt,
        }],
        "cover_design_image": image_b64 or "",
    }


async def design_generator(state: DesignGeneratorState, config: RunnableConfig) -> dict:
    """Generate design image for a non-cover slide, using cover as style reference."""
    cancel_event = (config.get("configurable") or {}).get("cancel_event")
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()

    from core.config import GEMINI_THINKING_BUDGET

    slide = state["slide_plan"]
    brief = state["research_brief"]
    ref_image = state.get("reference_image_b64") or None

    prompt = _build_design_prompt(slide, brief, reference_image=bool(ref_image))

    thinking = GEMINI_THINKING_BUDGET if slide["type"] in COMPLEX_SLIDE_TYPES else None

    logger.info("[DesignGen] START %s (%s) - prompt: %d chars, ref=%s, think=%s",
                slide["slide_id"], slide["type"], len(prompt), bool(ref_image), thinking)

    image_b64 = await generate_slide_image(
        prompt,
        aspect_ratio="16:9",
        reference_image_b64=ref_image,
        thinking_budget=thinking,
    )

    if image_b64:
        logger.info("[DesignGen] SUCCESS %s - image size: %d bytes", slide["slide_id"], len(image_b64))
    else:
        logger.warning("[DesignGen] FAILED %s - no image, continuing without", slide["slide_id"])

    return {
        "slide_designs": [{
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "image_b64": image_b64,
            "design_prompt": prompt,
        }]
    }
