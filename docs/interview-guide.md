# TraceGate Studio engineering discussion guide

## Thirty-second explanation

TraceGate Studio is a local-first workspace for evidence-grounded Pull Request
review and controlled Coding Agent Autofix. A seven-node read-only LangGraph
workflow produces commit-bound Findings/Evidence. A separate 11-node Fix
workflow can plan, propose, statically validate, hash-confirm, apply in an
isolated Git worktree, run controlled tests, reindex, re-review, and emit a
deterministic resolution. TraceGate Eval/ClaimBench remains the research and
agent-evaluation subsystem.

## Why Review and Fix are separate

Review has a simple read-only trust contract: source/PR/model text cannot
mutate a repository. Fix introduces confirmation, patch identity, optimistic
locking, worktree lifecycle, command execution, rollback, cleanup, and a
different failure model. Extending Review in place would make retries and
permissions ambiguous. The separate `TraceGateFixWorkflow` starts only from an
existing Finding and preserves Review's seven-node contract.

**Evidence:** `tracegate/agent/workflow.py`,
`tracegate/agent/fix_workflow.py`,
[`architecture/ADR-003-autofix-workflow.md`](architecture/ADR-003-autofix-workflow.md).

## Why the model cannot write files directly

Model output is untrusted. The provider returns a strict structured Patch
Proposal; the server independently parses the unified diff, validates exact
Finding/base/head identity, paths, symlinks, sensitive/binary targets and
limits, then runs `git apply --check`. Only a separately confirmed persisted
patch can reach apply. This converts free-form model text into an auditable
transaction with deterministic gates.

## How Patch Hash prevents replacement

TraceGate hashes normalized diff bytes with SHA-256. Confirmation binds Fix
Session, repository, PR, Finding, Head SHA, Patch Hash, nonce hash, and expiry.
Apply recomputes/compares identity, consumes confirmation once, and uses
optimistic `lock_version`. A proposal replacement, stale browser tab, expired
confirmation, or changed Head is rejected.

**Evidence:** `tracegate/autofix/confirmation.py`,
`tracegate/autofix/patch_safety.py`, `tests/test_autofix_api.py`.

## Why an isolated Git worktree

The enrolled source workspace may contain valuable uncommitted changes.
Autofix creates a detached worktree at the exact PR Head under a managed data
root and performs apply, tests, indexing, re-review, rollback, and cleanup
there. Reset/clean is only legal inside that registered Fix workspace; the
source workspace remains unchanged.

**Evidence:** `tracegate/autofix/workspace.py`,
`tests/test_autofix_safety.py`.

## How PR Head updates are handled

The session stores base/head SHA and index version. Eligibility, proposal,
confirmation, and apply compare current persisted PR Head to the Fix-bound
Head. A change invalidates confirmation and moves the transaction to `STALE`
instead of applying a previously reviewed patch to different code. The user
must sync/reindex/review again.

## How validation commands are selected

The model may describe validation intent but cannot choose executable shell
text. `ValidationCommandResolver` reads repository manifests and existing
scripts/presets, emits bounded argument vectors, and distinguishes tests from
lint/typecheck. The executor uses an isolated cwd, filtered environment,
allowlists, timeout, cancellation, process termination, and bounded output.
No recognized test yields `NO_TEST_COMMAND_AVAILABLE`, not an invented pass.

## How TraceGate decides a Finding is actually resolved

The model's re-review is only one input. Deterministic policy requires:

1. the exact confirmed patch was applied;
2. every required validation passed;
3. the modified worktree was reindexed;
4. the verifier no longer supports the original Finding;
5. no disqualifying new risk appeared.

Otherwise the result is `PARTIALLY_RESOLVED`, `NOT_RESOLVED`,
`VERIFICATION_FAILED`, or `NEEDS_HUMAN_REVIEW`.

## Why passing tests may still need human review

Tests can omit the affected behavior; parser coverage can be partial; Evidence
can be insufficient; the change can introduce an untested security or product
risk. Passing commands prove only their scoped assertions. `RESOLVED` therefore
also requires reindex/re-review/verifier evidence and sufficient certainty.

## How rollback and cleanup work

