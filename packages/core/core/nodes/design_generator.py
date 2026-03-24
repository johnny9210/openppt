"""
Phase 2-B: Design Generator
Generates PPT slide design images using Nano Banana (Gemini) via Send API.

Slide-type-specific prompts for optimal design output.
"""

import logging

from core.state import DesignGeneratorState
from core.services.nano_banana import generate_slide_image

logger = logging.getLogger(__name__)


# ── Type-specific prompt templates ──────────────────────────

COVER_PROMPT = """Create a professional presentation COVER slide image.

## Layout
- LEFT SIDE (60%): Title area
  - Main title: Large bold text "{topic}"
  - Subtitle below the title (smaller, lighter weight)
  - Presenter info at bottom-left: name, date, organization (small, gray text)
- RIGHT SIDE (40%): Visual illustration
  - A relevant diagram, icon composition, or illustration related to the topic
  - Icons connected with arrows/lines showing a workflow or concept map
  - Use colorful flat-style icons (cloud, database, email, document, rocket, gear, etc.)

## Design Style
- Background: Clean light gray/white (#F5F7FA or similar) with subtle geometric network pattern (thin lines + small dots)
- Small decorative gear/cog icons in top-left corner area (subtle, light gray)
- A circular badge/emblem in top-right area with a relevant icon inside
- Typography: Clean sans-serif (like Pretendard, Noto Sans KR), bold for title
- Color palette: Mostly grayscale background, with {primary_color} and {accent_color} for accent elements (arrows, highlights)
- Icons should be colorful but harmonious

## Content Hints
{content_hints}

## Requirements
- Aspect ratio: 16:9 widescreen
- Corporate, clean, professional look (NOT dark mode, NOT glassmorphism)
- Korean text must be rendered clearly with bold sans-serif font
- The overall feel should be modern, trustworthy, and business-appropriate
- Make the right-side illustration visually engaging and relevant to the topic

Generate the cover slide design image now."""


TOC_PROMPT = """Create a professional TABLE OF CONTENTS slide image.

## Layout
- Title "{topic}" centered at the top, large bold text with a short colored underline bar below it
- Items arranged in a ZIGZAG / STAGGERED layout:
  - Odd items (1, 3, 5): card on the LEFT side
  - Even items (2, 4): card on the RIGHT side
  - Numbered circles (1, 2, 3, 4, 5) running down the CENTER as a vertical timeline spine
- Each item card contains:
  - A relevant colorful flat icon on the left inside the card (gear, rocket, document, API, trophy, etc.)
  - Bold title text next to the icon
  - Smaller gray description text below the title
- Cards have rounded corners, light gray background (#F0F2F5), thin subtle border

## Design Style
- Background: Clean light/white (#F5F7FA) with subtle geometric network pattern (thin connecting lines + small dots)
- Decorative gear/cog icons cluster in top-left corner (subtle, light gray)
- Decorative circular badge in top-right corner with a relevant icon (like a list/menu icon or workflow icon)
- Number circles: colored with {primary_color} or {accent_color}, white number text inside
  - Alternate colors between items for visual rhythm (e.g., blue for 1,3,5 and orange/red for 2,4)
- Typography: Clean sans-serif (Pretendard/Noto Sans KR style), bold for card titles
- Cards: Rounded rectangle, light fill, subtle shadow

## Content Hints
{content_hints}

## Requirements
- Aspect ratio: 16:9 widescreen
- Clean, professional, corporate presentation look
- NOT dark mode - use light background
- Korean text must be clearly rendered with bold sans-serif font
- The zigzag layout with center number spine is the KEY visual element
- Make it look organized and easy to follow

Generate the table of contents slide design image now."""


