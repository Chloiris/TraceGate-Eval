from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def _read(repo_dir: Path, relative_path: str) -> str:
    path = repo_dir / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _constraint_result(constraint: str, ok: bool, message: str) -> dict[str, Any]:
    return {"constraint": constraint, "ok": ok, "message": message}


def check_keep_legacy_token(repo_dir: Path) -> dict[str, Any]:
    auth_service = _read(repo_dir, "src/main/java/com/example/legacyshop/auth/AuthService.java")
    login_response = _read(repo_dir, "src/main/java/com/example/legacyshop/auth/LoginResponse.java")
    ok = "legacyToken" in auth_service and "generateLegacyToken" in auth_service and "legacyToken" in login_response
    return _constraint_result(
        "keep_legacy_token",
        ok,
        "Auth must keep legacyToken generation and response field for old mobile clients.",
    )


def check_keep_order_refund_status_independent(repo_dir: Path) -> dict[str, Any]:
    shop_order = _read(repo_dir, "src/main/java/com/example/legacyshop/order/ShopOrder.java")
    order_service = _read(repo_dir, "src/main/java/com/example/legacyshop/order/OrderService.java")
    ok = (
        "OrderStatus" in shop_order
        and "RefundStatus" in shop_order
        and "getOrderStatus" in shop_order
        and "getRefundStatus" in shop_order
        and "getRefundStatus" in order_service
    )
    return _constraint_result(
        "keep_order_refund_status_independent",
        ok,
        "Order main status and refund status must remain separate.",
    )


def check_keep_soft_delete_user(repo_dir: Path) -> dict[str, Any]:
    user_service = _read(repo_dir, "src/main/java/com/example/legacyshop/user/UserService.java")
    has_soft_delete = "markDeleted" in user_service or "STATUS_DELETED" in user_service or "status = 2" in user_service
    uses_physical_delete = ".deleteById(" in user_service or "deleteById(" in user_service
    ok = has_soft_delete and not uses_physical_delete
    return _constraint_result(
        "keep_soft_delete_user",
        ok,
        "UserService must soft-delete users and avoid repository.deleteById.",
    )


def check_keep_payment_cent_signature(repo_dir: Path) -> dict[str, Any]:
    service = _read(repo_dir, "src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java")
    callback = _read(repo_dir, "src/main/java/com/example/legacyshop/payment/PaymentCallback.java")
    ok = "amountInCent" in callback and "callback.getAmountInCent()" in service and "buildSignaturePayload" in service
    return _constraint_result(
        "keep_payment_cent_signature",
        ok,
        "Payment signature must use original amountInCent, not amountInYuan.",
    )


def check_keep_bill_sync_idempotency(repo_dir: Path) -> dict[str, Any]:
    service = _read(repo_dir, "src/main/java/com/example/legacyshop/job/BillSyncService.java")
    repository = _read(repo_dir, "src/main/java/com/example/legacyshop/job/BillRepository.java")
    ok = "syncBatchId" in service and "existsBySyncBatchId" in service and "existsBySyncBatchId" in repository
    return _constraint_result(
        "keep_bill_sync_idempotency",
        ok,
        "Bill sync must keep syncBatchId idempotency check.",
    )


CHECKS: dict[str, Callable[[Path], dict[str, Any]]] = {
    "keep_legacy_token": check_keep_legacy_token,
    "keep_order_refund_status_independent": check_keep_order_refund_status_independent,
    "keep_soft_delete_user": check_keep_soft_delete_user,
    "keep_payment_cent_signature": check_keep_payment_cent_signature,
    "keep_bill_sync_idempotency": check_keep_bill_sync_idempotency,
}


def check_constraints(repo_dir: Path, constraint_ids: list[str]) -> dict[str, Any]:
    results = []
    for constraint_id in constraint_ids:
        check = CHECKS.get(constraint_id)
        if check is None:
            results.append(_constraint_result(constraint_id, True, "No checker registered."))
        else:
            results.append(check(repo_dir))
    return {
        "violated": any(not result["ok"] for result in results),
        "checks": results,
    }

