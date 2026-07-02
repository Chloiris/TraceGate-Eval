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
from tracegate.data.discover import write_discovery_doc
from tracegate.data.full_label_audit import run_full_label_audit
from tracegate.data.hard_cases import (
    mine_hard_candidates,
    promote_manual_labels,
    summarize_review_queue,
    write_accepted_labels,
    write_data_blocked,
)
from tracegate.data.manifest import build_dataset_manifest
from tracegate.data.normalize import normalize_raw_records
from tracegate.data.sources.base import RealDataError
from tracegate.data.sources.github_adapter import fetch_github_pull_requests
from tracegate.data.validate import DatasetValidationError, validate_dataset
from tracegate.core.guardrails import audit_run, strict_scan
from tracegate.core.run import RealRunError, regenerate_report, run_real_advisory
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


def data_discover_command() -> None:
    path = write_discovery_doc()
    print(f"Dataset discovery written to {path}")


def data_fetch_command(source: str, limit: int, real_only: bool, no_fallback: bool) -> None:
    if not real_only:
        raise SystemExit("real data fetch requires --real-only")
    if not no_fallback:
        raise SystemExit("real data fetch requires --no-fallback")
    if source not in {"auto", "github_api"}:
        raise SystemExit("P0 supports --source auto or --source github_api")
    raw_dir = Path("datasets/real_min/raw")
    output_path = Path("datasets/real_min/cases.jsonl")
    try:
        result = fetch_github_pull_requests(raw_dir=raw_dir, limit=limit)
        cases = normalize_raw_records(input_dir=raw_dir, output_path=output_path)
        manifest = build_dataset_manifest(output_path)
    except RealDataError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Fetched {result.records_written} raw records from {result.source}")
    print(f"Normalized {len(cases)} cases to {output_path}")
    print(f"Dataset manifest: {output_path.with_name('manifest.json')}")
    print(f"Scored real cases: {manifest['num_cases_scored']}")


def data_normalize_command(input_dir: Path, output_path: Path) -> None:
    try:
        cases = normalize_raw_records(input_dir=input_dir, output_path=output_path)
        build_dataset_manifest(output_path)
    except RealDataError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Normalized {len(cases)} cases to {output_path}")