Rollback restores only the managed Fix worktree to its recorded Head. Cleanup
removes only registered paths below the Autofix root after active-operation
checks. Cleanup failure remains persisted and visible through diagnostics;
retention does not silently erase evidence.

## Prompt-injection defenses

- PR descriptions, comments, code, README text, generated files, and model
  output are labelled untrusted data.
- System policy and Registry permissions are not writable prompt fields.
- Structured output is schema-validated; file/range/SHA/Evidence references are
  reverified by application code.
- Repository text cannot enable write mode, expand scope, select arbitrary
  commands, read denied files, or disable Patch Hash confirmation.
- Model failure remains failure; no fixture/rule result is substituted.
- Final resolution is deterministic and cannot be asserted by prompt text.

## Why TraceGate does not auto-push

Push, PR comment, PR creation, merge, and remote history changes cross a larger
authorization and collaboration boundary than local patch analysis. Version
`0.4.0` stops at exportable patch/report and managed local worktree. A future
remote action would need separate least-privilege credentials, target/branch
preview, fresh confirmation, idempotency, audit, and recovery design.

## Architecture choices

- **Tauri 2:** small native lifecycle/security layer around a React UI; owns
  Sidecar, secure store, single instance, tray, deep links, notifications, and
  true quit.
- **FastAPI/Python:** keeps existing parsers, Evidence/verifier, GitHub,
  LangGraph, Eval, and controlled subprocess logic in one typed runtime.
- **React + Zod:** strict shared boundary for API/SSE payloads; browser and
  desktop surfaces share the same UI without giving browser mode raw secrets.
- **SQLite + Alembic:** local-first transactional persistence and FTS5;
  optional MySQL DDL/profile remains a separately verified deployment path.
- **LangGraph:** observable stateful nodes while TraceGate owns persistence,
  policy, confirmation, and deterministic resolution.

## Static-analysis honesty

Python is AST-backed but still bounded to implemented same-file direct-call and
inheritance cases. JavaScript/TypeScript/Java are declaration-level partial
adapters, not semantic call-graph engines. Repository/Review Map consumes only
confirmed edges; inferred and unknown relations remain labelled. See
[`parser-capability-matrix.md`](parser-capability-matrix.md).

## How to demonstrate the closed loop

Follow [`demo-script.md`](demo-script.md): sync → Review → Finding/Evidence →
Fix Plan → Proposal/Hash → confirmation → isolated apply → real validation →
reindex → re-review → resolution/report → export → source-workspace proof →
rollback/cleanup. Announce fixture/real-local/real-model/public-PR scope before
starting.

## Limitations to state plainly

- Autofix full-suite and a real DeepSeek synthetic temporary-repository E2E are
  `VERIFIED_MACOS`; public-PR Fix E2E is `BLOCKED`, and no automatic-fix
  accuracy is claimed.
- The existing real DeepSeek public-PR record verifies Review only.
- Windows baseline, source-bound Autofix, and post-merge `main` CI produced
  unsigned packages; none is Windows GUI/manual acceptance.
- Validation argv/cwd/environment are controlled, but repository tests still
  run with local user authority and are not OS/container sandboxed.
- Windows GUI installation/tray/notifications/autostart/uninstall remain
  `BLOCKED` on a real target.
- Live GitHub OAuth Device Flow authorization is unverified.
- Vector Embedding is disabled; the real-PR dataset is small.
- No auto-commit, push, comment, PR creation, or merge exists.

## Evidence index

- [`implementation-status.md`](implementation-status.md)
- [`autofix-guide.md`](autofix-guide.md)
- [`autofix-safety.md`](autofix-safety.md)
- [`verification/real-autofix-e2e-macos.md`](verification/real-autofix-e2e-macos.md)
- [`verification/real-model-e2e-macos.md`](verification/real-model-e2e-macos.md)
- [`verification/windows-ci.md`](verification/windows-ci.md)
- [`windows-manual-acceptance.md`](windows-manual-acceptance.md)
- [`screenshots/autofix-playwright-fixture-confirmation-macos.png`](screenshots/autofix-playwright-fixture-confirmation-macos.png)
- [`screenshots/autofix-playwright-fixture-result-macos.png`](screenshots/autofix-playwright-fixture-result-macos.png)
