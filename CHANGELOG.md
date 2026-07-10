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
- Reproducible local performance smoke benchmark and product/interview/support
  documentation.

### Security

- Loopback-only authenticated API, exact CORS, bounded provider responses,
  sensitive-path protection, prompt-injection boundaries, filtered subprocess
  environments, secure OS credential storage, HMAC/replay protection, and
  redacted rotating JSON logs.

### Known limitations

- No real model credential was available for a production LLM E2E in this pass.
- GitHub remote synchronization was not rerun because remote access requires
  explicit user permission.
- Windows CI and Windows GUI acceptance are not verified.
- The newest macOS build started and its Sidecar passed lifecycle checks, but
  the local UI-control interface could not inspect a window/status item; tray
  clicking remains unverified.

