# TraceGate Studio controlled Autofix baseline

- Baseline captured: 2026-07-12
- Starting protected `main` HEAD: `a1dcd7d755c25e0f75aac499943a07b759ec30db`
- Working branch: `feat/coding-agent-autofix-loop`
- Worktree state at capture: clean

## Executed baseline

`./scripts/test.sh` completed on macOS arm64 before Autofix changes:

- Python: 212 passed; one existing Starlette/httpx deprecation warning.
- Shared TypeScript types: 5 passed.
- Typed API client: 7 passed.
- Web/Vitest: 18 passed across six files.
- Rust/Tauri: 22 passed and one explicit native credential mutation test ignored.
- ESLint, TypeScript strict typecheck, Rust format/check/clippy: passed.

The same starting commit has successful protected-`main` CI, Backend, Frontend,
Rust, Security, macOS packaging and Windows packaging runs. That evidence is a
baseline only; it does not verify the Autofix work introduced after this file.

## Existing review workflow

`TraceGateAgentWorkflow` is a seven-node LangGraph review workflow:

1. Planner
2. Repository Retriever
3. Context Resolver
4. Code Analyst
5. Risk Reviewer
6. Verifier
7. Report Composer

It persists `AgentRun`, `AgentStep`, `ToolCallRecord`, `EvidenceRecord` and
`Finding` rows. The workflow remains read-only by default and is not a fix
orchestration engine.

## Existing Tool Registry and `apply_patch`

The registry exposes 19 schema-validated tools. The existing `apply_patch`
tool already provides a useful low-level primitive:

- it is disabled unless `ToolContext.write_enabled` is true;
- it requires an exact confirmation identifier;
- it validates diff header paths through `RepositoryBoundary`;
- it runs `git apply --check` before `git apply`;
- it returns the resulting Git diff and never commits or pushes.

It does **not** yet provide a persisted Fix Session, a SHA-256 patch identity,
confirmation expiry/consumption, Head-SHA freshness checks, patch size/file
limits, isolated worktree creation, controlled validation selection, reindex,
post-fix review, resolution policy, rollback or crash-recovery cleanup.

## Existing persistence

The Studio schema currently contains repositories, Pull Requests and
snapshots, changed files/hunks, commit-bound index data and graph records,
model profiles, Agent runs/steps/tool calls, memory claims, Evidence, Findings,
evaluation runs, webhook deliveries and notifications.

Five Alembic revisions are present through
`20260711_0005_parser_relationships`. There are no Fix Session, patch proposal,
confirmation, validation or fix-result tables.

## Existing repository and index boundaries

- `RepositoryBoundary` canonicalizes enrolled roots, rejects absolute paths,
  parent traversal, symlink escape and credential paths.
- `GitProvider` uses argument vectors, a filtered environment, bounded output
  and timeouts.
- `persist_repository_index` is bound to an enrolled repository path and Git
  commit, but currently indexes the repository's configured primary workspace.

Autofix must reuse these invariants while ensuring every mutable operation and
validation command is rooted in a Fix-owned isolated Git worktree.

## Existing frontend entry points

`StudioShell` owns navigation and deep-link routing. `PullRequestDetailPage`
already provides typed tabs, Finding/Evidence views and Monaco Diff. Shared
Zod schemas live in `packages/shared-types`; the typed HTTP/SSE client lives in
`packages/api-client`; React Query hooks live in `apps/web/src/api/queries.ts`.

There is no Fix tab, Fix Session list/detail, proposal confirmation, validation
stream, post-fix report, export or rollback UI.

## Missing controlled loop

The baseline proves Review → Evidence → Finding. It does not prove:

Finding → Eligibility → Fix Plan → Patch Proposal → static validation →
hash-bound user confirmation → isolated apply → validation → reindex →
re-review → resolution → export/rollback/cleanup.

## Migration and compatibility risks

- Existing review runs and Finding/Evidence identifiers must remain valid.
- SQLite fresh/upgrade/idempotency and offline MySQL DDL must continue to work.
- A Fix Session must reject a Pull Request Head or Index Version that changed
  after proposal generation.
- Worktree lifecycle code must never reset or clean the enrolled user
  workspace.
- Model output is untrusted text until Pydantic validation, patch validation,
  `git apply --check` and explicit confirmation all pass.
- Validation commands must come from repository manifests and controlled
  presets, never directly from model-produced shell text.
- Absence of tests or a failed verifier cannot become `RESOLVED`.
