# Windows To Mac Handoff Plan

Date: 2026-07-01
Branch: `chore/win11-to-m5-handoff`

This document records the current TraceGate repository state for continuing
development on an Apple Silicon M5 Mac.

## Current Project Structure

The repository currently contains:

- `tracegate/`: Python package for dataset generation, context building,
  runners, metrics, oracles, reports, and the local Web/API prototype.
- `tracegate/web/`: FastAPI dashboard/API prototype backed by checked-in CSV
  summaries and task definitions.
- `experiments/`: YAML task, context, claim, oracle, and model specifications.
- `sample_repos/`: controlled Java/Spring Boot legacy-shop sample repositories.
- `reports/`, `reports_stage2/`, `reports_claim/`: checked-in report artifacts.
- `results/`: GitHub-facing Stage3 summaries and figures.
- `examples/`: small readable input/output examples extracted from ClaimBench.
- `scripts/`: thin Python entrypoints plus local handoff validation scripts.
- `tests/`: pytest coverage for the Web/API prototype and a ClaimBench dry-run
  smoke flow.
- `docs/`: design, metrics, API, audit, and handoff documentation.

There is no checked-in `datasets/` directory, `setup.cfg`, `package.json`, or
`.github/` workflow directory in the current repository.

## Current Completed Pieces

- Stage3 Controlled Claim Benchmark / ClaimBench definitions are present.
- The package exposes a `tracegate` console script via `pyproject.toml`.
- The CLI can generate controlled sample repos, run directories, model request
  payloads, result collection, reports, and the local Web/API service.
- The Web/API prototype reads checked-in summaries and exposes dashboard/API
  endpoints. It does not run model calls or generate patches.
- Checked-in Stage3 summary artifacts exist under `reports_claim/` and
  `results/`.
- The current public Stage3 result is a controlled synthetic legacy-shop
  benchmark, not a real Pull Request dataset.

## Commands Known To Run On Windows

Previously verified in this workspace using `.venv\Scripts\python.exe`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tracegate --help
.\.venv\Scripts\python.exe -m tracegate run-claimbench --model deepseek-v4-pro --limit 1 --dry-run --workers 1
```

This handoff branch also adds:

```powershell
.\.venv\Scripts\python.exe -m compileall .
.\.venv\Scripts\pytest.exe -q
powershell -ExecutionPolicy Bypass -File scripts/dev_check.ps1
```

## Commands Expected To Run On macOS

After creating and activating a Mac virtual environment:

```bash
python -m compileall .
pytest -q
bash scripts/dev_check.sh
python -m tracegate --help
python -m tracegate run-claimbench --model deepseek-v4-pro --limit 1 --dry-run --workers 1
```

The real model run still requires a real API key and should not fallback to demo
or mock data when a real-data source fails.

## Windows-Only Or Potentially Windows-Biased Areas

- Existing checked-in report rows include Windows-style backslashes in some
  `run_dir` values. This branch updates future collectors to write repo-relative
  POSIX paths, but it does not regenerate all historical report artifacts.
- `tracegate.runners.deepseek_runner._read_windows_user_env()` reads Windows user
  environment variables via `winreg`, but it is guarded by `os.name == "nt"` and
  returns `None` on macOS.
- There is no GitHub Actions workflow yet, so cross-platform CI still needs to be
  designed on the Mac development pass.
- The current README includes both Windows and macOS setup commands, but most
  benchmark-running examples still assume the user has activated the correct
  Python environment.

## Files That Should Not Be Committed

Do not commit or migrate:

- `.venv/`
- `venv/`
- `env/`
- `node_modules/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.m2/`
- `runs/`
- `runs_stage2/`
- `runs_claim/`
- `archives/`
- `datasets/real_min/raw/`
- `datasets/real_min/cache/`
- `.env`
- `.env.*` except `.env.example`
- raw datasets, local caches, large zip/parquet/jsonl files, or real tokens

Private untracked local notes were inspected as working-tree material and should
not be staged automatically.

## Mac Development Work Left

- Real data discovery and source selection.
- `real_min` dataset shape and manifest/provenance rules.
- Claim/evidence/status schema hardening for real Pull Request data.
- Deterministic Pull Request advisory behavior.
- A real CLI path for a non-demo run.
- Report generation for real-data runs.
- Guardrail audit for fake fallback, mock, and synthetic leakage.
- GitHub Action advisory skeleton and CI strategy.

## Work Done In This Windows Handoff

- Created/switch to the handoff branch.
- Added `.editorconfig`.
- Tightened `.gitattributes` and `.gitignore` for cross-platform handoff.
- Added `scripts/dev_check.sh` and `scripts/dev_check.ps1`.
- Updated future collectors to write repo-relative POSIX `run_dir` values.
- Updated README handoff scope and Mac setup guidance.
- Added precheck, cross-platform, fallback-risk, validation, and Mac handoff
  documentation.

## Work Explicitly Not Done

- No real-data pipeline was implemented.
- No complete AI-generated Pull Request risk advisor was implemented.
- No full TraceGate EvalOps engine was implemented.
- No GitHub Action advisory core behavior was implemented.
- No dashboard expansion was implemented.
- No large refactor was performed.
- No real dataset was fetched.

## Next Mac Entry Point

Start with:

```bash
git checkout chore/win11-to-m5-handoff
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
bash scripts/dev_check.sh
```

Then read:

- `docs/MACOS_M5_HANDOFF.md`
- `docs/CROSS_PLATFORM_AUDIT.md`
- `docs/FALLBACK_RISK_HANDOFF.md`
- `docs/WIN_TO_MAC_OPEN_QUESTIONS.md`
