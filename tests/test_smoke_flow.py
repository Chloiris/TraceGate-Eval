from __future__ import annotations

import shutil

from tracegate.config import BASELINE_DIRNAME, RUN_REPO_DIRNAME
from tracegate.contexts.context_group_builder import build_claim_context
from tracegate.dataio import read_json, write_json
from tracegate.dataset.claim_benchmark_generator import (
    default_claim_contexts,
    default_claim_tasks,
    generate_claim_sample_repo,
)
from tracegate.runners.claim_runner import build_claim_prompt, run_claim_experiment
from tracegate.runners.deepseek_runner import DeepSeekConfig


def test_claimbench_minimal_dry_run_smoke(tmp_path) -> None:
    sample_repo = generate_claim_sample_repo(tmp_path / "legacy-shop-spring-claim")
    task = next(item for item in default_claim_tasks() if item["id"] == "C3T03")
    context_text, context_ids, context_tokens = build_claim_context(
        task,
        "tracegate_verify_first",
        default_claim_contexts(),
    )

    run_dir = (
        tmp_path
        / "runs_claim"
        / "deepseek-v4-pro"
        / "c3t03_auth_legacytoken_unknown"
        / "tracegate_verify_first"
    )
    run_dir.mkdir(parents=True)
    shutil.copytree(sample_repo, run_dir / BASELINE_DIRNAME)
    shutil.copytree(sample_repo, run_dir / RUN_REPO_DIRNAME)
    (run_dir / "prompt.md").write_text(
        build_claim_prompt(task, "tracegate_verify_first", context_text),
        encoding="utf-8",
    )
    write_json(
        run_dir / "metadata.json",
        {
            "stage": 3,
            "model": {"id": "deepseek-v4-pro"},
            "task": task,
            "context_group": "tracegate_verify_first",
            "prompt": {
                "context_tokens": context_tokens,
                "selected_context_ids": context_ids,
            },
            "repo_dir": RUN_REPO_DIRNAME,
            "baseline_dir": BASELINE_DIRNAME,
        },
    )

    result = run_claim_experiment(
        run_dir,
        config=DeepSeekConfig(model="deepseek-v4-pro", temperature=0.0),
        dry_run=True,
    )

    request_path = run_dir / "results" / "deepseek_request.json"
    request = read_json(request_path)
    assert result["status"] == "dry_run"
    assert request["model"] == "deepseek-v4-pro"
    assert "===TRACEGATE_DECISION===" in request["messages"][1]["content"]
    assert "legacyToken" in request["messages"][1]["content"]
    assert (run_dir / "results" / "claimbench_run.json").exists()
    assert context_ids
    assert context_tokens > 0
