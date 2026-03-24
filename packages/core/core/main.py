"""
FastAPI Application - PPT Code Generation API
SSE streaming for real-time progress updates.

Architecture: Scoping -> Parallel (Text + Design) -> Synthesis -> Validation
"""

import json
import logging
import uuid

from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from langgraph.types import Command

from core.pipeline import get_pipeline

app = FastAPI(title="PPT Code Generation API", version="0.2.0")

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


class HumanReviewRequest(BaseModel):
    session_id: str
    action: str  # "retry" | "approve" | "abort"


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
        "generated_slides": [],
        "react_code": "",
        "slide_spec": {},
        "validation_result": {},
        "revision_count": 0,
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

                    # Phase 2: Design images (don't send base64 in SSE)
                    if "slide_designs" in update and update["slide_designs"]:
                        for design in update["slide_designs"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(
                                    {
                                        "slide_id": design["slide_id"],
                                        "type": design["type"],
                                        "has_image": design.get("image_b64")
                                        is not None,
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
    """Get current session state."""
    pipeline = get_pipeline()
    config = {"configurable": {"thread_id": session_id}}

    state = pipeline.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "react_code": state.values.get("react_code", ""),
        "research_brief": state.values.get("research_brief", {}),
        "validation_result": state.values.get("validation_result", {}),
        "revision_count": state.values.get("revision_count", 0),
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
