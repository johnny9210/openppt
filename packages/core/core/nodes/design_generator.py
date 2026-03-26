"""
Phase 2-B: Design Generator
Generates PPT slide design images using Nano Banana (Gemini) via Send API.

Prompt strategy based on Nano Banana Pro best practices:
  - ICS framework: Image type + Content + Style
  - Shared visual identity across all slides for consistency
  - Concrete text content embedded for accurate Korean text rendering
  - Professional style references (McKinsey, Apple Keynote level)
"""

import logging

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


# ── Type-specific prompt templates (ICS framework) ──────────


COVER_PROMPT = """## Image Type
Professional presentation COVER slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- LEFT 58%: Blank title zone (clean open area for text overlay)
  - Large blank area at top-left for title overlay
  - Accent bar (48×4px, {primary_color}) as a visual separator
  - Clean space below for subtitle overlay
  - Small blank zone at bottom-left for presenter info overlay
- RIGHT 42%: Thematic visual illustration
  - A cohesive icon composition related to the topic (3-5 connected icons)
  - Icons: Flat style, colorful but harmonious, connected by thin arrows/lines
  - A central icon badge (larger, circular, {primary_color} background) as the focal point
  - Surrounding smaller icons in white cards with subtle shadows
- Background: Light decorative curves/shapes in top-right area ({accent_color} at 8% opacity)

{visual_identity}

Generate this cover slide visual structure (NO TEXT) now."""


TOC_PROMPT = """## Image Type
Professional TABLE OF CONTENTS slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Clean blank zone for title overlay, accent bar below
- ZIGZAG/STAGGERED layout:
  - Vertical timeline spine down center with numbered circles (numbers as digits only)
  - Odd items: Blank card LEFT of spine
  - Even items: Blank card RIGHT of spine
  - Number circles: 36px, solid {primary_color} (odd) / {accent_color} (even)
- Each card: White rounded rectangle with icon badge — NO text inside cards
- Cards connected to number circles by thin lines

{visual_identity}

Generate this table of contents visual structure (NO TEXT) now."""


KEY_POINTS_PROMPT = """## Image Type
Professional KEY POINTS slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Clean blank zone for title + description overlay, accent bar
- 2×2 GRID of cards below:
  - Each card: White, rounded-16px, shadow, border
  - LEFT inside card: Circular icon badge (56px, alternating {primary_color}/{accent_color}) with emoji
  - RIGHT of icon: Blank area for title + description text overlay
  - Cards are uniform size, symmetric, evenly spaced with 20px gaps
- Maximum 4 cards visible

{visual_identity}

Generate this key points visual structure (NO TEXT) now."""


DATA_VIZ_PROMPT = """## Image Type
Professional DATA VISUALIZATION slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}
Layout emphasis: {design_direction}

## Layout
- Top: Clean blank zone for title overlay, accent bar
- CENTER: Chart visual structure (shapes and colors only, NO labels/numbers)
  - Chart placeholder: Donut/pie shape or bar chart shapes
  - Chart colors: {primary_color}, {accent_color}, #38A169, #F59E0B
  - Leave blank zones around chart for label overlays
- SIDE/BELOW: Small white cards (blank) for stat callouts
- BOTTOM: Blank zone for insight overlay

{visual_identity}

Generate this data visualization visual structure (NO TEXT) now."""


ACTION_PLAN_PROMPT = """## Image Type
Professional ACTION PLAN slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}
Layout emphasis: {design_direction}

## Layout
- Top: Clean blank zone for title overlay, accent bar
- VERTICAL TIMELINE flowing top to bottom:
  - Thin vertical line on left ({primary_color} to {accent_color} gradient)
  - Numbered circles (36px) as milestones (digits only, no text labels)
  - Each milestone → Blank card to the RIGHT (white, rounded, shadow)
  - Rocket/target icon at top of timeline
- Clear top-to-bottom visual flow

{visual_identity}

Generate this action plan visual structure (NO TEXT) now."""


HERO_PROMPT = """## Image Type
Professional HERO MESSAGE slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Ultra minimal — mostly blank for large text overlay
- CENTER: Large clean blank zone for text overlay (60% of slide)
- Background: #F5F7FA with a subtle oversized geometric shape ({accent_color} at 3-5% opacity)
- NO cards, NO icons, NO grids — pure empty canvas with subtle decoration
- Extreme whitespace

{visual_identity}

Generate this hero visual structure (NO TEXT) now."""


