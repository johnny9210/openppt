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
- Typography: Bold modern sans-serif (Pretendard / Noto Sans KR style)
  - Titles: Extra-bold, dark charcoal (#1A202C), large (40-52px equivalent)
  - Body: Regular weight, muted gray (#64748B), 14-16px equivalent
  - Accents: {primary_color} for emphasis, {accent_color} for secondary highlights
- Card elements: Pure white (#FFFFFF), border-radius 16px, subtle shadow (0 2px 8px rgba(0,0,0,0.06)), thin border (#E2E8F0)
- Icon badges: Circular, 50-60px, solid color fill ({primary_color} or {accent_color}), white icon/emoji inside
- Accent bar: Thin colored line (width 48px, height 4px) centered below titles using {primary_color}
- Decorations: Subtle geometric network pattern (thin lines + small dots) in top-right corner, opacity 10-15%
- Overall mood: McKinsey consulting deck meets Apple Keynote — clean, confident, premium

## Whitespace & Density Rules
- Maximum 6 text elements visible on a single slide
- At least 30% of slide area must be empty whitespace
- Group items into 3-4 categories if more than 6 exist — less is more
- Generous padding inside cards (24-28px) and between cards (20px gaps)
- Title area: Leave 48px+ below title before content starts

## Text Rendering Rules
- Korean text MUST be perfectly legible, crisp, properly kerned
- Use bold sans-serif for all Korean text (Pretendard or Noto Sans KR weight 700+)
- Keep total visible text under 80 words per slide
- Enclose exact text to render in double quotes within the prompt

## DO NOT (Negative Instructions)
- NO dark mode, NO glassmorphism, NO gradient backgrounds
- NO 3D effects, NO extreme drop shadows, NO bevels
- NO clip-art style graphics or cartoonish icons
- NO neon or overly saturated colors
- NO text smaller than 12px equivalent
- NO overlapping text or cramped layouts
- NO tag-spam modifiers like "4k, masterpiece, trending on artstation"
- NO more than 2 font sizes per card (title + body only)"""


# ── Type-specific prompt templates (ICS framework) ──────────


COVER_PROMPT = """## Image Type
Professional presentation COVER slide — the first impression slide.

## Content
- Title text (large, bold, left-aligned): "{topic}"
- Subtitle: Based on key points below
- Bottom-left: Presenter info + date in small gray text
- Key points for context: {content_hints}

## Layout
- LEFT 58%: Title block
  - Title: Extra-bold, 44-52px, dark charcoal, left-aligned, max 2 lines
  - Accent bar (48×4px, {primary_color}) directly below the title
  - Subtitle: 18px, muted gray, 1-2 lines, left-aligned
  - Presenter/date: 13px, bottom-left, light gray
- RIGHT 42%: Thematic visual illustration
  - A cohesive icon composition related to the topic (3-5 connected icons)
  - Icons: Flat style, colorful but harmonious, connected by thin arrows/lines
  - A central icon badge (larger, circular, {primary_color} background) as the focal point
  - Surrounding smaller icons in white cards with subtle shadows
- Background: Light decorative curves/shapes in top-right area (very subtle, {accent_color} at 8% opacity)

{visual_identity}

Generate this cover slide image now."""


TOC_PROMPT = """## Image Type
Professional TABLE OF CONTENTS slide — navigation overview.

## Content
- Title: "{topic}"
- Items to display: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Items in ZIGZAG/STAGGERED layout:
  - Vertical timeline spine running down center with numbered circles
  - Odd items (1, 3, 5): Card LEFT of spine
  - Even items (2, 4, 6): Card RIGHT of spine
  - Number circles: 36px, solid {primary_color} (odd) / {accent_color} (even), white number
- Each card: White rounded rectangle with icon + bold title + gray description
- Cards connected to number circles by thin lines

{visual_identity}

Generate this table of contents slide image now."""


KEY_POINTS_PROMPT = """## Image Type
Professional KEY POINTS slide — 2-4 main takeaways in card grid.

## Content
- Title: "{topic}"
- Points to display: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Optional description line: 14px, muted gray, centered
- 2×2 GRID of cards (or 1×2 / 1×3 depending on point count):
  - Each card: White, rounded-16px, shadow, border
  - LEFT inside card: Circular icon badge (56px, alternating {primary_color}/{accent_color})
    - White emoji or flat icon inside
  - RIGHT of icon: Bold title (17px, dark) + description (13px, gray) + optional metric
  - Cards are uniform size, symmetric, evenly spaced with 20px gaps
- Maximum 4 cards visible — if more points, group them

{visual_identity}

Generate this key points slide image now."""


DATA_VIZ_PROMPT = """## Image Type
Professional DATA VISUALIZATION slide — chart + insights.

## Content
- Title: "{topic}"
- Data and insights: {content_hints}
- Layout emphasis: {design_direction}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Description line below title: 14px, gray
- CENTER: Clean chart visualization
  - Chart type: Donut/pie chart with percentage labels OR bar chart with value labels
  - Chart colors: {primary_color}, {accent_color}, #38A169, #F59E0B (harmonious palette)
  - Each segment has value label and short description positioned clearly
  - Generous inner radius for donut (clean, modern look)
- BELOW or SIDE: Key stat callouts in small white cards (metric + label)
- BOTTOM: Insight line in {primary_color}, bold, prefixed with 💡
- Data labels must be large enough to read at a glance

{visual_identity}

Generate this data visualization slide image now."""


ACTION_PLAN_PROMPT = """## Image Type
Professional ACTION PLAN / ROADMAP slide — phased execution timeline.

## Content
- Title: "{topic}"
- Phases/steps: {content_hints}
- Layout emphasis: {design_direction}

## Layout
- Title: Centered top, extra-bold, accent bar below
- VERTICAL TIMELINE flowing top to bottom:
  - Thin vertical line on left side ({primary_color} to {accent_color} gradient)
  - Numbered circles (36px) on the line as milestone markers
    - Alternate {primary_color} and {accent_color}
  - Each milestone → Card to the RIGHT:
    - White rounded rectangle, shadow, border
    - Bold phase title (e.g., "Phase 1: 기초 학습")
    - Period/duration in small {accent_color} text
    - Bullet points: • task items in gray
  - A small rocket or target icon at the top of the timeline
- Clear top-to-bottom visual flow, each phase distinct

{visual_identity}

Generate this action plan slide image now."""


HERO_PROMPT = """## Image Type
Professional HERO MESSAGE slide — single powerful statement.

## Content
- Main message: "{topic}"
- Supporting context: {content_hints}

## Layout
- The text IS the design — ultra minimal
- CENTER: Main message in VERY large bold text (52-64px equivalent)
  - Dark charcoal (#1A202C), centered vertically and horizontally
  - If an accent word is specified, color it with {primary_color}
  - Max 2 lines, generous line-height (1.2)
- BELOW: Subtitle in 20px, muted gray, centered, max 1-2 lines
- Background: Light #F5F7FA with a subtle oversized geometric shape behind text
  - e.g., large circle or rounded rectangle at 3-5% opacity using {accent_color}
- Extreme whitespace — let the message breathe
- NO cards, NO icons, NO grids — pure typographic impact

{visual_identity}

Generate this hero message slide image now."""


QUOTE_PROMPT = """## Image Type
Professional QUOTE slide — impactful citation or statement.

## Content
- Quote: Based on key points: {content_hints}
- Topic context: "{topic}"

## Layout
- Decorative large opening quotation mark (") in {accent_color}, 120px, opacity 15%, top-left area
- Vertical accent bar: 4px wide × 60px tall, {primary_color}, centered above quote
- QUOTE TEXT: 28-36px, bold, dark charcoal, centered, max width 650px, line-height 1.5
- Attribution: "— Source name" in 16px, muted gray, centered below quote
- Optional context line: 14px, muted gray, below attribution
- Extreme whitespace — the quote is the only content
- Warm, thoughtful, contemplative mood

{visual_identity}

Generate this quote slide image now."""


ICON_GRID_PROMPT = """## Image Type
Professional ICON GRID slide — 4-6 items in visual grid.

## Content
- Title: "{topic}"
- Items to display: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Description line: 14px, muted gray, centered
- GRID: 2×3 or 3×2 arrangement of cards
  - Each card: White, rounded-16px, shadow, centered content
  - TOP of card: Circular icon badge (56px)
    - Alternating {primary_color}/{accent_color} backgrounds
    - White emoji or flat icon inside
  - MIDDLE: Bold label (16px, dark), centered
  - BOTTOM: Short description (12px, gray), centered, max 2 lines
- All cards identical size, symmetric spacing (20px gaps)
- Grid centered on slide

{visual_identity}

Generate this icon grid slide image now."""


PROCESS_FLOW_PROMPT = """## Image Type
Professional PROCESS FLOW slide — step-by-step horizontal progression.

## Content
- Title: "{topic}"
- Steps: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Description line if applicable: 14px, gray, centered
- HORIZONTAL FLOW: 3-5 step cards connected by arrows
  - Each step: White rounded card (min-width 130px), shadow, border
    - TOP: Circular number/icon badge (44px, alternating {primary_color}/{accent_color})
    - MIDDLE: Bold step title (14px), centered
    - BOTTOM: Description (11px, gray), centered, max 3 lines
  - Between cards: Bold arrow "→" in {primary_color}, 24px
  - Cards arranged LEFT→RIGHT in a single horizontal row
  - Equal card sizes, symmetric spacing
- The arrow flow is the KEY visual element — clear progression

{visual_identity}

Generate this process flow slide image now."""


COMPARISON_PROMPT = """## Image Type
Professional COMPARISON slide — side-by-side contrast.

## Content
- Title: "{topic}"
- Comparison items: {content_hints}

## Layout
- Title: Centered top, extra-bold
- TWO COLUMNS with 24px gap between them:
  - LEFT COLUMN: "Before" / "Problem" / negative side
    - Header: Red (#E53E3E) circle badge with ✕ icon + bold label
    - White card with subtle warm tint (light red border-left)
    - List items with ✕ marks in red
  - RIGHT COLUMN: "After" / "Solution" / positive side
    - Header: Green (#38A169) circle badge with ✓ icon + bold label
    - White card with subtle cool tint (light green border-left)
    - List items with ✓ marks in green
- Both columns: Equal width, same card height, balanced visual weight
- Clear visual contrast between left (negative) and right (positive)

{visual_identity}

Generate this comparison slide image now."""


THREE_COLUMN_PROMPT = """## Image Type
Professional THREE COLUMN slide — three equal categories.

## Content
- Title: "{topic}"
- Columns: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Description line: 14px, gray, centered
- THREE EQUAL COLUMNS (each ~30% width):
  - Each column: Tall white card, rounded-16px, shadow, border
  - TOP: Large circular icon (56px)
    - Column 1: {primary_color}, Column 2: {accent_color}, Column 3: #38A169
    - White emoji inside
  - UPPER-MIDDLE: Bold title (17px, dark), centered
  - CENTER: Description (13px, gray), centered, max 4 lines
  - BOTTOM: Optional metric in large bold {primary_color} text (20px)
- All three columns identical height, symmetric, 20-24px gaps

{visual_identity}

Generate this three column slide image now."""


TIMELINE_PROMPT = """## Image Type
Professional TIMELINE slide — chronological event sequence.

## Content
- Title: "{topic}"
- Events: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Description line: 14px, gray, centered
- HORIZONTAL TIMELINE:
  - Thin horizontal line (3px) running left→right, gradient {primary_color}→{accent_color}
  - Event markers: Colored circles (40px) ON the line, alternating {primary_color}/{accent_color}
    - White emoji inside each circle
  - ABOVE each circle: Time/period label in 12px, {primary_color}, bold
  - BELOW each circle: White card (rounded-12px, shadow)
    - Bold event title (13px, dark), centered
    - Description (11px, gray), centered
- Events evenly spaced, clear left→right temporal progression
- Timeline line is the unifying visual spine

{visual_identity}

Generate this timeline slide image now."""


RISK_ANALYSIS_PROMPT = """## Image Type
Professional RISK ANALYSIS slide — severity-coded risk assessment.

## Content
- Title: "{topic}"
- Risks to display: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Description line: 14px, gray, centered
- STACKED RISK CARDS (3-5), each card:
  - White rounded rectangle, shadow, full width
  - LEFT EDGE: Color-coded severity bar (6px wide × full height)
    - HIGH: #E53E3E (red), MEDIUM: #F59E0B (amber), LOW: #38A169 (green)
  - LEFT inside: Severity badge "[HIGH]" / "[MEDIUM]" / "[LOW]" in matching color, bold, 12px
  - CENTER: Bold risk title (17px, dark) + description (13px, gray)
  - RIGHT or below: Mitigation text in {primary_color}, prefixed with →
- Cards stacked vertically with 12px gaps
- Color coding creates immediate visual priority ranking

{visual_identity}

Generate this risk analysis slide image now."""


SUMMARY_PROMPT = """## Image Type
Professional SUMMARY slide — numbered key takeaways.

## Content
- Title: "{topic}"
- Summary points: {content_hints}

## Layout
- Title: Centered top, extra-bold, accent bar below
- NUMBERED LIST of 3-5 takeaways, each as a card:
  - White rounded card, shadow, horizontal layout
  - LEFT: Large numbered circle (50px, {primary_color}, white bold number)
  - RIGHT of circle: Bold title (17px, dark) + description (13px, gray)
- Cards stacked vertically, centered on slide (max-width 700px)
- 12px gaps between cards
- Clean, conclusive feel — this wraps up the presentation

{visual_identity}

Generate this summary slide image now."""


CLOSING_PROMPT = """## Image Type
Professional CLOSING slide — thank you + resources.

## Content
- Title: "{topic}"
- Resources/links: {content_hints}

## Layout
- UPPER CENTER: Title in 36px, extra-bold, dark charcoal
- CENTER: Closing message (16px, muted gray), centered, max 2 lines
- LOWER CENTER: Row of RESOURCE CARDS (3-5):
  - Each card: White, rounded-16px, shadow, compact (120-160px wide)
  - Emoji at top (24px), centered
  - Bold label (13px), centered
  - Optional description (10px, gray), centered
  - Cards evenly spaced with 20px gaps
- Warm, professional, conclusive mood
- Generous whitespace above and below content

{visual_identity}

Generate this closing slide image now."""


GENERIC_PROMPT = """## Image Type
Professional presentation slide — {slide_type} layout.

## Content
- Title: "{topic}"
- Content details: {content_hints}
- Layout emphasis: {design_direction}

## Layout
- Title: Centered top, extra-bold, accent bar below
- Content arranged in clean, structured layout appropriate for this slide type
- Use white cards with shadows for content grouping
- Colored circle badges for icons/numbers using {primary_color} and {accent_color}
- Clear visual hierarchy: Title → Content → Details

{visual_identity}

Generate this slide image now."""


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

    Uses ICS framework (Image type + Content + Style) with shared visual identity.
    Embeds actual content text in double quotes for accurate Korean text rendering.
    """
    style = brief.get("style", {})
    slide_type = slide["type"]

    # Build rich content hints from available data
    key_points = slide.get("key_points", [])
    content_parts = []

    # Include topic context
    if brief.get("purpose"):
        content_parts.append(f"프레젠테이션 목적: {brief['purpose']}")
    if brief.get("key_message"):
        content_parts.append(f'핵심 메시지: "{brief["key_message"]}"')

    # Include actual key points in double quotes (Nano Banana renders these accurately)
    if key_points:
        content_parts.append("포함할 항목:")
        for i, pt in enumerate(key_points, 1):
            content_parts.append(f'  {i}. "{pt}"')

    # Include data for data visualization slides
    data = slide.get("data")
    if data:
        content_parts.append(f"데이터: {data}")

    # Include design direction
    design_dir = slide.get("design_direction", "")
    if design_dir:
        content_parts.append(f"디자인 방향: {design_dir}")

    content_hints = "\n".join(content_parts) if content_parts else f'주제: "{slide["topic"]}"'
    content_hints = _truncate_content(content_hints)

    # Build visual identity with actual colors
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

    # Select template
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

    # GENERIC_PROMPT uses slide_type, others don't
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
