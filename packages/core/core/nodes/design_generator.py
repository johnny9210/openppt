"""
Phase 2-B: Design Generator
Generates PPT slide design images using Nano Banana (Gemini) via Send API.
"""

import logging

from core.state import DesignGeneratorState
from core.services.nano_banana import generate_slide_image

logger = logging.getLogger(__name__)

DESIGN_PROMPT_TEMPLATE = """Create a premium, professional presentation slide design.

## Slide Specifications
- Type: {slide_type}
- Topic: {topic}
- Layout Direction: {design_direction}

## Design System
- Style: Modern Dark Glassmorphism
- Background: Deep dark (#050810 or similar very dark blue-black)
- Cards: Frosted glass effect (semi-transparent white, subtle borders)
- Typography: Clean sans-serif, clear hierarchy
  - Main title: Large (42-52px equivalent), bold
  - Subtitles: Medium (20-24px equivalent)
  - Body: Small (14-15px equivalent), slightly transparent
- Colors:
  - Primary: {primary_color}
  - Accent: {accent_color}
  - Text: Light ({text_color})
- Decorations: Accent bars, icon badges with emoji, subtle gradients

## Content to Include
{content_hints}

## Requirements
- Aspect ratio: 16:9 (widescreen presentation)
- Professional business presentation quality
- All text should be clearly readable
- Use visual hierarchy to guide the eye
- Include decorative elements appropriate for the slide type
- Make it visually stunning and modern

Generate the slide design image now."""


def _build_design_prompt(slide: dict, brief: dict) -> str:
    """Build Nano Banana prompt for slide design generation."""
    style = brief.get("style", {})

    key_points = slide.get("key_points", [])
    content_hints = "\n".join(f"- {pt}" for pt in key_points) if key_points else "General content"

    data = slide.get("data")
    if data:
        content_hints += f"\n- Data: {data}"

    return DESIGN_PROMPT_TEMPLATE.format(
        slide_type=slide["type"],
        topic=slide["topic"],
        design_direction=slide.get("design_direction", "Professional layout"),
        primary_color=style.get("primary_color", "#6366F1"),
        accent_color=style.get("accent_color", "#818CF8"),
        text_color=style.get("text_color", "#E2E8F0"),
        content_hints=content_hints,
    )


async def design_generator(state: DesignGeneratorState) -> dict:
    """Generate design image for a single slide via Nano Banana."""
    slide = state["slide_plan"]
    brief = state["research_brief"]

    prompt = _build_design_prompt(slide, brief)

    logger.info("Generating design for %s (%s)", slide["slide_id"], slide["type"])
    image_b64 = await generate_slide_image(prompt, aspect_ratio="16:9")

    if not image_b64:
        logger.warning(
            "Design generation failed for %s, continuing without image",
            slide["slide_id"],
        )

    return {
        "slide_designs": [{
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "image_b64": image_b64,
            "design_prompt": prompt,
        }]
    }
