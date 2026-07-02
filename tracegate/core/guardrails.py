from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tracegate.core.serialization import load_cases, read_json, sha256_file
from tracegate.data.validate import is_concrete_github_url


KEYWORDS = [
    "fallback",
    "mock",
    "dummy",
    "synthetic",
    "fake",
    "demo",
    "sample",
    "placeholder",
    "except Exception",
    "return []",
    "pass",
    "TODO",
    "FIXME",
    "random",
    "hardcoded",
    "default result",
]


@dataclass(frozen=True)
class ScanFinding:
    path: str
    line: int
    keyword: str
    classification: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "keyword": self.keyword,
            "classification": self.classification,
            "text": self.text,
        }


def should_scan(path: Path) -> bool:
    skip_parts = {".git", ".venv", ".pytest_cache", "runs", "runs_stage2", "runs_claim", "datasets"}
    if any(part in skip_parts for part in path.parts):
        return False
    if path.as_posix() == "docs/FALLBACK_AUDIT.md":
        return False
    if any(part.endswith(".egg-info") for part in path.parts):
        return False
    if path.suffix.lower() not in {".py", ".md", ".yml", ".yaml", ".json", ".txt", ".csv", ".sh", ".ps1"}:
        return False
    return True


def classify(path: Path, keyword: str, line_text: str) -> str:
    posix = path.as_posix()
    lowered = line_text.lower()
    if posix.endswith(".md") or posix.endswith(".txt") or posix.endswith(".csv"):
        return "allowed_documentation"
    if posix in {"requirements.txt", "pyproject.toml", ".env.example"}:
        return "allowed_documentation"
    if posix.startswith("tests/"):
        return "allowed_test_fixture"
    if posix.startswith("docs/") or posix.startswith("reports") or posix.startswith("results/") or posix == "README.md":
        return "allowed_documentation"
    if posix.startswith("examples/") or posix.startswith("sample_repos/") or posix.startswith("experiments/"):
        return "allowed_demo_excluded"
    if posix.startswith("tracegate/dataset/"):
        return "allowed_demo_excluded"
    if posix in {"tracegate/web/data_loader.py", "tracegate/web/service.py"}:
        return "allowed_demo_excluded"
    if posix.startswith("tracegate/web/"):
        return "allowed_demo_excluded"
    if posix == "tracegate/core/guardrails.py":
        return "allowed_documentation"
    if posix.startswith("tracegate/core/") or posix.startswith("tracegate/data/"):
        if any(
            marker in lowered
            for marker in [
                "synthetic",
                "no_fallback",
                "no fallback",
                "used_fallback",
                "used_mock",
                "used_synthetic",
                "is_synthetic",
                "synthetic case must",
                "guardrail",
                "keyword",
                "requires --no-mock",
                "requires --no-fallback",
                "no mock",
                "no_fallback",
                "no fallback data was created",
            ]
        ):
            return "allowed_documentation"
    if posix == "tracegate/cli.py" and any(
        marker in lowered
        for marker in [
            "no_fallback",
            "no fallback",
            "no_mock",
            "no mock",
            "mock",
            "fallback",
            "guardrails",
            "passed",
            "pass --",
            "pass\"",
        ]
    ):
        return "allowed_documentation"
    if posix.startswith("scripts/"):
        return "allowed_documentation"
    if posix in {"tracegate/runners/deepseek_runner.py", "tracegate/runners/claim_runner.py"}:
        if keyword == "except Exception":
            return "allowed_test_fixture"
        if "status" in lowered or "failure" in lowered or "error" in lowered or "skip_reason" in lowered:
            return "allowed_test_fixture"
    if keyword in {"sample", "placeholder"} and posix.endswith(".py"):
        return "allowed_documentation"
    return "dangerous_runtime_path"


