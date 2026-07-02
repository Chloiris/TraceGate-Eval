from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from importlib import metadata

from tracegate.core.advisory import run_rule_advisor
from tracegate.core.metrics import compute_metrics
from tracegate.core.models import AdvisoryDecision
from tracegate.core.serialization import load_cases, read_json, sha256_file, write_json, write_jsonl
from tracegate.data.manifest import build_dataset_manifest
from tracegate.data.validate import DatasetValidationError, validate_dataset


class RealRunError(RuntimeError):
    """Raised when a real-data run cannot complete under strict guardrails."""


def git_output(args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def dependency_snapshot() -> str:
    rows = set()
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        version = dist.version
        if name and name.lower() in {"tracegate-eval", "pyyaml", "fastapi", "pydantic", "pytest", "httpx", "uvicorn"}:
            rows.add(f"{name}=={version}")
    return "\n".join(sorted(rows))


def ensure_real_run_flags(real_only: bool, no_mock: bool, no_fallback: bool) -> None:
    if not real_only:
        raise RealRunError("real run requires --real-only")
    if not no_mock:
        raise RealRunError("real run requires --no-mock")
    if not no_fallback:
        raise RealRunError("real run requires --no-fallback")


def manual_review_queue_count(path: Path = Path("datasets/real_min/labels/manual_review_queue.jsonl")) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def run_real_advisory(
    dataset_path: Path,
    advisor: str,
    run_dir: Path,
    real_only: bool,
    no_mock: bool,
    no_fallback: bool,
    command: str,
    min_cases: int = 8,
) -> dict[str, Any]:
    ensure_real_run_flags(real_only=real_only, no_mock=no_mock, no_fallback=no_fallback)
    if advisor != "rule":
        raise RealRunError("P0 only supports --advisor rule; no mock or fallback advisor is available")
    try:
        cases, validation = validate_dataset(dataset_path, strict=True, min_cases=min_cases)
    except DatasetValidationError as exc:
        raise RealRunError(str(exc)) from exc
    scored_cases = [case for case in cases if case.is_scored_real_case]
    advisories = run_rule_advisor(cases)
    metrics = compute_metrics(cases, advisories)
    metrics["manual_review_queue_cases"] = manual_review_queue_count()
    if metrics["num_cases_scored"] < min_cases:
        raise RealRunError(f"real run requires at least {min_cases} scored cases")

    run_dir.mkdir(parents=True, exist_ok=True)
    dataset_manifest_path = dataset_path.with_name("manifest.json")
    dataset_sha256 = sha256_file(dataset_path)
    if dataset_manifest_path.exists():
        dataset_manifest = read_json(dataset_manifest_path)
        if dataset_manifest.get("dataset_sha256") != dataset_sha256:
            dataset_manifest = build_dataset_manifest(dataset_path, dataset_manifest_path)
    else:
        dataset_manifest = build_dataset_manifest(dataset_path, dataset_manifest_path)
    run_id = datetime.now(timezone.utc).strftime("tracegate-real-%Y%m%dT%H%M%SZ")
    write_jsonl(run_dir / "advisory_results.jsonl", [item.to_dict() for item in advisories])
    write_json(run_dir / "metrics.json", metrics)
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_output(["rev-parse", "HEAD"]),
        "branch": git_output(["branch", "--show-current"]),
        "command": command,
        "dataset_path": dataset_path.as_posix(),
        "dataset_manifest_path": dataset_manifest_path.as_posix(),
        "dataset_sha256": dataset_sha256,
        "num_cases_total": metrics["num_cases_total"],
        "num_cases_scored": metrics["num_cases_scored"],
        "num_cases_excluded": metrics["num_cases_excluded"],
        "status_distribution": metrics["status_distribution"],
        "decision_distribution": metrics["decision_distribution"],
        "risk_level_distribution": metrics["risk_level_distribution"],
        "active_only": metrics["active_only"],
        "hard_benchmark_ready": metrics["hard_benchmark_ready"],
        "manual_review_queue_cases": metrics["manual_review_queue_cases"],
        "used_real_data": True,
        "used_synthetic_data": False,
        "used_mock_model": False,
        "used_fallback_data": False,
        "cache_mode": "downloaded",
        "source_datasets": dataset_manifest["source_datasets"],
        "python_version": sys.version,
        "python_arch": platform.machine(),
        "platform": platform.platform(),
        "local_arch": platform.machine(),
        "dependencies_snapshot": dependency_snapshot(),
        "real_evaluation_succeeded": True,
        "validation": validation,
    }
    write_json(run_dir / "run_manifest.json", manifest)
    write_report_files(run_dir, manifest, metrics, advisories)
    (run_dir / "command_log.txt").write_text(command + "\n", encoding="utf-8")
    return manifest


