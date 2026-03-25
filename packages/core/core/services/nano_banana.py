"""
Nano Banana - Gemini Image Generation Service
Google AI Studio API for PPT slide design generation.

Follows the same API pattern as aidx/search_api GoogleNanoBanana.
"""

import json
import logging
import re

import httpx

from core.config import GOOGLE_AI_STUDIO_KEY, GEMINI_IMAGE_MODEL

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _optimize_prompt_for_korean(prompt: str) -> str:
    """Optimize image prompt for Korean text accuracy.

    Matches aidx/search_api pattern: if quoted Korean text is found,
    convert to JSON format for better rendering accuracy.
    """
    korean_pattern = re.compile(r"[가-힣]+")
    if not korean_pattern.search(prompt):
        return prompt

    # Check for quoted Korean text
    quoted_pattern = re.compile(r"""['"]([^'"]*[가-힣][^'"]*)['"]""")
    quoted_matches = quoted_pattern.findall(prompt)

    if quoted_matches:
        korean_text = quoted_matches[0]
        structured = json.dumps(
            {
                "text_content": korean_text,
                "font_style": "Bold Sans-serif",
                "description": prompt,
            },
            ensure_ascii=False,
        )
        logger.info("[NanoBanana] Korean text optimized: '%s'", korean_text)
        return structured

    # Fallback: append Korean rendering instructions
    return (
        f"{prompt}\n\n"
        "IMPORTANT: For any Korean text in the design, render it clearly with "
        "a bold sans-serif font. Ensure Korean characters are legible and properly spaced."
    )


async def generate_slide_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
    reference_image_b64: str | None = None,
    thinking_budget: int | None = None,
) -> str | None:
    """Generate a PPT slide design image via Nano Banana (Gemini).

    Uses the same payload structure as aidx/search_api GoogleGeminiImageRequest.
    Returns base64-encoded image string, or None on failure.

    Args:
        prompt: Design prompt text.
        aspect_ratio: Image aspect ratio (default 16:9).
        image_size: Output resolution (1K, 2K, 4K).
        reference_image_b64: Optional cover slide image for style consistency.
        thinking_budget: Optional thinking tokens for complex layouts.
    """
    optimized = _optimize_prompt_for_korean(prompt)
    url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent"

    # Build multimodal parts: optional reference image + text prompt
    parts = []
    if reference_image_b64:
        parts.append({
            "inlineData": {
                "mimeType": "image/png",
                "data": reference_image_b64,
            }
        })
        logger.info("[NanoBanana] Reference image attached: %d bytes", len(reference_image_b64))
    parts.append({"text": optimized})

    generation_config = {
        "imageConfig": {
            "aspectRatio": aspect_ratio,
            "imageSize": image_size,
        }
    }
    if thinking_budget:
        generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
        logger.info("[NanoBanana] Thinking mode enabled: budget=%d", thinking_budget)

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": generation_config,
    }

    headers = {
        "x-goog-api-key": GOOGLE_AI_STUDIO_KEY,
        "Content-Type": "application/json",
    }

    logger.info("[NanoBanana] Model: %s", GEMINI_IMAGE_MODEL)
    logger.info("[NanoBanana] Request URL: %s", url)
    logger.info("[NanoBanana] Prompt length: %d chars, aspect: %s, size: %s",
                len(optimized), aspect_ratio, image_size)
    logger.info("[NanoBanana] API key present: %s (len=%d)",
                bool(GOOGLE_AI_STUDIO_KEY), len(GOOGLE_AI_STUDIO_KEY))

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            logger.info("[NanoBanana] Response status: %d", resp.status_code)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[NanoBanana] HTTP error %d: %s",
                     exc.response.status_code, exc.response.text[:500])
        return None
    except Exception as exc:
        logger.error("[NanoBanana] API call failed: %s", exc)
        return None

    candidates = data.get("candidates", [])
    logger.info("[NanoBanana] Candidates count: %d", len(candidates))
    if not candidates:
        logger.warning("[NanoBanana] No candidates. Response keys: %s", list(data.keys()))
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    logger.info("[NanoBanana] Parts count: %d, types: %s",
                len(parts), [list(p.keys()) for p in parts])

    image_data = None
    text_content = None
    for part in parts:
        if "inlineData" in part:
            image_data = part["inlineData"].get("data", "")
        elif "text" in part:
            text_content = part.get("text", "")

    if image_data:
        logger.info("[NanoBanana] Image OK, size: %d bytes (base64)", len(image_data))
        if text_content:
            logger.info("[NanoBanana] Text response: %s", text_content[:200])
        return image_data

    logger.warning("[NanoBanana] No image data in response. Parts: %s",
                   [list(p.keys()) for p in parts])
    return None
