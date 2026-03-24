"""
PPTX Exporter
Converts pipeline output (slide_spec + slide_contents + slide_designs) to .pptx file.

Strategy:
  - Each slide uses the design image as a full-bleed background
  - Structured text content is overlaid on top
  - Theme colors from research_brief.style are applied to text elements
"""

import base64
import io
import logging
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

logger = logging.getLogger(__name__)

# Slide dimensions: 16:9 widescreen
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def _hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert #RRGGBB to RGBColor."""
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _add_background_image(slide, image_b64: str) -> None:
    """Add a base64 PNG as a full-bleed background image."""
    image_bytes = base64.b64decode(image_b64)
    image_stream = io.BytesIO(image_bytes)
    slide.shapes.add_picture(
        image_stream,
        Emu(0), Emu(0),
        SLIDE_WIDTH, SLIDE_HEIGHT,
    )


def _add_textbox(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: int = 18,
    color: RGBColor = RGBColor(0xFF, 0xFF, 0xFF),
    bold: bool = False,
    alignment: PP_ALIGN = PP_ALIGN.LEFT,
) -> Any:
    """Add a text box to a slide and return the text frame."""
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = alignment
    return tf


def _add_paragraph(
    text_frame,
    text: str,
    font_size: int = 14,
    color: RGBColor = RGBColor(0xE2, 0xE8, 0xF0),
    bold: bool = False,
    space_before: int = 6,
) -> None:
    """Append a paragraph to an existing text frame."""
    p = text_frame.add_paragraph()
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.space_before = Pt(space_before)


# ── Slide type renderers ──────────────────────────────

def _render_cover(slide, content: dict, theme: dict) -> None:
    """Render cover slide with title, subtitle, presenter, date."""
    primary = _hex_to_rgb(theme.get("primary_color", "#6366F1"))
    text_color = _hex_to_rgb(theme.get("text_color", "#E2E8F0"))

    # Title
    _add_textbox(
        slide, 1.5, 2.0, 10.3, 1.5,
        content.get("title", ""),
        font_size=40, color=text_color, bold=True,
        alignment=PP_ALIGN.CENTER,
    )
    # Subtitle
    _add_textbox(
        slide, 2.5, 3.8, 8.3, 0.8,
        content.get("subtitle", ""),
        font_size=20, color=primary,
        alignment=PP_ALIGN.CENTER,
    )
    # Presenter + Date
    bottom_text = ""
    if content.get("presenter"):
        bottom_text += content["presenter"]
    if content.get("date"):
        if bottom_text:
            bottom_text += "  |  "
        bottom_text += content["date"]
    if bottom_text:
        _add_textbox(
            slide, 2.5, 5.5, 8.3, 0.5,
            bottom_text,
            font_size=14, color=text_color,
            alignment=PP_ALIGN.CENTER,
        )


def _render_table_of_contents(slide, content: dict, theme: dict) -> None:
    """Render table of contents slide."""
    text_color = _hex_to_rgb(theme.get("text_color", "#E2E8F0"))
    accent = _hex_to_rgb(theme.get("accent_color", "#818CF8"))

    _add_textbox(
        slide, 1.0, 0.5, 11.3, 0.8,
        content.get("title", "Contents"),
        font_size=32, color=text_color, bold=True,
    )

    items = content.get("items", [])
    y = 1.8
    for item in items:
        number = item.get("number", "")
        title = item.get("title", "")
        desc = item.get("description", "")

        tf = _add_textbox(
            slide, 1.5, y, 10.0, 0.4,
            f"{number}.  {title}",
            font_size=20, color=accent, bold=True,
        )
        if desc:
            _add_paragraph(tf, desc, font_size=14, color=text_color)
        y += 0.9


