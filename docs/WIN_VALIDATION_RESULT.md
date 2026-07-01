# Windows Validation Result

Date: 2026-07-01
Branch: `chore/win11-to-m5-handoff`

Validation used the repository virtual environment:
`.venv\Scripts\python.exe`.

## Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m compileall .` | success | Exit code 0. The command is intentionally recorded as requested, but it is noisy because `.` walks ignored local artifacts such as `.git`, `.m2`, `archives/`, and `.venv/`. |
| `.\.venv\Scripts\python.exe -m pytest -q` | success | `6 passed, 1 warning in 0.92s`. Warning: upstream Starlette/httpx deprecation from FastAPI test client. |
| `bash scripts/dev_check.sh` | not run | `bash` was not on PATH. `C:\Program Files\Git\bin\bash.exe` and `C:\Program Files\Git\usr\bin\bash.exe` were not present. |
| `$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; powershell -ExecutionPolicy Bypass -File scripts/dev_check.ps1` | success | Exit code 0. Runs compileall, pytest, and CLI help with the venv first on PATH. |
| `.\.venv\Scripts\python.exe -m tracegate --help` | success | Exit code 0. CLI help lists dataset, run, report, ClaimBench, and web commands. |

## Does This Affect GitHub Handoff?

No blocker for GitHub handoff was found.

The only incomplete validation item is Bash execution on Windows because Bash is
not installed. This does not invalidate the script for macOS; it means the M5 Mac
must run:

```bash
bash scripts/dev_check.sh
```

after creating and activating its own virtual environment.

## Mac Revalidation Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
python -m compileall .
pytest -q
bash scripts/dev_check.sh
python -m tracegate --help
```

## Validation Status

- Python compile check: passed
- Pytest: passed
- Windows PowerShell dev check: passed
- Bash dev check on Windows: not available
- Overall: partial, because the requested Bash script must be re-run on macOS