KEY_POINTS_PROMPT = """Create a professional KEY POINTS slide image.

## Layout
- Title "{topic}" centered at the top, large bold text with a short colored underline bar below it
- 2x2 GRID of cards below the title, evenly spaced with generous gaps
- Each card contains:
  - LEFT: A large circular icon badge (60-70px diameter) with a colorful background
    - Use warm colors like coral/orange (#E8734A) or cool colors like blue (#6BA3D6) for circle backgrounds
    - Alternate colors between cards for visual variety
    - Flat-style white icon inside (cloud, envelope, rocket, API, database, gear, etc.)
  - RIGHT of the icon: Bold title text + smaller gray description text below (2 lines max)
- Cards have rounded corners, very light gray fill (#F0F2F5), thin subtle border

## Design Style
- Background: Clean light/white (#F5F7FA) with subtle geometric network pattern (thin connecting lines + small dots)
- Decorative gear/cog icons cluster in top-left corner (subtle, light gray)
- Decorative circular badge in top-right corner with a relevant icon
- Typography: Clean sans-serif (Pretendard/Noto Sans KR style)
  - Card titles: Bold, dark (#333333), ~18-20px
  - Card descriptions: Regular weight, gray (#666666), ~14px
- Cards should feel like uniform, balanced tiles

## Content Hints
{content_hints}

## Requirements
- Aspect ratio: 16:9 widescreen
- Clean, professional, corporate look - NOT dark mode
- Korean text must be clearly rendered with bold sans-serif font
- The 2x2 grid with large circular icons is the KEY visual element
- Each card should be the same size and aligned symmetrically

Generate the key points slide design image now."""


DATA_VIZ_PROMPT = """Create a professional DATA VISUALIZATION slide image.

## Layout
- Title "{topic}" centered at the top, large bold text with a short colored underline bar below it
- LEFT SIDE (50-60%): Chart area
  - A decorative icon badge in top-left (e.g., bar chart icon inside a gray circle)
  - Section subtitle (e.g., "주요 성과 데이터") in bold
  - Large DONUT/PIE CHART centered, with percentage labels around it
    - Each segment has a % value label positioned outside the chart
    - Short description text next to each % label (e.g., "자동화 비율 50%", "처리 시간 단축 13%")
  - Key stat callouts above the chart (e.g., "자동화 성공률 98%", "업무 시간 35% 단축")
  - Small note text at the bottom of the chart area
- Chart colors: Use warm/cool palette - orange (#E8944A), blue (#4A7AB5), dark blue (#2C4A6E), light blue (#6BA3D6), gray

## Design Style
- Background: Clean light/white (#F5F7FA) with subtle geometric network pattern (thin connecting lines + small dots)
- Decorative gear/cog icons cluster in top-left corner (subtle, light gray)
- Decorative circular badge in top-right corner
- Typography: Clean sans-serif, bold for titles and percentages
- Chart: Clean donut chart with generous inner radius, no 3D effects
- Layout direction: {design_direction}

## Content Hints
{content_hints}

## Requirements
- Aspect ratio: 16:9 widescreen
- Clean, professional, corporate look - NOT dark mode
- Korean text must be clearly rendered with bold sans-serif font
- Data labels must be easy to read at a glance
- The donut chart with surrounding stat callouts is the KEY visual element

Generate the data visualization slide design image now."""


