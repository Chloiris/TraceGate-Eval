# TraceGate Studio product tour

This tour separates UI fixture evidence from real-model/public-PR evidence. The
current Autofix screenshots are Playwright fixture captures. A separate real
DeepSeek record is `VERIFIED_MACOS` for a synthetic temporary Git repository;
public-PR Fix E2E remains `BLOCKED`.

## 1. Start with system truth

Open **Overview**. Ready, unconfigured, unavailable, and error states are
distinct. Without credentials Studio says GitHub/model/Relay is not configured
and never substitutes a fixture provider or rule-generated semantic report.

Settings has secondary navigation for Appearance, Connections, Model,
Repositories, Monitoring, Autofix limits, and Diagnostics. Credential fields
write through the native bridge to Keychain/Credential Manager and return only
`configured`/`missing` status.

## 2. Enroll, synchronize, and index

Open **Repositories**, add `owner/name`, and explicitly authorize an absolute
local Git workspace. Sync persists PR metadata, snapshots, Base/Head SHA,
commits, files/hunks, comments, checks, ETag, and rate-limit state. Reindex
records content hashes, parser capability, symbols, relationships, and FTS data
for the exact commit.

An index mismatch is not repaired silently: fetch/check out the exact Head
outside TraceGate, then reindex.

## 3. Explore Repository Map

Use directory aggregation, path/language/relation/PR/risk filters, one/two-hop
exploration, MiniMap, collapse, and layout persistence. Node detail links to
symbols, tests, Findings, Evidence, Diff, VS Code, and GitHub. JSON/SVG/PNG
exports reflect the persisted response.

Only confirmed parser/index relationships are map edges. Inferred/unknown
observations stay labelled provenance, and response caps remain visible.

## 4. Review a Pull Request

PR Inbox reads persisted synchronization data. The detail workspace shows:

- **Files & Diff:** Monaco Base/Head/Diff, hunks, Finding/Evidence markers,
  GitHub and bounded VS Code jumps;
- **Review Map:** Git changed files + confirmed static neighbors + persisted
  Agent Evidence;
- **Change Tour:** changed files/symbols, purpose, prerequisites, risk,
  Evidence, confidence, checkpoints, and explicit incomplete order;
- **Checks/History:** real persisted GitHub state and prior Agent Runs.

![Fixture-backed PR detail](screenshots/p1-pr-diff-macos.png)

> Playwright repository fixture. This image verifies UI behavior only.

## 5. Inspect read-only Agent Review

Starting analysis requires a configured real provider and a Head-matching
index. Seven LangGraph nodes persist steps and Tool Calls. Agent Runs streams
authenticated SSE, supports cancellation/retry, and links Findings backward to
Evidence, file ranges, Tool Calls, and Agent steps.

The historical production-path DeepSeek review E2E proves requests,
Tool Calls, persistence, and traceability for one public PR; it is not Autofix
or accuracy evidence.

## 6. Generate a controlled Fix Plan

Open a persisted Finding and choose **Generate Fix**. Studio creates a session
bound to repository, PR, Finding, source Run, Base/Head SHA, and index. It checks
eligibility before asking the production ModelProvider for a structured plan.

Hard stale/sensitive/path/binary boundaries cannot be forced away. Planning
failure stays visible, and the seven-node Review workflow remains unchanged.

## 7. Inspect Patch Proposal and confirmation

Generation returns a structured unified diff and validation metadata. The
server parses and bounds it, resolves every path/symlink, rejects sensitive and
binary targets, checks exact Head/clean worktree, runs `git apply --check`, and
computes the authoritative normalized Patch Hash.

![Fixture-backed hash confirmation](screenshots/autofix-playwright-fixture-confirmation-macos.png)

> Playwright Autofix fixture. This is not a live-model/public-PR patch.

The user confirms that exact Patch Hash. Confirmation binds the session,
repository, PR, Finding, Head SHA, hash, nonce, and expiry; it is single-use.
A Head/hash change blocks apply.

## 8. Apply, validate, and watch events

Apply runs only in a Fix-owned detached Git worktree at the exact Head. The
enrolled user workspace is unchanged. Validation commands are derived from
manifests/presets as argument vectors and run with filtered environment,
timeout, cancellation, output caps, and persisted return codes. Model-supplied
shell text is never executed.

This is command control, not an OS/container sandbox: repository tests still
run with the local user's authority. Use a disposable environment for
untrusted PRs.

SSE resumes with `Last-Event-ID`. Validation running, failure, timeout,
cancellation, no-test, and success remain distinct states.

## 9. Reindex, re-review, and report

Studio creates a transient index bound to Head + Patch Hash, re-reviews the
actual applied diff and validation, then applies deterministic resolution
policy. Tests passing alone cannot produce `RESOLVED`; the original Finding
must lose verifier support and no disqualifying new risk may appear.

![Fixture-backed Post-Fix report](screenshots/autofix-playwright-fixture-result-macos.png)

> Playwright Autofix fixture. The separate
> [`VERIFIED_MACOS` real-model record](verification/real-autofix-e2e-macos.md)
> uses a synthetic temporary repository, not a public PR.

The report exposes commands/return codes, re-review, final diff, residual
Findings/risks, and one of five explicit resolutions.

## 10. Export, rollback, and clean up

Patch and JSON report downloads come from authoritative persisted content.
Export does not commit or push. Rollback resets/cleans only the managed Fix
worktree to its recorded Head. Cleanup deletes only registered worktrees under
the Autofix root; failures and retained/orphaned workspaces appear in
Diagnostics.

## 11. Finish with policy and evaluation

Registry exposes seven Review roles and 19 real Tool schemas/permissions/
limits. Eval Center renders the checked-in 19-case public-PR set and 160
ClaimBench rows without changing metric definitions. Diagnostics shows
redacted provider/index/graph/model/Fix/workspace state, not secrets.

Use [`implementation-status.md`](implementation-status.md) for current gates,
[`autofix-guide.md`](autofix-guide.md) for operations, and
[`autofix-safety.md`](autofix-safety.md) for the threat model.
