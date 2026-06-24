from __future__ import annotations

import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Any

from tracegate.config import MAVEN_REPO_DIR, RUN_REPO_DIRNAME, RUNS_DIR
from tracegate.dataio import write_json
from tracegate.metrics.junit_parser import parse_surefire_reports


def find_run_dirs(root: Path = RUNS_DIR) -> list[Path]:
    root = root.resolve()
    if root.name == RUN_REPO_DIRNAME and (root / "pom.xml").exists():
        return [root.parent]
    if (root / RUN_REPO_DIRNAME / "pom.xml").exists():
        return [root]
    return sorted(path.parent.parent for path in root.rglob(f"{RUN_REPO_DIRNAME}/pom.xml"))


def _maven_command(repo_dir: Path) -> list[str]:
    local_wrapper = repo_dir / ("mvnw.cmd" if _is_windows() else "mvnw")
    if local_wrapper.exists():
        return [str(local_wrapper), "test"]
    executable = shutil.which("mvn") or shutil.which("mvn.cmd")
    if executable:
        return [executable, "test"]
    return ["mvn", "test"]


def _is_windows() -> bool:
    return os.name == "nt"


def run_maven_tests(run_dir: Path, timeout_seconds: int = 180) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    repo_dir = run_dir / RUN_REPO_DIRNAME
    if not repo_dir.exists():
        raise FileNotFoundError(f"Run repo not found: {repo_dir}")

    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / "test.log"
    started = time.time()
    MAVEN_REPO_DIR.mkdir(parents=True, exist_ok=True)
    command = [*_maven_command(repo_dir)[:-1], f"-Dmaven.repo.local={MAVEN_REPO_DIR}", "test"]

    try:
        completed = subprocess.run(
            command,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        returncode = completed.returncode
        output = completed.stdout + "\n" + completed.stderr
    except FileNotFoundError:
        returncode = 127
        output = "mvn executable was not found. Install Maven or add it to PATH.\n"
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        output = (exc.stdout or "") + "\n" + (exc.stderr or "") + f"\nTimed out after {timeout_seconds}s.\n"

    duration = time.time() - started
    log_path.write_text(output, encoding="utf-8", errors="replace")
    junit_summary = parse_surefire_reports(repo_dir)
    result = {
        "command": " ".join(command),
        "returncode": returncode,
        "success": returncode == 0 and not junit_summary.get("failures") and not junit_summary.get("errors"),
        "duration_seconds": round(duration, 3),
        "log_path": str(log_path),
        "junit": junit_summary,
    }
    write_json(results_dir / "test_result.json", result)
    return result


def run_tests_for_many(run_dirs: list[Path], timeout_seconds: int = 180) -> list[dict[str, Any]]:
    return [run_maven_tests(run_dir, timeout_seconds=timeout_seconds) for run_dir in run_dirs]
