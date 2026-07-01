# macOS M5 Setup

## Verified Local State

- local_arch: `arm64`
- project_python_arch: `arm64`
- project_python_version: `3.12.13`
- Homebrew: `/opt/homebrew/bin/brew`
- Docker: not available on PATH in this environment
- GitHub CLI: not available on PATH in this environment

## Setup

```bash
git clone https://github.com/Chloiris/TraceGate-Eval.git
cd TraceGate-Eval
git fetch origin
git checkout feature/tracegate-pr-advisory-real-data-mac
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

If `/usr/bin/python3` is Python 3.9, install Homebrew Python 3.12 and run:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
```

## Validate

```bash
python -m compileall .
pytest -q
python -m tracegate --help
python -m tracegate guardrails scan --strict
```
