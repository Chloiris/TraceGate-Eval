# Reality Guard

## Real Evaluation

A TraceGate real evaluation must satisfy all of the following:

- `--real-only`
- `--no-mock`
- `--no-fallback`
- strict dataset validation
- at least 8 scored real cases
- `used_real_data=true`
- `used_synthetic_data=false`
- `used_mock_model=false`
- `used_fallback_data=false`

## Demo, Mock, Synthetic, Fixture

- Tests may construct synthetic fixtures, but they must be excluded from real metrics.
- Existing controlled ClaimBench sample repos are synthetic benchmark material, not real PR data.
- The Web/API demo endpoint is presentation-only and must not be reused as real run evidence.

## Failure Behavior

If GitHub API fetch fails, parsing fails, provenance is incomplete, or fewer than 8 scored real cases are available, TraceGate fails fast. It does not create sample records, default summaries, or fallback reports.

## Reproduce The Guard

```bash
python -m tracegate guardrails scan --strict
python -m tracegate data validate --dataset datasets/real_min/cases.jsonl --strict --min-cases 8
python -m tracegate guardrails audit --run runs/latest --strict
```

## Current Limits

The current evidence labels are heuristic and the sample is small. Passing the guard means the run is real and provenance-linked; it does not mean the benchmark is statistically significant.
