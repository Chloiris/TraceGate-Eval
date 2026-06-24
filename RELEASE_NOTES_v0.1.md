# TraceGate Eval v0.1 Controlled Benchmark Release Notes

## What Was Completed

- Rewrote the root `README.md` for GitHub readers and interview review.
- Added focused documentation under `docs/`.
- Added two minimal examples extracted from real `deepseek-v4-pro` Stage3 runs.
- Created GitHub-facing result summaries under `results/`.
- Added `scripts/plot_results.py` and generated the expected figure outputs under `results/figures/`.
- Added `.env.example`, expanded `.gitignore`, added `LICENSE`, and updated `requirements.txt`.
- Performed a security cleanup pass for local absolute paths and secret-like strings.

## Files Added or Organized

`README.md`

- Project positioning, Stage3 design, result summary, run commands, limitations, roadmap, and resume-ready description.

`docs/`

- `project_intro.md`: concise project overview.
- `stage3_design.md`: Stage3 benchmark matrix, context groups, and output protocol.
- `metrics.md`: execution, semantic, evidence, and risk metrics.
- `limitations_and_roadmap.md`: current constraints and planned next steps.

`examples/`

- `active_preserve_tracegate_routed.md`: active evidence with a correct `preserve` decision.
- `unknown_verify_first_tracegate_verify_first.md`: unknown evidence with a correct `verify_first` decision.

`results/`

- `summary.md`: overall Stage3 result summary.
- `context_group_summary.csv`: copied from the real Stage3 summary.
- `evidence_status_summary.csv`: copied from the real Stage3 summary.
- `figures/`: generated PNG charts.

`scripts/`

- `plot_results.py`: matplotlib-only chart generation from `results/*.csv`.

## Reproduce or Regenerate Reports

Install:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

Generate benchmark:

```bash
python -m tracegate create-claimbench
python -m tracegate create-claim-runs
```

Run model experiments:

```bash
# Set DEEPSEEK_API_KEY in your shell or secret manager before running.
python -m tracegate run-claimbench --model deepseek-v4-pro --sample all --workers 4 --skip-existing
```

Collect and report:

```bash
python -m tracegate collect-claim-results
python -m tracegate report-claimbench
python scripts/plot_results.py
```

## Current Limits

- v0.1 uses a controlled synthetic benchmark, not downloaded real external datasets.
- The public summary includes one complete `deepseek-v4-pro` Stage3 run.
- Oracles are intentionally task-specific and manually constructed.
- `conflicting` evidence remains the weakest and most important scenario to strengthen.
- The local workspace has an invalid `.git` directory, so `git status` could not be used during validation.

## Next Steps

- Add multi-model Stage3 comparison.
- Connect real data adapters for issue, session, failed-patch, and rollback sources.
- Strengthen conflict-detection tasks and scoring.
- Add case browsers for pollution, destructive changes, and over-conservative decisions.
- Publish a lean GitHub artifact that keeps raw model run outputs out of the default repository history.

## Resume Bullets

- Built TraceGate Eval, a controlled benchmark for AI coding-agent context safety and historical-claim validity.
- Designed a 160-run Stage3 benchmark across 5 modules, 4 evidence statuses, and 8 context groups.
- Implemented structured `PATCH + TRACEGATE_DECISION` evaluation to separate passing tests from evidence-aware safe success.
- Added metrics and oracles for `safe_success`, `pollution`, `destructive_change`, and verification-plan quality.
- Ran and summarized a complete `deepseek-v4-pro` experiment showing routed evidence improves safe success while misleading context increases pollution.
