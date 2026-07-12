# TraceGate Studio implementation status

- Last updated: 2026-07-12
- Verification source: feature branch `feat/tracegate-studio-fullstack` through
  commit `a7466ce69441871df229a5ed1cdf32ec594ba935`
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
| Existing suite plus Studio tests | VERIFIED_MACOS / VERIFIED_WINDOWS_CI | Source-bound Windows CI passed 212 Python tests, 30 TypeScript/Vitest tests (5 shared types + 7 API client + 18 web), and 22 Rust tests (1 explicit native secure-store mutation ignored); macOS also passed 4 Chrome Playwright flows; original Eval coverage remains intact; see `verification/windows-ci.md` |
| ClaimBench controlled benchmark | VERIFIED_MACOS | Existing tests and checked-in 160-run reports; metric definitions unchanged |
| Real-PR hard benchmark | VERIFIED_MACOS | Existing tests and checked-in 19 scored cases |
| EvidencePacket and redaction | VERIFIED_MACOS | Existing `tests/test_pr_advisor.py` |
| Semantic verifier/guardrails | VERIFIED_MACOS | Existing tests; strict scan reports 0 dangerous runtime paths |
| Real DeepSeek semantic execution | VERIFIED_MACOS | One Keychain-injected `deepseek-chat` run on `psf/requests#7565` completed all six required stages with 7 persisted Agent Trace rows, 4 real model requests, 3 Tool Calls, 1 Evidence and 1 Finding without logging the key; Run ID `f3273e5e-ef34-4370-800d-63ee107fd7a4`; see `verification/real-model-e2e-macos.md` |

