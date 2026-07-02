# Publish Safety Checklist

Run this checklist before every GitHub push.

## Required Checks

```bash
git status --short --branch
git diff --stat
git diff --check
git diff --cached --check
rg -n "ghp_|github_pat_|GITHUB_TOKEN|sk-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|PRIVATE) KEY|password\\s*=|token\\s*=" .
```

Also inspect staged files explicitly:

```bash
git diff --cached --name-only
git diff --cached --stat
```

## Do Not Push

- API keys, GitHub tokens, cloud credentials, SSH/private keys, or `.env` secrets.
- Local absolute paths such as `/Users/...`, Windows user folders, or machine-specific temp paths.
- `.venv`, `node_modules`, raw caches, `runs/latest`, large generated artifacts, or private logs.
- Unreviewed raw API responses containing rate-limit bodies, tokens, or private metadata.

If any check is ambiguous, stop and inspect the exact staged diff before pushing.
