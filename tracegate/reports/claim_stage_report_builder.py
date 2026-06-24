from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from tracegate.config import CLAIM_CONTEXT_GROUPS, CLAIM_EVIDENCE_STATUSES, REPORTS_CLAIM_DIR, RUNS_CLAIM_DIR
from tracegate.dataio import read_json
from tracegate.reports.claim_stage_case_report import write_case_report
from tracegate.reports.claim_stage_csv_report import write_claim_stage_csv, write_rows_csv
from tracegate.reports.claim_stage_html_report import write_claim_stage_html
from tracegate.reports.claim_stage_markdown_report import write_claim_stage_markdown


def _count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _avg_quality(rows: list[dict[str, Any]]) -> float:
    return round(sum(int(row.get("verification_plan_quality") or 0) for row in rows) / len(rows), 3) if rows else 0.0


def _context_summary_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row.get("context_group"))].append(row)
    rows: list[dict[str, Any]] = []
    for context in CLAIM_CONTEXT_GROUPS:
        items = grouped.get(context, [])
        rows.append(
            {
                "context_group": context,
                "runs": len(items),
                "safe_success": _count(items, "safe_success"),
                "destructive_change": _count(items, "destructive_change"),
                "pollution": _count(items, "pollution"),
                "avg_verification_plan_quality": _avg_quality(items),
            }
        )
    return rows


def _evidence_summary_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row.get("evidence_status"))].append(row)
    rows: list[dict[str, Any]] = []
    for status in CLAIM_EVIDENCE_STATUSES:
        items = grouped.get(status, [])
        rows.append(
            {
                "evidence_status": status,
                "runs": len(items),
                "correct_decision": _count(items, "evidence_aware_decision"),
                "test_success": _count(items, "test_success"),
                "destructive_change": _count(items, "destructive_change"),
                "pollution": _count(items, "pollution"),
                "avg_verification_plan_quality": _avg_quality(items),
            }
        )
    return rows


def _plan_quality_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[(str(row.get("context_group")), str(row.get("evidence_status")))].append(row)
    rows: list[dict[str, Any]] = []
    for context in CLAIM_CONTEXT_GROUPS:
        for status in CLAIM_EVIDENCE_STATUSES:
            items = grouped.get((context, status), [])
            row = {
                "context_group": context,
                "evidence_status": status,
                "runs": len(items),
                "avg_verification_plan_quality": _avg_quality(items),
            }
            for score in range(4):
                row[f"quality_{score}"] = sum(1 for item in items if int(item.get("verification_plan_quality") or 0) == score)
            rows.append(row)
    return rows


def generate_claim_stage_reports(
    runs_dir: Path = RUNS_CLAIM_DIR,
    reports_dir: Path = REPORTS_CLAIM_DIR,
) -> list[Path]:
    results = read_json(runs_dir / "results.json", default=[])
    if not results:
        raise FileNotFoundError("No ClaimBench results found. Run collect-claim-results first.")
    reports_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        write_claim_stage_markdown(results, reports_dir / "claim_stage_summary.md"),
        write_claim_stage_csv(results, reports_dir / "claim_stage_results.csv"),
        write_rows_csv(
            _evidence_summary_rows(results),
            reports_dir / "evidence_status_summary.csv",
            [
                "evidence_status",
                "runs",
                "correct_decision",
                "test_success",
                "destructive_change",
                "pollution",
                "avg_verification_plan_quality",
            ],
        ),
        write_rows_csv(
            _plan_quality_rows(results),
            reports_dir / "verification_plan_quality.csv",
            [
                "context_group",
                "evidence_status",
                "runs",
                "avg_verification_plan_quality",
                "quality_0",
                "quality_1",
                "quality_2",
                "quality_3",
            ],
        ),
        write_rows_csv(
            _context_summary_rows(results),
            reports_dir / "context_group_summary.csv",
            ["context_group", "runs", "safe_success", "destructive_change", "pollution", "avg_verification_plan_quality"],
        ),
        write_case_report(
            results,
            reports_dir / "destructive_change_cases.md",
            "Destructive Change Cases",
            lambda row: bool(row.get("destructive_change")),
        ),
        write_case_report(
            results,
            reports_dir / "pollution_cases.md",
            "Pollution Cases",
            lambda row: bool(row.get("pollution")),
        ),
        write_case_report(
            results,
            reports_dir / "unknown_evidence_cases.md",
            "Unknown Evidence Cases",
            lambda row: row.get("evidence_status") == "unknown",
        ),
        write_case_report(
            results,
            reports_dir / "conflicting_evidence_cases.md",
            "Conflicting Evidence Cases",
            lambda row: row.get("evidence_status") == "conflicting",
        ),
        write_case_report(
            results,
            reports_dir / "tracegate_verify_first_cases.md",
            "TraceGate Verify-First Success Cases",
            lambda row: row.get("context_group") == "tracegate_verify_first"
            and row.get("evidence_status") in {"unknown", "conflicting"}
            and row.get("evidence_aware_decision") is True
            and int(row.get("verification_plan_quality") or 0) >= 2,
        ),
        write_claim_stage_html(results, reports_dir / "claim_stage_report.html"),
    ]
    return paths