## P0: foundation and desktop loop

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Repository audit and baseline | VERIFIED_MACOS | `docs/current-baseline.md` plus recorded commands |
| Architecture decision | VERIFIED_MACOS | ADR boundaries were exercised by the packaged macOS app; see `docs/verification/p0-macos.md` |
| Development branch | VERIFIED_MACOS | `feat/tracegate-studio-fullstack` created from `76a23ab` |
| Monorepo workspace and locked Node dependencies | VERIFIED_MACOS / VERIFIED_WINDOWS_CI | pnpm workspace and `pnpm-lock.yaml`; Windows frozen install passed all 30 TypeScript/Vitest tests |
| Locked Python environment | VERIFIED_MACOS | `uv.lock`; frozen uv environment used for tests and packaging |
| React + strict TypeScript browser client | VERIFIED_MACOS | Dashboard plus P1 product pages exercised by Chrome Playwright; see `docs/verification/p1-macos.md` |
| Typed API client and shared types | VERIFIED_MACOS / VERIFIED_WINDOWS_CI | Zod-validated client; Windows CI passed 12 package tests plus 18 web tests |
| FastAPI `/api/v1` service | VERIFIED_MACOS | Authenticated API tests and real browser/desktop process |
| Local API authentication and CORS | VERIFIED_MACOS | Auth/CORS tests plus Tauri-origin runtime verification |
| SQLAlchemy 2 persistence | VERIFIED_MACOS | Studio models and API persistence tests |
| SQLite default database | VERIFIED_MACOS | Real onboarding/settings persistence and database tests |
| Alembic migration and SQLite migration test | VERIFIED_MACOS | `20260710_0001` through `20260711_0005`; fresh, idempotent, offline MySQL DDL and upgrade-with-data tests |
| Structured/redacted rotating logs | VERIFIED_MACOS | Packaged Sidecar wrote redacted JSONL with 5 MiB/3-backup limits and clean shutdown events |
| System status API | VERIFIED_MACOS | Explicit ready/not-configured/unavailable states tested and rendered |
| Diagnostics API/page | VERIFIED_MACOS | Redacted runtime/storage/queue/update state plus GitHub/index/graph/model/retrieval/notification metrics are API-tested and browser-rendered |
| Non-secret settings persistence | VERIFIED_MACOS | Theme/language/background choices persist; API never accepts a secret |
| macOS secure credential storage | VERIFIED_MACOS | Native Keychain round-trip passed and deleted its verification entry |
| Windows Credential Manager secure storage | VERIFIED_WINDOWS_CI | The ordinary Rust suite passed 22 tests with the mutation test ignored, then run `29176975492` explicitly reran `native_secure_store_round_trip -- --ignored` and passed its native write/read/delete cycle 1/1; this is automated runner evidence, not Windows GUI/manual acceptance |
| Python Sidecar entry and health check | VERIFIED_MACOS | Independent and packaged authenticated health checks passed |
| macOS arm64 PyInstaller Sidecar | VERIFIED_MACOS | Native Mach-O artifact built, authenticated-health-checked and bundled on 2026-07-10 |
| Tauri 2 shell | VERIFIED_MACOS | Latest packaged `.app` launched with one Tauri owner and real Sidecar; logs show migration, `api_ready`, graceful shutdown and no orphan process |
| macOS menu-bar tray and restore | IMPLEMENTED_UNVERIFIED | Rust construction/dispatch tests pass; direct status-item clicking was unavailable |
| Close-to-hide | VERIFIED_MACOS | Window closed while desktop and Sidecar processes remained alive |
| True quit stops Sidecar | VERIFIED_MACOS | Desktop plus PyInstaller bootloader/worker all disappeared after Quit |
| Single-instance foundation | VERIFIED_MACOS | Repeated native launch retained one application/Sidecar owner |
| Browser development mode | VERIFIED_MACOS | Browser UI exercised against real authenticated API |
| Windows x86_64 build workflow | VERIFIED_WINDOWS_CI | Push run [29176975492](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29176975492) and PR run [29176976588](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29176976588) succeeded for commit `a7466ce69441871df229a5ed1cdf32ec594ba935`; see `verification/windows-ci.md` |
| Windows Sidecar health check in CI | VERIFIED_WINDOWS_CI | PyInstaller produced `tracegate-backend.exe` and the Windows runner passed its authenticated loopback health check |
| Windows NSIS Setup.exe artifact | VERIFIED_WINDOWS_CI | Unsigned `TraceGate-Studio-Setup.exe` was produced, hashed, uploaded, and downloaded for hash/format inspection; this is not installation evidence |
| Windows MSI artifact | VERIFIED_WINDOWS_CI | Unsigned `TraceGate-Studio.msi` was produced, hashed, uploaded, and downloaded for hash/format inspection; this is not installation evidence |
| Windows portable archive | VERIFIED_WINDOWS_CI | `TraceGate-Studio-portable-x86_64.zip` contains `tracegate-studio.exe` and `tracegate-backend.exe`; archive hash verified after download |
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
| PR Inbox | VERIFIED_MACOS | Persisted fixture-backed inbox exercised in isolated Chrome Playwright |
| PR details and typed tabs | VERIFIED_MACOS | Nine persisted fixture-backed tabs exercised in isolated Chrome Playwright; unavailable Checks remain explicit |
| Monaco Diff with finding/evidence jumps | VERIFIED_MACOS | Local/offline Monaco and Finding→Diff flow verified by Playwright screenshot/test |
| Unified CodeParser interface | VERIFIED_MACOS | Audited 12-row Python/JS/TS/Java matrix with real temporary Git fixtures; Python AST is bounded and JS/TS/Java remain explicit declaration-level partial adapters; see `docs/parser-capability-matrix.md` |
| Incremental commit-bound index | VERIFIED_MACOS | Content hash/change/deletion and Head SHA binding tests |
| ripgrep/symbol/FTS5 hybrid retrieval | VERIFIED_MACOS | Sources remain labeled; vector retrieval explicitly disabled |
| Repository Map backend | VERIFIED_MACOS | Persisted parsed/indexed relationships and commit/index binding tests |
| Repository Map React Flow UI | VERIFIED_MACOS | Directory-first aggregation, 800-node cap, filters, MiniMap, collapse, save/restore and measured layout ADR-002; backend-local graph paging remains future work |
| Review Map backend | VERIFIED_MACOS | Real Git diff + static graph + persisted Agent Evidence API test |
| Review Map UI rendering | VERIFIED_MACOS | Review Map rendering is exercised in isolated Chrome Playwright |
| Review Map direct node ↔ Diff navigation | IMPLEMENTED_UNVERIFIED | UI foundations exist, but current Playwright evidence verifies Finding→Diff only; direct map-node navigation has not completed acceptance |
| Finding schema/storage foundation | VERIFIED_MACOS | Required traceability fields, filters and UI are persisted/API-tested |
| Evidence storage foundation | VERIFIED_MACOS | Commit/hash/source payload and Finding linkage verified |
| Agent Trace API/SSE/UI | VERIFIED_MACOS | Authenticated SSE parser, run detail, steps/tools and UI tests |
| Eval Center / ClaimBench integration | VERIFIED_MACOS | Real 19-case/160-run artifacts, hashes, drill-down and export rendered in Chrome |
| Desktop notifications implementation | IMPLEMENTED_UNVERIFIED | Official Tauri notification plugin, bounded native command, HostBridge and settings test action compile/test on macOS; actual OS display/click and Windows remain manual gates |
| Complete tray menu and monitoring controls | IMPLEMENTED_UNVERIFIED | All required Rust menu actions dispatch to real frontend sync/pause/navigation operations; direct status-item acceptance is still unavailable |

## P2: product enhancements

