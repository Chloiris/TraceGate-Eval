# Post-Merge Status

Generated on: 2026-07-02

## Main Currently Includes

- Stage3 Controlled Claim Benchmark / ClaimBench over the synthetic legacy-shop sample project.
- A minimal real-data Pull Request advisory smoke path on `main`.
- CLI commands for real-data discovery, fetch, normalize, validate, manifest, run, report, and guardrail audit.
- A deterministic rule-based PR advisory baseline.
- Reality guardrails that distinguish real, demo, mock, synthetic, and fixture data.
- GitHub Actions for Python CI and a warning-only TraceGate advisory skeleton.
- The `feature/hard-real-cases-mini-benchmark` branch adds hard-case mining commands and a manual review queue, without promoting unreviewed hard candidates into scored metrics.

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
- Dataset sha256: `84e9c0eff698689a807f675d9199953578d5f9c98c802cec13ccee7d8efecf18`

The smoke run uses real public GitHub PR data and does not use mock, synthetic, or fallback data. It is still a small smoke benchmark, not a statistically significant benchmark.

## Still Missing

- Real `stale` evidence cases.
- Real `unknown` evidence cases.
- Real `conflicting` evidence cases.
- Manual adjudication of hard evidence labels.
- Broader repository and language coverage.
- A production-ready LLM advisor.
- Merge-blocking policy calibration.

Hard candidates discovered by v0.2-alpha mining belong in `datasets/real_min/labels/manual_review_queue.jsonl` until they have concrete GitHub evidence, reviewer answers, and `label_confidence >= 0.7`.

## Next Hard Real Cases Plan

1. Curate PRs where a previous compatibility claim was later superseded by a newer PR, release note, or test change. Label these as candidate `stale` cases only when the newer evidence is provenance-linked.
2. Curate PRs that touch historically risky files but have incomplete issue/PR discussion. Label these as candidate `unknown` and exclude low-confidence records from scored metrics.
3. Curate PRs with supporting and contradicting evidence across issues, reviews, commits, or docs. Label these as candidate `conflicting` only when both sides have stable URLs.
4. Add manual review notes for every hard case before it enters scored metrics.
5. Keep the minimum real scored threshold and fail-fast behavior; do not fill missing hard cases with synthetic examples.

## v0.2-alpha Acceptance Gate

- Ideal target: `active>=8`, `unknown>=4`, `conflicting>=3`, `stale>=2`, and `scored_cases>=17`.
- Minimum target: `active>=8`, `unknown>=3`, `conflicting>=2`, `stale>=1`, and `scored_cases>=14`.
- If the minimum target is not met, TraceGate keeps the active-only smoke dataset, writes `docs/DATA_INSUFFICIENT.md`, and reports `hard_benchmark_ready=false`.
