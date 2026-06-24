from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tracegate.config import (
    BASELINE_DIRNAME,
    CONTEXT_GROUPS,
    RUN_REPO_DIRNAME,
    RUNS_DIR,
    SAMPLE_REPO_DIR,
)
from tracegate.dataio import write_json
from tracegate.dataset.context_generator import load_context_items, load_historical_failures
from tracegate.dataset.task_generator import load_tasks, task_slug
from tracegate.prompts.prompt_builder import build_prompt


def _safe_rmtree(path: Path, root: Path) -> None:
    target = path.resolve()
    allowed_root = root.resolve()
    if target == allowed_root or allowed_root not in target.parents:
        raise ValueError(f"Refusing to remove path outside runs root: {target}")
    shutil.rmtree(target)


def _copy_repo(source: Path, destination: Path) -> None:
    ignore = shutil.ignore_patterns("target", ".git", ".idea", ".DS_Store")
    shutil.copytree(source, destination, ignore=ignore)


def _manual_guide(task: dict[str, Any], context_group: str) -> str:
    return (
        "# Manual Run\n\n"
        f"- Task: {task['id']} {task['title']}\n"
        f"- Context group: {context_group}\n\n"
        "Steps:\n\n"
        "1. Open `prompt.md`.\n"
        "2. Enter the `repo/` directory.\n"
        "3. Give the prompt to the AI coding agent.\n"
        "4. Let the agent modify only `repo/`.\n"
        "5. Run `python -m tracegate run-tests --run-dir .` from this run directory, or run it from the project root with this directory as `--run-dir`.\n"
        "6. Run `python -m tracegate collect-results` and `python -m tracegate report`.\n"
    )


def create_manual_runs(
    sample_repo: Path = SAMPLE_REPO_DIR,
    runs_dir: Path = RUNS_DIR,
    force: bool = False,
) -> list[Path]:
    if not sample_repo.exists():
        raise FileNotFoundError(
            f"Sample repo does not exist: {sample_repo}. Run `python -m tracegate create-dataset` first."
        )

    tasks = load_tasks()
    context_items = load_context_items()
    historical_failures = load_historical_failures()
    created: list[Path] = []

    runs_dir.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        task_dir = runs_dir / task_slug(task)
        for context_group in CONTEXT_GROUPS:
            run_dir = task_dir / context_group
            if run_dir.exists():
                if not force:
                    created.append(run_dir)
                    continue
                _safe_rmtree(run_dir, runs_dir)

            run_dir.mkdir(parents=True, exist_ok=True)
            _copy_repo(sample_repo, run_dir / BASELINE_DIRNAME)
            _copy_repo(sample_repo, run_dir / RUN_REPO_DIRNAME)

            prompt, prompt_meta = build_prompt(
                task=task,
                context_group=context_group,
                context_items=context_items,
                historical_failures=historical_failures,
            )
            (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
            (run_dir / "MANUAL_RUN.md").write_text(_manual_guide(task, context_group), encoding="utf-8")
            write_json(
                run_dir / "metadata.json",
                {
                    "task": task,
                    "context_group": context_group,
                    "prompt": prompt_meta,
                    "repo_dir": RUN_REPO_DIRNAME,
                    "baseline_dir": BASELINE_DIRNAME,
                },
            )
            created.append(run_dir)

    return created

