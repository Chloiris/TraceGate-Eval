# Runbook

## Setup On Apple Silicon Mac

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

If the system `python3` is older than 3.11, install an arm64 Homebrew Python and create the venv with that interpreter.

## Basic Checks

```bash
python -m compileall .
pytest -q
python -m tracegate --help
python -m tracegate guardrails scan --strict
```

## Real Data Flow

```bash
python -m tracegate data discover
python -m tracegate data fetch --source auto --limit 12 --real-only --no-fallback
python -m tracegate data validate --dataset datasets/real_min/cases.jsonl --strict --min-cases 8
python -m tracegate run --dataset datasets/real_min/cases.jsonl --advisor rule --real-only --no-mock --no-fallback
python -m tracegate report --run runs/latest --format markdown,json
python -m tracegate guardrails audit --run runs/latest --strict
```

## Failure Path

If fetch or validation fails, do not continue to a success report. Create or update `docs/DATA_BLOCKED.md` or `docs/DATA_INSUFFICIENT.md` with the command output and next manual fix.

## Before Pushing To GitHub

Always run the publish safety checklist before `git push`:

```bash
git status --short --branch
git diff --stat
git diff --check
git diff --cached --check
rg -n "ghp_|github_pat_|GITHUB_TOKEN|sk-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|PRIVATE) KEY|password\\s*=|token\\s*=" .
```

See [docs/PUBLISH_SAFETY_CHECKLIST.md](PUBLISH_SAFETY_CHECKLIST.md) for the full checklist, including local-path and generated-artifact review.
