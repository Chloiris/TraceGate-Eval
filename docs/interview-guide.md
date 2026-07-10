# TraceGate Studio interview guide

## Thirty-second explanation

TraceGate Studio is a local-first AI coding-agent workspace for Pull Request
review. It combines commit-bound static analysis, controlled Tool Calling,
evidence-aware LangGraph reasoning, and the existing TraceGate Eval/ClaimBench
research core. The central product promise is traceability: every semantic
Finding must link to the analyzed commit, files, Evidence, Agent step, and Tool
trace, while missing providers or uncertain relationships remain explicit.

## Architecture

The Tauri host owns the desktop lifecycle and secure capabilities. A bundled
Python Sidecar exposes an authenticated loopback FastAPI API. React talks only
through a typed Zod-validating client. SQLAlchemy/Alembic persists repositories,
PR snapshots, commits/files/hunks, indexes/graphs, runs/steps/tools, Evidence,
Findings, model profiles, and notification outcomes. The existing TraceGate
Eval modules remain the source of benchmark artifacts and verifier policy.

See [`architecture/ADR-001-tracegate-studio.md`](architecture/ADR-001-tracegate-studio.md).

## Why Tauri?

Tauri provides a small native lifecycle/security layer without moving the
product UI out of React. Rust controls the single instance, random local API
token, Sidecar process, Keychain/Credential Manager, tray, deep links,
notifications, autostart, window state, and true quit. The WebView never needs
raw provider credentials.

## Why FastAPI?

The existing TraceGate core is Python. FastAPI keeps parsing, retrieval,
EvidencePacket/verifier integration, GitHub adapters, LangGraph, and evaluation
code in one runtime while providing validated request/response contracts and
authenticated SSE. It also packages cleanly as a PyInstaller Sidecar.

## Why LangGraph?

The review is a stateful, cancellable workflow with seven independently
observable roles: Planner, Repository Retriever, Context Resolver, Code
Analyst, Risk Reviewer, Verifier, and Report Composer. LangGraph makes the node
boundaries explicit while TraceGate persists each node and Tool call itself.
The roles are not prompt labels; they have distinct inputs, outputs, and policy.

## Why SQLite by default and MySQL as an option?

SQLite matches a single-user local desktop product: zero external service,
transactional persistence, FTS5, and straightforward backup. MySQL is an
optional deployment profile for future service/team operation. Its migrations
and CI service are implemented, but no local Docker/MySQL runtime was available
for this verification pass.

## Why polling in a local application?

GitHub cannot deliver a webhook directly to a laptop without a public endpoint.
TraceGate therefore uses bounded ETag polling with configurable intervals,
rate-limit persistence/backoff, Head-SHA deduplication, and pause behavior. An
optional Relay converts verified GitHub webhooks into repository-scoped,
authenticated SSE without exposing the local API.

## How the code maps are built

`RepositoryIndexer` parses the checked-out commit, records content hashes,
capabilities, symbols, imports, and references, and incrementally compares the
previous index. Repository Map adds repository/directory/file/test/symbol nodes
and confirmed static edges. Review Map starts from real Git changed files,
expands one/two hops through confirmed graph edges, and overlays persisted
Findings/Evidence. The LLM may explain an edge but cannot create a static edge.

## How static and LLM relationships stay separate

Graph edges have a source, kind, and `confirmed` flag. Static parser/index edges
are confirmed. Missing/uncertain relationships remain unconfirmed and use a
different line style. Change Tour reports low confidence and incomplete order
when confirmed cross-file evidence is absent.

## Prompt-injection defenses

- Repository/PR/comment/code text is wrapped as untrusted evidence.
- System prompts explicitly forbid treating it as instructions.
- Model output must validate against strict Pydantic/JSON schemas.
- Paths, line ranges, Evidence IDs, and Head SHA are reverified after the model.
- Tool selection never bypasses Registry schema, permission, path, timeout, or
  output controls.
- No model failure falls back to a fake provider or rule-generated report.

## Avoiding stale memory

Memory claims carry repository, source, source type, commit, status,
confidence, Evidence IDs, and invalidation links. The Context Resolver rereads
current commit-bound evidence, marks stale/conflicting/unknown state, and the
Verifier checks that final Findings cite the analyzed Head SHA. Historical
summaries cannot override current code.

## Finding traceability

A Finding stores severity, confidence, category, message, path, line range,
commit, symbol, suggested action, verifier status, model profile, Evidence IDs,
and run ID. From the UI it jumps to Monaco and can be traversed backward through
Agent Evidence Graph to Evidence, Tool calls, and Agent steps.

## macOS development versus Windows delivery

macOS can build and verify only the macOS arm64 Sidecar and `.app`. A Windows
executable must be built by PyInstaller on `windows-latest`, renamed to the
Tauri target triple, health-checked there, and bundled by Tauri into NSIS (and
portable/optional MSI where supported). That CI result still does not prove
tray, notification, autostart, install, or uninstall behavior in a real Windows
GUI; those remain a separate manual checklist.

## Current limitations to state plainly

- Real LLM E2E is blocked without a model credential.
- No new remote GitHub sync/CI verification occurred without explicit user
  permission.
- Windows CI artifact and Windows GUI acceptance are unverified.
- JavaScript/TypeScript/Java parsing is intentionally partial compared with the
  precise Python path.
- Vector embeddings are not enabled; retrieval labels that absence.
- Large graphs use caps/aggregation and do not claim full function rendering.
- Latest macOS process/Sidecar startup and shutdown were verified, but GUI
  automation could not inspect the status item/window in that run.

## Useful evidence during an interview

- [`implementation-status.md`](implementation-status.md)
- [`performance.md`](performance.md)
- [`verification/p1-macos.md`](verification/p1-macos.md)
- [`screenshots/p1-pr-diff-macos.png`](screenshots/p1-pr-diff-macos.png)
- [`screenshots/p1-review-map-macos.png`](screenshots/p1-review-map-macos.png)
- [`screenshots/p1-eval-center-macos.png`](screenshots/p1-eval-center-macos.png)
- [`screenshots/p1-registry-macos.png`](screenshots/p1-registry-macos.png)