def _render_data_visualization(slide, content: dict, theme: dict) -> None:
    """Render data visualization slide with text summary (chart is in background image)."""
    text_color = _hex_to_rgb(theme.get("text_color", "#E2E8F0"))
    accent = _hex_to_rgb(theme.get("accent_color", "#818CF8"))

    _add_textbox(
        slide, 0.8, 0.4, 11.7, 0.7,
        content.get("title", ""),
        font_size=28, color=text_color, bold=True,
    )

    if content.get("description"):
        _add_textbox(
            slide, 0.8, 1.2, 11.7, 0.5,
            content["description"],
            font_size=14, color=text_color,
        )

    # Data table as text (right side, since chart is often rendered in the design image)
    data = content.get("data", [])
    if data:
        y = 2.0
        tf = _add_textbox(
            slide, 8.5, y, 4.0, 0.4,
            f"({content.get('chart_type', 'chart')})",
            font_size=12, color=accent,
        )
        for item in data[:8]:
            name = item.get("name", "")
            value = item.get("value", "")
            _add_paragraph(tf, f"{name}: {value}", font_size=12, color=text_color)

    if content.get("insight"):
        _add_textbox(
            slide, 0.8, 6.2, 11.7, 0.6,
            f"Insight: {content['insight']}",
            font_size=14, color=accent, bold=True,
        )


def _render_key_points(slide, content: dict, theme: dict) -> None:
    """Render key points slide."""
    text_color = _hex_to_rgb(theme.get("text_color", "#E2E8F0"))
    accent = _hex_to_rgb(theme.get("accent_color", "#818CF8"))

    _add_textbox(
        slide, 1.0, 0.4, 11.3, 0.7,
        content.get("title", ""),
        font_size=28, color=text_color, bold=True,
    )

    if content.get("description"):
        _add_textbox(
            slide, 1.0, 1.2, 11.3, 0.5,
            content["description"],
            font_size=14, color=text_color,
        )

    points = content.get("points", [])
    y = 2.0
    for pt in points:
        emoji = pt.get("emoji", "")
        title = pt.get("title", "")
        desc = pt.get("description", "")
        metric = pt.get("metric", "")

        header = f"{emoji}  {title}"
        if metric:
            header += f"  ({metric})"

        tf = _add_textbox(
            slide, 1.2, y, 10.8, 0.4,
            header,
            font_size=18, color=accent, bold=True,
        )
        if desc:
            _add_paragraph(tf, desc, font_size=13, color=text_color)
        y += 1.0


def _render_risk_analysis(slide, content: dict, theme: dict) -> None:
    """Render risk analysis slide."""
    text_color = _hex_to_rgb(theme.get("text_color", "#E2E8F0"))
    accent = _hex_to_rgb(theme.get("accent_color", "#818CF8"))

    LEVEL_COLORS = {
        "high": RGBColor(0xE5, 0x3E, 0x3E),
        "medium": RGBColor(0xF6, 0xC9, 0x0E),
        "low": RGBColor(0x38, 0xA1, 0x69),
    }

    _add_textbox(
        slide, 1.0, 0.4, 11.3, 0.7,
        content.get("title", ""),
        font_size=28, color=text_color, bold=True,
    )

    if content.get("description"):
        _add_textbox(
            slide, 1.0, 1.2, 11.3, 0.5,
            content["description"],
            font_size=14, color=text_color,
        )

    risks = content.get("risks", [])
    y = 2.0
    for risk in risks:
        level = risk.get("level", "medium")
        level_color = LEVEL_COLORS.get(level, accent)
        title = risk.get("title", "")
        desc = risk.get("description", "")
        mitigation = risk.get("mitigation", "")

        tf = _add_textbox(
            slide, 1.2, y, 10.8, 0.4,
            f"[{level.upper()}]  {title}",
            font_size=18, color=level_color, bold=True,
        )
        if desc:
            _add_paragraph(tf, desc, font_size=13, color=text_color)
        if mitigation:
            _add_paragraph(tf, f"  -> {mitigation}", font_size=12, color=accent)
        y += 1.1


