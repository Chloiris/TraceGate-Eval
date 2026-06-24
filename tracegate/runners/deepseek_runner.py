from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tracegate.config import RUN_REPO_DIRNAME, RUNS_DIR
from tracegate.dataio import write_json
from tracegate.runners.command_runner import find_run_dirs, run_maven_tests


REPO_SNAPSHOT_EXTENSIONS = {
    ".java",
    ".xml",
    ".properties",
    ".md",
    ".yaml",
    ".yml",
}

REPO_SNAPSHOT_IGNORES = {
    "target",
    ".git",
    ".idea",
    ".mvn",
    "results",
}


@dataclass
class DeepSeekConfig:
    model: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    base_url: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
    api_key_envs: tuple[str, ...] = ("DEEPSEEK_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    thinking: str = os.environ.get("DEEPSEEK_THINKING", "disabled")
    reasoning_effort: str | None = os.environ.get("DEEPSEEK_REASONING_EFFORT")
    max_tokens: int = int(os.environ.get("DEEPSEEK_MAX_TOKENS", "12000"))
    temperature: float = float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.1"))

    def api_key(self) -> str | None:
        for name in self.api_key_envs:
            value = os.environ.get(name)
            if value:
                return value
            user_value = _read_windows_user_env(name)
            if user_value:
                return user_value
        return None


def _read_windows_user_env(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value) if value else None
    except Exception:
        return None


def _extract_diff(text: str) -> str | None:
    match = re.search(r"```(?:diff|patch)\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip() + "\n"
    bare = text.strip()
    if bare.startswith("diff --git") or bare.startswith("--- "):
        return bare + "\n"
    return None


def _iter_snapshot_files(repo_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repo_dir)
        if any(part in REPO_SNAPSHOT_IGNORES for part in relative.parts):
            continue
        if path.suffix.lower() not in REPO_SNAPSHOT_EXTENSIONS:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(repo_dir).as_posix())


def build_repo_snapshot(repo_dir: Path, max_file_chars: int = 30000) -> str:
    sections: list[str] = []
    for path in _iter_snapshot_files(repo_dir):
        relative = path.relative_to(repo_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if len(content) > max_file_chars:
            content = content[:max_file_chars] + "\n... <truncated> ...\n"
        sections.append(f"### File: {relative}\n```text\n{content.rstrip()}\n```")
    return "\n\n".join(sections)


def build_coding_prompt(run_dir: Path) -> str:
    repo_dir = run_dir / RUN_REPO_DIRNAME
    prompt = (run_dir / "prompt.md").read_text(encoding="utf-8")
    snapshot = build_repo_snapshot(repo_dir)
    return (
        f"{prompt.rstrip()}\n\n"
        "## Repository Snapshot\n\n"
        "Below is the current experiment repository source snapshot from `repo/`. Generate a patch based on these files.\n\n"
        f"{snapshot}\n\n"
        "## Patch Output Contract\n\n"
        "Return ONLY a unified diff patch that can be applied from the repository root with `git apply --whitespace=fix`.\n"
        "Do not wrap the patch in Markdown fences.\n"
        "Use paths relative to the repository root, preferably `diff --git a/path b/path` format.\n"
        "Do not modify files under `src/test/` unless the task explicitly requires test changes.\n"
    )


def create_patch_request(run_dir: Path, config: DeepSeekConfig | None = None) -> dict[str, Any]:
    config = config or DeepSeekConfig()
    prompt = build_coding_prompt(run_dir)
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an automated Java/Spring Boot coding agent. "
                    "You must return only a unified diff patch. "
                    "Do not include explanations, Markdown fences, secrets, or API keys."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": config.max_tokens,
        "thinking": {"type": config.thinking},
        "stream": False,
    }
    if config.thinking == "enabled":
        if config.reasoning_effort:
            payload["reasoning_effort"] = config.reasoning_effort
    else:
        payload["temperature"] = config.temperature
    return payload


def request_deepseek_patch(
    run_dir: Path,
    dry_run: bool = True,
    config: DeepSeekConfig | None = None,
    api_timeout_seconds: int = 180,
) -> dict[str, Any]:
    config = config or DeepSeekConfig()
    run_dir = run_dir.resolve()
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    payload = create_patch_request(run_dir, config)

    if dry_run:
        write_json(results_dir / "deepseek_request.json", payload)
        return {"status": "dry_run", "request_path": str(results_dir / "deepseek_request.json")}

    api_key = config.api_key()
    if not api_key:
        raise RuntimeError("Missing DeepSeek API key. Set DEEPSEEK_API_KEY or ANTHROPIC_AUTH_TOKEN.")

    request = urllib.request.Request(
        config.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=api_timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        (results_dir / "deepseek_error.json").write_text(body, encoding="utf-8")
        raise RuntimeError(f"DeepSeek API HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek API network error: {exc}") from exc
    duration = time.time() - started

    response_data = json.loads(body)
    write_json(results_dir / "deepseek_response.json", response_data)
    content = response_data["choices"][0]["message"]["content"]
    (results_dir / "model_response.md").write_text(content, encoding="utf-8")
    patch = _extract_diff(content)
    if patch:
        (results_dir / "model.patch").write_text(patch, encoding="utf-8")
    result = {
        "status": "ok",
        "model": response_data.get("model"),
        "requested_model": config.model,
        "thinking": config.thinking,
        "reasoning_effort": config.reasoning_effort,
        "duration_seconds": round(duration, 3),
        "response_path": str(results_dir / "deepseek_response.json"),
        "patch_extracted": bool(patch),
        "usage": response_data.get("usage", {}),
        "finish_reason": response_data.get("choices", [{}])[0].get("finish_reason"),
    }
    write_json(results_dir / "deepseek_request_result.json", result)
    return result


def apply_model_patch(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    repo_dir = run_dir / RUN_REPO_DIRNAME
    results_dir = run_dir / "results"
    patch_path = results_dir / "model.patch"
    apply_log_path = results_dir / "patch_apply.log"

    if not patch_path.exists():
        result = {"status": "no_patch", "success": False, "log_path": str(apply_log_path)}
        apply_log_path.write_text("No model.patch was extracted.\n", encoding="utf-8")
        write_json(results_dir / "patch_apply.json", result)
        return result

    attempts = [
        ["git", "apply", "--whitespace=fix", str(patch_path)],
        ["git", "apply", "--recount", "--whitespace=fix", str(patch_path)],
    ]
    logs: list[str] = []
    completed: subprocess.CompletedProcess[str] | None = None
    for command in attempts:
        completed = subprocess.run(
            command,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        logs.append(
            "$ " + " ".join(command) + "\n" + completed.stdout + "\n" + completed.stderr
        )
        if completed.returncode == 0:
            break
    assert completed is not None
    apply_log_path.write_text("\n\n".join(logs), encoding="utf-8", errors="replace")
    result = {
        "status": "ok" if completed.returncode == 0 else "apply_failed",
        "success": completed.returncode == 0,
        "returncode": completed.returncode,
        "log_path": str(apply_log_path),
    }
    write_json(results_dir / "patch_apply.json", result)
    return result


def retry_existing_patch_run(run_dir: Path, test_timeout_seconds: int = 180) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    results_dir = run_dir / "results"
    existing = results_dir / "deepseek_run.json"
    if not existing.exists():
        return {"status": "missing_deepseek_run", "run_dir": str(run_dir)}

    patch_result = apply_model_patch(run_dir)
    if not patch_result.get("success"):
        test_result = _write_synthetic_test_failure(run_dir, "Model patch failed to apply after retry.")
        final = {
            "status": "apply_failed",
            "run_dir": str(run_dir),
            "patch_apply": patch_result,
            "test": test_result,
        }
        write_json(results_dir / "deepseek_run.json", final)
        return final

    test_result = run_maven_tests(run_dir, timeout_seconds=test_timeout_seconds)
    final = {
        "status": "ok" if test_result.get("success") else "test_failed",
        "run_dir": str(run_dir),
        "patch_apply": patch_result,
        "test": test_result,
        "retry_existing_patch": True,
    }
    write_json(results_dir / "deepseek_run.json", final)
    return final


def retry_apply_failed_patches(root: Path = RUNS_DIR, test_timeout_seconds: int = 180) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for run_dir in find_run_dirs(root):
        run_result_path = run_dir / "results" / "deepseek_run.json"
        if not run_result_path.exists():
            continue
        try:
            current = json.loads(run_result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if current.get("status") != "apply_failed":
            continue
        result = retry_existing_patch_run(run_dir, test_timeout_seconds=test_timeout_seconds)
        results.append(result)
        print(f"{result.get('status')} {run_dir}")
    return results


def _write_synthetic_test_failure(run_dir: Path, reason: str) -> dict[str, Any]:
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / "test.log"
    log_path.write_text(reason + "\n", encoding="utf-8")
    result = {
        "command": "not run",
        "returncode": 125,
        "success": False,
        "duration_seconds": 0,
        "log_path": str(log_path),
        "junit": {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "failed_tests": [],
            "report_files": [],
        },
        "skip_reason": reason,
    }
    write_json(results_dir / "test_result.json", result)
    return result


def run_deepseek_experiment(
    run_dir: Path,
    config: DeepSeekConfig | None = None,
    api_timeout_seconds: int = 180,
    test_timeout_seconds: int = 180,
    dry_run: bool = False,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    config = config or DeepSeekConfig()

    request_result = request_deepseek_patch(
        run_dir=run_dir,
        dry_run=dry_run,
        config=config,
        api_timeout_seconds=api_timeout_seconds,
    )
    if dry_run:
        final = {
            "status": "dry_run",
            "run_dir": str(run_dir),
            "request": request_result,
            "duration_seconds": round(time.time() - started, 3),
        }
        write_json(results_dir / "deepseek_run.json", final)
        return final

    if not request_result.get("patch_extracted"):
        test_result = _write_synthetic_test_failure(run_dir, "DeepSeek response did not contain an applicable patch.")
        final = {
            "status": "no_patch",
            "run_dir": str(run_dir),
            "request": request_result,
            "test": test_result,
            "duration_seconds": round(time.time() - started, 3),
        }
        write_json(results_dir / "deepseek_run.json", final)
        return final

    apply_result = apply_model_patch(run_dir)
    if not apply_result.get("success"):
        test_result = _write_synthetic_test_failure(run_dir, "Model patch failed to apply.")
        final = {
            "status": "apply_failed",
            "run_dir": str(run_dir),
            "request": request_result,
            "patch_apply": apply_result,
            "test": test_result,
            "duration_seconds": round(time.time() - started, 3),
        }
        write_json(results_dir / "deepseek_run.json", final)
        return final

    test_result = run_maven_tests(run_dir, timeout_seconds=test_timeout_seconds)
    final = {
        "status": "ok" if test_result.get("success") else "test_failed",
        "run_dir": str(run_dir),
        "request": request_result,
        "patch_apply": apply_result,
        "test": test_result,
        "duration_seconds": round(time.time() - started, 3),
    }
    write_json(results_dir / "deepseek_run.json", final)
    return final


def run_deepseek_for_many(
    root: Path = RUNS_DIR,
    config: DeepSeekConfig | None = None,
    all_runs: bool = False,
    limit: int | None = None,
    skip_existing: bool = True,
    api_timeout_seconds: int = 180,
    test_timeout_seconds: int = 180,
    dry_run: bool = False,
    workers: int = 1,
) -> list[dict[str, Any]]:
    run_dirs = find_run_dirs(root) if all_runs else find_run_dirs(root)
    if limit is not None:
        run_dirs = run_dirs[:limit]

    results: list[dict[str, Any]] = []
    pending: list[Path] = []
    for run_dir in run_dirs:
        if skip_existing and (run_dir / "results" / "deepseek_run.json").exists():
            result = {"status": "skipped_existing", "run_dir": str(run_dir)}
            results.append(result)
            print(f"{result['status']} {run_dir}")
        else:
            pending.append(run_dir)

    def run_one(run_dir: Path) -> dict[str, Any]:
        return run_deepseek_experiment(
            run_dir=run_dir,
            config=config,
            api_timeout_seconds=api_timeout_seconds,
            test_timeout_seconds=test_timeout_seconds,
            dry_run=dry_run,
        )

    if workers <= 1:
        for run_dir in pending:
            result = run_one(run_dir)
            results.append(result)
            print(f"{result.get('status')} {run_dir}")
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(run_one, run_dir): run_dir for run_dir in pending}
            for future in as_completed(futures):
                run_dir = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"status": "error", "run_dir": str(run_dir), "error": str(exc)}
                    results_dir = run_dir / "results"
                    results_dir.mkdir(parents=True, exist_ok=True)
                    write_json(results_dir / "deepseek_run.json", result)
                results.append(result)
                print(f"{result.get('status')} {run_dir}")
    return results
