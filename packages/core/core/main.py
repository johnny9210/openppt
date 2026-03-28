"""
FastAPI Application - PPT Code Generation API
SSE streaming for real-time progress updates.

Architecture: Scoping -> Parallel (Text + Design) -> Synthesis -> Validation
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from langgraph.types import Command

from core.pipeline import get_pipeline
from core.database import get_sessions_collection

app = FastAPI(title="PPT Code Generation API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class GenerateRequest(BaseModel):
    user_request: str
    model_type: str | None = None  # "claude" | "gpt"


class EditRequest(BaseModel):
    session_id: str
    user_request: str
    target_slide_id: str


class HumanReviewRequest(BaseModel):
    session_id: str
    action: str  # "retry" | "approve" | "abort"


class ImageExportRequest(BaseModel):
    slide_images: list[str]  # base64 PNG images


# --- MongoDB session helpers ---

async def save_session(session_id: str, state_values: dict) -> None:
    """Save pipeline final state to MongoDB.

    Strips large base64 image data from slide_designs and generated_slides
    to stay within MongoDB's 16MB BSON document size limit.
    Images are already delivered to the frontend via SSE events.
    """
    col = get_sessions_collection()

    # Strip base64 image data to avoid exceeding MongoDB 16MB limit
    designs = state_values.get("slide_designs", [])
    designs_slim = [
        {k: v for k, v in d.items() if k != "image_b64"}
        for d in designs
    ]
    gen_slides = state_values.get("generated_slides", [])
    gen_slides_slim = [
        {k: v for k, v in s.items() if k != "image_b64"}
        for s in gen_slides
    ]

    doc = {
        "session_id": session_id,
        "user_request": state_values.get("user_request", ""),
        "research_brief": state_values.get("research_brief", {}),
        "slide_contents": state_values.get("slide_contents", []),
        "slide_designs": designs_slim,
        "generated_slides": gen_slides_slim,
        "pptx_layouts": state_values.get("pptx_layouts", []),
        "react_code": state_values.get("react_code", ""),
        "slide_spec": state_values.get("slide_spec", {}),
        "validation_result": state_values.get("validation_result", {}),
        "revision_count": state_values.get("revision_count", 0),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await col.update_one(
        {"session_id": session_id},
        {"$set": doc},
        upsert=True,
    )
    logger.info("[MongoDB] Session saved: %s", session_id)


async def load_session(session_id: str) -> dict | None:
    """Load session from MongoDB."""
    col = get_sessions_collection()
    return await col.find_one({"session_id": session_id})


# --- Index creation on startup ---

@app.on_event("startup")
async def create_indexes():
    try:
        col = get_sessions_collection()
        await col.create_index("session_id", unique=True)
        await col.create_index("created_at")
        logger.info("[MongoDB] Indexes ensured")
    except Exception as e:
        logger.warning("[MongoDB] Index creation deferred (mongo may not be ready yet): %s", e)


# --- SSE Streaming Endpoints ---

@app.post("/api/generate", response_class=EventSourceResponse)
async def generate_ppt(request: GenerateRequest):
    """Generate PPT code from natural language. Streams progress via SSE."""
    pipeline = get_pipeline()
    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_request": request.user_request,
        "research_brief": {},
        "slide_contents": [],
        "slide_designs": [],
        "cover_design_image": "",
        "generated_slides": [],
        "react_code": "",
        "slide_spec": {},
        "validation_result": {},
        "revision_count": 0,
        "pptx_layouts": [],
        "error_log": [],
    }

    logger.info("[SSE] Session started: %s", thread_id)
    yield ServerSentEvent(
        raw_data=json.dumps({"session_id": thread_id, "status": "started"}),
        event="session",
    )

    try:
        async for mode, chunk in pipeline.astream(
            initial_state,
            config,
            stream_mode=["updates", "custom"],
        ):
            if mode == "custom":
                yield ServerSentEvent(
                    raw_data=json.dumps(chunk, ensure_ascii=False),
                    event="progress",
                )
            elif mode == "updates":
                for node_name, update in chunk.items():
                    if not update or not isinstance(update, dict):
                        continue
                    logger.info("[SSE] Node '%s' update keys: %s", node_name, list(update.keys()))

                    # Phase 1: Scoping result
                    if "research_brief" in update and update["research_brief"]:
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                update["research_brief"], ensure_ascii=False
                            ),
                            event="scoping",
                        )

                    # Phase 2: Text content
                    if "slide_contents" in update and update["slide_contents"]:
                        for content in update["slide_contents"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(content, ensure_ascii=False),
                                event="text",
                            )

                    # Phase 2: Design images (include base64 for Design tab preview)
                    if "slide_designs" in update and update["slide_designs"]:
                        for design in update["slide_designs"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(
                                    {
                                        "slide_id": design["slide_id"],
                                        "type": design["type"],
                                        "has_image": design.get("image_b64")
                                        is not None,
                                        "image_b64": design.get("image_b64"),
                                    },
                                    ensure_ascii=False,
                                ),
                                event="design",
                            )

                    # Phase 3: Synthesized slide code
                    if "generated_slides" in update and update["generated_slides"]:
                        for slide_data in update["generated_slides"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(
                                    slide_data, ensure_ascii=False
                                ),
                                event="slide",
                            )

                    # Phase 3: Assembled code + slide_spec
                    if "react_code" in update and update["react_code"]:
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                {"react_code": update["react_code"]},
                                ensure_ascii=False,
                            ),
                            event="code",
                        )
                    if "slide_spec" in update and update["slide_spec"]:
                        print(f"[SSE] slide_spec emitted: {len(update['slide_spec'].get('ppt_state', {}).get('presentation', {}).get('slides', []))} slides", flush=True)
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                {"slide_spec": update["slide_spec"]},
                                ensure_ascii=False,
                            ),
                            event="state",
                        )

                    # Phase 3-B: PPTX Layouts
                    if "pptx_layouts" in update and update["pptx_layouts"]:
                        for layout_data in update["pptx_layouts"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(layout_data, ensure_ascii=False),
                                event="pptx_layout",
                            )

                    # Phase 4: Validation
                    if "validation_result" in update:
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                update["validation_result"], ensure_ascii=False
                            ),
                            event="validation",
                        )

        # Final state
        final_state = pipeline.get_state(config)
        final_slide_spec = final_state.values.get("slide_spec", {})
        print(f"[COMPLETE] react_code: {len(final_state.values.get('react_code', ''))} chars", flush=True)
        print(f"[COMPLETE] slide_spec slides: {len(final_slide_spec.get('ppt_state', {}).get('presentation', {}).get('slides', []))}", flush=True)
        print(f"[COMPLETE] revision_count: {final_state.values.get('revision_count', 0)}", flush=True)

        # Save to MongoDB
        await save_session(thread_id, final_state.values)

        yield ServerSentEvent(
            raw_data=json.dumps(
                {
                    "status": "completed",
                    "react_code": final_state.values.get("react_code", ""),
                    "slide_spec": final_slide_spec,
                    "research_brief": final_state.values.get("research_brief", {}),
                    "validation_result": final_state.values.get(
                        "validation_result", {}
                    ),
                    "revision_count": final_state.values.get("revision_count", 0),
                },
                ensure_ascii=False,
            ),
            event="complete",
        )

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"Pipeline error:\n{tb}", flush=True)
        yield ServerSentEvent(
            raw_data=json.dumps({"error": str(e), "traceback": tb}),
            event="error",
        )


@app.post("/api/edit", response_class=EventSourceResponse)
async def edit_slide(request: EditRequest):
    """Edit a specific slide by re-synthesizing it with user instructions.

    Uses LangGraph update_state to inject a fix_prompt targeting the slide,
    then resumes from semantic_validator -> semantic_decision -> code_synthesizer.
    """
    pipeline = get_pipeline()
    config = {"configurable": {"thread_id": request.session_id}}

    current_state = pipeline.get_state(config)
    if not current_state.values:
        yield ServerSentEvent(
            raw_data=json.dumps({
                "error": "세션이 만료되었습니다. PPT를 다시 생성해주세요.",
                "detail": "Session not found",
            }),
            event="error",
        )
        return

    logger.info("[Edit] Session: %s, target: %s, request: %s",
                request.session_id, request.target_slide_id, request.user_request[:100])

    yield ServerSentEvent(
        raw_data=json.dumps({"session_id": request.session_id, "status": "editing"}),
        event="session",
    )

    try:
        # Inject edit instruction as a semantic validation failure for the target slide.
        # This makes the pipeline resume: semantic_decision -> code_synthesizer (re-synth target only)
        fix_prompt = (
            f"[사용자 수정 요청]\n"
            f"슬라이드 {request.target_slide_id}에 대한 수정:\n"
            f"{request.user_request}\n\n"
            f"[수정 원칙]\n"
            f"- 위 요청사항을 반영하여 해당 슬라이드만 수정\n"
            f"- 나머지 레이아웃/디자인은 유지\n"
            f"- content props 동적 바인딩 유지"
        )

        pipeline.update_state(
            config,
            {
                "validation_result": {
                    "layer": "semantic",
                    "status": "fail",
                    "fix_prompt": fix_prompt,
                    "failed_slide_ids": [request.target_slide_id],
                },
                "revision_count": 0,
            },
            as_node="semantic_validator",
        )

        # Resume pipeline — semantic_decision sees fail -> routes to code_synthesizer
        async for mode, chunk in pipeline.astream(
            None,
            config,
            stream_mode=["updates", "custom"],
        ):
            if mode == "custom":
                yield ServerSentEvent(
                    raw_data=json.dumps(chunk, ensure_ascii=False),
                    event="progress",
                )
            elif mode == "updates":
                for node_name, update in chunk.items():
                    if not update or not isinstance(update, dict):
                        continue
                    if "generated_slides" in update and update["generated_slides"]:
                        for slide_data in update["generated_slides"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(slide_data, ensure_ascii=False),
                                event="slide",
                            )
                    if "react_code" in update and update["react_code"]:
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                {"react_code": update["react_code"]},
                                ensure_ascii=False,
                            ),
                            event="code",
                        )
                    if "slide_spec" in update and update["slide_spec"]:
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                {"slide_spec": update["slide_spec"]},
                                ensure_ascii=False,
                            ),
                            event="state",
                        )
                    if "validation_result" in update:
                        yield ServerSentEvent(
                            raw_data=json.dumps(
                                update["validation_result"], ensure_ascii=False
                            ),
                            event="validation",
                        )

        final_state = pipeline.get_state(config)
        final_slide_spec = final_state.values.get("slide_spec", {})

        await save_session(request.session_id, final_state.values)

        yield ServerSentEvent(
            raw_data=json.dumps(
                {
                    "status": "completed",
                    "react_code": final_state.values.get("react_code", ""),
                    "slide_spec": final_slide_spec,
                },
                ensure_ascii=False,
            ),
            event="complete",
        )

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"Edit pipeline error:\n{tb}", flush=True)
        yield ServerSentEvent(
            raw_data=json.dumps({"error": str(e), "traceback": tb}),
            event="error",
        )


@app.post("/api/human-review")
async def human_review(request: HumanReviewRequest):
    """Handle human-in-the-loop response after max revision failures."""
    pipeline = get_pipeline()
    config = {"configurable": {"thread_id": request.session_id}}

    result = await pipeline.ainvoke(
        Command(resume=request.action),
        config,
    )

    return {
        "status": "resumed",
        "react_code": result.get("react_code", ""),
        "validation_result": result.get("validation_result", {}),
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state (from MongoDB)."""
    session = await load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "react_code": session.get("react_code", ""),
        "research_brief": session.get("research_brief", {}),
        "validation_result": session.get("validation_result", {}),
        "revision_count": session.get("revision_count", 0),
    }


