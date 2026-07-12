# TraceGate Studio implementation status

- Last updated: 2026-07-12
- Product version: `0.4.0`
- Current branch: `main`
- Current `main` SHA at this post-PR-#17 audit boundary:
  `35bc8caf66dcc61b6f1559e26405980b4ff1ae5d`
- Merged delivery PR: [#17](https://github.com/Chloiris/TraceGate-Eval/pull/17)
- Feature branch: `feat/coding-agent-autofix-loop` — merged / historical
- Pre-Autofix baseline main SHA: `a1dcd7d755c25e0f75aac499943a07b759ec30db`
- Source-bound tested implementation SHA: `69402dd7d570b64a36fba883f98b540f8a893ee5`
- PR head SHA: `74e457704f431bc21ad5b1d29fbfc475fa077be7`
- PR CI merge-ref SHA: `456c0914cd214961b9c4265b239e74eb00a6e390`
- Latest post-merge Windows Run: [29197940209](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29197940209)
- Latest Windows Artifact: `8261706447` —
  `TraceGate-Studio-Windows-x86_64-unsigned-35bc8caf66dcc61b6f1559e26405980b4ff1ae5d`
- Canonical facts: [`project-facts.yaml`](project-facts.yaml)

This is the current-facing status page. Older source-bound evidence keeps its
original SHA/run and carries a **Historical verification record** marker.
The documentation-only finalization PR can advance `main`; that later Git
commit does not replace the PR #17 delivery SHA or source-bound runtime evidence.

## Status definitions

- `PENDING`: a required run or dynamic evidence has not been produced yet.
- `IN_PROGRESS`: implementation and verification are actively incomplete.
- `IMPLEMENTED_UNVERIFIED`: code exists, but the named runtime/platform gate
  has not run.
- `VERIFIED_MACOS`: the stated scope ran on the source-bound macOS record.
- `VERIFIED_WINDOWS_CI`: the stated automated scope ran on a Windows runner.
- `VERIFIED_WINDOWS_MANUAL`: a human completed the stated check on a real
  Windows graphical desktop.
- `BLOCKED`: an external prerequisite is unavailable and documented.

`VERIFIED_WINDOWS_CI` never implies `VERIFIED_WINDOWS_MANUAL`.

## Current controlled Autofix

| Capability | Status | Code/test/evidence boundary |
| --- | --- | --- |
| Separate Fix workflow | `VERIFIED_MACOS` | `tracegate/agent/fix_workflow.py` defines 11 observable nodes; all 11 persisted as completed in the real-model run. Review remains seven-node/read-only. |
| Finding eligibility | `VERIFIED_MACOS` | Verifies Finding/Run/PR/repository/index/Evidence, Head SHA, path/range and sensitive/binary constraints; failed real runs demonstrated explicit rejection. |
| Structured Fix Plan | `VERIFIED_MACOS` | Production DeepSeek `ModelProvider.complete_structured` plus one persisted real `read_file` Registry Tool Call. |
| Structured Patch Proposal | `VERIFIED_MACOS` | Real patch, identity bindings, risks, validation metadata and token/latency accounting are in the scoped run record. |
| Static patch safety | `VERIFIED_MACOS` | Path/symlink/sensitive/binary/mode/rename/limit checks, exact Head, clean worktree and `git apply --check`; malformed real outputs failed closed. |
| Hash-bound confirmation | `VERIFIED_MACOS` | Session/repository/PR/Finding/Head/Patch Hash/nonce/expiry binding and single-use consumption; exact E2E Hash recorded. |
| Isolated apply | `VERIFIED_MACOS` | Detached worktree at exact Head; the real run proved the enrolled source workspace remained byte-clean and unchanged. |
| Controlled validation | `VERIFIED_MACOS` | Three resolver-approved argv commands passed and persisted. Command selection is controlled, but repository test code is not OS/container sandboxed. |
| Reindex and re-review | `VERIFIED_MACOS` | Transient index uses the actual worktree state hash and full diff; real production-provider re-review completed. |
| Deterministic resolution | `VERIFIED_MACOS` | `RESOLVED` additionally requires a changed Finding-path content hash and a passing path-related directed test; model re-review is advisory. |
| Persistence/migration | `VERIFIED_MACOS` | Alembic `20260712_0006`, fresh/upgrade/idempotency/downgrade-upgrade SQLite and offline MySQL DDL tests passed. |
| Authenticated API/SSE | `VERIFIED_MACOS` | 17 method/path contracts, optimistic locking, idempotency, typed Agent Trace, exports, diagnostics cleanup and resumable `Last-Event-ID` SSE passed. |
| Frontend Fix experience | `VERIFIED_MACOS` | Typed Finding → plan → patch projection → confirmation → validation → report/history/trace UI; Vitest and five fixture-labelled Playwright flows passed. |
| Rollback/cleanup | `VERIFIED_MACOS` | Real run recorded rollback and deletion; native Diagnostics showed no residual managed workspace. |
| Real-model Autofix E2E | `VERIFIED_MACOS` | Real DeepSeek reached `RESOLVED` on an explicitly labelled synthetic temporary Git repository; public-PR Fix E2E is `BLOCKED`. |
| macOS package with Autofix | `VERIFIED_MACOS` | PyInstaller Sidecar health, Tauri `.app`, native authenticated launch, Settings/Diagnostics and unsigned arm64 ZIP SHA were verified locally. |
| Windows CI with Autofix | `VERIFIED_WINDOWS_CI` | Post-merge `main` Run `29197940209`: 269 Python, 60 TypeScript, 22 Rust + 1 ignored, PyInstaller Sidecar health, Tauri NSIS/MSI, portable ZIP, checksums and metadata passed. |
| Windows Autofix GUI/manual | `BLOCKED` | No real Windows graphical target is available. |

Focused test sources are `tests/test_autofix_safety.py`,
`tests/test_fix_workflow.py`, `tests/test_autofix_api.py`, database/migration
tests, shared schemas, typed client, `FixExperience` Vitest, and the
fixture-labelled Playwright flow. File presence is not a pass claim; aggregate
counts below are copied from the completed matrix.

## Review and evidence product

| Capability | Current evidence |
| --- | --- |
| Seven-node read-only LangGraph review | `VERIFIED_MACOS`; production workflow persists Run/Step/Tool/Evidence/Finding and exposes cancellation/retry/SSE. |
| Tool Registry | 19 production schema-validated tools with read/command/write-confirmation permissions and execution-time enablement. |
| Real model review E2E | `VERIFIED_MACOS` historical record: `deepseek-chat` on `psf/requests#7565`, 4 real requests, 3 completed Tool Calls, 1 Evidence, 1 Finding, 7 Agent Trace rows, 3,826 tokens. This is review evidence, not Autofix evidence. |
| GitHub sync | ETag/rate-limit state, PR snapshots, Head-SHA dedup, files/commits/comments/checks and explicit unavailable states are implemented/tested. Live OAuth Device Flow authorization remains unverified. |
| Commit-bound code intelligence | Python AST plus bounded JS/TS/Java adapters, incremental index, ripgrep/symbol/FTS5 retrieval, Repository Map, Review Map, Change Tour. Vector embedding is disabled. |
| Eval Center | 19 scored public-PR cases and 160 checked-in ClaimBench rows with artifact provenance; the real-PR set is intentionally small. |

## Desktop and platform evidence

| Platform/capability | Status | Scope |
| --- | --- | --- |
| macOS arm64 baseline product path | `VERIFIED_MACOS` | Historical browser/API/SQLite, packaged Sidecar, secure-store and bounded desktop lifecycle evidence at the pre-Autofix source SHA. Direct status-item and notification-click acceptance remain excluded. |
| Windows x86-64 baseline CI | `VERIFIED_WINDOWS_CI` | Historical run `29185555800`, artifact `8258026173`: automated tests, Credential Manager round trip, authenticated Sidecar health, unsigned Setup.exe/MSI/portable ZIP, checksums, build metadata. |
| macOS Autofix package | `VERIFIED_MACOS` | `TraceGate Studio.app` launched natively and connected to its authenticated packaged Sidecar; ZIP SHA-256 `bbb08229fdcdd7f1757c87a066bc80112974b7297e72bd1f4f13e318ae2af527`. |
| Windows Autofix CI/package | `VERIFIED_WINDOWS_CI` | Post-merge `main` Run `29197940209`, Artifact `8261706447`; Setup.exe, MSI, portable ZIP and checksums were downloaded and revalidated. |
| Historical source-bound Windows Autofix CI | `VERIFIED_WINDOWS_CI` | Historical Run `29196292381`, Artifact `8261244145`; preserved as implementation-source evidence, not current delivery metadata. |
| Windows installation and GUI | `BLOCKED` | Installer, WebView2, tray, notifications, autostart, single instance, hidden monitoring, true quit, uninstall and residue require the real target checklist. |

The current Autofix artifact is recorded in
[`verification/windows-autofix-ci.md`](verification/windows-autofix-ci.md).
It is unsigned automated evidence and does not establish Windows GUI acceptance.

## Executable baseline and current totals

The clean starting `main` ran:

| Suite | Historical pre-Autofix result |
| --- | ---: |
| Python | 212 passed |
| Shared types | 5 passed |
| API client | 7 passed |
| Web/Vitest | 18 passed |
| Rust | 22 passed; 1 explicit native mutation test ignored |
| Playwright | 4 flows in the recorded baseline |

Current source-bound implementation totals from `./scripts/test.sh` and
`pnpm test:e2e`:

| Suite | Current result |
| --- | ---: |
| Python | 269 passed |
| Shared types | 15 passed |
| API client | 17 passed |
| Web/Vitest | 28 passed |
| Rust | 22 passed; 1 explicit native mutation test ignored |
| Playwright | 5 passed |

Docs consistency, lint, typecheck, Rust fmt/clippy and native packaging also
passed. The same aggregate matrix and package gates passed on the source-bound
Windows workflow.

## Parser and graph boundary

The authoritative 12-row matrix is
[`parser-capability-matrix.md`](parser-capability-matrix.md). Python is
AST-backed but bounded. JavaScript/TypeScript/Java are declaration-level
partial adapters; semantic references and JS/TS/Java function call graphs are
not claimed. Repository Map and Review Map consume only confirmed static
edges. LLM text cannot change static confidence.

## Security and mutation boundary

Review is read-only by default. Autofix:

- requires a user-created Fix Session from an existing Finding;
- binds confirmation to exact Head SHA and Patch Hash;
- applies only in a managed isolated worktree;
- runs only resolver-approved argument-vector validation commands;
- makes the user acknowledge that repository test code still runs with local
  user authority and is not OS/container sandboxed;
- never auto-commits, pushes, comments, opens a PR, or merges;
- cannot mark failed/absent tests or uncertain re-review as `RESOLVED`;
- keeps failure, stale state, rollback, cleanup, and residual risks visible.

See [`autofix-safety.md`](autofix-safety.md).

## Explicitly deferred interfaces

| Feature | Status |
| --- | --- |
| P4/Perforce provider | `NOT_STARTED` |
| UE WebView host | `NOT_STARTED` |
| Maya WebView host | `NOT_STARTED` |
| Multi-user/team service | `NOT_STARTED` |
| Cloud synchronization | `NOT_STARTED` |
| Automatic external commit/push/comment/merge | Out of scope by safety decision |

## Completed delivery evidence

- feature source commit and Pull Request URL;
- complete local test totals;
- real-model Autofix scope, model, Fix Session ID, Tool Calls, token/latency,
  Patch Hash, changed files/lines, commands/return codes, re-review, resolution,
  authoritative files, rollback/cleanup;
- macOS Sidecar/Tauri build and runtime result;
- Windows workflow URL, per-job status, artifact name/ID/paths/hashes;
- explicit statement that Windows CI is not Windows GUI manual acceptance.

These fields are source-bound in the verification records. A signed release,
public-PR Autofix E2E, and Windows graphical/manual acceptance are not claimed.

## Status update rule

Every promotion must cite a test, migration result, runtime record, screenshot
with provenance, API/database evidence, artifact, workflow run, or Git commit.
Code review alone can reach only `IMPLEMENTED_UNVERIFIED`; a fixture screenshot
cannot become real-model/public-PR evidence.
