# Post-Merge Status

Generated on: 2026-07-02

## Main Currently Includes

- Stage3 Controlled Claim Benchmark / ClaimBench over the synthetic legacy-shop sample project.
- A minimal real-data Pull Request advisory smoke path on `main`.
- CLI commands for real-data discovery, fetch, normalize, validate, manifest, run, report, and guardrail audit.
- A deterministic rule-based PR advisory baseline.
- Reality guardrails that distinguish real, demo, mock, synthetic, and fixture data.
- GitHub Actions for Python CI and a warning-only TraceGate advisory skeleton.

## Real-Data Smoke Run

- Dataset: `datasets/real_min/cases.jsonl`
- Manifest: `datasets/real_min/manifest.json`
- Source: public GitHub REST API Pull Request metadata and changed-file provenance.
- Source repositories: `psf/requests`, `pytest-dev/pytest`, `pydantic/pydantic`
- Raw records inspected: 12
- Normalized cases: 12
- Scored real cases: 12
- Excluded cases: 0
- Evidence status distribution: `active=12`
- Dataset sha256: `08cf975fc5daffb19c0e0791bc60244f5e6f2b9a2394661147b7f36032a7f4e2`

The smoke run uses real public GitHub PR data and does not use mock, synthetic, or fallback data. It is still a small smoke benchmark, not a statistically significant benchmark.

## Still Missing

- Real `stale` evidence cases.
- Real `unknown` evidence cases.
- Real `conflicting` evidence cases.
- Manual adjudication of hard evidence labels.
- Broader repository and language coverage.
- A production-ready LLM advisor.
- Merge-blocking policy calibration.

## Next Hard Real Cases Plan

1. Curate PRs where a previous compatibility claim was later superseded by a newer PR, release note, or test change. Label these as candidate `stale` cases only when the newer evidence is provenance-linked.
2. Curate PRs that touch historically risky files but have incomplete issue/PR discussion. Label these as candidate `unknown` and exclude low-confidence records from scored metrics.
3. Curate PRs with supporting and contradicting evidence across issues, reviews, commits, or docs. Label these as candidate `conflicting` only when both sides have stable URLs.
4. Add manual review notes for every hard case before it enters scored metrics.
5. Keep the minimum real scored threshold and fail-fast behavior; do not fill missing hard cases with synthetic examples.
