from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from tracegate.config import (
    REPORTS_CLAIM_DIR,
    REPORTS_DIR,
    REPORTS_STAGE2_DIR,
    RUNS_CLAIM_DIR,
    RUNS_DIR,
    RUNS_STAGE2_DIR,
    SAMPLE_REPO_CLAIM_DIR,
    SAMPLE_REPO_DIR,
)
from tracegate.dataset.claim_benchmark_generator import generate_claim_sample_repo, write_claimbench_data
from tracegate.dataset.active_stale_case_generator import write_stage2_data
from tracegate.dataset.context_generator import write_default_context_files
from tracegate.dataset.legacy_shop_generator import generate_legacy_shop
from tracegate.dataset.legacy_shop_v2_generator import generate_legacy_shop_v2
from tracegate.dataset.task_generator import write_default_tasks
from tracegate.metrics.result_collector import collect_results
from tracegate.metrics.claim_collector import collect_claim_results
from tracegate.metrics.stage2_collector import collect_stage2_results
from tracegate.reports.claim_stage_report_builder import generate_claim_stage_reports
from tracegate.reports.report_builder import generate_reports
from tracegate.reports.stage2_report_builder import generate_stage2_reports
from tracegate.runners.command_runner import find_run_dirs, run_maven_tests
from tracegate.runners.deepseek_runner import DeepSeekConfig, retry_apply_failed_patches, run_deepseek_for_many
from tracegate.runners.claim_runner import create_claim_runs, run_claimbench_model
from tracegate.runners.manual_runner import create_manual_runs
from tracegate.runners.stage2_runner import create_stage2_runs, run_stage2_model


def create_dataset_command(force: bool = False) -> None:
    write_default_tasks(force=force)
    write_default_context_files(force=force)
    repo = generate_legacy_shop(force=force)
    print(f"Dataset ready: {repo}")


def create_runs_command(force: bool = False) -> None:
    created = create_manual_runs(force=force)
    print(f"Runs ready: {len(created)} directories under {RUNS_DIR}")


def create_stage2_dataset_command(force: bool = False) -> None:
    write_stage2_data(force=force)
    repo = generate_legacy_shop_v2(force=force)
    print(f"Stage2 dataset ready: {repo}")


def create_stage2_runs_command(force: bool = False) -> None:
    if not (SAMPLE_REPO_DIR.parent / "legacy-shop-spring-v2").exists():
        create_stage2_dataset_command(force=False)
    created = create_stage2_runs(force=force)
    print(f"Stage2 runs ready: {len(created)} directories under {RUNS_STAGE2_DIR}")


def create_claimbench_command(force: bool = False) -> None:
    write_claimbench_data(force=force)
    repo = generate_claim_sample_repo(force=force)
    print(f"ClaimBench dataset ready: {repo}")


def create_claim_runs_command(force: bool = False) -> None:
    if not SAMPLE_REPO_CLAIM_DIR.exists():
        create_claimbench_command(force=False)
    created = create_claim_runs(force=force)
    print(f"ClaimBench runs ready: {len(created)} directories under {RUNS_CLAIM_DIR}")


def run_tests_command(run_dir: Path | None, run_all: bool, timeout_seconds: int) -> None:
    if run_all:
        run_dirs = find_run_dirs(RUNS_DIR)
    elif run_dir is not None:
        run_dirs = find_run_dirs(run_dir)
    else:
        raise SystemExit("Pass --run-dir or --all.")

    if not run_dirs:
        raise SystemExit("No run directories found.")

    for item in run_dirs:
        result = run_maven_tests(item, timeout_seconds=timeout_seconds)
        status = "PASS" if result["success"] else "FAIL"
        print(f"{status} {item} ({result['duration_seconds']}s)")


