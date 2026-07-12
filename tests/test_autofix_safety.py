from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from tracegate.autofix.errors import AutofixError
from tracegate.autofix.patch_safety import PatchLimits, PatchSafetyValidator, compute_patch_hash
from tracegate.autofix.resolution import ValidationOutcome, decide_resolution
from tracegate.autofix.schemas import (
    FixPermissionMode,
    FixResolution,
    FixSessionStatus,
    ReReviewAssessment,
    ValidationCommand,
    ValidationStatus,
)
from tracegate.autofix.state_machine import allowed_actions, ensure_transition
from tracegate.autofix.validation import ValidationCommandResolver, ValidationExecutor
from tracegate.autofix.workspace import FixWorkspaceManager
from tracegate.repository import RepositoryBoundary


def initialize_repository(root: Path) -> str:
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "service.py").write_text(
        "def total(value: int) -> int:\n    return value * 2\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "tracegate@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "TraceGate Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def service_patch() -> str:
    return """--- a/src/service.py
+++ b/src/service.py
@@ -1,2 +1,2 @@
 def total(value: int) -> int:
-    return value * 2
+    return value + 2
"""


def test_state_machine_rejects_skips_and_returns_server_actions() -> None:
    ensure_transition(FixSessionStatus.CREATED, FixSessionStatus.CHECKING_ELIGIBILITY)
    with pytest.raises(AutofixError) as caught:
        ensure_transition(FixSessionStatus.CREATED, FixSessionStatus.APPLYING_PATCH)
    assert caught.value.code == "fix_invalid_transition"
    assert allowed_actions(
        FixSessionStatus.PLAN_READY,
        FixPermissionMode.APPLY_IN_ISOLATED_WORKSPACE,
        has_workspace=True,
        has_patch=False,
        has_result=False,
    ) == ["generate", "cancel", "delete_workspace"]


def test_patch_hash_is_normalized_and_patch_is_statically_checked(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    head = initialize_repository(repository)
    validator = PatchSafetyValidator(RepositoryBoundary(repository))
    inspection = validator.validate(
        service_patch().replace("\n", "\r\n"),
        expected_head_sha=head,
        expected_files=["src/service.py"],
    )
    assert inspection.patch_hash == compute_patch_hash(service_patch())
    assert inspection.changed_files == ["src/service.py"]
    assert inspection.changed_lines == 2
    assert inspection.additions == 1
    assert inspection.deletions == 1


@pytest.mark.parametrize(
    "patch",
    [
        "--- a/.env\n+++ b/.env\n@@ -0,0 +1 @@\n+SECRET=x\n",
        "--- a/../escape.py\n+++ b/../escape.py\n@@ -0,0 +1 @@\n+x=1\n",
        "--- /dev/null\n+++ /tmp/absolute.py\n@@ -0,0 +1 @@\n+x=1\n",
        "GIT binary patch\nliteral 1\nA\n",
    ],
)
def test_patch_safety_rejects_credentials_traversal_absolute_and_binary(
    tmp_path: Path,
    patch: str,
) -> None:
    repository = tmp_path / "repository"
    head = initialize_repository(repository)
    with pytest.raises(AutofixError) as caught:
        PatchSafetyValidator(RepositoryBoundary(repository)).validate(
            patch,
            expected_head_sha=head,
        )
    assert caught.value.code == "fix_patch_unsafe"


def test_patch_safety_rejects_symlink_and_size_limits(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    head = initialize_repository(repository)
    outside = tmp_path / "outside.py"
    outside.write_text("safe = False\n", encoding="utf-8")
    (repository / "linked.py").symlink_to(outside)
    symlink_patch = """--- a/linked.py
+++ b/linked.py
@@ -1 +1 @@
-safe = False
+safe = True
"""
    with pytest.raises(AutofixError, match="symbolic link"):
        PatchSafetyValidator(RepositoryBoundary(repository)).validate(
            symlink_patch,
            expected_head_sha=head,
            require_clean=False,
        )
    with pytest.raises(AutofixError, match="limit"):
        PatchSafetyValidator(
            RepositoryBoundary(repository),
            PatchLimits(max_files=8, max_changed_lines=1, max_changed_lines_per_file=1),
        ).validate(service_patch(), expected_head_sha=head, require_clean=False)


def test_isolated_worktree_apply_rollback_and_cleanup_leave_source_unchanged(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    head = initialize_repository(repository)
    source_file = repository / "src" / "service.py"
    source_file.write_text(source_file.read_text() + "# user local change\n", encoding="utf-8")
    source_before = source_file.read_bytes()

    manager = FixWorkspaceManager(tmp_path / "managed")
    workspace = manager.create(
        session_id="session-123",
        repository_id="repository-123",
        source_root=repository,
        head_sha=head,
    )
    validator = PatchSafetyValidator(workspace.boundary)
    validator.validate(service_patch(), expected_head_sha=head)
    validator.apply(service_patch(), expected_head_sha=head)
    assert "return value + 2" in (workspace.worktree_root / "src" / "service.py").read_text()
    assert source_file.read_bytes() == source_before
    assert "return value + 2" in manager.diff(workspace, ["src/service.py"])

    manager.rollback(workspace)
    assert "return value * 2" in (workspace.worktree_root / "src" / "service.py").read_text()
    assert source_file.read_bytes() == source_before
    manager.delete(workspace)
    assert not workspace.session_root.exists()
    assert source_file.read_bytes() == source_before


@pytest.mark.asyncio
async def test_validation_resolver_and_executor_use_controlled_argv(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    initialize_repository(repository)
    boundary = RepositoryBoundary(repository)
    plan = ValidationCommandResolver().resolve(boundary)
    assert [command.argv for command in plan.commands] == [["git", "diff", "--check"]]
    assert plan.notes == ["NO_TEST_COMMAND_AVAILABLE"]

    result = await ValidationExecutor(boundary, safe_home=tmp_path / "home").execute(
        plan.commands[0]
    )
    assert result.status == ValidationStatus.PASSED
    assert result.return_code == 0

    forbidden = ValidationCommand(
        argv=["python", "-m", "pytest", ";", "rm"],
        command_purpose="unsafe",
        required=True,
        timeout=10,
        expected_result="never",
        source="test",
    )
    with pytest.raises(AutofixError) as caught:
        await ValidationExecutor(boundary, safe_home=tmp_path / "home").execute(forbidden)
    assert caught.value.code == "fix_validation_forbidden"


@pytest.mark.asyncio
async def test_validation_cancellation_is_explicit(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    initialize_repository(repository)
    (repository / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (repository / "test_wait.py").write_text(
        "import time\n\ndef test_wait():\n    time.sleep(20)\n",
        encoding="utf-8",
    )
    command = ValidationCommand(
        argv=["python", "-m", "pytest", "-q", "test_wait.py"],
        command_purpose="cancellation test",
        required=True,
        timeout=30,
        expected_result="cancelled",
        source="test",
    )
    cancellation = asyncio.Event()
    task = asyncio.create_task(
        ValidationExecutor(
            RepositoryBoundary(repository),
            safe_home=tmp_path / "home",
        ).execute(command, cancellation_event=cancellation)
    )
    await asyncio.sleep(0.2)
    cancellation.set()
    result = await task
    assert result.status == ValidationStatus.CANCELLED


def test_resolution_requires_apply_tests_reindex_and_re_review() -> None:
    review = ReReviewAssessment(
        original_finding_supported=False,
        residual_findings=[],
        residual_risks=[],
        new_high_risk=False,
        summary="The original behavior is no longer present.",
        confidence=0.9,
    )
    assert decide_resolution(
        patch_applied=True,
        validation_outcomes=[ValidationOutcome(True, ValidationStatus.PASSED)],
        test_command_available=True,
        reindex_succeeded=True,
        re_review=review,
    ) == FixResolution.RESOLVED
    assert decide_resolution(
        patch_applied=True,
        validation_outcomes=[ValidationOutcome(True, ValidationStatus.FAILED)],
        test_command_available=True,
        reindex_succeeded=True,
        re_review=review,
    ) == FixResolution.VERIFICATION_FAILED
    assert decide_resolution(
        patch_applied=True,
        validation_outcomes=[ValidationOutcome(True, ValidationStatus.PASSED)],
        test_command_available=False,
        reindex_succeeded=True,
        re_review=review,
    ) == FixResolution.NEEDS_HUMAN_REVIEW
