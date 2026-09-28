import json
import uuid
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

from app.config import settings, MODEL_DOMAINS, reload_settings
from app.orchestrator import orchestrator
from app.agents.router_agent import route_query
from app.file_handler import extract_file_content

app = FastAPI(
    title="AI Nexus Orchestrator",
    description="Intelligent AI agent that routes queries to domain-specific models",
    version="2.0.0",
)


@app.on_event("startup")
async def on_startup():
    """Reload settings from .env on every server start."""
    reload_settings()
    info = settings.info()
    print(f"[STARTUP] Provider: {info['provider']} | Model: {info['model']}")


# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class PipelineRequest(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/models")
async def get_models():
    """Get the registry of available domain-specific AI models."""
    return {
        "models": {
            mid: {"name": m["name"], "description": m["description"], "icon": m["icon"]}
            for mid, m in MODEL_DOMAINS.items()
        }
    }


@app.post("/api/route")
async def route_only(req: PipelineRequest):
    """Route a query to the best model without executing the pipeline."""
    result = await route_query(req.query)
    return result


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document or image for analysis."""
    try:
        content, file_info = await extract_file_content(file)
        return {
            "success": True,
            "file_info": file_info,
            "content_preview": content[:500] + ("..." if len(content) > 500 else ""),
            "content": content,
        }
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/api/pipeline/start")
async def start_pipeline(req: PipelineRequest):
    """Route query to the best AI model and execute its pipeline."""
    try:
        settings.validate()
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    run_id = str(uuid.uuid4())[:8]

    async def event_stream():
        async for event in orchestrator.run_pipeline(run_id, req.query):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"event\": \"stream_end\"}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/pipeline/{run_id}")
async def get_pipeline_status(run_id: str):
    """Get the status and results of a pipeline run."""
    run = orchestrator.get_run(run_id)
    if not run:
        return JSONResponse(status_code=404, content={"error": "Pipeline run not found"})
    return run.to_dict()


@app.get("/api/pipeline/{run_id}/artifacts")
async def get_pipeline_artifacts(run_id: str):
    """Get the full artifacts for a run."""
    artifacts = orchestrator.get_full_artifacts(run_id)
    if artifacts is None:
        return JSONResponse(status_code=404, content={"error": "Pipeline run not found"})
    return artifacts


@app.get("/api/health")
async def health():
    reload_settings()
    info = settings.info()
    return {
        "status": "healthy",
        "demo_mode": info.get("demo_mode", False),
        "provider": info["provider"],
        "model": info["model"],
        "base_url": info["base_url"],
        "available_models": len(MODEL_DOMAINS),
    }