@app.get("/api/export/pptx/{session_id}")
async def export_pptx_get(session_id: str):
    """Export session result as a .pptx file (text-based fallback)."""
    from core.export.pptx_exporter import export_pptx as generate_pptx

    session = await load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    slide_spec = session.get("slide_spec", {})
    slide_contents = session.get("slide_contents", [])
    slide_designs = session.get("slide_designs", [])

    if not slide_spec:
        raise HTTPException(status_code=400, detail="No slide spec available")

    try:
        buf = generate_pptx(slide_spec, slide_contents, slide_designs)
    except Exception as e:
        logger.error("PPTX export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    return _pptx_response(buf, slide_spec)


@app.post("/api/export/pptx/{session_id}")
async def export_pptx_post(session_id: str, body: ImageExportRequest):
    """Export PPTX using captured slide images from Preview."""
    from core.export.pptx_exporter import export_pptx_from_images

    session = await load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    slide_spec = session.get("slide_spec", {})
    if not slide_spec:
        raise HTTPException(status_code=400, detail="No slide spec available")

    try:
        buf = export_pptx_from_images(slide_spec, body.slide_images)
    except Exception as e:
        logger.error("PPTX image export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    return _pptx_response(buf, slide_spec)


def _pptx_response(buf, slide_spec: dict) -> StreamingResponse:
    """Build a StreamingResponse for a PPTX buffer."""
    title = (
        slide_spec
        .get("ppt_state", {})
        .get("presentation", {})
        .get("meta", {})
        .get("title", "presentation")
    )
    safe_title = "".join(
        c for c in title if c.isalnum() or c in " _-" or ("\uac00" <= c <= "\ud7a3")
    ).strip()[:50]
    if not safe_title:
        safe_title = "presentation"
    filename = f"{safe_title}.pptx"

    ascii_fallback = "presentation.pptx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}",
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
