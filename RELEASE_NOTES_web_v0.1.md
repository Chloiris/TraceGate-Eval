# TraceGate Eval Web/API v0.1 Release Notes

## What Was Added

- Added a lightweight FastAPI service under `tracegate/web/`.
- Added a static dashboard at `/` and `/dashboard`.
- Added rule-based demo analysis through `/api/analyze-demo`.
- Added file-based data loading for checked-in Stage3 results and task definitions.
- Added API documentation in `docs/api.md`.
- Added minimal API tests in `tests/test_web_api.py`.
- Updated README with Web Dashboard / API Prototype instructions.

## New Files

- `tracegate/web/app.py`
- `tracegate/web/schemas.py`
- `tracegate/web/data_loader.py`
- `tracegate/web/service.py`
- `tracegate/web/templates/dashboard.html`
- `tracegate/web/static/dashboard.css`
- `tracegate/web/static/dashboard.js`
- `docs/api.md`
- `tests/test_web_api.py`

## New API Endpoints

- `GET /api/health`
- `GET /api/overview`
- `GET /api/context-groups`
- `GET /api/evidence-status`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/results`
- `POST /api/analyze-demo`

## Start The Dashboard

```bash
python -m pip install -r requirements.txt
uvicorn tracegate.web.app:app --reload
```

Optional:

```bash
python -m tracegate web --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

## Data Loading

The Web/API layer loads real checked-in project files first:

- `results/context_group_summary.csv`
- `results/evidence_status_summary.csv`
- `reports_claim/claim_stage_results.csv`
- `experiments/claim_tasks.yaml`

If structured summary files are missing, it falls back to aggregate project-summary values and marks responses with `data_source: "project_summary_fallback"`. It does not fabricate full run-level logs.

## Tests

```bash
pytest tests/test_web_api.py
```

The tests cover health, overview, context groups, evidence status summaries, and the rule-based analyze-demo endpoint.

## Current Limitations

- The dashboard is a v0.1 presentation layer, not an industrial online evaluation system.
- `/api/analyze-demo` is rule-based and does not represent model output.
- The service reads local files and does not download real datasets.
- The service does not execute Stage1, Stage2, or Stage3 experiments.

## Next Steps

- Add a compact run-detail page for selected Stage3 records.
- Add simple filtering controls to the dashboard tables.
- Add charts for evidence-status accuracy and risk summaries.
- Add optional export endpoints for reproducible project reports.
