# Hard Case Labeling Guide

TraceGate v0.2-alpha mines hard real-data candidates from public GitHub Pull Requests, issues, review comments, and commits. Mined candidates are not scored automatically.

## Candidate Flow

1. Run hard-case mining:

```bash
python -m tracegate data mine-hard --repos psf/requests,pytest-dev/pytest,pydantic/pydantic --limit 40 --real-only --no-fallback
```

2. Review candidates in:

```text
datasets/real_min/labels/manual_review_queue.jsonl
```

3. Write confirmed labels to:

```text
datasets/real_min/labels/manual_labels.jsonl
```

4. Promote only reviewed labels:

```bash
python -m tracegate data promote-labels --labels datasets/real_min/labels/manual_labels.jsonl --output datasets/real_min/cases.jsonl
```

## Label Rules

- `stale`: requires an older claim and newer provenance-linked evidence showing the claim may no longer apply.
- `unknown`: requires a concrete PR URL and an explicit insufficient-evidence rationale; one evidence item is allowed.
- `conflicting`: requires supporting and contradicting evidence from stable GitHub URLs.
- `needs_manual_review`: never enters scored metrics.

Every scored hard case must have `is_real=true`, `is_synthetic=false`, `excluded_from_real_metrics=false`, `label_source` of `heuristic_verified` or `manual_verified`, `label_confidence>=0.7`, and a non-empty `rationale`.

Do not promote a candidate to satisfy distribution targets. If evidence is weak, keep it in the queue or mark it `needs_manual_review`.
