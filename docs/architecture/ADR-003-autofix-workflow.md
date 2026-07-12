# ADR-003: controlled Autofix workflow

- Status: Proposed
- Date: 2026-07-12
- Decision owners: TraceGate maintainers
- Starting main: `a1dcd7d755c25e0f75aac499943a07b759ec30db`

## Context

TraceGate Studio has a production review workflow that produces commit-bound
Findings and Evidence. Its existing write-gated `apply_patch` tool is a safe
primitive, but it is not a product-level repair transaction. Extending the
review graph in place would mix read-only analysis guarantees with mutable
state, confirmation and rollback concerns.

## Decision

Create a separate `TraceGateFixWorkflow`. Review remains read-only and Autofix
starts only from an explicit user request for an existing Finding.

The Fix workflow owns these observable stages:

1. `LOAD_FINDING`
2. `CHECK_FIX_ELIGIBILITY`
3. `PLAN_FIX`
4. `GENERATE_PATCH`
5. `VALIDATE_PATCH`
6. `AWAIT_USER_CONFIRMATION`
7. `APPLY_PATCH`
8. `RUN_VALIDATION`
9. `REINDEX_CHANGES`
10. `RE_REVIEW`
11. `FINALIZE`

Terminal states are `COMPLETED`, `FAILED`, `CANCELLED`, `ROLLED_BACK` and
`STALE`. A session cannot skip stages through API retries.

## Transaction identity

A Fix Session is bound to repository, Pull Request, Finding, base SHA, Head
SHA and Index Version. A normalized unified diff receives
`SHA256(normalized_patch)`. Confirmation binds the Fix Session, Finding,
repository, Pull Request, Head SHA, patch hash, nonce hash and expiry.

Any patch or Head-SHA change invalidates confirmation. A confirmation is
single-use and is consumed atomically when apply begins.

## Isolation

Default apply mode is `APPLY_IN_ISOLATED_WORKSPACE`. TraceGate creates a Git
worktree at the exact Pull Request Head under a controlled Autofix data root.
All patch operations, validation commands, indexing and re-review are rooted
there. The enrolled user workspace is never cleaned, reset or modified.

`PROPOSE_ONLY` is supported. Automatic commit, push, external PR creation and
GitHub comments are out of scope. A future local-commit mode requires a second
independent confirmation.

## Patch safety

Patch text is untrusted. Before confirmation it must pass:

- unified-diff parsing and normalization;
- bounded file and changed-line limits;
- `RepositoryBoundary` path and symlink validation;
- sensitive path and binary rejection;
- deletion/configuration/CI/security/lockfile risk classification;
- exact Head-SHA and worktree cleanliness checks;
- `git apply --check` inside the isolated worktree.

Safety boundaries cannot be disabled through settings.

## Validation and resolution

`ValidationCommandResolver` derives argument-vector commands only from
repository manifests, existing scripts and controlled presets. It filters the
environment, bounds time/output and persists return codes and summaries.

Re-review consumes the applied Git diff, validation results, a new local index,
the original Finding/Evidence and newly collected Evidence. `RESOLVED` requires
all required validation to pass, the original Finding to lose verifier support
and no disqualifying new risk. Missing tests, uncertain static capability or
incomplete evidence produces `NEEDS_HUMAN_REVIEW`, not success.

## Persistence and API

Persist queryable Fix Session, Patch Proposal, Confirmation, Validation Run and
Fix Result records. API transitions are idempotent, authenticated and reject
illegal states. SSE reports persisted state transitions and validation output
summaries without returning secrets or unbounded raw logs.

## Rollback and cleanup

Rollback only resets the Fix-owned worktree to its recorded Head SHA. Cleanup
removes only registered Autofix worktrees after confirming they are not active.
Residual worktrees are visible in diagnostics and eligible for bounded expiry
collection.

## Alternatives rejected

- Appending mutable nodes to the review graph: weakens the default read-only
  contract and couples unrelated retries.
- Applying to the enrolled repository: risks overwriting user changes.
- Trusting model-proposed shell commands: creates command-injection risk.
- Treating a passing test or missing Finding alone as resolution: insufficient
  evidence for a repair claim.

## Verification gates

This ADR becomes Accepted only after migration tests, state-transition tests,
path/patch/confirmation security tests, isolated-worktree integration tests,
API/SSE tests, frontend tests, a full fixture-labelled Playwright flow and one
truthfully scoped real-model Autofix execution all pass.
