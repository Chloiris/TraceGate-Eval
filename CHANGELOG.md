# Changelog

All notable changes are documented here. The project is pre-1.0; dates describe
repository state, not a published signed release.

## 0.4.0 - Unreleased

### Added

- TraceGate Studio local-first React, FastAPI, SQLite/Alembic, LangGraph, and
  Tauri product path.
- GitHub Device Flow/PAT adapters, ETag polling, persisted PR/check/commit/file/
  hunk records, optional authenticated Webhook Relay, and rate-limit backoff.
- Commit-bound parsing/indexing, hybrid retrieval, Repository Map, Review Map,
  Change Tour, Monaco Diff, Agent Evidence Graph, Findings, and Evidence.
- Persistent Agent/Tool Registry controls with execution-time enforcement.
- Structured model profiles, structured notification delivery records, model
  streaming/tool compatibility modes, context scope, cost inputs, and runtime
  observability.
- Eval Center confusion matrix, case drill-down, model/context comparisons, and
  report export using unchanged 19-case/160-run artifacts.
- Native Sidecar lifecycle, tray/single-instance/deep-link/autostart/
  notification code, macOS arm64 packaging, and Windows CI packaging workflow.
- Verified one production-path DeepSeek E2E on `psf/requests#7565`, including 4
  real model requests and persisted Tool Calls, Evidence, Finding, and Agent
  Trace without storing the API key.
- Historical source-bound Windows x86_64 CI verified 212 Python tests, 30
  TypeScript/Vitest tests, 22 passing Rust tests (1 explicit native
  secure-store mutation test ignored in the ordinary suite), an explicit
  Credential Manager round trip, authenticated Sidecar health, and unsigned
  NSIS/MSI/portable packaging at pre-Autofix baseline commit
  `a1dcd7d755c25e0f75aac499943a07b759ec30db`.
- Reproducible local performance smoke benchmark and product/operator/support
  documentation.
- Separate 11-node controlled Autofix workflow from persisted Finding through
  eligibility, structured Fix Plan, structured model Patch Proposal, static
  validation, hash-bound confirmation, isolated apply, controlled validation,
  transient reindex, re-review, deterministic resolution and report.
- Alembic `20260712_0006` and SQLAlchemy records for Fix sessions, patch
  proposals, confirmations, validation runs, Fix results, steps, Tool Calls and
  persisted SSE events.
- Authenticated/idempotent Fix API with optimistic lock versions, stable
  failure states, authoritative patch/report exports, resumable
  `Last-Event-ID` SSE, rollback, cleanup and managed-worktree diagnostics.
- Typed shared/API-client contracts and a Finding → Fix Plan → Patch/Hash →
  confirmation → validation → re-review/report/history frontend flow with
  fixture-labelled Vitest/Playwright coverage.
- Canonical `docs/project-facts.yaml`, repository-wide Markdown-link/version/
  workflow/README boundary checks, and parallel 26-section English/Chinese
  READMEs.

### Security

- Loopback-only authenticated API, exact CORS, bounded provider responses,
  sensitive-path protection, prompt-injection boundaries, filtered subprocess
  environments, secure OS credential storage, HMAC/replay protection, and
  redacted rotating JSON logs.
- Normalized SHA-256 Patch Hash bound to session/repository/PR/Finding/Head,
  expiring single-use confirmation, exact-Head and clean-worktree checks,
  canonical path/symlink/sensitive/binary limits, and `git apply --check`.
- Detached managed Git worktrees protect the enrolled source workspace;
  resolver-selected argument-vector validation filters environment, limits
  time/output, supports cancellation, and never runs model-authored shell text.
- Deterministic post-fix policy prevents failed/absent validation or uncertain
  re-review from becoming `RESOLVED`; commit/push/comment/PR/merge remain out
  of scope.

### Known limitations

- The single real DeepSeek E2E verifies execution and trace persistence, not
  comparative model accuracy or broad model quality.
- Live GitHub OAuth Device Flow authorization remains unverified.
- Windows CI is verified only for automated compilation, tests, Sidecar health,
  and unsigned packaging. Installation, WebView2, tray, notification,
  autostart, single-instance, background process, and uninstall behavior have
  no real Windows GUI/manual acceptance evidence.
- The newest macOS build, packaged Sidecar health, native Tauri launch,
  authenticated connection, Settings, and Autofix Diagnostics are verified;
  status-item and notification-click interaction remain unverified.
- Current branch verification records 268 Python, 60 TypeScript/Vitest, 22
  Rust passed (+1 ignored), five Playwright flows, a real DeepSeek synthetic
  temporary-repository Autofix E2E, and fresh macOS packaging. Source-bound
  Windows Autofix CI/artifacts remain pending.
- No public-PR Autofix success rate, automatic-fix accuracy, native Tool
  Calling, or complete Java/JS/TS semantic call graph is claimed.
- Autofix does not automatically commit, push, comment, open a PR, or merge.
