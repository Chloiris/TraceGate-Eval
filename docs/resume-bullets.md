# Evidence-backed resume bullets

Use only bullets matching the role. Each bullet names its code, test, visual,
or run evidence. Windows bullets are limited to CI build/test/package evidence;
real-model claims are limited to the single recorded macOS production-path run.

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
- Produced a native Windows x86_64 PyInstaller Sidecar plus unsigned NSIS, MSI,
  and portable Tauri packages in GitHub Actions, with authenticated Sidecar
  health, build metadata, and downloaded SHA-256 verification. **Evidence:**
  `docs/verification/windows-ci.md`; workflow runs `29163495677` and
  `29163496649`; artifact ID `8251618586`. This bullet does not claim Windows
  installation or GUI acceptance.

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
  `tests/test_model_provider.py`, `tests/test_studio_run_manager.py`; one
  production-path `deepseek-chat` run on `psf/requests#7565` completed 4 real
  requests and persisted 3 Tool Calls, 1 Evidence, 1 Finding, and 7 Agent Trace
  rows (`docs/verification/real-model-e2e-macos.md`).

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
  existing benchmark reports, 163 passing Python tests in the recorded Windows
  CI run.

## Test development internship

- Built cross-layer verification covering 163 Python tests, 30
  TypeScript/Vitest tests, 22 passing Rust tests with 1 explicit native
  secure-store mutation test ignored, strict TypeScript/ESLint, Rust
  fmt/clippy, and 4 Chrome E2E product flows. **Evidence:** `scripts/test.sh`,
  `e2e/studio.spec.ts`, `docs/verification/windows-ci.md`, and the macOS
  verification records.
- Added reproducible production-path performance smoke tests for 100/1000-file
  indexing and Repository/Review Maps; recorded method, environment, caps, UI
  readiness, idle CPU, and blocked measurements without invented values.
  **Evidence:** `scripts/benchmark_studio.py`, `docs/performance-results.json`,
  `docs/performance.md`.

## Claims not to use yet

- “Shipped, signed, or manually verified a Windows installer” — CI produced
  unsigned NSIS/MSI/portable artifacts, but no Windows installation or GUI
  acceptance run exists.
- “Verified native notification clicks on macOS/Windows” — code/tests exist,
  but current manual OS interaction evidence is incomplete.
- “Improved model accuracy” — the single real DeepSeek E2E proves the production
  request/persistence path, not an accuracy gain or comparative experiment.
- “Production GitHub OAuth verified end to end” — adapter and secure-storage
  code are tested, but no live authorization was performed in this pass.
