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
| Existing suite plus Studio tests | VERIFIED_MACOS | `./scripts/test.sh`: 78 Python tests passed; the original 61 remain intact |
| ClaimBench controlled benchmark | VERIFIED_MACOS | Existing tests and checked-in 160-run reports; metric definitions unchanged |
| Real-PR hard benchmark | VERIFIED_MACOS | Existing tests and checked-in 19 scored cases |
| EvidencePacket and redaction | VERIFIED_MACOS | Existing `tests/test_pr_advisor.py` |
| Semantic verifier/guardrails | VERIFIED_MACOS | Existing tests; strict scan reports 0 dangerous runtime paths |
| Real DeepSeek semantic execution | BLOCKED | No model key is configured in the current environment |

## P0: foundation and desktop loop

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Repository audit and baseline | VERIFIED_MACOS | `docs/current-baseline.md` plus recorded commands |
| Architecture decision | VERIFIED_MACOS | ADR boundaries were exercised by the packaged macOS app; see `docs/verification/p0-macos.md` |
| Development branch | VERIFIED_MACOS | `feat/tracegate-studio-fullstack` created from `76a23ab` |
| Monorepo workspace and locked Node dependencies | VERIFIED_MACOS | pnpm workspace, `pnpm-lock.yaml`, frozen install and 14 tests |
| Locked Python environment | VERIFIED_MACOS | `uv.lock`; frozen uv environment used for tests and packaging |
| React + strict TypeScript browser client | VERIFIED_MACOS | Real Dashboard/onboarding/settings browser run and screenshots |
| Typed API client and shared types | VERIFIED_MACOS | Zod-validated client; 9 package tests plus 5 web integration tests |
| FastAPI `/api/v1` service | VERIFIED_MACOS | Authenticated API tests and real browser/desktop process |
| Local API authentication and CORS | VERIFIED_MACOS | Auth/CORS tests plus Tauri-origin runtime verification |
| SQLAlchemy 2 persistence | VERIFIED_MACOS | Studio models and API persistence tests |
| SQLite default database | VERIFIED_MACOS | Real onboarding/settings persistence and database tests |
| Alembic migration and SQLite migration test | VERIFIED_MACOS | `20260710_0001`; fresh/idempotent migration tests |
| Structured/redacted rotating logs | VERIFIED_MACOS | Packaged Sidecar wrote redacted JSONL with 5 MiB/3-backup limits and clean shutdown events |
| System status API | VERIFIED_MACOS | Explicit ready/not-configured/unavailable states tested and rendered |
| Diagnostics API/page | NOT_STARTED | P0 status is present; full diagnostics remains separate work |
| Non-secret settings persistence | VERIFIED_MACOS | Theme/language/background choices persist; API never accepts a secret |
| Platform secure credential storage | VERIFIED_MACOS | Native Keychain round-trip passed and deleted its verification entry; Windows code awaits CI |
| Python Sidecar entry and health check | VERIFIED_MACOS | Independent and packaged authenticated health checks passed |
| macOS arm64 PyInstaller Sidecar | VERIFIED_MACOS | Native Mach-O artifact built and bundled |
| Tauri 2 shell | VERIFIED_MACOS | Packaged `.app` launched with real Sidecar/WebView |
| macOS menu-bar tray and restore | IMPLEMENTED_UNVERIFIED | Rust construction/dispatch tests pass; direct status-item clicking was unavailable |
| Close-to-hide | VERIFIED_MACOS | Window closed while desktop and Sidecar processes remained alive |
| True quit stops Sidecar | VERIFIED_MACOS | Desktop plus PyInstaller bootloader/worker all disappeared after Quit |
| Single-instance foundation | VERIFIED_MACOS | Repeated native launch retained one application/Sidecar owner |
| Browser development mode | VERIFIED_MACOS | Browser UI exercised against real authenticated API |
| Windows x86_64 build workflow | IMPLEMENTED_UNVERIFIED | `build-windows.yml` is actionlint-clean; no runner execution yet |
| Windows Sidecar health check in CI | IMPLEMENTED_UNVERIFIED | Authenticated loopback check is in workflow/script; no CI run yet |
| Windows NSIS Setup.exe artifact | IMPLEMENTED_UNVERIFIED | Native Windows build/package gate exists; no artifact exists yet |
| Windows portable archive | IMPLEMENTED_UNVERIFIED | Workflow packages executable plus Sidecar; no CI artifact exists yet |
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
| Finding schema/storage foundation | IMPLEMENTED_UNVERIFIED | Initial tables exist; required traceability fields and production API remain incomplete |
| Evidence storage foundation | IMPLEMENTED_UNVERIFIED | Evidence table exists; commit-bound workflow persistence remains incomplete |
| Agent Trace API/SSE/UI | NOT_STARTED | No durable run event stream |
| Eval Center / ClaimBench integration | IN_PROGRESS | System status reads real checked-in artifacts; run/list/detail UI remains absent |
| Desktop notifications implementation | NOT_STARTED | Windows requires CI plus separate manual gate |
| Complete tray menu and monitoring controls | IN_PROGRESS | Full menu structure exists; monitor actions and direct tray verification remain |

## P2: product enhancements

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Change Tour | NOT_STARTED | Must derive ordering from static relationships/evidence |
| Agent Evidence Graph | NOT_STARTED | Depends on durable run events |
| Webhook relay with HMAC/deduplication | NOT_STARTED | Local polling remains default |
| Optional MySQL 8 profile | NOT_STARTED | Requires compose, migration and integration smoke |
| Agent and Tool Registry screens | NOT_STARTED | Depends on registries and UI |
| MCP client adapter | NOT_STARTED | No provider selected |
| Deep links | IMPLEMENTED_UNVERIFIED | Scheme/parser/plugin code and Rust tests exist; end-to-end navigation is not verified |
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

P0 browser, API, SQLite/Alembic, packaged Sidecar, Tauri shell, close-hide,
single-instance and true-quit behavior are `VERIFIED_MACOS`. Exact commands,
artifact hash, limitations and screenshots are recorded in
`docs/verification/p0-macos.md`. Direct tray restore remains
`IMPLEMENTED_UNVERIFIED`.

### Windows x86_64 CI

Studio Windows workflow code exists and passes local YAML/actionlint checks,
but no workflow run exists yet. Nothing is marked `VERIFIED_WINDOWS_CI`.

### Windows graphical manual acceptance

No manual evidence exists. All installation, WebView2, tray, notification,
autostart, single-instance, background process and uninstall checks remain
`BLOCKED` or `NOT_STARTED`; none are `VERIFIED_WINDOWS_MANUAL`.

## Status update rule

Every update to this file must point to at least one test, build artifact,
runtime log, screenshot, API response, database record, CI run, or Git commit.
Code review alone may advance a feature only to `IMPLEMENTED_UNVERIFIED`.