def run_deepseek_command(
    run_dir: Path | None,
    run_all: bool,
    limit: int | None,
    skip_existing: bool,
    api_timeout_seconds: int,
    test_timeout_seconds: int,
    dry_run: bool,
    model: str,
    thinking: str,
    reasoning_effort: str | None,
    max_tokens: int,
    temperature: float,
    workers: int,
) -> None:
    if run_all:
        root = RUNS_DIR
    elif run_dir is not None:
        root = run_dir
    else:
        raise SystemExit("Pass --run-dir or --all.")

    config = DeepSeekConfig(
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    results = run_deepseek_for_many(
        root=root,
        config=config,
        all_runs=True,
        limit=limit,
        skip_existing=skip_existing,
        api_timeout_seconds=api_timeout_seconds,
        test_timeout_seconds=test_timeout_seconds,
        dry_run=dry_run,
        workers=workers,
    )
    print(f"DeepSeek experiments processed: {len(results)}")


def collect_results_command() -> None:
    results = collect_results()
    print(f"Collected {len(results)} run results into {RUNS_DIR / 'results.json'}")


def retry_patches_command(run_dir: Path | None, test_timeout_seconds: int) -> None:
    root = run_dir if run_dir is not None else RUNS_DIR
    results = retry_apply_failed_patches(root=root, test_timeout_seconds=test_timeout_seconds)
    print(f"Retried existing patches: {len(results)}")


def report_command() -> None:
    paths = generate_reports()
    print(f"Reports written to {REPORTS_DIR}:")
    for path in paths:
        print(f"- {path}")


def run_stage2_command(
    model: str,
    workers: int,
    skip_existing: bool,
    api_timeout_seconds: int,
    test_timeout_seconds: int,
) -> None:
    results = run_stage2_model(
        model=model,
        workers=workers,
        skip_existing=skip_existing,
        api_timeout_seconds=api_timeout_seconds,
        test_timeout_seconds=test_timeout_seconds,
    )
    print(f"Stage2 experiments processed: {len(results)}")


def collect_stage2_results_command() -> None:
    results = collect_stage2_results()
    print(f"Collected {len(results)} Stage2 results into {RUNS_STAGE2_DIR / 'results.json'}")


def report_stage2_command() -> None:
    paths = generate_stage2_reports()
    print(f"Stage2 reports written to {REPORTS_STAGE2_DIR}:")
    for path in paths:
        print(f"- {path}")


def run_claimbench_command(
    model: str,
    thinking: str,
    reasoning_effort: str | None,
    max_tokens: int,
    temperature: float,
    workers: int,
    sample: str,
    limit: int | None,
    skip_existing: bool,
    api_timeout_seconds: int,
    test_timeout_seconds: int,
    dry_run: bool,
) -> None:
    results = run_claimbench_model(
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        temperature=temperature,
        workers=workers,
        sample=sample,
        limit=limit,
        skip_existing=skip_existing,
        api_timeout_seconds=api_timeout_seconds,
        test_timeout_seconds=test_timeout_seconds,
        dry_run=dry_run,
    )
    print(f"ClaimBench experiments processed: {len(results)}")


def collect_claim_results_command() -> None:
    results = collect_claim_results()
    print(f"Collected {len(results)} ClaimBench results into {RUNS_CLAIM_DIR / 'results.json'}")


def report_claimbench_command() -> None:
    paths = generate_claim_stage_reports()
    print(f"ClaimBench reports written to {REPORTS_CLAIM_DIR}:")
    for path in paths:
        print(f"- {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracegate", description="TraceGate Eval MVP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dataset = subparsers.add_parser("create-dataset", help="Generate sample repo and experiment data files.")
    dataset.add_argument("--force", action="store_true", help="Overwrite generated dataset files.")

    runs = subparsers.add_parser("create-runs", help="Generate independent run directories and prompts.")
    runs.add_argument("--force", action="store_true", help="Overwrite generated run directories.")

    stage2_dataset = subparsers.add_parser("create-stage2-dataset", help="Generate Stage2 Active/Stale dataset.")
    stage2_dataset.add_argument("--force", action="store_true", help="Overwrite generated Stage2 dataset files.")

    stage2_runs = subparsers.add_parser("create-stage2-runs", help="Generate Stage2 independent run directories.")
    stage2_runs.add_argument("--force", action="store_true", help="Overwrite generated Stage2 run directories.")

    claimbench = subparsers.add_parser("create-claimbench", help="Generate Stage3 ClaimBench dataset.")
    claimbench.add_argument("--force", action="store_true", help="Overwrite generated ClaimBench dataset files.")

    claim_runs = subparsers.add_parser("create-claim-runs", help="Generate Stage3 ClaimBench independent run directories.")
    claim_runs.add_argument("--force", action="store_true", help="Overwrite generated ClaimBench run directories.")

    tests = subparsers.add_parser("run-tests", help="Run mvn test for one or more runs.")
    tests.add_argument("--run-dir", type=Path, help="Run directory or parent directory containing runs.")
    tests.add_argument("--all", action="store_true", help="Run tests for all runs under runs/.")
    tests.add_argument("--timeout-seconds", type=int, default=180)

    deepseek = subparsers.add_parser("run-deepseek", help="Call DeepSeek, apply patches, and run tests.")
    deepseek.add_argument("--run-dir", type=Path, help="Run directory or parent directory containing runs.")
    deepseek.add_argument("--all", action="store_true", help="Run all experiments under runs/.")
    deepseek.add_argument("--limit", type=int, help="Limit number of run directories processed.")
    deepseek.add_argument("--skip-existing", action="store_true", default=False, help="Skip runs with results/deepseek_run.json.")
    deepseek.add_argument("--api-timeout-seconds", type=int, default=180)
    deepseek.add_argument("--test-timeout-seconds", type=int, default=180)
    deepseek.add_argument("--dry-run", action="store_true", help="Write request JSON without calling DeepSeek.")
    deepseek.add_argument("--model", default="deepseek-v4-flash")
    deepseek.add_argument("--thinking", choices=["enabled", "disabled"], default="disabled")
    deepseek.add_argument("--reasoning-effort", choices=["high", "max"], help="DeepSeek V4 thinking effort. Used when --thinking enabled.")
    deepseek.add_argument("--max-tokens", type=int, default=12000)
    deepseek.add_argument("--temperature", type=float, default=0.1)
    deepseek.add_argument("--workers", type=int, default=1, help="Number of run directories to process concurrently.")

    retry = subparsers.add_parser("retry-patches", help="Retry applying existing model.patch files for apply_failed runs.")
    retry.add_argument("--run-dir", type=Path, help="Run directory or parent directory containing runs.")
    retry.add_argument("--test-timeout-seconds", type=int, default=180)

    stage2_run = subparsers.add_parser("run-stage2", help="Run Stage2 experiments for a model.")
    stage2_run.add_argument("--model", default="deepseek-v4-pro")
    stage2_run.add_argument("--workers", type=int, default=3)
    stage2_run.add_argument("--skip-existing", action="store_true", default=False)
    stage2_run.add_argument("--api-timeout-seconds", type=int, default=240)
    stage2_run.add_argument("--test-timeout-seconds", type=int, default=300)

    claim_run = subparsers.add_parser("run-claimbench", help="Run ClaimBench experiments for a model.")
    claim_run.add_argument("--model", default="deepseek-v4-pro")
    claim_run.add_argument("--thinking", choices=["enabled", "disabled"], default="disabled")
    claim_run.add_argument("--reasoning-effort", choices=["high", "max"], help="DeepSeek V4 thinking effort. Used when --thinking enabled.")
    claim_run.add_argument("--max-tokens", type=int, default=12000)
    claim_run.add_argument("--temperature", type=float, default=0.0)
    claim_run.add_argument("--workers", type=int, default=4)
    claim_run.add_argument("--sample", choices=["pilot", "all"], default="all")
    claim_run.add_argument("--limit", type=int)
    claim_run.add_argument("--skip-existing", action="store_true", default=False)
    claim_run.add_argument("--api-timeout-seconds", type=int, default=240)
    claim_run.add_argument("--test-timeout-seconds", type=int, default=300)
    claim_run.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("collect-results", help="Collect test, diff, and constraint metrics.")
    subparsers.add_parser("report", help="Generate Markdown, CSV, and HTML reports.")
    subparsers.add_parser("collect-stage2-results", help="Collect Stage2 execution and semantic metrics.")
    subparsers.add_parser("report-stage2", help="Generate Stage2 Markdown, CSV, and HTML reports.")
    subparsers.add_parser("collect-claim-results", help="Collect ClaimBench execution and semantic metrics.")
    subparsers.add_parser("report-claimbench", help="Generate ClaimBench reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-dataset":
        create_dataset_command(force=args.force)
    elif args.command == "create-runs":
        if not SAMPLE_REPO_DIR.exists():
            create_dataset_command(force=False)
        create_runs_command(force=args.force)
    elif args.command == "create-stage2-dataset":
        create_stage2_dataset_command(force=args.force)
    elif args.command == "create-stage2-runs":
        create_stage2_runs_command(force=args.force)
    elif args.command == "create-claimbench":
        create_claimbench_command(force=args.force)
    elif args.command == "create-claim-runs":
        create_claim_runs_command(force=args.force)
    elif args.command == "run-tests":
        run_tests_command(args.run_dir, args.all, args.timeout_seconds)
    elif args.command == "run-deepseek":
        run_deepseek_command(
            run_dir=args.run_dir,
            run_all=args.all,
            limit=args.limit,
            skip_existing=args.skip_existing,
            api_timeout_seconds=args.api_timeout_seconds,
            test_timeout_seconds=args.test_timeout_seconds,
            dry_run=args.dry_run,
            model=args.model,
            thinking=args.thinking,
            reasoning_effort=args.reasoning_effort,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            workers=args.workers,
        )
    elif args.command == "collect-results":
        collect_results_command()
    elif args.command == "retry-patches":
        retry_patches_command(args.run_dir, args.test_timeout_seconds)
    elif args.command == "run-stage2":
        run_stage2_command(
            model=args.model,
            workers=args.workers,
            skip_existing=args.skip_existing,
            api_timeout_seconds=args.api_timeout_seconds,
            test_timeout_seconds=args.test_timeout_seconds,
        )
    elif args.command == "run-claimbench":
        run_claimbench_command(
            model=args.model,
            thinking=args.thinking,
            reasoning_effort=args.reasoning_effort,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            workers=args.workers,
            sample=args.sample,
            limit=args.limit,
            skip_existing=args.skip_existing,
            api_timeout_seconds=args.api_timeout_seconds,
            test_timeout_seconds=args.test_timeout_seconds,
            dry_run=args.dry_run,
        )
    elif args.command == "report":
        report_command()
    elif args.command == "collect-stage2-results":
        collect_stage2_results_command()
    elif args.command == "report-stage2":
        report_stage2_command()
    elif args.command == "collect-claim-results":
        collect_claim_results_command()
    elif args.command == "report-claimbench":
        report_claimbench_command()
    else:  # pragma: no cover - argparse enforces command choices
        parser.print_help()
