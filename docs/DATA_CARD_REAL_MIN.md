# Data Card: real_min

Generated on: 2026-07-01

## Dataset

- Path: `datasets/real_min/cases.jsonl`
- Manifest: `datasets/real_min/manifest.json`
- Source dataset: `github_api`
- Source URL: `https://docs.github.com/en/rest/pulls/pulls`
- Dataset sha256: `08cf975fc5daffb19c0e0791bc60244f5e6f2b9a2394661147b7f36032a7f4e2`

## Counts

- Raw records inspected: 12
- Normalized cases: 12
- Scored real cases: 12
- Excluded cases: 0
- Evidence status distribution: `active=12`
- Expected decision distribution in baseline run: `preserve=12`

## Repositories

- `psf/requests`
- `pytest-dev/pytest`
- `pydantic/pydantic`

## Case Provenance

- `https://github.com/psf/requests/pull/7551`
- `https://github.com/pytest-dev/pytest/pull/14663`
- `https://github.com/pytest-dev/pytest/pull/14658`
- `https://github.com/pytest-dev/pytest/pull/14659`
- `https://github.com/pytest-dev/pytest/pull/14655`
- `https://github.com/pytest-dev/pytest/pull/14652`
- `https://github.com/pytest-dev/pytest/pull/14657`
- `https://github.com/pytest-dev/pytest/pull/14656`
- `https://github.com/pytest-dev/pytest/pull/14639`
- `https://github.com/pytest-dev/pytest/pull/14653`
- `https://github.com/pytest-dev/pytest/pull/14646`
- `https://github.com/pydantic/pydantic/pull/13373`

## Labeling

Labels are `heuristic_verified`, not manually adjudicated ground truth. A merged PR with changed-file provenance is treated as `active` evidence for a small smoke benchmark. This should be manually reviewed before any production governance use.

## Limitations

This is a minimal real-data smoke dataset. It does not cover all evidence statuses, does not provide statistical significance, and does not prove advisor accuracy.
