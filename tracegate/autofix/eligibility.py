from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from tracegate.repository import RepositoryBoundary, RepositoryPathError
from tracegate.studio.models import (
    AgentRun,
    EvidenceRecord,
    Finding,
    IndexVersion,
    PullRequest,
    Repository,
)

from .errors import AutofixError
from .schemas import FixEligibilityResult, FixEligibilityStatus


@dataclass(frozen=True)
class FixSourceContext:
    finding: Finding
    source_run: AgentRun
    pull_request: PullRequest
    repository: Repository
    index_version: IndexVersion
    evidence: tuple[EvidenceRecord, ...]


def _git_environment() -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in ("LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP")
        if name in os.environ
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


class FixEligibilityService:
    def __init__(self, *, confidence_threshold: float = 0.75) -> None:
        self.confidence_threshold = confidence_threshold

    def load_context(self, session: Session, finding_id: str) -> FixSourceContext:
        finding = session.get(Finding, finding_id)
        if finding is None:
            raise AutofixError("fix_finding_not_found", "Finding was not found")
        source_run = session.get(AgentRun, finding.agent_run_id)
        if source_run is None or not source_run.pull_request_id:
            raise AutofixError("fix_eligibility_blocked", "Finding has no Pull Request review run")
        pull_request = session.get(PullRequest, source_run.pull_request_id)
        repository = session.get(Repository, source_run.repository_id)
        if pull_request is None or repository is None:
            raise AutofixError("fix_eligibility_blocked", "Finding source is incomplete")
        if pull_request.repository_id != repository.id:
            raise AutofixError("fix_eligibility_blocked", "Finding repository binding is inconsistent")
        if not source_run.index_version:
            raise AutofixError("fix_index_stale", "Finding review has no bound Index Version")
        index_version = session.get(IndexVersion, source_run.index_version)
        if index_version is None or index_version.repository_id != repository.id:
            raise AutofixError("fix_index_stale", "Finding Index Version no longer exists")
        evidence_rows = tuple(
            session.scalars(
                select(EvidenceRecord).where(
                    EvidenceRecord.id.in_(finding.evidence_ids_json or ["__none__"])
                )
            )
        )
        return FixSourceContext(
            finding,
            source_run,
            pull_request,
            repository,
            index_version,
            evidence_rows,
        )

    def evaluate(self, session: Session, finding_id: str) -> FixEligibilityResult:
        try:
            context = self.load_context(session, finding_id)
        except AutofixError as exc:
            if exc.code in {"fix_index_stale", "fix_head_stale"}:
                status = FixEligibilityStatus.STALE_HEAD
            elif exc.code == "fix_finding_not_found":
                status = FixEligibilityStatus.BLOCKED
            else:
                status = FixEligibilityStatus.BLOCKED
            return FixEligibilityResult(status=status, reasons=[str(exc)], force_allowed=False)

        finding = context.finding
        run = context.source_run
        pull_request = context.pull_request
        repository = context.repository
        index_version = context.index_version

        stale_reasons: list[str] = []
        if not pull_request.head_sha:
            stale_reasons.append("Pull Request has no current Head SHA")
        if run.head_sha != pull_request.head_sha:
            stale_reasons.append("Review run Head SHA differs from the current Pull Request")
        if finding.commit_sha and finding.commit_sha != pull_request.head_sha:
            stale_reasons.append("Finding commit differs from the current Pull Request Head")
        if index_version.commit_sha != pull_request.head_sha:
            stale_reasons.append("Finding Index Version is not bound to the current Pull Request Head")
        if repository.current_index_version != index_version.id:
            stale_reasons.append("Repository current Index Version differs from the Finding review")
        if stale_reasons:
            return FixEligibilityResult(
                status=FixEligibilityStatus.STALE_HEAD,
                reasons=stale_reasons,
                force_allowed=False,
            )

        if not finding.file_path or finding.line_start is None or finding.line_end is None:
            return FixEligibilityResult(
                status=FixEligibilityStatus.INSUFFICIENT_EVIDENCE,
                reasons=["Finding requires a real file path and line range"],
                force_allowed=False,
            )
        if finding.line_start < 1 or finding.line_end < finding.line_start:
            return FixEligibilityResult(
                status=FixEligibilityStatus.INSUFFICIENT_EVIDENCE,
                reasons=["Finding line range is invalid"],
                force_allowed=False,
            )
        if not finding.evidence_ids_json or len(context.evidence) != len(set(finding.evidence_ids_json)):
            return FixEligibilityResult(
                status=FixEligibilityStatus.INSUFFICIENT_EVIDENCE,
                reasons=["Finding does not have complete persisted Evidence"],
                force_allowed=False,
            )
        if any(row.agent_run_id != run.id for row in context.evidence):
            return FixEligibilityResult(
                status=FixEligibilityStatus.INSUFFICIENT_EVIDENCE,
                reasons=["Finding Evidence is not bound to its review run"],
                force_allowed=False,
            )
        if not repository.local_path:
            return FixEligibilityResult(
                status=FixEligibilityStatus.BLOCKED,
                reasons=["Repository has no enrolled local Git workspace"],
                force_allowed=False,
            )

        try:
            boundary = RepositoryBoundary(Path(repository.local_path))
            boundary.resolve(finding.file_path, allow_missing=True)
        except (OSError, RepositoryPathError, ValueError):
            return FixEligibilityResult(
                status=FixEligibilityStatus.SENSITIVE_PATH,
                reasons=["Finding path is unavailable or denied by RepositoryBoundary"],
                force_allowed=False,
            )

        blob = self._read_blob(boundary.root, pull_request.head_sha or "", finding.file_path)
        if blob is None:
            return FixEligibilityResult(
                status=FixEligibilityStatus.UNSUPPORTED_FILE,
                reasons=["Finding file does not exist at the current Pull Request Head"],
                force_allowed=False,
            )
        if b"\x00" in blob[:4096]:
            return FixEligibilityResult(
                status=FixEligibilityStatus.UNSUPPORTED_FILE,
                reasons=["Binary files are not eligible for Autofix"],
                force_allowed=False,
            )
        line_count = len(blob.decode("utf-8", errors="replace").splitlines())
        if finding.line_end > max(1, line_count):
            return FixEligibilityResult(
                status=FixEligibilityStatus.INSUFFICIENT_EVIDENCE,
                reasons=["Finding line range exceeds the current file"],
                force_allowed=False,
            )

        warnings: list[str] = []
        if finding.verifier_status != "verified":
            warnings.append("Finding verifier status requires human confirmation")
        if finding.confidence < self.confidence_threshold:
            warnings.append(
                f"Finding confidence {finding.confidence:.2f} is below {self.confidence_threshold:.2f}"
            )
        if finding.severity in {"info", "low"}:
            warnings.append("Low-severity Finding requires an explicit risk decision")
        if warnings:
            return FixEligibilityResult(
                status=FixEligibilityStatus.NEEDS_CONFIRMATION,
                reasons=["Finding is structurally eligible but not fully verified"],
                warnings=warnings,
                force_allowed=True,
            )
        return FixEligibilityResult(
            status=FixEligibilityStatus.ELIGIBLE,
            reasons=["Finding, Evidence, Head SHA and Index Version are current"],
            force_allowed=False,
        )

    @staticmethod
    def _read_blob(root: Path, head_sha: str, relative_path: str) -> bytes | None:
        if not head_sha:
            return None
        try:
            process = subprocess.run(
                ["git", "-C", str(root), "show", f"{head_sha}:{relative_path}"],
                capture_output=True,
                timeout=30,
                env=_git_environment(),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if process.returncode != 0 or len(process.stdout) > 2 * 1024 * 1024:
            return None
        return process.stdout
