from __future__ import annotations

from .errors import AutofixError
from .schemas import FixPermissionMode, FixSessionStatus


TERMINAL_STATUSES = {
    FixSessionStatus.CANCELLED,
    FixSessionStatus.ROLLED_BACK,
}


ALLOWED_TRANSITIONS: dict[FixSessionStatus, frozenset[FixSessionStatus]] = {
    FixSessionStatus.CREATED: frozenset(
        {FixSessionStatus.CHECKING_ELIGIBILITY, FixSessionStatus.CANCELLED}
    ),
    FixSessionStatus.CHECKING_ELIGIBILITY: frozenset(
        {
            FixSessionStatus.ELIGIBLE,
            FixSessionStatus.FAILED,
            FixSessionStatus.STALE,
            FixSessionStatus.CANCELLED,
        }
    ),
    FixSessionStatus.ELIGIBLE: frozenset(
        {FixSessionStatus.PLANNING, FixSessionStatus.CANCELLED, FixSessionStatus.STALE}
    ),
    FixSessionStatus.PLANNING: frozenset(
        {
            FixSessionStatus.PLAN_READY,
            FixSessionStatus.FAILED,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.PLAN_READY: frozenset(
        {
            FixSessionStatus.GENERATING_PATCH,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.GENERATING_PATCH: frozenset(
        {
            FixSessionStatus.VALIDATING_PATCH,
            FixSessionStatus.FAILED,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.VALIDATING_PATCH: frozenset(
        {
            FixSessionStatus.AWAITING_USER_CONFIRMATION,
            FixSessionStatus.FAILED,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.AWAITING_USER_CONFIRMATION: frozenset(
        {
            FixSessionStatus.APPLYING_PATCH,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.APPLYING_PATCH: frozenset(
        {
            FixSessionStatus.PATCH_APPLIED,
            FixSessionStatus.FAILED,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.PATCH_APPLIED: frozenset(
        {
            FixSessionStatus.RUNNING_VALIDATION,
            FixSessionStatus.ROLLED_BACK,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.RUNNING_VALIDATION: frozenset(
        {
            FixSessionStatus.VALIDATION_COMPLETE,
            FixSessionStatus.FAILED,
            FixSessionStatus.CANCELLED,
            FixSessionStatus.ROLLED_BACK,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.VALIDATION_COMPLETE: frozenset(
        {
            FixSessionStatus.REINDEXING_CHANGES,
            FixSessionStatus.ROLLED_BACK,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.REINDEXING_CHANGES: frozenset(
        {
            FixSessionStatus.RE_REVIEWING,
            FixSessionStatus.FAILED,
            FixSessionStatus.ROLLED_BACK,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.RE_REVIEWING: frozenset(
        {
            FixSessionStatus.FINALIZING,
            FixSessionStatus.FAILED,
            FixSessionStatus.ROLLED_BACK,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.FINALIZING: frozenset(
        {
            FixSessionStatus.COMPLETED,
            FixSessionStatus.FAILED,
            FixSessionStatus.ROLLED_BACK,
            FixSessionStatus.STALE,
        }
    ),
    FixSessionStatus.COMPLETED: frozenset({FixSessionStatus.ROLLED_BACK}),
    FixSessionStatus.FAILED: frozenset({FixSessionStatus.ROLLED_BACK}),
    FixSessionStatus.CANCELLED: frozenset({FixSessionStatus.ROLLED_BACK}),
    FixSessionStatus.STALE: frozenset({FixSessionStatus.ROLLED_BACK}),
    FixSessionStatus.ROLLED_BACK: frozenset(),
}


def ensure_transition(current: str | FixSessionStatus, target: str | FixSessionStatus) -> None:
    try:
        current_status = FixSessionStatus(current)
        target_status = FixSessionStatus(target)
    except ValueError as exc:
        raise AutofixError("fix_invalid_transition", "Fix Session status is invalid") from exc
    if target_status not in ALLOWED_TRANSITIONS[current_status]:
        raise AutofixError(
            "fix_invalid_transition",
            f"Cannot transition Fix Session from {current_status.value} to {target_status.value}",
        )


def allowed_actions(
    status: str | FixSessionStatus,
    permission_mode: str | FixPermissionMode,
    *,
    has_workspace: bool,
    has_patch: bool,
    has_result: bool,
) -> list[str]:
    current = FixSessionStatus(status)
    permission = FixPermissionMode(permission_mode)
    actions: list[str] = []
    if current == FixSessionStatus.ELIGIBLE:
        actions.append("plan")
    elif current == FixSessionStatus.PLAN_READY:
        actions.append("generate")
    elif current == FixSessionStatus.AWAITING_USER_CONFIRMATION:
        if permission == FixPermissionMode.APPLY_IN_ISOLATED_WORKSPACE:
            actions.extend(["confirm", "apply"])
        actions.append("export_patch")
    elif current == FixSessionStatus.PATCH_APPLIED:
        actions.extend(["validate", "export_patch", "rollback"])
    elif current == FixSessionStatus.VALIDATION_COMPLETE:
        actions.extend(["re_review", "export_patch", "rollback"])
    elif current == FixSessionStatus.COMPLETED:
        actions.extend(["export_patch", "export_report"])
        if has_workspace:
            actions.append("rollback")
    elif current in {FixSessionStatus.FAILED, FixSessionStatus.CANCELLED, FixSessionStatus.STALE}:
        if has_workspace and has_patch:
            actions.append("rollback")
        if has_patch:
            actions.append("export_patch")
        if has_result:
            actions.append("export_report")
    if current not in {
        FixSessionStatus.COMPLETED,
        FixSessionStatus.FAILED,
        FixSessionStatus.CANCELLED,
        FixSessionStatus.ROLLED_BACK,
        FixSessionStatus.STALE,
    }:
        actions.append("cancel")
    if has_workspace and current in {
        FixSessionStatus.FAILED,
        FixSessionStatus.CANCELLED,
        FixSessionStatus.ROLLED_BACK,
        FixSessionStatus.STALE,
    }:
        actions.append("delete_workspace")
    return list(dict.fromkeys(actions))
