# Mac Execution Plan

Generated on: 2026-07-01

## 1. Inherited From Windows

- Base branch `chore/win11-to-m5-handoff` at commit `a56b59975aa438815fe31c98627d67e3f382759f`.
- Existing `python -m tracegate` entrypoint backed by `tracegate/__main__.py` and `tracegate/cli.py`.
- Stage3 controlled ClaimBench over the synthetic legacy-shop sample repository.
- Existing metrics/report/oracle modules for controlled benchmark runs.
- Handoff docs covering cross-platform cleanup, validation, and fallback risks.
- `.gitignore` already excludes `.venv/`, generated runs, raw real-data cache directories, and common local artifacts.
- `scripts/dev_check.sh` and `scripts/dev_check.ps1`.

## 2. Still Not Complete

- No real Pull Request dataset is fetched, normalized, validated, or scored.
- No real-data manifest/provenance contract exists yet.
- No deterministic Pull Request advisory CLI exists yet.
- No guardrail audit exists for real/demo/mock/synthetic separation.
- No GitHub Action advisory workflow or base CI exists yet.
- Existing reports are controlled synthetic benchmark artifacts and must not be described as real evaluation.

## 3. P0 Goal

Build a minimal, reproducible, real-data-driven PR advisory MVP that:

- Uses real public GitHub Pull Request/issue/commit/review data.
- Enforces no mock, no fallback, no synthetic contamination in real runs.
- Produces at least 8 scored real cases if data is available.
- Fails fast and documents `DATA_BLOCKED` or `DATA_INSUFFICIENT` if the real-data threshold is not met.
- Keeps claims, evidence, evidence status, expected decisions, advisory outputs, reports, and guardrails deterministic and auditable.

## 4. Data Source Discovery Strategy

Prefer sources that can be sampled with Python standard-library HTTP tooling and stable URLs:

- GitHub public API for selected public repositories and Pull Requests.
- SWE-bench Lite/Verified metadata only if a small, reproducible subset can be read without large dependencies.
- AIDev/agent-authored PR datasets only if publicly accessible, small enough for P0, and clearly licensed.

Discovery will document candidate URLs, fields, token requirements, download method, sample size, cache behavior, and why sources were selected or rejected.

## 5. Real-Data Minimal Sample Strategy

- Target 12 normalized cases from public GitHub API data.
- Minimum threshold: 8 scored real cases.
- Each scored case must have stable `case_id`, repo provenance, PR or issue URL when available, at least one evidence item, `is_real=true`, `is_synthetic=false`, `excluded_from_real_metrics=false`, `label_source != unknown`, and `label_confidence >= 0.7`.
- Cases with insufficient provenance or low confidence become `needs_manual_review` and are excluded from scored metrics.
- No tests fixture, demo, sample repo, or controlled ClaimBench artifact can enter real metrics.

## 6. Core Module Design

Add a small real-data/advisory surface alongside the existing controlled benchmark:

- `tracegate/core/models.py`: dataclasses and enum validation for claims, evidence, eval cases, advisory decisions, run records, and reports.
- `tracegate/core/policy.py`: deterministic mapping from evidence status and support/contradiction into decisions and risk.
- `tracegate/core/advisory.py`: rule-based advisory generation.
- `tracegate/core/metrics.py`: smoke benchmark metrics that avoid accuracy claims without ground truth.
- `tracegate/core/pollution.py`: unsupported/stale/conflicting/unclear evidence pollution detection.
- `tracegate/core/serialization.py`: JSON/JSONL helpers with fail-fast validation.

## 7. CLI Design

Extend `tracegate/cli.py` while preserving existing commands:

```text
python -m tracegate data discover
python -m tracegate data fetch --source auto --limit 12 --real-only --no-fallback
python -m tracegate data normalize --input datasets/real_min/raw --output datasets/real_min/cases.jsonl
python -m tracegate data validate --dataset datasets/real_min/cases.jsonl --strict --min-cases 8
python -m tracegate data manifest --dataset datasets/real_min/cases.jsonl
python -m tracegate run --dataset datasets/real_min/cases.jsonl --advisor rule --real-only --no-mock --no-fallback
python -m tracegate report --run runs/latest --format markdown,json
python -m tracegate guardrails audit --run runs/latest --strict
python -m tracegate guardrails scan --strict
```

Real-only commands will fail if required flags are missing.

## 8. Guardrail Audit Design

- Validate dataset and run manifest reality fields.
- Enforce `num_cases_scored >= 8` for strict real runs.
- Compare dataset sha256 against run manifest.
- Scan source/docs/tests for risky fallback/mock/demo/synthetic/fake keywords.
- Classify each keyword occurrence as allowed fixture, allowed documentation, allowed demo excluded, or dangerous runtime path.
- Strict mode fails on dangerous runtime path.
- Write `docs/FALLBACK_AUDIT.md` and maintain `docs/REALITY_GUARD.md`.

## 9. GitHub Action Advisory Design

Add `.github/workflows/tracegate-advisory.yml`:

- Runs on Pull Request.
- Installs Python and package dependencies.
- Reads PR diff from GitHub context.
- Reads `tracegate.yml` or `.tracegate/claims.yml`.
- Produces a deterministic advisory summary to `$GITHUB_STEP_SUMMARY`.
- Defaults to warning-only behavior.
- Never substitutes a mock dataset when PR context is missing.

## 10. Test Plan

- Unit tests for enum/model validation, serialization, decision policy, pollution flags, and report generation.
- Data validation tests for missing provenance, synthetic exclusion, manual-review exclusion, low-confidence exclusion, and min-case strict failure.
- CLI tests for help, data validate, run with fixture data, and report generation.
- Guardrail tests for fake fallback detection and empty dataset failure.
- Cross-platform tests for `pathlib`/POSIX relative paths and absence of hardcoded Windows or local Mac paths in runtime logic.

## 11. Acceptance Commands

```bash
python -m compileall .
pytest -q
python -m tracegate --help
python -m tracegate guardrails scan --strict
python -m tracegate data discover
python -m tracegate data fetch --source auto --limit 12 --real-only --no-fallback
python -m tracegate data validate --dataset datasets/real_min/cases.jsonl --strict --min-cases 8
python -m tracegate run --dataset datasets/real_min/cases.jsonl --advisor rule --real-only --no-mock --no-fallback
python -m tracegate report --run runs/latest --format markdown,json
python -m tracegate guardrails audit --run runs/latest --strict
bash scripts/dev_check.sh
```

## 12. Risks And Mitigations

- GitHub API rate limits or network failure: fail fast, write `DATA_BLOCKED`, and do not create fake data.
- Fewer than 8 scored real cases: write `DATA_INSUFFICIENT`, set `real_evaluation_succeeded=false`, and commit infrastructure only.
- Evidence status heuristic uncertainty: mark low-confidence cases as excluded and avoid accuracy claims.
- Existing Web/API fallback wording: keep it documented as presentation-only and prevent reuse in real runs.
- Python version mismatch: use Homebrew arm64 Python 3.12 for `.venv`.
- `gh` and Docker unavailable: use `git` for push and keep Docker status documented as unavailable.
