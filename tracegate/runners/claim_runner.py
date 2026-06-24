from __future__ import annotations

import json
import re
import shutil
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from tracegate.config import (
    BASELINE_DIRNAME,
    CLAIM_CONTEXT_GROUPS,
    RUN_REPO_DIRNAME,
    RUNS_CLAIM_DIR,
    SAMPLE_REPO_CLAIM_DIR,
)
from tracegate.contexts.context_group_builder import build_claim_context
from tracegate.dataio import read_json, write_json
from tracegate.dataset.claim_benchmark_generator import load_claim_contexts, load_claim_models, load_claim_tasks
from tracegate.oracle.claim_oracle import normalize_decision
from tracegate.runners.command_runner import find_run_dirs, run_maven_tests
from tracegate.runners.deepseek_runner import DeepSeekConfig, build_repo_snapshot
from tracegate.runners.patch_applier import apply_patch_if_present


PATCH_MARKER = "===PATCH==="
DECISION_MARKER = "===TRACEGATE_DECISION==="
DECISION_KEYS = {"decision", "evidence_used", "risks", "verification_plan"}


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def model_id(model: str) -> str:
    return slug(model).replace("_", "-")


def claim_task_slug(task: dict[str, Any]) -> str:
    return f"{task['id'].lower()}_{task['module']}_{slug(task['pitfall'])}_{task['evidence_status']}"


def _safe_rmtree(path: Path, root: Path) -> None:
    target = path.resolve()
    allowed = root.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError(f"Refusing to remove path outside claim runs root: {target}")
    shutil.rmtree(target)


def _copy_repo(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("target", ".git", ".idea", ".DS_Store"))


def build_claim_prompt(task: dict[str, Any], context_group: str, context_text: str) -> str:
    target_files = "\n".join(f"- {item}" for item in task.get("target_files", []))
    return f"""You are maintaining a TraceGate ClaimBench Spring Boot legacy project.

## Current Task

- Task ID: {task['id']}
- Module: {task['module']}
- Pitfall under review: {task['pitfall']}

{task['instruction']}

## Claim Context Group

{context_group}

{context_text}

## Target Files

{target_files}

## Output Protocol

Return exactly these two sections:

===PATCH===
<unified diff patch, or leave this section empty when the safest action is to avoid code changes>

===TRACEGATE_DECISION===
decision: preserve | optimize | verify_first | conflict_detected
evidence_used:
risks:
verification_plan:

Use `preserve` when the compatibility claim is currently supported by evidence.
Use `optimize` when current evidence shows the compatibility claim no longer holds.
Use `verify_first` when evidence is insufficient for a destructive compatibility change.
Use `conflict_detected` when evidence disagrees and the change needs human confirmation or a feature flag.
Do not modify files under `src/test/`.
"""


