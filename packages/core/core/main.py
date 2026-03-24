"""
FastAPI Application - PPT Code Generation API
SSE streaming for real-time progress updates.

FastAPI 0.135+ SSE pattern: endpoint with response_class=EventSourceResponse
must be an async generator that yields ServerSentEvent directly.
"""

import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from langgraph.types import Command

from core.pipeline import get_pipeline

app = FastAPI(title="PPT Code Generation API", version="0.1.0")

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


# --- SSE Streaming Endpoints ---

@app.post("/api/generate", response_class=EventSourceResponse)
async def generate_ppt(request: GenerateRequest):
    """Generate PPT code from natural language. Streams progress via SSE."""
    pipeline = get_pipeline()
    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_request": request.user_request,
        "mode": "create",
        "target_slide_id": None,
        "slide_spec": {},
        "reference_components": {},
        "generated_slides": [],
        "react_code": "",
        "validation_result": {},
        "revision_count": 0,
        "error_log": [],
    }

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
                    if "generated_slides" in update and update["generated_slides"]:
                        for slide_data in update["generated_slides"]:
                            yield ServerSentEvent(
                                raw_data=json.dumps(slide_data, ensure_ascii=False),
                                event="slide",
                            )
                    if "react_code" in update and update["react_code"]:
                        yield ServerSentEvent(
                            raw_data=json.dumps({
                                "react_code": update["react_code"],
                            }, ensure_ascii=False),
                            event="code",
                        )
                    if "validation_result" in update:
                        yield ServerSentEvent(
                            raw_data=json.dumps(update["validation_result"], ensure_ascii=False),
                            event="validation",
                        )
                    if "slide_spec" in update and update["slide_spec"]:
                        yield ServerSentEvent(
                            raw_data=json.dumps({
                                "node": node_name,
                                "slide_spec": update["slide_spec"],
                            }, ensure_ascii=False),
                            event="state",
                        )

        # Final state
        final_state = pipeline.get_state(config)
        yield ServerSentEvent(
            raw_data=json.dumps({
                "status": "completed",
                "react_code": final_state.values.get("react_code", ""),
                "slide_spec": final_state.values.get("slide_spec", {}),
                "validation_result": final_state.values.get("validation_result", {}),
                "revision_count": final_state.values.get("revision_count", 0),
            }, ensure_ascii=False),
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
    """Edit a specific slide. Resumes existing session."""
    pipeline = get_pipeline()
    config = {"configurable": {"thread_id": request.session_id}}

    current_state = pipeline.get_state(config)
    if not current_state.values:
        raise HTTPException(status_code=404, detail="Session not found")

    yield ServerSentEvent(
        raw_data=json.dumps({"session_id": request.session_id, "status": "editing"}),
        event="session",
    )

    async for mode, chunk in pipeline.astream(
        {
            "user_request": request.user_request,
            "mode": "edit",
            "target_slide_id": request.target_slide_id,
        },
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
                if "react_code" in update:
                    yield ServerSentEvent(
                        raw_data=json.dumps({"react_code": update["react_code"]}, ensure_ascii=False),
                        event="code",
                    )

    final_state = pipeline.get_state(config)
    yield ServerSentEvent(
        raw_data=json.dumps({
            "status": "completed",
            "react_code": final_state.values.get("react_code", ""),
        }, ensure_ascii=False),
        event="complete",
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
        "mode": state.values.get("mode"),
        "react_code": state.values.get("react_code", ""),
        "validation_result": state.values.get("validation_result", {}),
        "revision_count": state.values.get("revision_count", 0),
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