QUOTE_PROMPT = """## Image Type
Professional QUOTE slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Decorative large quotation mark (") in {accent_color}, 120px, opacity 15%, top-left
- Vertical accent bar: 4px × 60px, {primary_color}, centered
- Large blank zone in center for quote text overlay (max-width 650px area)
- Blank zone below for attribution overlay
- Extreme whitespace, warm contemplative mood

{visual_identity}

Generate this quote visual structure (NO TEXT) now."""


ICON_GRID_PROMPT = """## Image Type
Professional ICON GRID slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title + description overlay, accent bar
- GRID: 2×3 or 3×2 arrangement of cards
  - Each card: White, rounded-16px, shadow
  - TOP of card: Circular icon badge (56px, alternating {primary_color}/{accent_color}) with emoji
  - BELOW icon: Blank area for label + description overlay
- All cards identical size, symmetric, 20px gaps

{visual_identity}

Generate this icon grid visual structure (NO TEXT) now."""


PROCESS_FLOW_PROMPT = """## Image Type
Professional PROCESS FLOW slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title overlay, accent bar
- HORIZONTAL FLOW: 3-5 step cards connected by arrows
  - Each step: White rounded card, shadow, border
  - TOP: Circular badge (44px, alternating {primary_color}/{accent_color}) with step emoji
  - BELOW badge: Blank area for title + description overlay
  - Between cards: Bold arrow → in {primary_color}
- LEFT→RIGHT single row, equal card sizes

{visual_identity}

Generate this process flow visual structure (NO TEXT) now."""


COMPARISON_PROMPT = """## Image Type
Professional COMPARISON slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title overlay
- TWO COLUMNS with 24px gap:
  - LEFT: Red (#E53E3E) circle badge with ✕, warm-tinted card, blank list area
  - RIGHT: Green (#38A169) circle badge with ✓, cool-tinted card, blank list area
- Equal width, balanced visual weight, clear contrast

{visual_identity}

Generate this comparison visual structure (NO TEXT) now."""


THREE_COLUMN_PROMPT = """## Image Type
Professional THREE COLUMN slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title + description overlay, accent bar
- THREE EQUAL COLUMNS:
  - Each: Tall white card, rounded-16px, shadow
  - TOP: Large circular icon (56px) — Col1: {primary_color}, Col2: {accent_color}, Col3: #38A169, emoji inside
  - BELOW icon: Blank zones for title, description, metric overlays
- All three identical height, symmetric, 20-24px gaps

{visual_identity}

Generate this three column visual structure (NO TEXT) now."""


TIMELINE_PROMPT = """## Image Type
Professional TIMELINE slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title overlay, accent bar
- HORIZONTAL TIMELINE:
  - Thin line (3px) left→right, gradient {primary_color}→{accent_color}
  - Event circles (40px) ON the line, alternating colors, emoji inside
  - ABOVE circles: Blank zone for time labels
  - BELOW circles: Small white cards (blank) for title + description overlay
- Evenly spaced, clear left→right progression

{visual_identity}

Generate this timeline visual structure (NO TEXT) now."""


RISK_ANALYSIS_PROMPT = """## Image Type
Professional RISK ANALYSIS slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title overlay, accent bar
- STACKED CARDS (3-5):
  - White rounded rectangle, shadow, full width
  - LEFT EDGE: Color-coded severity bar (6px wide)
    - Bars use #E53E3E, #F59E0B, #38A169 colors
  - Inside cards: Blank zones for severity label, title, description, mitigation overlay
- Cards stacked with 12px gaps

{visual_identity}

Generate this risk analysis visual structure (NO TEXT) now."""


SUMMARY_PROMPT = """## Image Type
Professional SUMMARY slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- Top: Blank zone for title overlay, accent bar
- NUMBERED CARDS (3-5) stacked vertically:
  - White rounded card, shadow, horizontal layout
  - LEFT: Large circle (50px, {primary_color}) — may contain digit number
  - RIGHT of circle: Blank zone for title + description overlay
- Cards centered (max-width 700px), 12px gaps

{visual_identity}

Generate this summary visual structure (NO TEXT) now."""


CLOSING_PROMPT = """## Image Type
Professional CLOSING slide — visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}

## Layout
- UPPER: Blank zone for title overlay
- CENTER: Blank zone for closing message overlay
- LOWER: Row of compact cards (3-5):
  - Each card: White, rounded-16px, shadow (120-160px wide)
  - Emoji symbol at top, blank zones for label + description overlay
  - Cards evenly spaced, 20px gaps
- Warm, professional, conclusive mood

{visual_identity}

Generate this closing visual structure (NO TEXT) now."""


