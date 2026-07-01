# Mac Branch Plan

Generated on: 2026-07-01

## Branches

- Base branch: `chore/win11-to-m5-handoff`
- Development branch: `feature/tracegate-pr-advisory-real-data-mac`
- Current commit at branch creation: `a56b59975aa438815fe31c98627d67e3f382759f`
- Remote URL: `https://github.com/Chloiris/TraceGate-Eval.git`

## Branch Preparation

The workspace started without a local Git checkout, so the handoff branch was cloned directly:

```text
git clone --branch chore/win11-to-m5-handoff https://github.com/Chloiris/TraceGate-Eval.git TraceGate-Eval
```

The handoff branch was then verified with:

```text
git fetch origin
git pull --ff-only origin chore/win11-to-m5-handoff
```

The pull reported `Already up to date.` The Mac development branch was created from the handoff commit:

```text
git checkout -b feature/tracegate-pr-advisory-real-data-mac
```

## In Scope This Round

- Build the smallest reproducible real-data PR advisory MVP.
- Preserve the existing `python -m tracegate` module entrypoint.
- Discover and document public real-data sources.
- Fetch, normalize, validate, and manifest a minimal real dataset.
- Enforce no mock, no fallback, no synthetic contamination for real runs.
- Implement deterministic advisory decisions around claim validity, evidence status, verification-first behavior, and pollution risk.
- Add CLI paths for data discovery/fetch/normalize/validate/manifest, run, report, and guardrail audit/scan.
- Add a minimal GitHub Action advisory skeleton and Ubuntu CI.
- Update docs and tests honestly, including limitations and blocked/insufficient-data paths.
- Commit and push this work to `feature/tracegate-pr-advisory-real-data-mac` if GitHub push is available.

## Out of Scope This Round

- Full SaaS product, login, permissions, or multi-tenant workflow.
- General-purpose code review bot behavior.
- Public Relations monitoring or reporting.
- Full CodeRabbit/LangSmith/Langfuse/Promptfoo/OpenHands replacement.
- Automated code-fixing agent.
- Merge-blocking policy by default.
- Large-scale benchmark claims.
- Fake, demo, mock, or synthetic data passed off as real evaluation output.
