# TraceGate Studio implementation status

- Last updated: 2026-07-10
- Branch: `feat/tracegate-studio-fullstack`
- Status owner: TraceGate maintainers

## Status definitions

- `NOT_STARTED`: no implementation exists.
- `IN_PROGRESS`: implementation or verification is actively incomplete.
- `IMPLEMENTED_UNVERIFIED`: code exists but has not run on the target platform.
- `VERIFIED_MACOS`: run and verified on the current macOS arm64 environment.
- `VERIFIED_WINDOWS_CI`: built or automatically tested on a Windows runner.
- `VERIFIED_WINDOWS_MANUAL`: installed and manually operated in a real Windows
  graphical desktop environment.
- `BLOCKED`: an external requirement currently prevents progress and the
  blocker is recorded.

`VERIFIED_WINDOWS_CI` never implies `VERIFIED_WINDOWS_MANUAL`.

## Preserved TraceGate baseline

| Feature | Status | Evidence / note |
| --- | --- | --- |
| Existing 61-test Python suite | VERIFIED_MACOS | `./.venv/bin/python -m pytest -q`: 61 passed |
| ClaimBench controlled benchmark | VERIFIED_MACOS | Existing tests and checked-in 160-run reports; metric definitions unchanged |
| Real-PR hard benchmark | VERIFIED_MACOS | Existing tests and checked-in 19 scored cases |
| EvidencePacket and redaction | VERIFIED_MACOS | Existing `tests/test_pr_advisor.py` |
| Semantic verifier/guardrails | VERIFIED_MACOS | Existing tests; strict scan reports 0 dangerous runtime paths |
| Real DeepSeek semantic execution | BLOCKED | No model key is configured in the current environment |

## P0: foundation and desktop loop

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Repository audit and baseline | VERIFIED_MACOS | `docs/current-baseline.md` plus recorded commands |
| Architecture decision | IMPLEMENTED_UNVERIFIED | `docs/architecture/ADR-001-tracegate-studio.md`; implementation must validate it |
| Development branch | VERIFIED_MACOS | `feat/tracegate-studio-fullstack` created from `76a23ab` |
| Monorepo workspace and locked Node dependencies | NOT_STARTED | Need pnpm workspace and lock file |
| Locked Python environment | NOT_STARTED | Existing environment is healthy; no `uv.lock` yet |
| React + strict TypeScript browser client | NOT_STARTED | No frontend at baseline |
| Typed API client and shared types | NOT_STARTED | No TS packages at baseline |
| FastAPI `/api/v1` service | NOT_STARTED | Legacy unversioned benchmark API exists only |
| Local API authentication and CORS | NOT_STARTED | Per-launch token design accepted in ADR |
| SQLAlchemy 2 persistence | NOT_STARTED | No application database models at baseline |
| SQLite default database | NOT_STARTED | No application database at baseline |
| Alembic migration and SQLite migration test | NOT_STARTED | No Alembic tree at baseline |
| Structured/redacted rotating logs | NOT_STARTED | Existing redaction can be reused |
| System status and diagnostics API | NOT_STARTED | Must expose explicit unconfigured/error states |
| Settings persistence without secret leakage | NOT_STARTED | Secure-store bridge not implemented |
| Python Sidecar entry and health check | NOT_STARTED | Legacy Uvicorn app is not a packaged sidecar |
| macOS arm64 PyInstaller Sidecar | NOT_STARTED | Must be built natively on this Mac |
| Tauri 2 shell | NOT_STARTED | Rust toolchain not yet confirmed |
| macOS menu-bar tray | NOT_STARTED | Requires real Tauri runtime verification |
| Close-to-hide and tray restore | NOT_STARTED | Requires real Tauri runtime verification |
| True quit stops Sidecar | NOT_STARTED | Requires process-lifecycle tests and runtime evidence |
| Single-instance foundation | NOT_STARTED | Requires Tauri implementation |
| Browser development mode | NOT_STARTED | No React client at baseline |
| Windows x86_64 build workflow | NOT_STARTED | Existing CI covers Python on Linux/macOS only |
| Windows Sidecar health check in CI | NOT_STARTED | Must execute on `windows-latest` |
| Windows NSIS Setup.exe artifact | NOT_STARTED | No Windows artifact exists |
| Windows portable archive | NOT_STARTED | Feasibility to be validated in Windows CI |
| Windows desktop manual acceptance | BLOCKED | No real Windows graphical environment/evidence is available |

