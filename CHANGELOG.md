# Changelog

All notable changes are documented here. The project is pre-1.0; dates describe
repository state, not a published signed release.

## Unreleased

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
- Verified Windows x86_64 CI compilation, 212 Python tests, 30
  TypeScript/Vitest tests, and 22 passing Rust tests (1 explicit native
  secure-store mutation test ignored in the ordinary suite), followed by a
  passing explicit 1/1 Windows Credential Manager round-trip, authenticated
  PyInstaller Sidecar health, and unsigned NSIS, MSI, and portable artifact
  generation for commit `a7466ce69441871df229a5ed1cdf32ec594ba935`.
- Reproducible local performance smoke benchmark and product/operator/support
  documentation.

### Security

- Loopback-only authenticated API, exact CORS, bounded provider responses,
  sensitive-path protection, prompt-injection boundaries, filtered subprocess
  environments, secure OS credential storage, HMAC/replay protection, and
  redacted rotating JSON logs.

### Known limitations

- The single real DeepSeek E2E verifies execution and trace persistence, not
  comparative model accuracy or broad model quality.
- Live GitHub OAuth Device Flow authorization remains unverified.
- Windows CI is verified only for automated compilation, tests, Sidecar health,
  and unsigned packaging. Installation, WebView2, tray, notification,
  autostart, single-instance, background process, and uninstall behavior have
  no real Windows GUI/manual acceptance evidence.
- The newest macOS build started and its Sidecar passed lifecycle checks, but
  the local UI-control interface could not inspect a window/status item; tray
  clicking remains unverified.
