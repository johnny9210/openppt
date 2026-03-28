"""
MinIO client for PPT code storage.
Pattern from aidx/ai_apis/file_extractor_api/app/services/minio_utils.py
"""

import base64
import io
import json
import logging
import os

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

BUCKET_NAME = "ppt"

_client: Minio | None = None


def get_minio_client() -> Minio | None:
    global _client
    if _client is not None:
        return _client
    try:
        client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        client.list_buckets()
        _client = client
        logger.info("[MinIO] Connected: %s", MINIO_ENDPOINT)
        return _client
    except Exception as e:
        logger.warning("[MinIO] Connection failed: %s", e)
        return None


def _ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket_name=bucket):
        client.make_bucket(bucket_name=bucket)
        logger.info("[MinIO] Created bucket: %s", bucket)


def upload_data(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    bucket: str = BUCKET_NAME,
) -> bool:
    """Upload raw bytes to MinIO."""
    try:
        client = get_minio_client()
        if not client:
            return False
        _ensure_bucket(client, bucket)
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info("[MinIO] Uploaded %s/%s (%d bytes)", bucket, object_name, len(data))
        return True
    except S3Error as e:
        logger.error("[MinIO] S3 error uploading %s: %s", object_name, e)
        return False
    except Exception as e:
        logger.error("[MinIO] Error uploading %s: %s", object_name, e)
        return False


def _upload_json(object_name: str, data: dict | list) -> bool:
    return upload_data(
        object_name=object_name,
        data=json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"),
        content_type="application/json; charset=utf-8",
    )


def upload_session(session_id: str, state_values: dict) -> None:
    """Upload all session data to MinIO bucket 'ppt'.

    Structure:
        ppt/{session_id}/
            presentation.html
            metadata.json
            slide_contents.json
            slide_spec.json
            pptx_layouts.json
            designs/slide_001.png
            designs/slide_002.png ...
            slides/slide_001.html
            slides/slide_002.html ...
    """
    prefix = session_id

    # 1. Full assembled HTML
    html_code = state_values.get("react_code", "")
    if html_code:
        upload_data(
            f"{prefix}/presentation.html",
            html_code.encode("utf-8"),
            "text/html; charset=utf-8",
        )

    # 2. Metadata (research_brief, validation, revision_count)
    _upload_json(f"{prefix}/metadata.json", {
        "user_request": state_values.get("user_request", ""),
        "research_brief": state_values.get("research_brief", {}),
        "validation_result": state_values.get("validation_result", {}),
        "revision_count": state_values.get("revision_count", 0),
    })

    # 3. Slide contents (text JSON per slide)
    slide_contents = state_values.get("slide_contents", [])
    if slide_contents:
        _upload_json(f"{prefix}/slide_contents.json", slide_contents)

    # 4. Slide spec
    slide_spec = state_values.get("slide_spec", {})
    if slide_spec:
        _upload_json(f"{prefix}/slide_spec.json", slide_spec)

    # 5. PPTX layouts
    pptx_layouts = state_values.get("pptx_layouts", [])
    if pptx_layouts:
        _upload_json(f"{prefix}/pptx_layouts.json", pptx_layouts)

    # 6. Design images (base64 PNG → binary PNG)
    slide_designs = state_values.get("slide_designs", [])
    for design in slide_designs:
        image_b64 = design.get("image_b64")
        if not image_b64:
            continue
        slide_id = design.get("slide_id", "unknown")
        try:
            png_bytes = base64.b64decode(image_b64)
            upload_data(
                f"{prefix}/designs/{slide_id}.png",
                png_bytes,
                "image/png",
            )
        except Exception as e:
            logger.warning("[MinIO] Failed to upload design %s: %s", slide_id, e)

    # 7. Individual slide HTML
    generated_slides = state_values.get("generated_slides", [])
    for slide in generated_slides:
        slide_id = slide.get("slide_id", "unknown")
        code = slide.get("code", "")
        if code:
            upload_data(
                f"{prefix}/slides/{slide_id}.html",
                code.encode("utf-8"),
                "text/html; charset=utf-8",
            )

    logger.info(
        "[MinIO] Session uploaded: %s (%d designs, %d slides)",
        session_id, len(slide_designs), len(generated_slides),
    )