GENERIC_PROMPT = """## Image Type
Professional presentation slide — {slide_type} visual structure only (no text).

## Content Context (for layout decisions only — do NOT render this text)
{content_hints}
Layout emphasis: {design_direction}

## Layout
- Top: Blank zone for title overlay, accent bar
- Content area: White cards with shadows for content grouping
- Colored circle badges ({primary_color}/{accent_color}) for visual anchors
- All text zones left blank for code overlay

{visual_identity}

Generate this slide visual structure (NO TEXT) now."""


# ── Template selection ──────────────────────────

TYPE_PROMPT_MAP = {
    "cover": COVER_PROMPT,
    "table_of_contents": TOC_PROMPT,
    "hero": HERO_PROMPT,
    "quote": QUOTE_PROMPT,
    "icon_grid": ICON_GRID_PROMPT,
    "key_points": KEY_POINTS_PROMPT,
    "three_column": THREE_COLUMN_PROMPT,
    "comparison": COMPARISON_PROMPT,
    "process_flow": PROCESS_FLOW_PROMPT,
    "timeline": TIMELINE_PROMPT,
    "data_visualization": DATA_VIZ_PROMPT,
    "risk_analysis": RISK_ANALYSIS_PROMPT,
    "action_plan": ACTION_PLAN_PROMPT,
    "summary": SUMMARY_PROMPT,
    "closing": CLOSING_PROMPT,
}


def _truncate_content(content: str, max_chars: int = 400) -> str:
    """Truncate content hints to stay under Nano Banana's text limit."""
    if len(content) <= max_chars:
        return content
    lines = content.split("\n")
    result = []
    total = 0
    for line in lines:
        if total + len(line) > max_chars:
            break
        result.append(line)
        total += len(line) + 1
    return "\n".join(result)


def _build_design_prompt(
    slide: dict,
    brief: dict,
    reference_image: bool = False,
) -> str:
    """Build Nano Banana prompt for slide design generation.

    Strategy:
    1. If slide has 'design_prompt' (LLM-generated in scoping) → use it + guardrails
    2. Fallback: use hardcoded TYPE_PROMPT_MAP templates (legacy)
    """
    style = brief.get("style", {})
    slide_type = slide["type"]
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

    # --- Strategy 1: LLM-generated design_prompt from scoping ---
    custom_prompt = slide.get("design_prompt")
    if custom_prompt:
        logger.info("[DesignGen] Using LLM-generated design_prompt for %s", slide.get("slide_id"))
        return f"{custom_prompt}\n\n{visual_identity}"

    # --- Strategy 2: Fallback to hardcoded templates ---
    logger.info("[DesignGen] Fallback to template for %s (%s)", slide.get("slide_id"), slide_type)

    key_points = slide.get("key_points", [])
    content_parts = []

    if brief.get("purpose"):
        content_parts.append(f"프레젠테이션 목적: {brief['purpose']}")
    if brief.get("key_message"):
        content_parts.append(f'핵심 메시지: "{brief["key_message"]}"')

    if key_points:
        content_parts.append("포함할 항목:")
        for i, pt in enumerate(key_points, 1):
            content_parts.append(f'  {i}. "{pt}"')

    data = slide.get("data")
    if data:
        content_parts.append(f"데이터: {data}")

    design_dir = slide.get("design_direction", "")
    if design_dir:
        content_parts.append(f"디자인 방향: {design_dir}")

    content_hints = "\n".join(content_parts) if content_parts else f'주제: "{slide["topic"]}"'
    content_hints = _truncate_content(content_hints)

    template = TYPE_PROMPT_MAP.get(slide_type, GENERIC_PROMPT)

    format_kwargs = {
        "topic": slide["topic"],
        "design_direction": design_dir or "Professional layout",
        "primary_color": primary,
        "accent_color": accent,
        "text_color": style.get("text_color", "#1A202C"),
        "content_hints": content_hints,
        "visual_identity": visual_identity,
    }

    if slide_type not in TYPE_PROMPT_MAP:
        format_kwargs["slide_type"] = slide_type

    return template.format(**format_kwargs)


# Slide types that benefit from Gemini's Thinking mode (complex layouts)
COMPLEX_SLIDE_TYPES = {
    "data_visualization", "process_flow", "comparison",
    "risk_analysis", "action_plan", "timeline", "cover",
}


async def cover_design_generator(state: DesignGeneratorState) -> dict:
    """Generate cover slide design FIRST — its image becomes the style reference for all other slides."""
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


async def design_generator(state: DesignGeneratorState) -> dict:
    """Generate design image for a non-cover slide, using cover as style reference."""
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
