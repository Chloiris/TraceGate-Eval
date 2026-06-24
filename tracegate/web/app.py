from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tracegate.config import PROJECT_ROOT
from tracegate.web import service
from tracegate.web.data_loader import PROJECT_NAME, VERSION
from tracegate.web.schemas import (
    AnalyzeDemoRequest,
    AnalyzeDemoResponse,
    ContextGroupSummary,
    EvidenceStatusSummary,
    HealthResponse,
    OverviewResponse,
    ResultsResponse,
    TaskDetail,
    TaskSummary,
)


WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

app = FastAPI(
    title="TraceGate Eval API",
    version=VERSION,
    description="Lightweight Web/API prototype for the TraceGate Eval controlled benchmark.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/figures", StaticFiles(directory=PROJECT_ROOT / "results" / "figures", check_dir=False), name="figures")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(TEMPLATES_DIR / "dashboard.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_alias() -> FileResponse:
    return dashboard()


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok", "project": PROJECT_NAME, "version": VERSION}


@app.get("/api/overview", response_model=OverviewResponse)
def api_overview() -> dict:
    return service.overview()


@app.get("/api/context-groups", response_model=list[ContextGroupSummary])
def api_context_groups() -> list[dict]:
    return service.context_groups()


@app.get("/api/evidence-status", response_model=list[EvidenceStatusSummary])
def api_evidence_status() -> list[dict]:
    return service.evidence_statuses()


@app.get("/api/tasks", response_model=list[TaskSummary])
def api_tasks() -> list[dict]:
    return service.tasks()


@app.get("/api/tasks/{task_id}", response_model=TaskDetail)
def api_task_detail(task_id: str) -> dict:
    task = service.task_detail(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return task


@app.get("/api/results", response_model=ResultsResponse)
def api_results(
    context_group: str | None = Query(default=None),
    evidence_status: str | None = Query(default=None),
    module: str | None = Query(default=None),
) -> dict:
    return service.results(context_group=context_group, evidence_status=evidence_status, module=module)


@app.post("/api/analyze-demo", response_model=AnalyzeDemoResponse)
def api_analyze_demo(request: AnalyzeDemoRequest) -> dict:
    return service.analyze_demo(request)
