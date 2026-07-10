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
| Existing suite plus Studio tests | VERIFIED_MACOS | 110 Python tests plus 20 Vitest tests and 4 Chrome Playwright flows; original Eval coverage remains intact |
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
| React + strict TypeScript browser client | VERIFIED_MACOS | Dashboard plus P1 product pages exercised by Chrome Playwright; see `docs/verification/p1-macos.md` |
| Typed API client and shared types | VERIFIED_MACOS | Zod-validated client; 12 package tests plus 8 web/unit integration tests |
| FastAPI `/api/v1` service | VERIFIED_MACOS | Authenticated API tests and real browser/desktop process |
| Local API authentication and CORS | VERIFIED_MACOS | Auth/CORS tests plus Tauri-origin runtime verification |
| SQLAlchemy 2 persistence | VERIFIED_MACOS | Studio models and API persistence tests |
| SQLite default database | VERIFIED_MACOS | Real onboarding/settings persistence and database tests |
| Alembic migration and SQLite migration test | VERIFIED_MACOS | `20260710_0001`; fresh/idempotent migration tests |
| Structured/redacted rotating logs | VERIFIED_MACOS | Packaged Sidecar wrote redacted JSONL with 5 MiB/3-backup limits and clean shutdown events |
| System status API | VERIFIED_MACOS | Explicit ready/not-configured/unavailable states tested and rendered |
| Diagnostics API/page | VERIFIED_MACOS | Redacted runtime/storage/queue/update state is API-tested and rendered in the React client |
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
| Real LangGraph workflow | VERIFIED_MACOS | LangGraph 1.2.8 runs seven real persisted nodes; `tests/test_agent_workflow.py` |
| Structured observable Agent state | VERIFIED_MACOS | Run, Step and ToolCall rows plus typed detail/SSE APIs verified locally |
| Cancellation and bounded retry | VERIFIED_MACOS | RunManager, workflow cancellation and explicit retry behavior are tested; Playwright proves missing-model retry failure |
| Pydantic Tool Registry | VERIFIED_MACOS | 19 schema-validated registered tools; registry API/UI and unit tests |
| Safe repository path boundary | VERIFIED_MACOS | Canonical, traversal, symlink and credential-path tests in `tests/test_repository_security.py` |
| Restricted command tool | VERIFIED_MACOS | Argument allowlist, filtered environment, timeout and output limits; forbidden command test |
| Write-mode gated patch tool | VERIFIED_MACOS | Defaults disabled, exact confirmation required, real temp-repo patch test, never commits/pushes |
| GitHubProvider abstraction | VERIFIED_MACOS | Bounded async REST provider with PR/files/commits/comments/checks tests |
| GitHub connection state | VERIFIED_MACOS | API and Chrome show “GitHub 尚未连接” without substituting data |
| ETag-aware PR polling | VERIFIED_MACOS | Durable ETag/rate-limit sync plus background monitor and unit tests |
| PR snapshots and Head-SHA deduplication | VERIFIED_MACOS | Snapshot uniqueness, ETag and analysis dedup are database/API tested |
| PR Inbox | VERIFIED_MACOS | Real persisted inbox exercised in Chrome Playwright |
| PR details and typed tabs | VERIFIED_MACOS | Nine real-data tabs exercised in Chrome; unavailable Checks remain explicit |
| Monaco Diff with finding/evidence jumps | VERIFIED_MACOS | Local/offline Monaco and Finding→Diff flow verified by Playwright screenshot/test |
| Unified CodeParser interface | VERIFIED_MACOS | Python precise and JS/TS/Java partial capability levels tested and persisted |
| Incremental commit-bound index | VERIFIED_MACOS | Content hash/change/deletion and Head SHA binding tests |
| ripgrep/symbol/FTS5 hybrid retrieval | VERIFIED_MACOS | Sources remain labeled; vector retrieval explicitly disabled |
| Repository Map backend | VERIFIED_MACOS | Persisted parsed/indexed relationships and commit/index binding tests |
| Repository Map React Flow UI | VERIFIED_MACOS | Lazy React Flow, 800-node cap, filters, MiniMap and measured layout ADR-002 |
| Review Map backend | VERIFIED_MACOS | Real Git diff + static graph + persisted Agent Evidence API test |
| Review Map UI and Diff bidirectional jump | VERIFIED_MACOS | Chrome Playwright and `p1-review-map-macos.png` |
| Finding schema/storage foundation | VERIFIED_MACOS | Required traceability fields, filters and UI are persisted/API-tested |
| Evidence storage foundation | VERIFIED_MACOS | Commit/hash/source payload and Finding linkage verified |
| Agent Trace API/SSE/UI | VERIFIED_MACOS | Authenticated SSE parser, run detail, steps/tools and UI tests |
| Eval Center / ClaimBench integration | VERIFIED_MACOS | Real 19-case/160-run artifacts, hashes, drill-down and export rendered in Chrome |
| Desktop notifications implementation | IMPLEMENTED_UNVERIFIED | Official Tauri notification plugin, bounded native command, HostBridge and settings test action compile/test on macOS; actual OS display/click and Windows remain manual gates |
| Complete tray menu and monitoring controls | IMPLEMENTED_UNVERIFIED | All required Rust menu actions dispatch to real frontend sync/pause/navigation operations; direct status-item acceptance is still unavailable |

## P2: product enhancements

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Change Tour | VERIFIED_MACOS | Static relationship/evidence ordering API with low-confidence incomplete state tests |
| Agent Evidence Graph | VERIFIED_MACOS | Dedicated run-owned task→step→tool→evidence→finding API/React Flow graph is covered by API and Chrome E2E |
| Webhook relay with HMAC/deduplication | VERIFIED_MACOS | Separate FastAPI relay has one-use repository-scoped pairing, authenticated SSE, HMAC/replay tests and hardened compose; container/TLS deployment is unverified |
| Optional MySQL 8 profile | IMPLEMENTED_UNVERIFIED | PyMySQL profile, dialect-aware migrations/retrieval, MySQL 8.4 CI service and smoke script exist; offline SQL compiles but Docker is unavailable locally |
| Agent and Tool Registry screens | VERIFIED_MACOS | Seven workflow nodes and 19 actual tools rendered from API; Chrome screenshot/test |
| MCP client adapter | VERIFIED_MACOS | MCP 2025-11-25 stdio negotiation/list/call with executable/tool allowlists, filtered env and bounded fixture tests |
| Deep links | IMPLEMENTED_UNVERIFIED | Scheme/parser/single-instance delivery and real frontend repo/PR/run routing tests exist; OS URL invocation is not verified |
| Autostart toggle | IMPLEMENTED_UNVERIFIED | Official Tauri autostart manager and native settings bridge compile/test; defaults off and real login behavior remains manual by platform |
| Update interface reservation | VERIFIED_MACOS | Authenticated typed API reports an explicitly unconfigured signed-update channel; it never offers an unsigned payload |
| English localization | IN_PROGRESS | Persisted locale switches the shell, status primitives, Dashboard, Settings and Repository Map; remaining detailed pages are still Chinese-first |
| Graph JSON export | VERIFIED_MACOS | Repository Map downloads the current typed API payload in the browser flow |
| Graph PNG/SVG export | VERIFIED_MACOS | Standalone deterministic SVG is unit-tested; Chrome E2E downloads PNG and verifies its binary signature |
| GitHub OAuth Device Flow / App | VERIFIED_MACOS | GitHub Device Flow adapter enforces official URI/polling semantics and passes tokens only to a secure `SecretStr` sink; desktop UI still ships PAT first |

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