def data_validate_command(dataset_path: Path, strict: bool, min_cases: int) -> None:
    try:
        _, summary = validate_dataset(dataset_path=dataset_path, strict=strict, min_cases=min_cases)
    except (DatasetValidationError, ValueError, FileNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc
    print("Dataset validation passed")
    for key, value in summary.items():
        print(f"{key}: {value}")


def data_manifest_command(dataset_path: Path) -> None:
    manifest = build_dataset_manifest(dataset_path)
    print(f"Dataset manifest written to {dataset_path.with_name('manifest.json')}")
    print(f"dataset_sha256: {manifest['dataset_sha256']}")


def data_mine_hard_command(repos: str, limit: int, real_only: bool, no_fallback: bool) -> None:
    if not real_only:
        raise SystemExit("hard case mining requires --real-only")
    if not no_fallback:
        raise SystemExit("hard case mining requires --no-fallback")
    repo_list = [item.strip() for item in repos.split(",") if item.strip()]
    try:
        summary = mine_hard_candidates(repos=repo_list, limit=limit)
    except RealDataError as exc:
        blocked = write_data_blocked(str(exc))
        raise SystemExit(f"{exc}\nData blocker written to {blocked}") from exc
    print("Hard candidate mining complete")
    for key, value in summary.items():
        print(f"{key}: {value}")


def data_review_queue_command(input_path: Path) -> None:
    summary = summarize_review_queue(input_path)
    print("Manual review queue summary")
    for key, value in summary.items():
        print(f"{key}: {value}")


def data_accept_labels_command(labels_path: Path, output_path: Path, accepted_by: str) -> None:
    try:
        summary = write_accepted_labels(labels_path=labels_path, output_path=output_path, accepted_by=accepted_by)
    except RealDataError as exc:
        raise SystemExit(str(exc)) from exc
    print("Accepted labels written")
    for key, value in summary.items():
        print(f"{key}: {value}")


def data_promote_labels_command(labels_path: Path, dataset_path: Path | None, output_path: Path, accepted_sources: str) -> None:
    sources = {item.strip() for item in accepted_sources.split(",") if item.strip()}
    try:
        summary = promote_manual_labels(
            labels_path=labels_path,
            dataset_path=dataset_path,
            output_path=output_path,
            accepted_sources=sources,
        )
    except RealDataError as exc:
        raise SystemExit(str(exc)) from exc
    print("Manual labels promoted")
    for key, value in summary.items():
        print(f"{key}: {value}")


def data_full_label_audit_command(queue_path: Path, labels_path: Path, report_path: Path, checklist_path: Path) -> None:
    try:
        summary = run_full_label_audit(
            queue_path=queue_path,
            labels_path=labels_path,
            report_path=report_path,
            checklist_path=checklist_path,
        )
    except (RealDataError, FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print("Full label audit complete")
    for key, value in summary.items():
        print(f"{key}: {value}")


def real_run_command(
    dataset_path: Path,
    advisor: str,
    real_only: bool,
    no_mock: bool,
    no_fallback: bool,
) -> None:
    command = (
        f"python -m tracegate run --dataset {dataset_path.as_posix()} --advisor {advisor} "
        f"{'--real-only' if real_only else ''} {'--no-mock' if no_mock else ''} {'--no-fallback' if no_fallback else ''}"
    ).strip()
    try:
        manifest = run_real_advisory(
            dataset_path=dataset_path,
            advisor=advisor,
            run_dir=Path("runs/latest"),
            real_only=real_only,
            no_mock=no_mock,
            no_fallback=no_fallback,
            command=command,
        )
    except RealRunError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Real advisory run complete: {manifest['run_id']}")
    print("Run directory: runs/latest")


def real_report_command(run_dir: Path, formats: str) -> None:
    requested = {item.strip() for item in formats.split(",") if item.strip()}
    unknown = requested - {"markdown", "json"}
    if unknown:
        raise SystemExit(f"unsupported report format(s): {', '.join(sorted(unknown))}")
    paths = regenerate_report(run_dir=run_dir, formats=requested)
    for path in paths:
        print(f"Report written: {path}")


def guardrails_scan_command(strict: bool) -> None:
    findings, errors = strict_scan()
    print(f"Guardrail scan findings: {len(findings)}")
    print("Fallback audit written to docs/FALLBACK_AUDIT.md")
    if strict and errors:
        raise SystemExit("\n".join(errors))


def guardrails_audit_command(run_dir: Path, strict: bool) -> None:
    result = audit_run(run_dir=run_dir, strict=strict)
    print(f"Guardrail audit passed: {result['passed']}")
    print("Fallback audit written to docs/FALLBACK_AUDIT.md")
    if strict and not result["passed"]:
        raise SystemExit("\n".join(result["errors"]))


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


def web_command(host: str, port: int, reload: bool) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Install web dependencies first: python -m pip install -r requirements.txt") from exc
    uvicorn.run("tracegate.web.app:app", host=host, port=port, reload=reload)


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

    web = subparsers.add_parser("web", help="Start the lightweight Web/API dashboard.")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8000)
    web.add_argument("--reload", action="store_true")

    data = subparsers.add_parser("data", help="Real-data discovery, fetch, normalize, validate, and manifest commands.")
    data_subparsers = data.add_subparsers(dest="data_command", required=True)

    data_subparsers.add_parser("discover", help="Document candidate real-data sources.")

    data_fetch = data_subparsers.add_parser("fetch", help="Fetch and normalize minimal real GitHub PR data.")
    data_fetch.add_argument("--source", default="auto")
    data_fetch.add_argument("--limit", type=int, default=12)
    data_fetch.add_argument("--real-only", action="store_true")
    data_fetch.add_argument("--no-fallback", action="store_true")

    data_normalize = data_subparsers.add_parser("normalize", help="Normalize raw real-data artifacts into cases.jsonl.")
    data_normalize.add_argument("--input", type=Path, required=True)
    data_normalize.add_argument("--output", type=Path, required=True)

    data_validate = data_subparsers.add_parser("validate", help="Validate normalized real-data cases.")
    data_validate.add_argument("--dataset", type=Path, required=True)
    data_validate.add_argument("--strict", action="store_true")
    data_validate.add_argument("--min-cases", type=int, default=8)

    data_manifest = data_subparsers.add_parser("manifest", help="Write a dataset manifest.")
    data_manifest.add_argument("--dataset", type=Path, required=True)

    data_mine_hard = data_subparsers.add_parser("mine-hard", help="Mine hard real PR candidates into a manual review queue.")
    data_mine_hard.add_argument("--repos", required=True, help="Comma-separated owner/name repositories.")
    data_mine_hard.add_argument("--limit", type=int, default=40)
    data_mine_hard.add_argument("--real-only", action="store_true")
    data_mine_hard.add_argument("--no-fallback", action="store_true")

    data_review_queue = data_subparsers.add_parser("review-queue", help="Summarize hard candidate manual review queue.")
    data_review_queue.add_argument("--input", type=Path, required=True)

    data_accept = data_subparsers.add_parser("accept-labels", help="Write human-accepted labels from Codex semantic audit promotes.")
    data_accept.add_argument("--labels", type=Path, required=True)
    data_accept.add_argument("--output", type=Path, required=True)
    data_accept.add_argument("--accepted-by", default="Chloiris")

    data_full_audit = data_subparsers.add_parser("full-label-audit", help="Audit all manual review candidates into Codex review labels.")
    data_full_audit.add_argument("--input", type=Path, default=Path("datasets/real_min/labels/manual_review_queue.jsonl"))
    data_full_audit.add_argument("--labels", type=Path, default=Path("datasets/real_min/labels/manual_labels.jsonl"))
    data_full_audit.add_argument("--report", type=Path, default=Path("docs/CODEX_FULL_LABEL_AUDIT_REPORT.md"))
    data_full_audit.add_argument("--checklist", type=Path, default=Path("docs/HUMAN_FINAL_CHECKLIST.md"))

    data_promote = data_subparsers.add_parser("promote-labels", help="Promote manually confirmed hard labels into cases.jsonl.")
    data_promote.add_argument("--labels", type=Path, required=True)
    data_promote.add_argument("--dataset", type=Path)
    data_promote.add_argument("--output", type=Path, required=True)
    data_promote.add_argument("--accepted-sources", default="manual_verified")

    real_run = subparsers.add_parser("run", help="Run deterministic real-data PR advisory baseline.")
    real_run.add_argument("--dataset", type=Path, required=True)
    real_run.add_argument("--advisor", default="rule")
    real_run.add_argument("--real-only", action="store_true")
    real_run.add_argument("--no-mock", action="store_true")
    real_run.add_argument("--no-fallback", action="store_true")

    guardrails = subparsers.add_parser("guardrails", help="Reality guardrails for real-data runs.")
    guardrail_subparsers = guardrails.add_subparsers(dest="guardrails_command", required=True)
    guardrails_scan = guardrail_subparsers.add_parser("scan", help="Scan code/docs for fallback/mock/synthetic risk.")
    guardrails_scan.add_argument("--strict", action="store_true")
    guardrails_audit = guardrail_subparsers.add_parser("audit", help="Audit a real advisory run.")
    guardrails_audit.add_argument("--run", type=Path, required=True)
    guardrails_audit.add_argument("--strict", action="store_true")

    subparsers.add_parser("collect-results", help="Collect test, diff, and constraint metrics.")
    report = subparsers.add_parser("report", help="Generate legacy reports or real-data run reports.")
    report.add_argument("--run", type=Path, help="Real-data run directory, e.g. runs/latest.")
    report.add_argument("--format", default="markdown,json", help="Comma-separated real-data report formats.")
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
        if args.run is not None:
            real_report_command(run_dir=args.run, formats=args.format)
        else:
            report_command()
    elif args.command == "collect-stage2-results":
        collect_stage2_results_command()
    elif args.command == "report-stage2":
        report_stage2_command()
    elif args.command == "collect-claim-results":
        collect_claim_results_command()
    elif args.command == "report-claimbench":
        report_claimbench_command()
    elif args.command == "web":
        web_command(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "data":
        if args.data_command == "discover":
            data_discover_command()
        elif args.data_command == "fetch":
            data_fetch_command(
                source=args.source,
                limit=args.limit,
                real_only=args.real_only,
                no_fallback=args.no_fallback,
            )
        elif args.data_command == "normalize":
            data_normalize_command(input_dir=args.input, output_path=args.output)
        elif args.data_command == "validate":
            data_validate_command(dataset_path=args.dataset, strict=args.strict, min_cases=args.min_cases)
        elif args.data_command == "manifest":
            data_manifest_command(dataset_path=args.dataset)
        elif args.data_command == "mine-hard":
            data_mine_hard_command(
                repos=args.repos,
                limit=args.limit,
                real_only=args.real_only,
                no_fallback=args.no_fallback,
            )
        elif args.data_command == "review-queue":
            data_review_queue_command(input_path=args.input)
        elif args.data_command == "full-label-audit":
            data_full_label_audit_command(
                queue_path=args.input,
                labels_path=args.labels,
                report_path=args.report,
                checklist_path=args.checklist,
            )
        elif args.data_command == "accept-labels":
            data_accept_labels_command(labels_path=args.labels, output_path=args.output, accepted_by=args.accepted_by)
        elif args.data_command == "promote-labels":
            data_promote_labels_command(
                labels_path=args.labels,
                dataset_path=args.dataset,
                output_path=args.output,
                accepted_sources=args.accepted_sources,
            )
    elif args.command == "run":
        real_run_command(
            dataset_path=args.dataset,
            advisor=args.advisor,
            real_only=args.real_only,
            no_mock=args.no_mock,
            no_fallback=args.no_fallback,
        )
    elif args.command == "guardrails":
        if args.guardrails_command == "scan":
            guardrails_scan_command(strict=args.strict)
        elif args.guardrails_command == "audit":
            guardrails_audit_command(run_dir=args.run, strict=args.strict)
    else:  # pragma: no cover - argparse enforces command choices
        parser.print_help()