def create_claim_runs(
    sample_repo: Path = SAMPLE_REPO_CLAIM_DIR,
    runs_dir: Path = RUNS_CLAIM_DIR,
    force: bool = False,
) -> list[Path]:
    if not sample_repo.exists():
        raise FileNotFoundError(f"ClaimBench sample repo does not exist: {sample_repo}")
    tasks = load_claim_tasks()
    contexts = load_claim_contexts()
    models = load_claim_models()
    created: list[Path] = []
    runs_dir.mkdir(parents=True, exist_ok=True)
    for model in models:
        model_dir = runs_dir / model_id(model["id"])
        for task in tasks:
            for context_group in CLAIM_CONTEXT_GROUPS:
                run_dir = model_dir / claim_task_slug(task) / context_group
                if run_dir.exists():
                    if not force:
                        created.append(run_dir)
                        continue
                    _safe_rmtree(run_dir, runs_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                _copy_repo(sample_repo, run_dir / BASELINE_DIRNAME)
                _copy_repo(sample_repo, run_dir / RUN_REPO_DIRNAME)
                context_text, context_ids, context_tokens = build_claim_context(task, context_group, contexts)
                prompt = build_claim_prompt(task, context_group, context_text)
                (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
                write_json(
                    run_dir / "metadata.json",
                    {
                        "stage": 3,
                        "model": model,
                        "task": task,
                        "context_group": context_group,
                        "prompt": {
                            "context_tokens": context_tokens,
                            "selected_context_ids": context_ids,
                        },
                        "repo_dir": RUN_REPO_DIRNAME,
                        "baseline_dir": BASELINE_DIRNAME,
                    },
                )
                created.append(run_dir)
    return created


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:diff|patch|text)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped


def _patch_is_present(patch_text: str) -> bool:
    text = _normalize_patch_text(patch_text)
    if not text:
        return False
    lowered = text.lower()
    if lowered in {"none", "n/a", "no patch", "no changes"}:
        return False
    return text.startswith("diff --git") or text.startswith("--- ")


def _normalize_patch_text(patch_text: str) -> str:
    text = _strip_fence(patch_text).strip()
    diff_index = text.find("diff --git")
    if diff_index >= 0:
        return text[diff_index:].strip()
    match = re.search(r"(?m)^---\s+", text)
    if match:
        return text[match.start() :].strip()
    return text


def _parse_decision(decision_text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "decision": "",
        "evidence_used": "",
        "risks": "",
        "verification_plan": "",
        "decision_present": False,
        "raw": decision_text.strip(),
    }
    current_key: str | None = None
    buckets: dict[str, list[str]] = {key: [] for key in DECISION_KEYS}
    for raw_line in decision_text.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*)$", line)
        key = match.group(1).lower() if match else ""
        if match and key in DECISION_KEYS:
            current_key = key
            buckets[key].append(match.group(2).strip())
        elif current_key:
            buckets[current_key].append(line.strip())
    parsed["decision"] = normalize_decision(" ".join(buckets["decision"]).strip())
    parsed["evidence_used"] = "\n".join(item for item in buckets["evidence_used"] if item).strip()
    parsed["risks"] = "\n".join(item for item in buckets["risks"] if item).strip()
    parsed["verification_plan"] = "\n".join(item for item in buckets["verification_plan"] if item).strip()
    parsed["decision_present"] = bool(parsed["decision"])
    return parsed


def parse_claim_response(text: str) -> dict[str, Any]:
    if DECISION_MARKER in text:
        patch_part, decision_part = text.split(DECISION_MARKER, 1)
    else:
        patch_part, decision_part = text, ""
    if PATCH_MARKER in patch_part:
        patch_part = patch_part.split(PATCH_MARKER, 1)[1]
    patch_text = _normalize_patch_text(patch_part)
    patch_present = _patch_is_present(patch_text)
    decision = _parse_decision(decision_part)
    return {
        "patch_text": patch_text if patch_present else "",
        "patch_present": patch_present,
        "decision": decision,
        "decision_present": bool(decision.get("decision_present")),
    }


def build_claim_coding_prompt(run_dir: Path) -> str:
    repo_dir = run_dir / RUN_REPO_DIRNAME
    prompt = (run_dir / "prompt.md").read_text(encoding="utf-8")
    snapshot = build_repo_snapshot(repo_dir)
    return (
        f"{prompt.rstrip()}\n\n"
        "## Repository Snapshot\n\n"
        "Below is the current experiment repository source snapshot from `repo/`. Use these files to generate the PATCH section.\n\n"
        f"{snapshot}\n"
    )


def create_claim_request(run_dir: Path, config: DeepSeekConfig | None = None) -> dict[str, Any]:
    config = config or DeepSeekConfig()
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an automated Java/Spring Boot coding agent evaluating historical compatibility claims. "
                    "Return only the two requested sections: PATCH and TRACEGATE_DECISION. "
                    "Do not include secrets, API keys, or prose outside those sections."
                ),
            },
            {"role": "user", "content": build_claim_coding_prompt(run_dir)},
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


def request_deepseek_claim(
    run_dir: Path,
    dry_run: bool = True,
    config: DeepSeekConfig | None = None,
    api_timeout_seconds: int = 180,
) -> dict[str, Any]:
    config = config or DeepSeekConfig()
    run_dir = run_dir.resolve()
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    payload = create_claim_request(run_dir, config)
    if dry_run:
        write_json(results_dir / "deepseek_request.json", payload)
        return {"status": "dry_run", "request_path": str(results_dir / "deepseek_request.json")}

    api_key = config.api_key()
    if not api_key:
        raise RuntimeError("Missing DeepSeek API key. Set DEEPSEEK_API_KEY or ANTHROPIC_AUTH_TOKEN.")
    request = urllib.request.Request(
        config.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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
    parsed = parse_claim_response(content)
    if parsed["patch_present"]:
        (results_dir / "model.patch").write_text(parsed["patch_text"].strip() + "\n", encoding="utf-8")
    write_json(results_dir / "tracegate_decision.json", parsed["decision"])
    result = {
        "status": "ok",
        "model": response_data.get("model"),
        "requested_model": config.model,
        "thinking": config.thinking,
        "reasoning_effort": config.reasoning_effort,
        "duration_seconds": round(duration, 3),
        "response_path": str(results_dir / "deepseek_response.json"),
        "patch_present": bool(parsed["patch_present"]),
        "decision_present": bool(parsed["decision_present"]),
        "usage": response_data.get("usage", {}),
        "finish_reason": response_data.get("choices", [{}])[0].get("finish_reason"),
    }
    write_json(results_dir / "deepseek_request_result.json", result)
    return result


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
        "junit": {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "failed_tests": [], "report_files": []},
        "skip_reason": reason,
    }
    write_json(results_dir / "test_result.json", result)
    return result


