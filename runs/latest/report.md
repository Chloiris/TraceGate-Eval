# TraceGate Real-Data PR Advisory Report

- benchmark: `TraceGate v0.2-alpha hard real-data mini benchmark`
- run_id: `tracegate-real-20260702T145237Z`
- real_evaluation_succeeded: `True`
- used_real_data: `True`
- used_synthetic_data: `False`
- used_mock_model: `False`
- used_fallback_data: `False`
- dataset: `datasets/real_min/cases.jsonl`
- dataset_sha256: `097957c8aaabda56cc9fc29c4de433c7261ec2aea1adb7953df9d7abecbfb5d4`

This is a v0.2-alpha hard real-data mini benchmark. It remains a small non-statistical benchmark.

- Hard labels come from Codex evidence audit plus human final acceptance.
- This benchmark does not replace human code review.
- GitHub Action advisory remains warning-only.

## Metrics

- num_cases_total: `17`
- num_cases_scored: `17`
- num_cases_excluded: `0`
- active_count: `12`
- stale_count: `2`
- unknown_count: `1`
- conflicting_count: `2`
- promoted_cases: `5`
- pollution_flag_rate: `0.17647058823529413`
- needs_manual_review_rate: `0.0`
- provenance_completeness_rate: `1.0`
- unsafe_allow_rate: `0.0`
- verify_first_rate_on_unknown_or_conflicting: `1.0`
- scored_cases: `17`
- excluded_cases_count: `0`
- manual_review_cases: `0`
- manual_review_queue_cases: `40`
- active_only: `False`
- hard_benchmark_ready: `False`

## Limitations

- v0.2-alpha is a small hard real-data mini benchmark and is not statistically significant.
- Hard labels come from Codex evidence audit plus human final acceptance, and do not replace human code review.
- GitHub Action advisory remains warning-only and should not be treated as a merge blocker.
- hard_benchmark_ready remains false until the minimum distribution is met: unknown>=3, conflicting>=2, stale>=1, scored_cases>=14.

## Distributions

- status_distribution: `{'active': 12, 'conflicting': 2, 'stale': 2, 'unknown': 1}`
- scored_status_distribution: `{'active': 12, 'conflicting': 2, 'stale': 2, 'unknown': 1}`
- decision_distribution: `{'detect_conflict': 2, 'preserve': 12, 'verify_first': 3}`
- risk_level_distribution: `{'high': 2, 'low': 8, 'medium': 7}`
- label_source_distribution: `{'heuristic_verified': 12, 'human_accepted_codex_audit': 5}`

## Run Type

- real-data smoke run: `false`
- hard real-data mini benchmark: `true`
- manual review queue cases: `40`
- excluded candidates: `0`


## Advisories

### github_api:psf__requests:pull:7551

- evidence_status: `active`
- decision: `preserve`
- risk_level: `medium`
- risk_score: `55`
- requires_human_review: `False`
- summary: preserve for psf/requests; touched files: .pre-commit-config.yaml
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14663

- evidence_status: `active`
- decision: `preserve`
- risk_level: `medium`
- risk_score: `55`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: .pre-commit-config.yaml
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14658

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: testing/plugins_integration/requirements.txt
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14659

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: .github/workflows/deploy.yml, .github/workflows/doc-check-links.yml, .github/workflows/prepare-release-pr.yml
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14655

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: doc/en/backwards-compatibility.rst
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14652

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: src/_pytest/assertion/_typing.py, src/_pytest/assertion/truncate.py, testing/test_assertion.py
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14657

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: doc/en/reference/plugin_list.rst
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14656

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: doc/en/reference/plugin_list.rst
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14639

- evidence_status: `active`
- decision: `preserve`
- risk_level: `medium`
- risk_score: `55`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: AUTHORS, changelog/14637.bugfix.rst, src/_pytest/assertion/compare_text.py
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14653

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: doc/en/how-to/capture-warnings.rst
- pollution_flags: `[]`

### github_api:pytest-dev__pytest:pull:14646

- evidence_status: `active`
- decision: `preserve`
- risk_level: `medium`
- risk_score: `55`
- requires_human_review: `False`
- summary: preserve for pytest-dev/pytest; touched files: changelog/14638.bugfix.rst, src/_pytest/config/findpaths.py, testing/test_config.py
- pollution_flags: `[]`

### github_api:pydantic__pydantic:pull:13373

- evidence_status: `active`
- decision: `preserve`
- risk_level: `low`
- risk_score: `30`
- requires_human_review: `False`
- summary: preserve for pydantic/pydantic; touched files: pydantic/_internal/_generate_schema.py
- pollution_flags: `[]`

### hard_candidate:psf__requests:pull:7424

- evidence_status: `conflicting`
- decision: `detect_conflict`
- risk_level: `high`
- risk_score: `80`
- requires_human_review: `True`
- summary: detect_conflict for psf/requests; touched files: no files listed
- pollution_flags: `['contradicting_evidence_present']`

### hard_candidate:psf__requests:pull:6265

- evidence_status: `stale`
- decision: `verify_first`
- risk_level: `medium`
- risk_score: `50`
- requires_human_review: `True`
- summary: verify_first for psf/requests; touched files: no files listed
- pollution_flags: `['certainty_from_stale_evidence']`

### hard_candidate:psf__requests:pull:7538

- evidence_status: `conflicting`
- decision: `detect_conflict`
- risk_level: `high`
- risk_score: `80`
- requires_human_review: `True`
- summary: detect_conflict for psf/requests; touched files: no files listed
- pollution_flags: `['contradicting_evidence_present']`

### hard_candidate:psf__requests:pull:6965

- evidence_status: `unknown`
- decision: `verify_first`
- risk_level: `medium`
- risk_score: `60`
- requires_human_review: `True`
- summary: verify_first for psf/requests; touched files: no files listed
- pollution_flags: `[]`

### hard_candidate:pytest-dev__pytest:pull:11844

- evidence_status: `stale`
- decision: `verify_first`
- risk_level: `medium`
- risk_score: `50`
- requires_human_review: `True`
- summary: verify_first for pytest-dev/pytest; touched files: no files listed
- pollution_flags: `[]`