def _render_action_plan(slide, content: dict, theme: dict) -> None:
    """Render action plan slide."""
    text_color = _hex_to_rgb(theme.get("text_color", "#E2E8F0"))
    accent = _hex_to_rgb(theme.get("accent_color", "#818CF8"))

    _add_textbox(
        slide, 1.0, 0.4, 11.3, 0.7,
        content.get("title", ""),
        font_size=28, color=text_color, bold=True,
    )

    if content.get("description"):
        _add_textbox(
            slide, 1.0, 1.2, 11.3, 0.5,
            content["description"],
            font_size=14, color=text_color,
        )

    actions = content.get("actions", [])
    y = 2.0
    for action in actions:
        phase = action.get("phase", "")
        title = action.get("title", "")
        period = action.get("period", "")
        tasks = action.get("tasks", [])

        header = f"{phase}: {title}"
        if period:
            header += f"  ({period})"

        tf = _add_textbox(
            slide, 1.2, y, 10.8, 0.4,
            header,
            font_size=18, color=accent, bold=True,
        )
        for task in tasks:
            _add_paragraph(tf, f"  - {task}", font_size=13, color=text_color)
        y += 1.1


# Renderer dispatch
RENDERERS = {
    "cover": _render_cover,
    "table_of_contents": _render_table_of_contents,
    "data_visualization": _render_data_visualization,
    "key_points": _render_key_points,
    "risk_analysis": _render_risk_analysis,
    "action_plan": _render_action_plan,
}


def export_pptx(
    slide_spec: dict,
    slide_contents: list[dict],
    slide_designs: list[dict],
) -> io.BytesIO:
    """Generate a .pptx file from pipeline output.

    Args:
        slide_spec: The ppt_state spec with presentation metadata and slide list.
        slide_contents: List of {slide_id, type, content} from text_generator.
        slide_designs: List of {slide_id, type, image_b64} from design_generator.

    Returns:
        BytesIO buffer containing the .pptx file.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # Use blank layout
    blank_layout = prs.slide_layouts[6]  # Blank

    # Build lookup maps
    ppt_state = slide_spec.get("ppt_state", slide_spec)
    presentation = ppt_state.get("presentation", {})
    meta = presentation.get("meta", {})
    theme = meta.get("theme", {})
    slides = presentation.get("slides", [])

    contents_map = {c["slide_id"]: c.get("content", {}) for c in slide_contents}
    designs_map = {d["slide_id"]: d.get("image_b64") for d in slide_designs}

    for slide_data in slides:
        slide_id = slide_data["slide_id"]
        slide_type = slide_data["type"]
        content = slide_data.get("content") or contents_map.get(slide_id, {})
        image_b64 = designs_map.get(slide_id)

        slide = prs.slides.add_slide(blank_layout)

        # Background image (if available)
        if image_b64:
            try:
                _add_background_image(slide, image_b64)
            except Exception as e:
                logger.warning("Failed to add background for %s: %s", slide_id, e)

        # Render text content by type
        renderer = RENDERERS.get(slide_type)
        if renderer:
            try:
                renderer(slide, content, theme)
            except Exception as e:
                logger.warning("Failed to render %s (%s): %s", slide_id, slide_type, e)
                _add_textbox(
                    slide, 1.0, 3.0, 11.0, 1.0,
                    f"{slide_type}: {content.get('title', slide_id)}",
                    font_size=24,
                    color=_hex_to_rgb(theme.get("text_color", "#E2E8F0")),
                    bold=True,
                    alignment=PP_ALIGN.CENTER,
                )
        else:
            # Fallback: just show the title
            _add_textbox(
                slide, 1.0, 3.0, 11.0, 1.0,
                content.get("title", slide_id),
                font_size=24,
                color=_hex_to_rgb(theme.get("text_color", "#E2E8F0")),
                bold=True,
                alignment=PP_ALIGN.CENTER,
            )

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
