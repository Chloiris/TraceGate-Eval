# TraceGate v0.2-alpha Release Notes

TraceGate v0.2-alpha introduces a hard real-data mini benchmark layer on top of the existing active real-data smoke cases.

## What Changed

- Added `datasets/real_min/labels/manual_labels.accepted.jsonl` with `5` human-accepted Codex semantic audit labels.
- Promoted accepted hard labels into `datasets/real_min/cases.jsonl`.
- Added strict promotion rules so raw `codex_evidence_audit_semantic_v2` labels cannot enter scored metrics directly.
- Added report fields for `active_count`, `stale_count`, `unknown_count`, `conflicting_count`, `promoted_cases`, `scored_cases`, `label_source_distribution`, `hard_benchmark_ready`, and limitations.
- Generated updated `runs/latest/report.md` and `runs/latest/report.json`.

## Current Dataset

- active_count: `12`
- stale_count: `2`
- unknown_count: `1`
- conflicting_count: `2`
- promoted_cases: `5`
- scored_cases: `17`
- label_source_distribution: `{'heuristic_verified': 12, 'human_accepted_codex_audit': 5}`
- hard_benchmark_ready: `false`

## Guardrails

- No mock data.
- No synthetic data.
- No fallback data.
- `reject` and `needs_more_evidence` labels are excluded from scored metrics.
- `codex_evidence_audit_semantic_v2` cannot be promoted directly.
- Only `human_accepted_codex_audit` or `manual_verified` hard labels can enter scored metrics.

## Limitations

- v0.2-alpha is still a small hard real-data mini benchmark and is not statistically significant.
- Hard labels come from Codex evidence audit plus human final acceptance.
- The benchmark does not replace human code review.
- GitHub Action advisory remains warning-only.
- `hard_benchmark_ready=false` until the accepted hard-label mix reaches at least `unknown>=3`, `conflicting>=2`, `stale>=1`, and `scored_cases>=14`.
