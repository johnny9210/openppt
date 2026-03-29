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


# ── Visual Identity: Base rules (common to all themes) ──────

VISUAL_IDENTITY_BASE = """## Slide Design Rules (MUST apply)
- Aspect ratio: 16:9 widescreen (960×540 proportions)

## CRITICAL: Text-Free Image Rule
This image will be used as a BACKGROUND with text overlaid by code later.
- DO NOT render any Korean or English text in the image
- Leave title areas as clean blank zones
- Leave body/description areas empty within cards and containers
- Cards should show visual structure (borders, shadows, icons) but NO text labels
- Icon badges may contain emoji symbols but NO text words

## Whitespace & Density Rules
- Maximum 6 visual elements per slide (cards, badges, decorations)
- At least 30% of slide area must be empty for text overlay space
- Generous padding inside cards and between cards
- Title zone: Clean open area at top 15-25% of slide

## DO NOT
- NO text of any kind (Korean, English, numbers) — except emoji symbols in icon badges
- NO dark mode, NO 3D effects, NO extreme drop shadows
- NO neon or overly saturated colors
- NO overcrowded layouts"""


# ── Theme-specific visual styles (mood-driven, not CSS-level) ──────

THEME_VISUAL_STYLES = {
    "tech": """## Visual Style
Clean minimal tech slide background, soft light blue ({background}).
Subtle dot grid or circuit trace pattern at 5% opacity.
Geometric line accents in {primary_color}. White card placeholders with thin borders
and subtle shadows, border-radius 12px. Icon areas as rounded-square badges.
Precise, data-driven, modern tech company pitch deck mood.""",

    "education": """## Visual Style
Friendly approachable slide background, soft mint ({background}).
Subtle notebook ruled-line or open-book pattern at 5% opacity.
Warm green accents in {primary_color} with teal highlights ({accent_color}).
Rounded white card placeholders with medium shadows, border-radius 16px.
Icon areas as circular badges. Welcoming, clear, educational workshop mood.""",

    "business": """## Visual Style
Conservative corporate slide background, soft blue-gray ({background}).
Clean horizontal rule structure, minimal decoration.
Sharp-cornered white card placeholders with strong borders, border-radius 8px.
Navy accents ({primary_color}) with gold highlights ({accent_color}).
Structured grid layout. Authoritative McKinsey consulting report mood.""",

    "marketing": """## Visual Style
Bold vibrant slide background, warm rose-tinted ({background}).
Dynamic diagonal stripe or wave pattern at 8% opacity.
Red-to-orange gradient accents from {primary_color} to {accent_color}.
White card placeholders with large rounded corners and strong drop shadows,
border-radius 20px, no visible border. Icon areas as large circular badges with gradient fill.
Energetic, attention-grabbing, advertising agency pitch mood.""",

    "creative": """## Visual Style
Artistic warm slide background, soft peach ({background}).
Organic flowing curves and brush stroke textures at 8% opacity.
Orange and amber accents ({primary_color}, {accent_color}).
White card placeholders with varied rounded corners and soft shadows,
border-radius 20px. Playful asymmetric layout feel.
Creative studio portfolio mood — artistic and expressive.""",

    "lifestyle": """## Visual Style
Elegant soft slide background, light rose ({background}).
Flowing gradient curves and organic shapes at 8% opacity.
Rose pink accents ({primary_color}) with soft pink highlights ({accent_color}).
White card placeholders with very rounded corners and gentle shadows,
border-radius 24px. Soft, premium beauty editorial mood.""",

    "minimal": """## Visual Style
Ultra-minimal slide background, barely-there off-white ({background}).
Almost no decoration — pure negative space.
Slate gray accents ({primary_color}) with light gray ({accent_color}).
Barely visible card outlines, extremely thin borders, nearly no shadows,
border-radius 12px. Maximum whitespace.
Apple Keynote simplicity — less is more.""",

    "entertainment": """## Visual Style
Energetic vibrant slide background, soft lavender ({background}).
Star sparkle or confetti scatter pattern at 8% opacity.
Purple-to-magenta gradient accents from {primary_color} to {accent_color}.
White card placeholders with medium rounded corners and colorful shadows,
border-radius 16px. Icon areas as circular badges with vivid gradient fill.
Fun, bold, entertainment industry showcase mood.""",

    "medical": """## Visual Style
Clean trustworthy slide background, soft cyan-tinted ({background}).
Subtle cross or plus pattern at 5% opacity.
Teal accents ({primary_color}) with emerald highlights ({accent_color}).
White card placeholders with clean corners and precise borders,
border-radius 12px. Structured and balanced layout.
Healthcare professional — clean, precise, trustworthy mood.""",

    "environment": """## Visual Style
Fresh natural slide background, soft sage green ({background}).
Organic leaf vein or topographic contour pattern at 5% opacity.
Green accents ({primary_color}) with lime highlights ({accent_color}).
White card placeholders with soft rounded corners and gentle shadows,
border-radius 16px. Nature-inspired flowing layout feel.
Sustainability report mood — fresh, organic, hopeful.""",
}


def _build_design_prompt(
    slide: dict,
    brief: dict,
    reference_image: bool = False,
) -> str:
    """Build Nano Banana prompt for slide design generation.

    Uses LLM-generated design_prompt from scoping phase
    + theme-specific visual style + base design rules.
    """
    style = brief.get("style", {})
    primary = style.get("primary_color", "#6366F1")
    accent = style.get("accent_color", "#818CF8")
    background = style.get("background", "#F5F7FA")
    color_theme = style.get("color_theme", "minimal")

    # Pick theme-specific visual style
    theme_style = THEME_VISUAL_STYLES.get(
        color_theme, THEME_VISUAL_STYLES["minimal"]
    )
    formatted_theme = theme_style.format(
        primary_color=primary,
        accent_color=accent,
        background=background,
    )

    visual_identity = f"{formatted_theme}\n\n{VISUAL_IDENTITY_BASE}"

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

    logger.info("[DesignGen] Using LLM-generated design_prompt for %s (theme=%s)",
                slide.get("slide_id"), color_theme)
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
