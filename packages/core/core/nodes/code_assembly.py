"""
Phase 2-C: Code Assembly (HTML Edition)
Merges individual HTML slide snippets into a single HTML presentation document.

Each slide provides:
  <style>.slide_NNN { ... }</style>
  <div class="slide-container slide_NNN"> ... </div>

Assembly wraps all slides in a complete HTML document with:
  - CDN links (Google Fonts, Tailwind, FontAwesome)
  - Tailwind custom theme config
  - Common base styles
  - Navigation JavaScript
"""

import json
import re
from core.state import PPTState


def _extract_slide_parts(code: str) -> tuple[str, str]:
    """Separate <style> blocks from slide HTML content.

    Returns (styles_str, html_str).
    """
    styles = []
    remaining = code

    # Extract all <style>...</style> blocks
    for m in re.finditer(r"<style>([\s\S]*?)</style>", code):
        styles.append(m.group(0))

    # Remove style blocks from the HTML
    remaining = re.sub(r"<style>[\s\S]*?</style>\s*", "", remaining).strip()

    return "\n".join(styles), remaining


# Use $PLACEHOLDER$ syntax to avoid Python .format() clashing with JS braces.
_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            primary: '$PRIMARY$',
            accent: '$ACCENT$',
            heading: '$HEADING$',
            body: '#64748B',
            card: '#FFFFFF',
            'card-border': '#E2E8F0',
            'slide-bg': '$SLIDE_BG$',
            danger: '#E53E3E',
            warning: '#F59E0B',
            success: '#38A169',
          },
          boxShadow: {
            card: '0 2px 8px rgba(0,0,0,0.06)',
            'card-hover': '0 8px 24px rgba(0,0,0,0.12)',
          }
        }
      }
    };
  </script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Noto Sans KR', sans-serif;
      background-color: #E8ECF1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .slide-container {
      width: 1280px;
      height: 720px;
      display: none;
      flex-direction: column;
      background-color: #ffffff;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .slide-container.active {
      display: flex;
    }
  </style>
$SLIDE_STYLES$
</head>
<body>
  <div id="presentation">
$SLIDE_CONTENT$
  </div>

  <script>
    // ── Navigation ───────────────────────────────────────────
    var current = 0;
    var slides = document.querySelectorAll('.slide-container');
    var total = slides.length;

    function goTo(i) {
      if (total === 0) return;
      slides[current].classList.remove('active');
      current = Math.max(0, Math.min(total - 1, i));
      slides[current].classList.add('active');
      try { window.parent.postMessage({ type: 'slideChange', index: current }, '*'); } catch(e) {}
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowLeft') goTo(current - 1);
      if (e.key === 'ArrowRight') goTo(current + 1);
    });

    window.addEventListener('message', function(e) {
      if (e.data && e.data.type === 'goToSlide') goTo(e.data.index);
      if (e.data && e.data.type === 'captureSlide') captureSlide(e.data.index);
    });

    window.__goToSlide = goTo;

    // Initialize first slide
    if (slides.length > 0) slides[0].classList.add('active');

    // ── Capture support ──────────────────────────────────────
    function captureSlide(index) {
      if (typeof html2canvas === 'undefined') {
        window.parent.postMessage({ type: 'captureResult', index: index, dataUrl: '' }, '*');
        return;
      }
      // Test capture (index -1): confirm html2canvas is available
      if (index === -1) {
        window.parent.postMessage({ type: 'captureResult', index: -1, dataUrl: 'ok' }, '*');
        return;
      }
      // Navigate to target slide
      var prev = current;
      goTo(index);
      setTimeout(function() {
        var target = slides[index];
        if (!target) {
          window.parent.postMessage({ type: 'captureResult', index: index, dataUrl: '' }, '*');
          return;
        }
        html2canvas(target, { scale: 2, useCORS: true, backgroundColor: null, logging: false })
          .then(function(canvas) {
            window.parent.postMessage({ type: 'captureResult', index: index, dataUrl: canvas.toDataURL('image/png') }, '*');
          })
          .catch(function() {
            window.parent.postMessage({ type: 'captureResult', index: index, dataUrl: '' }, '*');
          });
      }, 300);
    }
  </script>
  <script src="https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js" async></script>
</body>
</html>'''


def code_assembly(state: PPTState) -> dict:
    """Assemble individual HTML slides into a complete HTML presentation document."""
    style = state.get("research_brief", {}).get("style", {})
    generated_slides = state["generated_slides"]

    primary = style.get("primary_color", "#6366F1")
    accent = style.get("accent_color", "#818CF8")
    slide_bg = style.get("background", "#F5F7FA")
    heading = style.get("text_color", "#1A202C")

    # Deduplicate by slide_id (keep latest on retries, since operator.add appends)
    seen = {}
    for slide in generated_slides:
        seen[slide["slide_id"]] = slide
    generated_slides = sorted(seen.values(), key=lambda s: s["slide_id"])

    all_styles = []
    all_content = []

    for i, slide in enumerate(generated_slides):
        code = slide["code"]
        slide_style, slide_html = _extract_slide_parts(code)

        # Collect styles
        if slide_style:
            all_styles.append(f"  <!-- {slide['slide_id']} ({slide['type']}) -->")
            all_styles.append(f"  {slide_style}")

        # First slide gets 'active' class
        if i == 0 and "active" not in slide_html:
            slide_html = slide_html.replace(
                'class="slide-container',
                'class="slide-container active',
                1,
            )

        all_content.append(f"    <!-- {slide['slide_id']} ({slide['type']}) -->")
        all_content.append(f"    {slide_html}")

    # Build the full HTML document using placeholder replacement
    full_code = _TEMPLATE
    full_code = full_code.replace("$PRIMARY$", primary)
    full_code = full_code.replace("$ACCENT$", accent)
    full_code = full_code.replace("$SLIDE_BG$", slide_bg)
    full_code = full_code.replace("$HEADING$", heading)
    full_code = full_code.replace("$SLIDE_STYLES$", "\n".join(all_styles))
    full_code = full_code.replace("$SLIDE_CONTENT$", "\n".join(all_content))

    # Build backward-compatible slide_spec for validators
    contents_map = {c["slide_id"]: c for c in state.get("slide_contents", [])}
    slides_for_spec = []
    for slide in generated_slides:
        content = contents_map.get(slide["slide_id"], {}).get("content", {})
        slides_for_spec.append({
            "slide_id": slide["slide_id"],
            "type": slide["type"],
            "content": content,
        })

    slide_spec = {
        "ppt_state": {
            "presentation": {
                "meta": {
                    "title": state.get("research_brief", {}).get("purpose", ""),
                    "theme": {
                        "primary_color": primary,
                        "accent_color": accent,
                        "background": slide_bg,
                        "text_color": heading,
                    },
                },
                "slides": slides_for_spec,
            }
        }
    }

    return {"react_code": full_code, "slide_spec": slide_spec}
