# Hard Benchmark Status

TraceGate v0.2-alpha now includes a hard real-data mini benchmark layer built from Codex evidence audit labels that received human final acceptance.

## Summary

- benchmark: `TraceGate v0.2-alpha hard real-data mini benchmark`
- active_count: `12`
- stale_count: `2`
- unknown_count: `1`
- conflicting_count: `2`
- promoted_cases: `5`
- scored_cases: `17`
- label_source_distribution: `{'heuristic_verified': 12, 'human_accepted_codex_audit': 5}`
- hard_benchmark_ready: `false`
- used_real_data: `true`
- used_synthetic_data: `false`
- used_mock_model: `false`
- used_fallback_data: `false`

## Acceptance Source

- Hard labels come from Codex evidence audit plus human final acceptance.
- `datasets/real_min/labels/manual_labels.accepted.jsonl` contains only `action=promote` rows.
- Accepted hard labels use `label_source=human_accepted_codex_audit`.
- Raw `codex_evidence_audit_semantic_v2` labels are not promoted directly.
- `reject` and `needs_more_evidence` rows are not included in scored metrics.

## Readiness

`hard_benchmark_ready` is `false` because the current v0.2-alpha distribution does not meet the minimum hard benchmark mix:

- required unknown: `3`; current unknown: `1`
- required conflicting: `2`; current conflicting: `2`
- required stale: `1`; current stale: `2`
- required scored_cases: `14`; current scored_cases: `17`

## Limitations

- This is a small v0.2-alpha hard real-data mini benchmark, not a statistically significant benchmark.
- It does not replace human code review.
- GitHub Action advisory remains warning-only.
- More accepted `unknown` cases are needed before `hard_benchmark_ready` can become true.
