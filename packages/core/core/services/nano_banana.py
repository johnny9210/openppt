"""
Nano Banana - Gemini Image Generation Service
Google AI Studio API for PPT slide design generation.
"""

import logging
import re

import httpx

from core.config import GOOGLE_AI_STUDIO_KEY, GEMINI_IMAGE_MODEL

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _optimize_prompt_for_korean(prompt: str) -> str:
    """Add Korean text rendering instructions if Korean is detected."""
    if not re.search(r"[가-힣]", prompt):
        return prompt
    return (
        f"{prompt}\n\n"
        "IMPORTANT: For any Korean text in the design, render it clearly with "
        "a bold sans-serif font. Ensure Korean characters are legible and properly spaced."
    )


async def generate_slide_image(
    prompt: str,
    aspect_ratio: str = "16:9",
) -> str | None:
    """Generate a PPT slide design image via Nano Banana (Gemini).

    Returns base64-encoded image string, or None on failure.
    """
    optimized = _optimize_prompt_for_korean(prompt)
    url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": optimized}]}],
        "generationConfig": {
            "responseModalities": ["image", "text"],
        },
    }

    headers = {
        "x-goog-api-key": GOOGLE_AI_STUDIO_KEY,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Nano Banana API call failed: %s", exc)
        return None

    candidates = data.get("candidates", [])
    if not candidates:
        logger.warning("Nano Banana returned no candidates")
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            return part["inlineData"]["data"]

    logger.warning("Nano Banana response has no image data")
    return None
