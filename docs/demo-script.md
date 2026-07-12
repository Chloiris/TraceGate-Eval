# TraceGate Studio 3–5 minute demo

## Before the demo

Use a disposable authorized repository and redact every token/path/log. Choose
one of these scopes and say it on screen:

- **Playwright fixture:** reliable UI demonstration; not a model/public-PR run.
- **Real local repository + real model:** production plumbing evidence; not a
  public-PR result unless it actually uses a public PR.
- **Public PR + real model:** only when the Finding, exact Head, permission, and
  validation command are defensible and recorded.

```bash
./scripts/test.sh
pnpm test:e2e
./scripts/dev.sh
```

If no model is configured, demonstrate explicit failure. Do not use a fixture,
mock, cache, or rule fallback and call it a real semantic run.

## Live story

1. **Sync and truth (20 seconds).** Open PR Inbox. Show repository, PR,
   Base/Head SHA, sync/check state, and exact index identity.
2. **Review (25 seconds).** Run/read the seven-node read-only Agent Review.
   Jump from a Finding to its Evidence and exact Monaco Diff range.
3. **Generate Fix Plan (20 seconds).** Click **Generate Fix**. Explain that the
   new 11-node Fix graph is separate from Review and begins with eligibility.
4. **Patch Proposal (30 seconds).** Show affected files, risk warnings, full
   Unified Diff, `git apply --check`, and normalized SHA-256 Patch Hash.
5. **User confirmation (20 seconds).** Confirm the displayed hash. Explain
   session/repository/PR/Finding/Head/hash/expiry binding and single use.
6. **Isolated apply (20 seconds).** Apply to the managed worktree. In a second
   terminal, show the original workspace `git status` unchanged.
7. **Validation (30 seconds).** Watch SSE progress. Show the manifest-derived
   argument-vector command and real return code. If it fails, keep the failure
   and explain why it cannot become `RESOLVED`.
8. **Reindex + re-review (30 seconds).** Show transient index identity and the
   verifier's assessment of the original Finding/new risks.
9. **Final report (25 seconds).** Show resolution, final diff, residual
   Findings/risks, token/latency, Tool Call and command evidence.
10. **Export + rollback (20 seconds).** Download authoritative `.patch` and
    JSON report; roll back and clean only the Fix worktree. Repeat that Studio
    never auto-commits, pushes, comments, opens a PR, or merges.

## Required closing boundary

Say exactly what was shown. For fixture mode:

> “This run proves the deterministic UI/API/state-machine path over a test
> fixture. It is not a live-model or public-PR Autofix result.”

For one real-model run:

> “This run proves the scoped production request, Tool, patch, isolation,
> validation, re-review, persistence, and report path. It does not establish a
> general fix-success rate or Windows GUI behavior.”

## Failure branch worth showing

Use a fixture-labelled validation failure to show that:

- return code/output/error are persisted;
- the state does not become `RESOLVED`;
- report/export/rollback remain available;
- the user workspace stays unchanged.

Never simulate a green result merely to finish the demo.

## Evidence ready for slides

- [PR Diff fixture screenshot](screenshots/p1-pr-diff-macos.png)
- [Autofix confirmation fixture screenshot](screenshots/autofix-playwright-fixture-confirmation-macos.png)
- [Autofix result fixture screenshot](screenshots/autofix-playwright-fixture-result-macos.png)
- [Implementation status](implementation-status.md)
- [Autofix safety](autofix-safety.md)
- [Scoped real-model Autofix E2E status](verification/real-autofix-e2e-macos.md)
- [Historical real-model Review E2E](verification/real-model-e2e-macos.md)
- [Historical Windows CI](verification/windows-ci.md)
- [Windows manual checklist](windows-manual-acceptance.md)
