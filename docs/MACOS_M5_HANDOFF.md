# macOS M5 Handoff

Date: 2026-07-01
Branch: `chore/win11-to-m5-handoff`

## What The Windows Pass Completed

- Created the Windows-to-M5 handoff branch.
- Added cross-platform text/config hygiene through `.gitattributes`,
  `.editorconfig`, and `.gitignore`.
- Added `scripts/dev_check.sh` for macOS/Linux and `scripts/dev_check.ps1` for
  Windows.
- Updated future metrics collectors to avoid local Windows path formatting in
  `run_dir` fields.
- Updated README to mark this as a handoff branch and not a completed real-data
  MVP.
- Added handoff/audit docs for Mac continuation.

## What The Windows Pass Did Not Do

- Did not implement a real-data pipeline.
- Did not implement a complete AI-generated Pull Request risk advisor.
- Did not implement a complete TraceGate EvalOps engine.
- Did not implement GitHub Action advisory core behavior.
- Did not fetch real datasets.
- Did not treat demo, mock, fixture, or synthetic data as real evaluation data.

## Clone Or Pull On M5 Mac

```bash
git clone https://github.com/Chloiris/TraceGate-Eval.git
cd TraceGate-Eval
git fetch origin
git checkout chore/win11-to-m5-handoff
```

If the repository already exists locally:

```bash
cd TraceGate-Eval
git fetch origin
git checkout chore/win11-to-m5-handoff
git pull --ff-only
```

## Check Apple Silicon Architecture

```bash
uname -m
python3 -c "import platform; print(platform.machine())"
which brew
```

Expected:

```text
uname -m -> arm64
Python -> arm64
Homebrew -> /opt/homebrew/bin/brew
```

## Create A Fresh Mac Environment

Do not copy the Windows `.venv`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

## Install Dependencies

The current repository has both `requirements.txt` and `pyproject.toml`.

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

For plots:

```bash
python -m pip install -e ".[plots]"
```

## Run Basic Checks

```bash
python -m compileall .
pytest -q
bash scripts/dev_check.sh
python -m tracegate --help
```

Optional no-network ClaimBench dry run:

```bash
python -m tracegate run-claimbench --model deepseek-v4-pro --limit 1 --dry-run --workers 1
```

## Mac Development Targets

- Real data discovery.
- `real_min` dataset.
- Data manifest and provenance.
- Claim/evidence/status schema for real Pull Request data.
- Deterministic Pull Request advisory behavior.
- Real-run CLI path.
- Real-data report path.
- Guardrail audit for fake fallback, mock, demo, and synthetic leakage.
- GitHub Action advisory skeleton.

## Hard Reminders

- Do not migrate `.venv/` from Windows.
- Do not migrate `node_modules/` from Windows.
- Do not migrate `runs/`, raw data, or caches from Windows.
- Do not fallback from real-data failure to demo/mock/synthetic data.
- Do not treat PR as Public Relations. In this project, PR means Pull Request.
- Do not commit real API keys or tokens.