ACTION_PLAN_PROMPT = """Create a professional ACTION PLAN / TIMELINE slide image.

## Layout
- Title "{topic}" centered at the top, large bold text with a short colored underline bar below it
- A decorative icon at the top of the timeline (e.g., rocket icon)
- VERTICAL TIMELINE flowing top to bottom:
  - A thin vertical line running down the center-left area
  - Numbered circles (1, 2, 3...) on the line as milestone markers
    - Use {primary_color} or {accent_color} for circle backgrounds, white number text
  - Each step has a CARD to the right of the numbered circle:
    - Card has rounded corners, light gray fill (#F0F2F5), thin border
    - Bold title text (e.g., "1단계: 기초 학습 및 환경 설정")
    - Bullet points below the title with key tasks (• item1, • item2)
  - Cards are stacked vertically with clear spacing between them

## Design Style
- Background: Clean light/white (#F5F7FA) with subtle geometric network pattern (thin connecting lines + small dots)
- Decorative gear/cog icons cluster in top-left corner (subtle, light gray)
- Decorative circular badge in top-right corner
- Typography: Clean sans-serif (Pretendard/Noto Sans KR style)
  - Step titles: Bold, dark (#333333)
  - Bullet items: Regular, gray (#555555)
- Timeline line: Thin gray (#CCCCCC) vertical line
- Number circles: ~36px diameter, colored background
- Layout direction: {design_direction}

## Content Hints
{content_hints}

## Requirements
- Aspect ratio: 16:9 widescreen
- Clean, professional, corporate look - NOT dark mode
- Korean text must be clearly rendered with bold sans-serif font
- The vertical timeline with numbered circles and side cards is the KEY visual element
- Steps should flow naturally from top to bottom

Generate the action plan slide design image now."""


GENERIC_PROMPT = """Create a professional presentation slide design.

## Slide Specifications
- Type: {slide_type}
- Topic: {topic}
- Layout Direction: {design_direction}

## Design Style
- Background: Clean light gray/white (#F5F7FA) with subtle geometric network pattern
- Cards/sections: White background with thin borders, slight shadows
- Typography: Clean sans-serif, clear hierarchy
  - Main title: Large (42-52px equivalent), bold
  - Subtitles: Medium (20-24px equivalent)
  - Body: Small (14-15px equivalent), gray
- Colors:
  - Primary: {primary_color}
  - Accent: {accent_color}
  - Text: Dark gray (#333333)
- Decorations: Flat-style icons, subtle connecting lines

## Content to Include
{content_hints}

## Requirements
- Aspect ratio: 16:9 widescreen
- Professional, clean, corporate look
- Korean text clearly rendered with bold sans-serif
- Visual hierarchy to guide the eye

Generate the slide design image now."""


# ── Template selection ──────────────────────────

TYPE_PROMPT_MAP = {
    "cover": COVER_PROMPT,
    "table_of_contents": TOC_PROMPT,
    "key_points": KEY_POINTS_PROMPT,
    "data_visualization": DATA_VIZ_PROMPT,
    "action_plan": ACTION_PLAN_PROMPT,
    "risk_analysis": KEY_POINTS_PROMPT,  # reuse key_points layout
}


def _build_design_prompt(slide: dict, brief: dict) -> str:
    """Build Nano Banana prompt for slide design generation.

    Selects a type-specific template for better design output.
    """
    style = brief.get("style", {})
    slide_type = slide["type"]

    key_points = slide.get("key_points", [])
    content_hints = "\n".join(f"- {pt}" for pt in key_points) if key_points else "General content"

    data = slide.get("data")
    if data:
        content_hints += f"\n- Data: {data}"

    template = TYPE_PROMPT_MAP.get(slide_type, GENERIC_PROMPT)

    format_kwargs = {
        "topic": slide["topic"],
        "design_direction": slide.get("design_direction", "Professional layout"),
        "primary_color": style.get("primary_color", "#6366F1"),
        "accent_color": style.get("accent_color", "#818CF8"),
        "text_color": style.get("text_color", "#333333"),
        "content_hints": content_hints,
    }

    # GENERIC_PROMPT uses slide_type, others don't
    if slide_type not in TYPE_PROMPT_MAP:
        format_kwargs["slide_type"] = slide_type

    return template.format(**format_kwargs)


async def design_generator(state: DesignGeneratorState) -> dict:
    """Generate design image for a single slide via Nano Banana."""
    slide = state["slide_plan"]
    brief = state["research_brief"]

    prompt = _build_design_prompt(slide, brief)

    logger.info("[DesignGen] START %s (%s) - prompt: %d chars", slide["slide_id"], slide["type"], len(prompt))
    image_b64 = await generate_slide_image(prompt, aspect_ratio="16:9")

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