def load_advisories(path: Path) -> list[AdvisoryDecision]:
    rows = []
    for row in load_jsonl_dicts(path):
        rows.append(
            AdvisoryDecision(
                case_id=row["case_id"],
                risk_level=row["risk_level"],
                risk_score=int(row["risk_score"]),
                evidence_status=row["evidence_status"],
                decision=row["decision"],
                summary=row["summary"],
                rationale=row["rationale"],
                evidence_used=list(row.get("evidence_used", [])),
                verification_plan=list(row.get("verification_plan", [])),
                pollution_flags=list(row.get("pollution_flags", [])),
                limitations=list(row.get("limitations", [])),
                requires_human_review=bool(row.get("requires_human_review")),
            )
        )
    return rows


def load_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    import json

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def render_markdown_report(manifest: dict[str, Any], metrics: dict[str, Any], advisories: list[AdvisoryDecision]) -> str:
    lines = [
        "# TraceGate Real-Data PR Advisory Report",
        "",
        f"- benchmark: `{metrics.get('benchmark_name', 'TraceGate real-data benchmark')}`",
        f"- run_id: `{manifest['run_id']}`",
        f"- real_evaluation_succeeded: `{manifest.get('real_evaluation_succeeded', False)}`",
        f"- used_real_data: `{manifest.get('used_real_data')}`",
        f"- used_synthetic_data: `{manifest.get('used_synthetic_data')}`",
        f"- used_mock_model: `{manifest.get('used_mock_model')}`",
        f"- used_fallback_data: `{manifest.get('used_fallback_data')}`",
        f"- dataset: `{manifest.get('dataset_path')}`",
        f"- dataset_sha256: `{manifest.get('dataset_sha256')}`",
        "",
        (
            "This run is an active-only real-data smoke run, not a hard real-data mini benchmark."
            if metrics.get("active_only")
            else "This is a v0.2-alpha hard real-data mini benchmark. It remains a small non-statistical benchmark."
        ),
        "",
        "- Hard labels come from Codex evidence audit plus human final acceptance.",
        "- This benchmark does not replace human code review.",
        "- GitHub Action advisory remains warning-only.",
        "",
        "## Metrics",
        "",
    ]
    for key in [
        "num_cases_total",
        "num_cases_scored",
        "num_cases_excluded",
        "active_count",
        "stale_count",
        "unknown_count",
        "conflicting_count",
        "promoted_cases",
        "pollution_flag_rate",
        "needs_manual_review_rate",
        "provenance_completeness_rate",
        "unsafe_allow_rate",
        "verify_first_rate_on_unknown_or_conflicting",
        "scored_cases",
        "excluded_cases_count",
        "manual_review_cases",
        "manual_review_queue_cases",
        "active_only",
        "hard_benchmark_ready",
    ]:
        lines.append(f"- {key}: `{metrics.get(key)}`")
    lines.extend(["", "## Limitations", ""])
    for item in metrics.get("limitations", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Distributions", ""])
    for key in [
        "status_distribution",
        "scored_status_distribution",
        "decision_distribution",
        "risk_level_distribution",
        "label_source_distribution",
    ]:
        lines.append(f"- {key}: `{metrics.get(key)}`")
    lines.extend(
        [
            "",
            "## Run Type",
            "",
            "- real-data smoke run: `true`" if metrics.get("active_only") else "- real-data smoke run: `false`",
            "- hard real-data mini benchmark: `false`" if metrics.get("active_only") else "- hard real-data mini benchmark: `true`",
            f"- manual review queue cases: `{metrics.get('manual_review_queue_cases')}`",
            f"- excluded candidates: `{metrics.get('num_cases_excluded')}`",
            "",
        ]
    )
    lines.extend(["", "## Advisories", ""])
    for item in advisories:
        lines.extend(
            [
                f"### {item.case_id}",
                "",
                f"- evidence_status: `{item.evidence_status}`",
                f"- decision: `{item.decision}`",
                f"- risk_level: `{item.risk_level}`",
                f"- risk_score: `{item.risk_score}`",
                f"- requires_human_review: `{item.requires_human_review}`",
                f"- summary: {item.summary}",
                f"- pollution_flags: `{item.pollution_flags}`",
                "",
            ]
        )
    return "\n".join(lines)


def write_report_files(
    run_dir: Path,
    manifest: dict[str, Any],
    metrics: dict[str, Any],
    advisories: list[AdvisoryDecision],
) -> None:
    markdown = render_markdown_report(manifest, metrics, advisories)
    (run_dir / "report.md").write_text(markdown.rstrip() + "\n", encoding="utf-8")
    write_json(
        run_dir / "report.json",
        {
            "manifest": manifest,
            "metrics": metrics,
            "advisories": [item.to_dict() for item in advisories],
        },
    )


def regenerate_report(run_dir: Path, formats: set[str]) -> list[Path]:
    from tracegate.core.serialization import read_json

    manifest = read_json(run_dir / "run_manifest.json")
    metrics = read_json(run_dir / "metrics.json")
    advisories = load_advisories(run_dir / "advisory_results.jsonl")
    write_report_files(run_dir, manifest, metrics, advisories)
    paths: list[Path] = []
    if "markdown" in formats:
        paths.append(run_dir / "report.md")
    if "json" in formats:
        paths.append(run_dir / "report.json")
    return paths