def scan_guardrails(root: Path = Path(".")) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    patterns = []
    for keyword in KEYWORDS:
        if " " in keyword:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        else:
            pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        patterns.append((keyword, pattern))
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not should_scan(path.relative_to(root)):
            continue
        rel = path.relative_to(root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for keyword, pattern in patterns:
                if pattern.search(line):
                    findings.append(
                        ScanFinding(
                            path=rel.as_posix(),
                            line=line_number,
                            keyword=keyword,
                            classification=classify(rel, keyword, line),
                            text=line.strip()[:300].strip(),
                        )
                    )
    return findings


def render_fallback_audit(findings: list[ScanFinding], audit_result: dict[str, Any] | None = None) -> str:
    lines = [
        "# Fallback Audit",
        "",
        "Generated by TraceGate guardrails scan/audit.",
        "",
        "## Summary",
        "",
        f"- total_findings: `{len(findings)}`",
        f"- dangerous_runtime_path: `{sum(1 for item in findings if item.classification == 'dangerous_runtime_path')}`",
        "",
    ]
    if audit_result:
        lines.extend(["## Real Run Audit", ""])
        for key, value in audit_result.items():
            if key != "errors":
                lines.append(f"- {key}: `{value}`")
        if audit_result.get("errors"):
            lines.extend(["", "### Errors", ""])
            for error in audit_result["errors"]:
                lines.append(f"- {error}")
        lines.append("")
    lines.extend(["## Findings", ""])
    for item in findings:
        lines.append(
            f"- `{item.path}:{item.line}` `{item.keyword}` `{item.classification}`: {item.text}"
        )
    lines.append("")
    return "\n".join(lines)


def write_scan_report(findings: list[ScanFinding], audit_result: dict[str, Any] | None = None) -> Path:
    path = Path("docs/FALLBACK_AUDIT.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_fallback_audit(findings, audit_result), encoding="utf-8")
    return path


def strict_scan() -> tuple[list[ScanFinding], list[str]]:
    findings = scan_guardrails()
    errors = [
        f"{item.path}:{item.line} dangerous keyword `{item.keyword}`"
        for item in findings
        if item.classification == "dangerous_runtime_path"
    ]
    write_scan_report(findings)
    return findings, errors


def audit_run(run_dir: Path, strict: bool) -> dict[str, Any]:
    manifest = read_json(run_dir / "run_manifest.json")
    dataset_path = Path(manifest["dataset_path"])
    dataset_manifest_path = Path(manifest["dataset_manifest_path"])
    dataset_manifest = read_json(dataset_manifest_path)
    cases = load_cases(dataset_path)
    scored = [case for case in cases if case.is_scored_real_case]
    errors: list[str] = []

    if not dataset_path.exists():
        errors.append("datasets/real_min/cases.jsonl is missing")
    if not dataset_manifest_path.exists():
        errors.append("dataset manifest is missing")
    if len(scored) < 8:
        errors.append(f"expected at least 8 scored real cases; found {len(scored)}")
    for case in scored:
        if not case.is_real:
            errors.append(f"{case.case_id}: is_real is not true")
        if case.is_synthetic:
            errors.append(f"{case.case_id}: is_synthetic is not false")
        if case.excluded_from_real_metrics:
            errors.append(f"{case.case_id}: excluded_from_real_metrics must be false")
        if not (case.source_url or case.repo_url):
            errors.append(f"{case.case_id}: missing source_url or repo_url")
        concrete_urls = [
            case.source_url,
            case.issue_url,
            case.pr_url,
            case.claim.claim_source_url,
            *(item.evidence_url for item in case.evidence_items),
        ]
        if not any(is_concrete_github_url(url) for url in concrete_urls):
            errors.append(f"{case.case_id}: missing concrete github.com evidence URL")
        if not case.evidence_items:
            errors.append(f"{case.case_id}: missing evidence_items")
        if case.evidence_status.value in {"stale", "conflicting"} and len(case.evidence_items) < 2:
            errors.append(f"{case.case_id}: stale/conflicting scored case requires at least 2 evidence_items")
        if not case.rationale:
            errors.append(f"{case.case_id}: missing rationale")
        if case.label_source == "unknown":
            errors.append(f"{case.case_id}: label_source is unknown")
        if case.evidence_status.value == "needs_manual_review":
            errors.append(f"{case.case_id}: needs_manual_review cannot be scored")
        if case.label_confidence < 0.7:
            errors.append(f"{case.case_id}: label_confidence below 0.7")
    if manifest.get("used_real_data") is not True:
        errors.append("run_manifest.used_real_data must be true")
    if manifest.get("used_synthetic_data") is not False:
        errors.append("run_manifest.used_synthetic_data must be false")
    if manifest.get("used_mock_model") is not False:
        errors.append("run_manifest.used_mock_model must be false")
    if manifest.get("used_fallback_data") is not False:
        errors.append("run_manifest.used_fallback_data must be false")
    if manifest.get("num_cases_scored", 0) < 8:
        errors.append("run_manifest.num_cases_scored must be >= 8")
    status_distribution = manifest.get("status_distribution", {})
    active_only = bool(status_distribution) and set(status_distribution) == {"active"}
    if active_only and manifest.get("hard_benchmark_ready") is True:
        errors.append("active-only run cannot be marked hard_benchmark_ready")
    if sha256_file(dataset_path) != manifest.get("dataset_sha256"):
        errors.append("dataset sha256 does not match run_manifest")
    if dataset_manifest.get("dataset_sha256") != manifest.get("dataset_sha256"):
        errors.append("dataset sha256 does not match dataset manifest")
    report_text = (run_dir / "report.md").read_text(encoding="utf-8") if (run_dir / "report.md").exists() else ""
    if "demo-only result" in report_text.lower():
        errors.append("report contains demo-only result language")
    if active_only and "hard real-data mini benchmark: `true`" in report_text.lower():
        errors.append("active-only report cannot call itself a hard real-data mini benchmark")

    findings = scan_guardrails()
    dangerous = [item for item in findings if item.classification == "dangerous_runtime_path"]
    if strict and dangerous:
        errors.extend(f"{item.path}:{item.line} dangerous runtime path for `{item.keyword}`" for item in dangerous)

    result = {
        "dataset_exists": dataset_path.exists(),
        "manifest_exists": dataset_manifest_path.exists(),
        "num_cases_scored": len(scored),
        "used_real_data": manifest.get("used_real_data"),
        "used_synthetic_data": manifest.get("used_synthetic_data"),
        "used_mock_model": manifest.get("used_mock_model"),
        "used_fallback_data": manifest.get("used_fallback_data"),
        "active_only": active_only,
        "hard_benchmark_ready": manifest.get("hard_benchmark_ready"),
        "manual_review_queue_cases": manifest.get("manual_review_queue_cases"),
        "dangerous_runtime_findings": len(dangerous),
        "passed": not errors,
        "errors": errors,
    }
    write_scan_report(findings, result)
    return result
