# Data Card: real_min

Generated on: 2026-07-01

## Dataset

- Path: `datasets/real_min/cases.jsonl`
- Manifest: `datasets/real_min/manifest.json`
- Source dataset: `github_api`, `github_api_hard_semantic_v2`
- Source URL: public GitHub REST API Pull Request endpoints, with each scored
  case linked to a concrete `https://github.com/.../pull/...` URL.
- Dataset sha256: `bab6d5096b04ec0020c9bc1103d169c0fa712f78b62bb4138509c8aab462f57c`

## Counts

- Raw active smoke records inspected: 12
- Normalized cases: 19
- Scored real cases: 19
- Excluded cases: 0
- Evidence status distribution: `active=12`, `stale=2`, `unknown=3`, `conflicting=2`
- Expected decision distribution in baseline run: `preserve=12`,
  `verify_first=5`, `detect_conflict=2`
- Label source distribution: `heuristic_verified=12`, `human_accepted_codex_audit=7`

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
- `https://github.com/psf/requests/pull/7424`
- `https://github.com/psf/requests/pull/6265`
- `https://github.com/psf/requests/pull/7538`
- `https://github.com/psf/requests/pull/6965`
- `https://github.com/pytest-dev/pytest/pull/11844`
- `https://github.com/psf/requests/pull/7555`
- `https://github.com/psf/requests/pull/7545`

## Labeling

The 12 active smoke labels are `heuristic_verified`, not manually adjudicated
ground truth. The 7 hard labels are `human_accepted_codex_audit` records
promoted only after focused review of public GitHub evidence.

## Limitations

This is a minimal v0.2-alpha real-data dataset. It now meets the hard mini
benchmark readiness floor, but it remains small, does not provide statistical
significance, and does not prove advisor accuracy.
