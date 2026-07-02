# Mac Local Precheck

Generated on: 2026-07-01

## Summary

| Check | Result |
| --- | --- |
| local_arch | `arm64` |
| python_arch | `arm64` |
| python_version | `3.9.6 (default, Apr 17 2026, 18:15:52) [Clang 21.0.0 (clang-2100.1.1.101)]` |
| python_path | `/usr/bin/python3` |
| project_python_arch | `arm64` |
| project_python_version | `3.12.13 (main, Mar 3 2026, 12:39:30) [Clang 21.0.0 (clang-2100.0.123.102)]` |
| project_python_path | `/opt/homebrew/opt/python@3.12/bin/python3.12` |
| pip_path | not found on global PATH |
| brew_path | `/opt/homebrew/bin/brew` |
| git_version | `git version 2.50.1 (Apple Git-155)` |
| gh_available | false (`gh` not found) |
| docker_available | false (`docker` not found) |
| current_working_directory | `<local TraceGate-Eval checkout>` |
| current_branch | `feature/tracegate-pr-advisory-real-data-mac` |
| remote_url | `https://github.com/Chloiris/TraceGate-Eval.git` |
| started_on_handoff_branch | yes, cloned and verified `chore/win11-to-m5-handoff` |
| handoff_branch_current | yes, `git pull --ff-only origin chore/win11-to-m5-handoff` reported already up to date |

## Raw Command Notes

Initial workspace directory was not a Git repository. The handoff branch was cloned from `https://github.com/Chloiris/TraceGate-Eval.git` into `TraceGate-Eval/`.

The cloned repository was initially on:

```text
## chore/win11-to-m5-handoff...origin/chore/win11-to-m5-handoff
```

Then the required development branch was created:

```text
feature/tracegate-pr-advisory-real-data-mac
```

## Remote

```text
origin  https://github.com/Chloiris/TraceGate-Eval.git (fetch)
origin  https://github.com/Chloiris/TraceGate-Eval.git (push)
```

## Recent Commits

```text
a56b599 chore: prepare Win11 to M5 Mac handoff
787ea31 Improve repo onboarding and smoke tests
c4deb1b Add web API prototype
5f67e2e Prepare v0.1 controlled benchmark
```

Current HEAD:

```text
a56b59975aa438815fe31c98627d67e3f382759f
```

## Environment Interpretation

- The local machine and global Python are both `arm64`, so this is not blocked by Rosetta/x86_64 Python.
- The global `/usr/bin/python3` is Python 3.9.6, while the project declares `requires-python = ">=3.11"`. Homebrew `python@3.12` was installed and used to create `.venv`.
- Homebrew is installed in the expected Apple Silicon path: `/opt/homebrew/bin/brew`.
- `gh` and `docker` are not currently available on PATH. The P0 work can continue without Docker. GitHub operations will use `git` directly.
- Global `pip` is not on PATH. The project should use a fresh `.venv` and `python -m pip`.

## Inheritance Validation

Using `.venv` created with `/opt/homebrew/bin/python3.12`:

```text
python -m compileall .                 PASS
pytest -q                              PASS: 6 passed, 1 warning
bash scripts/dev_check.sh              PASS
python -m tracegate --help             PASS
```

Dependency notes:

- `python -m pip install -U pip` found `pip 26.1.2` already installed in the venv.
- `pip install -r requirements.txt` required network access and succeeded after explicit approval.
- `pip install -e ".[dev]"` required network access for build dependencies and succeeded after explicit approval.
