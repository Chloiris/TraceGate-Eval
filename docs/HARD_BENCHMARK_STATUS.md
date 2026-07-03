# Hard Benchmark Status

TraceGate v0.2-alpha now includes a hard real-data mini benchmark layer built from Codex evidence audit labels that received human final acceptance.

## Summary

- benchmark: `TraceGate v0.2-alpha hard real-data mini benchmark`
- active_count: `12`
- stale_count: `2`
- unknown_count: `3`
- conflicting_count: `2`
- promoted_cases: `7`
- scored_cases: `19`
- label_source_distribution: `{'heuristic_verified': 12, 'human_accepted_codex_audit': 7}`
- hard_benchmark_ready: `true`
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

`hard_benchmark_ready` is `true` because the current v0.2-alpha distribution meets the minimum hard benchmark mix:

- required unknown: `3`; current unknown: `3`
- required conflicting: `2`; current conflicting: `2`
- required stale: `1`; current stale: `2`
- required scored_cases: `14`; current scored_cases: `19`

## Limitations

- This is a small v0.2-alpha hard real-data mini benchmark, not a statistically significant benchmark.
- It does not replace human code review.
- GitHub Action advisory remains warning-only.
- More accepted hard cases are still needed before using the benchmark for broad model comparison.
