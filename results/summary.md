# Results Summary

Source: generated from `reports_claim/claim_stage_results.csv`, `reports_claim/context_group_summary.csv`, and `reports_claim/evidence_status_summary.csv`.

Model: `deepseek-v4-pro`

Benchmark: Stage3 Controlled Claim Benchmark, 20 tasks x 8 context groups = 160 runs.

## Overall

| Metric | Result |
| --- | ---: |
| Total records | 160 |
| Run status `ok` | 152 |
| `apply_failed` | 8 |
| Test success | 152/160 |
| Decision present | 160/160 |
| Correct evidence-aware decision | 73/160 |
| Safe success | 68/160 |
| Destructive change | 2/160 |
| Pollution | 15/160 |

## Context Group Summary

| Context group | Runs | Safe success | Destructive change | Pollution | Avg plan quality |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no_context` | 20 | 5 | 1 | 0 | 2.05 |
| `result_history` | 20 | 4 | 0 | 0 | 2.30 |
| `plain_claim` | 20 | 6 | 0 | 0 | 1.90 |
| `claim_with_evidence` | 20 | 13 | 0 | 0 | 2.25 |
| `tracegate_routed` | 20 | 14 | 0 | 0 | 2.15 |
| `tracegate_verify_first` | 20 | 9 | 1 | 0 | 3.00 |
| `misleading_same_scope` | 20 | 5 | 0 | 15 | 2.35 |
| `full_unfiltered_claims` | 20 | 12 | 0 | 0 | 2.25 |

## Evidence Status Summary

| Evidence status | Runs | Correct decision | Test success | Destructive change | Pollution | Avg plan quality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `active` | 40 | 32 | 39 | 1 | 1 | 2.275 |
| `stale` | 40 | 17 | 36 | 0 | 5 | 2.250 |
| `unknown` | 40 | 20 | 38 | 0 | 4 | 2.250 |
| `conflicting` | 40 | 4 | 39 | 1 | 5 | 2.350 |

## Reading Notes

- `tracegate_routed` has the strongest safe-success result: 14/20.
- `misleading_same_scope` creates 15/20 pollution cases, showing why same-domain historical context can be risky.
- `conflicting` is the hardest evidence status: 4/40 correct decisions.
- High test success does not imply context safety: tests passed in 152/160 runs, but safe success was 68/160.
