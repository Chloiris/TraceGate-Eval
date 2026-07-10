# Evidence-backed resume bullets

Use only bullets matching the role. Each bullet names its code, test, visual,
or run evidence; none claims Windows verification or real-model execution.

## AI product full-stack internship

- Built a local-first Pull Request review product with React/TypeScript,
  FastAPI, SQLAlchemy/Alembic, SQLite, LangGraph, and Tauri, including typed
  authenticated APIs, SSE, diagnostics, settings, and desktop Sidecar
  lifecycle. **Evidence:** `apps/web/src`, `tracegate/studio`,
  `apps/desktop/src-tauri`; `tests/test_studio_api.py`; `e2e/studio.spec.ts`;
  `artifacts/macos/TraceGate-Studio-macos-arm64.zip`.
- Delivered Repository/Review Maps, Change Tour, Monaco Diff, Agent Trace, and
  evidence-backed navigation using real Git/index/database state rather than
  demo data. **Evidence:** `tracegate/graph/repository_map.py`,
  `tracegate/studio/api.py`, `apps/web/src/pages`; 4 passing Chrome E2E flows;
  `screenshots/p1-review-map-macos.png`.

## Coding Agent engineering internship

- Implemented a seven-node observable LangGraph review workflow with
  cancellation, bounded retry, commit-bound context, structured model output,
  persisted Agent/Tool traces, and verifier-gated Findings. **Evidence:**
  `tracegate/agent/workflow.py`, `tracegate/models/provider.py`,
  `tests/test_agent_workflow.py`, `tests/test_model_provider.py`.
- Built a 19-tool schema/permission Registry with traversal and sensitive-file
  boundaries, restricted command execution, execution-time enable/disable
  policy, and exact-confirmation patch mode that never commits or pushes.
  **Evidence:** `tracegate/tools/registry.py`, `tests/test_tool_registry.py`,
  `screenshots/p1-registry-macos.png`.

## Python AI application development internship

- Designed a versioned FastAPI/SQLAlchemy data layer for GitHub PR snapshots,
  commits, files, hunks, checks, indexes, graphs, model profiles, Agent runs,
  Evidence, Findings, notifications, and rate-limit/latency diagnostics.
  **Evidence:** `tracegate/studio/models.py`, migration `20260710_0004`,
  `tests/test_studio_database.py`, `tests/test_studio_api.py`.
- Integrated finite-retry OpenAI-compatible structured output, SSE streaming,
  native/compatibility Tool selection, token/latency accounting, context-scope
  control, and secure configuration without persisting API keys. **Evidence:**
  `tracegate/models/provider.py`, `tracegate/studio/run_manager.py`,
  `tests/test_model_provider.py`, `tests/test_studio_run_manager.py`.

## Agent Eval internship

- Productized TraceGate Eval’s 19 scored real-PR cases and 160 ClaimBench runs
  into an Eval Center with artifact hashes, unchanged safety metrics, confusion
  matrix, case drill-down, model/context comparisons, and report export.
  **Evidence:** `tracegate/studio/eval_bridge.py`,
  `apps/web/src/pages/EvalCenterPage.tsx`, `tests/test_studio_api.py`,
  `screenshots/p1-eval-center-macos.png`.
- Preserved explicit active/stale/unknown/conflicting evidence semantics and
  commit-bound verification so passing tests alone cannot count as safe agent
  behavior. **Evidence:** `tracegate/evidence_packet.py`, `tracegate/verifier.py`,
  existing benchmark reports, 125 passing Python tests.

## Test development internship

- Built cross-layer verification covering 125 Python tests, 20 Rust tests,
  20 TypeScript/Vitest tests, strict TypeScript/ESLint, Rust fmt/clippy, and 4
  Chrome E2E product flows. **Evidence:** `scripts/test.sh`, `e2e/studio.spec.ts`,
  local 2026-07-10 verification run.
- Added reproducible production-path performance smoke tests for 100/1000-file
  indexing and Repository/Review Maps; recorded method, environment, caps, UI
  readiness, idle CPU, and blocked measurements without invented values.
  **Evidence:** `scripts/benchmark_studio.py`, `docs/performance-results.json`,
  `docs/performance.md`.

## Claims not to use yet

- “Shipped a verified Windows installer” — Windows CI has not run.
- “Verified native notification clicks on macOS/Windows” — code/tests exist,
  but current manual OS interaction evidence is incomplete.
- “Improved model accuracy” — metric definitions were preserved; no new real
  model experiment was run.
- “Production GitHub OAuth verified end to end” — adapter and secure-storage
  code are tested, but no live authorization was performed in this pass.