## P1: coding-agent product loop

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Real LangGraph workflow | NOT_STARTED | Dependency is not installed and no graph exists |
| Structured observable Agent state | NOT_STARTED | Must persist run/node state |
| Cancellation and bounded retry | NOT_STARTED | Must cover node and tool boundaries |
| Pydantic Tool Registry | NOT_STARTED | Existing functions are not a unified registry |
| Safe repository path boundary | NOT_STARTED | Canonical path/symlink tests required |
| Restricted command tool | NOT_STARTED | Allowlist/environment/output/timeout tests required |
| Write-mode gated patch tool | NOT_STARTED | Must default disabled; no auto commit/push |
| GitHubProvider abstraction | IN_PROGRESS | Existing public PR collector is a reusable seed, not a complete provider |
| GitHub connection state | NOT_STARTED | Must report “GitHub 尚未连接” without a token |
| ETag-aware PR polling | NOT_STARTED | Durable ETag/rate-limit tests required |
| PR snapshots and Head-SHA deduplication | NOT_STARTED | Requires database schema and monitor |
| PR Inbox | NOT_STARTED | No React client |
| PR details and typed tabs | NOT_STARTED | No React client |
| Monaco Diff with finding/evidence jumps | NOT_STARTED | No React client |
| Unified CodeParser interface | NOT_STARTED | Capability matrix must be explicit |
| Incremental commit-bound index | NOT_STARTED | Requires file hash/deletion tests |
| ripgrep/symbol/FTS5 hybrid retrieval | NOT_STARTED | Embeddings remain optional and explicit |
| Repository Map backend | NOT_STARTED | Must use parsed/indexed relationships |
| Repository Map React Flow UI | NOT_STARTED | Must lazy-load/aggregate large graphs |
| Review Map backend | NOT_STARTED | Must derive from real diff and graph data |
| Review Map UI and Diff bidirectional jump | NOT_STARTED | No React client |
| Finding schema and storage | NOT_STARTED | Must include commit/evidence/verifier/run fields |
| Evidence storage and traceability | IN_PROGRESS | Existing EvidencePacket semantics reusable; persistence absent |
| Agent Trace API/SSE/UI | NOT_STARTED | No durable run event stream |
| Eval Center / ClaimBench integration | IN_PROGRESS | Real loaders/results exist; typed Studio API and UI absent |
| Desktop notifications implementation | NOT_STARTED | Windows requires CI plus separate manual gate |
| Complete tray menu and monitoring controls | NOT_STARTED | Requires Tauri and monitor service |

## P2: product enhancements

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Change Tour | NOT_STARTED | Must derive ordering from static relationships/evidence |
| Agent Evidence Graph | NOT_STARTED | Depends on durable run events |
| Webhook relay with HMAC/deduplication | NOT_STARTED | Local polling remains default |
| Optional MySQL 8 profile | NOT_STARTED | Requires compose, migration and integration smoke |
| Agent and Tool Registry screens | NOT_STARTED | Depends on registries and UI |
| MCP client adapter | NOT_STARTED | No provider selected |
| Deep links | NOT_STARTED | Requires Tauri command/route integration |
| Autostart toggle | NOT_STARTED | Must default off and be verified by platform |
| Update interface reservation | NOT_STARTED | Signing/update service out of current verified scope |
| English localization | NOT_STARTED | Chinese-first UI planned |
| Graph JSON export | NOT_STARTED | Depends on graph API |
| Graph PNG/SVG export | NOT_STARTED | Feasibility to be tested after graph UI |
| GitHub OAuth Device Flow / App | NOT_STARTED | Fine-grained PAT/public-read can ship first |

## P3: explicitly deferred interfaces

| Feature | Status | Evidence / note |
| --- | --- | --- |
| P4 Provider | NOT_STARTED | Do not advertise without real `p4` CLI implementation/tests |
| UE WebView host | NOT_STARTED | Adapter interface only is allowed |
| Maya WebView host | NOT_STARTED | Adapter interface only is allowed |
| Multi-user/team service | NOT_STARTED | Out of P0/P1 focus |
| Cloud synchronization | NOT_STARTED | Out of P0/P1 focus |

## Platform evidence

### macOS arm64

Only the preserved Python baseline is currently `VERIFIED_MACOS`. React,
Sidecar packaging, Tauri, tray and `.app` evidence will be added with exact
commands and artifact paths when they exist.

### Windows x86_64 CI

No Studio Windows workflow has run yet. Nothing is marked
`VERIFIED_WINDOWS_CI`.

### Windows graphical manual acceptance

No manual evidence exists. All installation, WebView2, tray, notification,
autostart, single-instance, background process and uninstall checks remain
`BLOCKED` or `NOT_STARTED`; none are `VERIFIED_WINDOWS_MANUAL`.

## Status update rule

Every update to this file must point to at least one test, build artifact,
runtime log, screenshot, API response, database record, CI run, or Git commit.
Code review alone may advance a feature only to `IMPLEMENTED_UNVERIFIED`.
