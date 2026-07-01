# GitHub Action

TraceGate includes a minimal warning-only Pull Request advisory workflow at `.github/workflows/tracegate-advisory.yml`.

## Behavior

- Runs on Pull Request events.
- Reads changed files from the PR base/head SHAs.
- Reads repo-local claim configuration from `tracegate.yml`.
- Writes a Markdown advisory to the GitHub job summary.
- Does not use mock datasets.
- Does not block merges by default.

## Local Dry Run

```bash
git diff --name-only origin/main...HEAD > /tmp/tracegate_changed_files.txt
python scripts/github_action_advisory.py \
  --config tracegate.yml \
  --changed-files /tmp/tracegate_changed_files.txt \
  --output /tmp/tracegate_summary.md
```

If there is no PR context, run the local dry-run command above with an explicit changed-file list.
