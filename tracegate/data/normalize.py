from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.core.models import Claim, EvalCase, EvidenceItem, EvidenceStatus, ExpectedDecision
from tracegate.core.serialization import read_jsonl, stable_hash_text, write_cases
from tracegate.data.sources.base import RealDataError


def excerpt(text: str | None, max_chars: int = 600) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def normalize_record(record: dict[str, Any]) -> EvalCase:
    repo = str(record["repo"])
    pr = record["pull_request"]
    files = record.get("files", [])
    number = int(pr["number"])
    html_url = str(pr["html_url"])
    repo_url = f"https://github.com/{repo}"
    files_changed = [str(item.get("filename")) for item in files if item.get("filename")]
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")
    problem_statement = excerpt(f"{title}\n\n{body}", max_chars=1200)
    merge_commit_sha = pr.get("merge_commit_sha")
    base_commit = (pr.get("base") or {}).get("sha")
    head_commit = (pr.get("head") or {}).get("sha")
    evidence_text = excerpt(
        f"Merged Pull Request #{number}: {title}. Files changed: {', '.join(files_changed[:8])}.",
        max_chars=700,
    )
    evidence_url = html_url
    evidence_hash = stable_hash_text(f"{repo}#{number}|{evidence_text}|{evidence_url}|{merge_commit_sha}")
    claim_text = (
        f"Merged Pull Request #{number} in {repo} captured a historical repository change: {title}. "
        "Future changes touching the same files should preserve or explicitly re-verify that behavior."
    )
    rationale = (
        "This active smoke case is scored because the merged public GitHub Pull Request has concrete PR URL "
        "provenance, changed-file provenance, and a merge commit. It is active smoke data, not a hard stale, "
        "unknown, or conflicting case."
    )
    case_id = f"github_api:{repo.replace('/', '__')}:pull:{number}"
    evidence_status = EvidenceStatus.ACTIVE
    exclusion_reason = None
    excluded = False
    confidence = 0.78
    if not merge_commit_sha or not files_changed or not html_url:
        evidence_status = EvidenceStatus.NEEDS_MANUAL_REVIEW
        excluded = True
        confidence = 0.0
        exclusion_reason = "missing merge commit, file list, or PR URL provenance"

    return EvalCase(
        case_id=case_id,
        source_dataset="github_api",
        source_url=html_url,
        repo=repo,
        repo_url=repo_url,
        issue_url=html_url.replace("/pull/", "/issues/"),
        pr_url=html_url,
        base_commit=base_commit,
        head_commit=head_commit,
        commit_sha=merge_commit_sha,
        created_at=pr.get("created_at"),
        files_changed=files_changed,
        diff_summary=f"Merged PR changed {len(files_changed)} file(s): {', '.join(files_changed[:8])}",
        problem_statement=problem_statement,
        claim=Claim(
            claim_id=f"{case_id}:claim",
            claim_text=claim_text,
            validity_condition="Applies when future PRs touch files changed by this merged Pull Request.",
            claim_source="pr",
            claim_source_url=html_url,
        ),
        evidence_items=[
            EvidenceItem(
                evidence_id=f"{case_id}:evidence:pr",
                evidence_type="pr",
                evidence_text_excerpt=evidence_text,
                evidence_url=evidence_url,
                file_path=None,
                commit_sha=merge_commit_sha,
                timestamp=pr.get("merged_at"),
                supports_or_contradicts="supports",
                provenance_hash=evidence_hash,
            )
        ],
        evidence_status=evidence_status,
        expected_decision=ExpectedDecision.PRESERVE if not excluded else ExpectedDecision.NEEDS_MANUAL_REVIEW,
        label_source="heuristic_verified" if not excluded else "unknown",
        label_confidence=confidence,
        rationale=rationale if not excluded else "Excluded because required merge/file/URL provenance is incomplete.",
        is_real=True,
        is_synthetic=False,
        excluded_from_real_metrics=excluded,
        exclusion_reason=exclusion_reason,
    )


def normalize_raw_records(input_dir: Path, output_path: Path) -> list[EvalCase]:
    raw_path = input_dir / "github_prs.jsonl"
    rows = read_jsonl(raw_path)
    if not rows:
        raise RealDataError(f"no raw records found at {raw_path}; no fallback data was created")
    cases = [normalize_record(row) for row in rows]
    write_cases(output_path, cases)
    return cases