| Feature | Status | Evidence / next gate |
| --- | --- | --- |
| Change Tour | VERIFIED_MACOS | Static relationship/evidence ordering API plus files/symbols/purpose/prerequisite/risk/Evidence/checkpoints UI; low-confidence wording verified in Chrome |
| Agent Evidence Graph | VERIFIED_MACOS | Dedicated run-owned task→step→tool→evidence→finding API/React Flow graph is covered by API and Chrome E2E |
| Webhook relay with HMAC/deduplication | VERIFIED_MACOS | Separate FastAPI relay has one-use repository-scoped pairing, authenticated SSE, HMAC/replay tests and hardened compose; container/TLS deployment is unverified |
| Optional MySQL 8 profile | IMPLEMENTED_UNVERIFIED | PyMySQL profile, dialect-aware migrations/retrieval, MySQL 8.4 CI service and smoke script exist; offline SQL compiles but Docker is unavailable locally |
| Agent and Tool Registry screens | VERIFIED_MACOS | Seven workflow nodes and 19 actual tools, persistent toggles and execution-time enforcement; API/unit/Chrome toggle tests |
| MCP client adapter | VERIFIED_MACOS | MCP 2025-11-25 stdio negotiation/list/call with executable/tool allowlists, filtered env and bounded fixture tests |
| Deep links | IMPLEMENTED_UNVERIFIED | Scheme/parser/single-instance delivery and real frontend repo/PR/run routing tests exist; OS URL invocation is not verified |
| Autostart toggle | IMPLEMENTED_UNVERIFIED | Official Tauri autostart manager and native settings bridge compile/test; defaults off and real login behavior remains manual by platform |
| Update interface reservation | VERIFIED_MACOS | Authenticated typed API reports an explicitly unconfigured signed-update channel; it never offers an unsigned payload |
| English localization | VERIFIED_MACOS | Persisted locale switches the shell, status primitives, Dashboard, Onboarding, repositories, PR Inbox/detail, maps, runs, Eval, Registry, Diagnostics and Settings; English render has a Vitest integration check |
| Graph JSON export | VERIFIED_MACOS | Repository Map downloads the current typed API payload in the browser flow |
| Graph PNG/SVG export | VERIFIED_MACOS | Standalone deterministic SVG is unit-tested; Chrome E2E downloads PNG and verifies its binary signature |
| GitHub OAuth Device Flow / App | IMPLEMENTED_UNVERIFIED | Rust Device Flow state is memory-only, validates official URI/polling semantics and writes tokens directly to Keychain/Credential Manager; no live GitHub authorization was performed |

## Latest local performance evidence

The reproducible smoke record in `docs/performance.md` measured 100/1000-file
production index/graph paths, Review Map, a 157 ms browser data-ready wall-clock
upper bound, and five 0.1% idle Python-worker CPU samples. A subsequent real
DeepSeek PR-analysis run measured 12,362 ms end-to-end and 11,998 ms of model
latency; see `verification/real-model-e2e-macos.md`. Windows performance
remains outside the current Mac verification boundary.

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

P0 browser, API, SQLite/Alembic, packaged Sidecar, Tauri shell, prior
close-hide/single-instance/true-quit evidence, and the latest process/Sidecar
startup/shutdown are `VERIFIED_MACOS`. The latest build is
`artifacts/macos/TraceGate-Studio-macos-arm64.zip` with SHA-256
`bd29c2b7c587cdb4d285e91423a2d1535866dc073f013959508da24a807d0324`.
The current UI automation surface could not inspect a new app window/status
item, so direct tray restore and notification click remain
`IMPLEMENTED_UNVERIFIED`.

### Windows x86_64 CI

Commit `a7466ce69441871df229a5ed1cdf32ec594ba935` passed the push and Pull
Request Windows workflows on `windows-latest`. The runner passed 212 Python,
30 TypeScript/Vitest, and 22 Rust tests (with 1 native secure-store test ignored
in the ordinary suite), then passed that native Credential Manager round-trip
in a separate explicit 1/1 invocation, authenticated the PyInstaller Sidecar
health endpoint, and produced unsigned NSIS, MSI, and portable packages.
Artifact `TraceGate-Studio-Windows-x86_64-unsigned-a7466ce69441871df229a5ed1cdf32ec594ba935`
(ID `8255326332`) contains the packages, `SHA256SUMS.txt`, `build-info.json`,
and `test-summary.txt`. Exact runs, hashes, retention, and download evidence are
recorded in [`verification/windows-ci.md`](verification/windows-ci.md).

### Windows graphical manual acceptance

No manual evidence exists. Installation, WebView2, tray, notification,
autostart, single-instance, background process and uninstall checks remain
`BLOCKED` or `IMPLEMENTED_UNVERIFIED`; none are `VERIFIED_WINDOWS_MANUAL`.

## Status update rule

Every update to this file must point to at least one test, build artifact,
runtime log, screenshot, API response, database record, CI run, or Git commit.
Code review alone may advance a feature only to `IMPLEMENTED_UNVERIFIED`.
