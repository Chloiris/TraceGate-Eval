# Data Provenance

## Source

TraceGate P0 real data uses the GitHub REST API:

- Pull Request list endpoint: `GET /repos/{owner}/{repo}/pulls`
- Pull Request files endpoint: `GET /repos/{owner}/{repo}/pulls/{pull_number}/files`

Public data can be fetched without a token, but authenticated requests may have higher rate limits.

## Raw Artifacts

Raw responses are written to:

```text
datasets/real_min/raw/github_prs.jsonl
datasets/real_min/raw/raw_manifest.json
```

These files are ignored by Git. They are not committed because they are raw cache artifacts.

## Normalized Artifacts

The small normalized public dataset is committed:

```text
datasets/real_min/cases.jsonl
datasets/real_min/manifest.json
```

Every scored case includes:

- `repo` and `repo_url`
- `pr_url`
- `commit_sha` when available
- changed file list
- claim source URL
- at least one evidence item
- provenance hash for the evidence item
- `is_real=true`
- `is_synthetic=false`
- `excluded_from_real_metrics=false`

## Hashes

The current normalized dataset sha256 is:

```text
08cf975fc5daffb19c0e0791bc60244f5e6f2b9a2394661147b7f36032a7f4e2
```

`python -m tracegate guardrails audit --run runs/latest --strict` compares this hash against both dataset and run manifests.
