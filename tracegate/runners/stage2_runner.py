from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from tracegate.config import (
    BASELINE_DIRNAME,
    RUN_REPO_DIRNAME,
    RUNS_STAGE2_DIR,
    SAMPLE_REPO_V2_DIR,
    STAGE2_CONTEXT_GROUPS,
)
from tracegate.contexts.context_router import build_stage2_context
from tracegate.dataio import write_json
from tracegate.dataset.active_stale_case_generator import load_stage2_contexts, load_stage2_models, load_stage2_tasks
from tracegate.runners.deepseek_runner import DeepSeekConfig, run_deepseek_for_many


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def task_slug(task: dict[str, Any]) -> str:
    return f"{task['id'].lower()}_{task['module']}_{slug(task['pitfall'])}_{task['lifecycle']}"


def model_id(model: str) -> str:
    return slug(model).replace("_", "-")


def _safe_rmtree(path: Path, root: Path) -> None:
    target = path.resolve()
    allowed = root.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError(f"Refusing to remove path outside stage2 runs root: {target}")
    shutil.rmtree(target)


def _copy_repo(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("target", ".git", ".idea", ".DS_Store"))


def build_stage2_prompt(task: dict[str, Any], context_group: str, context_text: str) -> str:
    target_files = "\n".join(f"- {item}" for item in task.get("target_files", []))
    return f"""You are maintaining a TraceGate Stage2 Spring Boot legacy project.

## Current Task

- Task ID: {task['id']}
- Module: {task['module']}
- Lifecycle: {task['lifecycle']}
- Ground truth family: {task['ground_truth']}
- Pitfall: {task['pitfall']}

{task['instruction']}

## Context Group

{context_group}

{context_text}

## Target Files

{target_files}

## Requirements

1. Modify source code in `repo/` and keep the project compiling.
2. Do not modify files under `src/test/`.
3. Return a unified diff patch that can be applied from the repository root.
4. The current business fact in the task has priority over stale historical records.
5. If the historical workaround is still active, preserve it. If the historical reason is stale, optimize it safely.
"""


def create_stage2_runs(
    sample_repo: Path = SAMPLE_REPO_V2_DIR,
    runs_dir: Path = RUNS_STAGE2_DIR,
    force: bool = False,
) -> list[Path]:
    if not sample_repo.exists():
        raise FileNotFoundError(f"Stage2 sample repo does not exist: {sample_repo}")
    tasks = load_stage2_tasks()
    contexts = load_stage2_contexts()
    models = load_stage2_models()
    created: list[Path] = []
    runs_dir.mkdir(parents=True, exist_ok=True)
    for model in models:
        model_dir = runs_dir / model_id(model["id"])
        for task in tasks:
            for context_group in STAGE2_CONTEXT_GROUPS:
                run_dir = model_dir / task_slug(task) / context_group
                if run_dir.exists():
                    if not force:
                        created.append(run_dir)
                        continue
                    _safe_rmtree(run_dir, runs_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                _copy_repo(sample_repo, run_dir / BASELINE_DIRNAME)
                _copy_repo(sample_repo, run_dir / RUN_REPO_DIRNAME)
                context_text, context_ids, context_tokens = build_stage2_context(task, context_group, contexts)
                prompt = build_stage2_prompt(task, context_group, context_text)
                (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
                write_json(
                    run_dir / "metadata.json",
                    {
                        "stage": 2,
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


def run_stage2_model(
    model: str,
    runs_dir: Path = RUNS_STAGE2_DIR,
    workers: int = 3,
    skip_existing: bool = False,
    api_timeout_seconds: int = 240,
    test_timeout_seconds: int = 300,
) -> list[dict[str, Any]]:
    root = runs_dir / model_id(model)
    config = DeepSeekConfig(
        model=model,
        thinking="disabled",
        reasoning_effort=None,
        temperature=0.0,
        max_tokens=12000,
    )
    return run_deepseek_for_many(
        root=root,
        config=config,
        all_runs=True,
        skip_existing=skip_existing,
        api_timeout_seconds=api_timeout_seconds,
        test_timeout_seconds=test_timeout_seconds,
        workers=workers,
    )