def run_claim_experiment(
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
    request_result = request_deepseek_claim(
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
        write_json(results_dir / "claimbench_run.json", final)
        return final

    patch_result = apply_patch_if_present(run_dir, bool(request_result.get("patch_present")))
    if patch_result.get("status") == "apply_failed":
        test_result = _write_synthetic_test_failure(run_dir, "ClaimBench model patch failed to apply.")
        final = {
            "status": "apply_failed",
            "run_dir": str(run_dir),
            "request": request_result,
            "patch_apply": patch_result,
            "test": test_result,
            "duration_seconds": round(time.time() - started, 3),
        }
        write_json(results_dir / "claimbench_run.json", final)
        return final

    test_result = run_maven_tests(run_dir, timeout_seconds=test_timeout_seconds)
    final = {
        "status": "ok" if test_result.get("success") else "test_failed",
        "run_dir": str(run_dir),
        "request": request_result,
        "patch_apply": patch_result,
        "test": test_result,
        "duration_seconds": round(time.time() - started, 3),
    }
    write_json(results_dir / "claimbench_run.json", final)
    return final


def _claim_run_dirs(root: Path, sample: str, limit: int | None) -> list[Path]:
    run_dirs = find_run_dirs(root)
    if sample == "pilot":
        filtered: list[Path] = []
        for run_dir in run_dirs:
            metadata = read_json(run_dir / "metadata.json", default={}) or {}
            task = metadata.get("task", {})
            context_group = metadata.get("context_group")
            if task.get("module") in {"auth", "payment"} and context_group in {
                "tracegate_verify_first",
                "misleading_same_scope",
            }:
                filtered.append(run_dir)
        run_dirs = filtered
    if limit is not None:
        run_dirs = run_dirs[:limit]
    return run_dirs


def run_claimbench_for_many(
    root: Path,
    config: DeepSeekConfig,
    sample: str = "all",
    limit: int | None = None,
    skip_existing: bool = False,
    api_timeout_seconds: int = 180,
    test_timeout_seconds: int = 180,
    dry_run: bool = False,
    workers: int = 1,
) -> list[dict[str, Any]]:
    run_dirs = _claim_run_dirs(root, sample=sample, limit=limit)
    results: list[dict[str, Any]] = []
    pending: list[Path] = []
    for run_dir in run_dirs:
        if skip_existing and (run_dir / "results" / "claimbench_run.json").exists():
            result = {"status": "skipped_existing", "run_dir": str(run_dir)}
            results.append(result)
            print(f"{result['status']} {run_dir}")
        else:
            pending.append(run_dir)

    def run_one(item: Path) -> dict[str, Any]:
        return run_claim_experiment(
            item,
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
                    write_json(results_dir / "claimbench_run.json", result)
                results.append(result)
                print(f"{result.get('status')} {run_dir}")
    return results


def run_claimbench_model(
    model: str,
    runs_dir: Path = RUNS_CLAIM_DIR,
    thinking: str = "disabled",
    reasoning_effort: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 12000,
    workers: int = 4,
    sample: str = "all",
    limit: int | None = None,
    skip_existing: bool = False,
    api_timeout_seconds: int = 240,
    test_timeout_seconds: int = 300,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    config = DeepSeekConfig(
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return run_claimbench_for_many(
        root=runs_dir / model_id(model),
        config=config,
        sample=sample,
        limit=limit,
        skip_existing=skip_existing,
        api_timeout_seconds=api_timeout_seconds,
        test_timeout_seconds=test_timeout_seconds,
        dry_run=dry_run,
        workers=workers,
    )
