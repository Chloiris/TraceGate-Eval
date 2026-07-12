# Evidence-backed project bullets

Use only statements whose evidence has completed its named gate. Autofix
design/code bullets below do not imply a successful real-model public-PR fix;
Windows bullets are limited to automated CI/build evidence.

## AI product full-stack development

- Built a local-first Pull Request intelligence workspace with React/strict
  TypeScript, FastAPI, SQLAlchemy/Alembic, SQLite, LangGraph, and Tauri 2,
  including authenticated REST/SSE, secure desktop credentials, diagnostics,
  code maps, Monaco Diff, Agent Trace, and Sidecar lifecycle. **Basis:**
  `apps/web/src`, `tracegate/studio`, `apps/desktop/src-tauri`;
  `tests/test_studio_api.py`; `e2e/studio.spec.ts`;
  [`verification/p1-macos.md`](verification/p1-macos.md).
- Added an end-to-end Fix experience from persisted Finding through plan,
  diff/hash review, confirmation, validation stream, re-review report,
  export/rollback, and session history using shared Zod schemas and typed API
  clients. **Basis:** `apps/web/src/components/FixExperience.tsx`,
  `packages/shared-types/src`, `packages/api-client/src`;
  `apps/web/src/components/FixExperience.test.tsx`;
  fixture-only screenshots in `screenshots/autofix-playwright-fixture-*.png`.
  **Gate:** final full suite remains pending.

## Coding Agent engineering

- Designed a separate 11-node controlled Coding Agent repair workflow so the
  existing seven-node review path stays read-only; persisted Fix sessions,
  steps, Tool Calls, events, proposals, confirmations, validation, transient
  index identity, re-review, and deterministic resolution. **Basis:**
  `tracegate/agent/fix_workflow.py`, `tracegate/studio/models.py`, migration
  `20260712_0006`, `tests/test_fix_workflow.py`,
  [`architecture/ADR-003-autofix-workflow.md`](architecture/ADR-003-autofix-workflow.md).
- Implemented SHA-256 Patch Hash + exact Head-SHA confirmation with TTL,
  single-use consumption, optimistic locking, and server-authoritative
  patch/report exports. **Basis:** `tracegate/autofix/confirmation.py`,
  `tracegate/autofix/patch_safety.py`, `tracegate/studio/fix_api.py`,
  `tests/test_autofix_api.py`.
- Isolated model-generated mutations in detached Git worktrees and built
  bounded patch/path/symlink/sensitive-file checks, manifest-derived
  argument-vector validation, environment filtering, timeout/cancellation,
  rollback, and cleanup that never auto-commit or push. **Basis:**
  `tracegate/autofix/workspace.py`, `tracegate/autofix/validation.py`,
  `tests/test_autofix_safety.py`, [`autofix-safety.md`](autofix-safety.md).

## Agent Workflow engineering

- Implemented observable, cancellable LangGraph workflows with distinct Review
  and Fix state machines, durable node/Tool/event traces, idempotent actions,
  stale-client compare-and-swap protection, and resumable `Last-Event-ID` SSE.
  **Basis:** `tracegate/agent/workflow.py`,
  `tracegate/agent/fix_workflow.py`, `tracegate/studio/fix_manager.py`,
  `tracegate/studio/fix_api.py`; workflow/API tests.
- Kept model output subordinate to application policy: strict Pydantic
  structures, commit/Evidence/path verification, static patch validation,
  controlled tools, and deterministic post-fix resolution prevent a prompt
  from authorizing write or declaring success. **Basis:**
  `tracegate/autofix/schemas.py`, `tracegate/autofix/eligibility.py`,
  `tracegate/autofix/resolution.py`; Autofix safety/workflow tests.

## Python AI application development

- Built an OpenAI-compatible structured model path with bounded retry,
  token/latency accounting, compatibility Tool selection, provider provenance,
  explicit no-fallback failure, and secure Keychain/environment configuration.
  **Basis:** `tracegate/models/provider.py`, workflow modules,
  `tests/test_model_provider.py`; historical production-path Review record
  [`verification/real-model-e2e-macos.md`](verification/real-model-e2e-macos.md).
- Designed a versioned FastAPI/SQLAlchemy data layer for GitHub PR snapshots,
  commit-bound index/graph, Agent/Evidence/Finding traceability, and the Fix
  transaction, with SQLite upgrade/fresh/idempotency and offline MySQL DDL
  coverage. **Basis:** `tracegate/studio/models.py`,
  `tracegate/studio/migrations`, `tests/test_studio_database.py`,
  `tests/test_autofix_api.py`.

## Test development and Agent Eval

- Productized 19 scored public-PR cases and 160 controlled ClaimBench rows into
  an Eval Center with provenance hashes, unchanged metrics, confusion matrix,
  case drill-down, model/context comparison, and export. **Basis:**
  `tracegate/studio/eval_bridge.py`,
  `apps/web/src/pages/EvalCenterPage.tsx`, benchmark artifacts and API/E2E
  tests. The 19-case set is intentionally small and not statistically
  significant.
- Built cross-layer Autofix regression coverage for malicious patches,
  traversal/symlinks/sensitive files, confirmation replacement/expiry/stale
  Head, command injection/timeouts/cancellation, isolated rollback/cleanup,
  migration, API/SSE resume, typed clients, and fixture-labelled UI flow.
  **Basis:** `tests/test_autofix_safety.py`, `tests/test_fix_workflow.py`,
  `tests/test_autofix_api.py`, shared/API-client/Vitest/Playwright tests.
  **Gate:** use final counts only after the complete branch matrix passes.
- Automated canonical version/product/fact/README/Autofix-boundary and
  repository-wide Markdown-link checks so historical evidence stays immutable
  while current claims cannot silently drift. **Basis:**
  `docs/project-facts.yaml`, `scripts/check_docs_consistency.py`,
  `tests/test_docs_consistency.py`.

## Cross-platform delivery

- Built native macOS arm64 and Windows x86-64 PyInstaller Sidecars and Tauri
  packaging workflows with authenticated health checks, checksums, build
  metadata, and unsigned Windows NSIS/MSI/portable artifacts. **Basis:** build
  workflows/scripts and historical source-bound records
  [`verification/p1-macos.md`](verification/p1-macos.md) and
  [`verification/windows-ci.md`](verification/windows-ci.md). This does not
  claim Windows installation or GUI acceptance, and fresh Autofix artifacts
  are pending.

## Claims not supported yet

- A real public-PR Autofix success, fix accuracy, success rate, or comparative
  model quality.
- Signed or manually verified Windows installer/GUI behavior.
- Enterprise users, commercial deployment, production readiness, or scale.
- Native Tool Calling for the recorded DeepSeek compatibility-mode run.
- Complete Java, JavaScript, or TypeScript semantic/function call graphs.
- Automatic commit, push, external PR creation/comment, or merge.
