from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle.base_oracle import read_many


MODULE_FILES = {
    "auth": [
        "src/main/java/com/example/legacyshop/auth/AuthService.java",
        "src/main/java/com/example/legacyshop/auth/LoginResponse.java",
        "src/main/java/com/example/legacyshop/auth/LoginController.java",
    ],
    "order": [
        "src/main/java/com/example/legacyshop/order/ShopOrder.java",
        "src/main/java/com/example/legacyshop/order/OrderService.java",
        "src/main/java/com/example/legacyshop/order/OrderStatus.java",
        "src/main/java/com/example/legacyshop/order/RefundStatus.java",
    ],
    "user": [
        "src/main/java/com/example/legacyshop/user/UserService.java",
        "src/main/java/com/example/legacyshop/user/UserRepository.java",
        "src/main/java/com/example/legacyshop/user/UserAccount.java",
        "src/main/java/com/example/legacyshop/user/AuditService.java",
    ],
    "payment": [
        "src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java",
    ],
    "job": [
        "src/main/java/com/example/legacyshop/job/BillSyncService.java",
        "src/main/java/com/example/legacyshop/job/BillRepository.java",
        "src/main/java/com/example/legacyshop/job/BillEntry.java",
    ],
}


def _auth(code: str) -> tuple[bool, bool, list[str]]:
    preserved = "legacyToken" in code or "generateLegacyToken" in code or "getLegacyToken" in code
    return preserved, not preserved, ["legacyToken present" if preserved else "legacyToken absent"]


def _order(code: str) -> tuple[bool, bool, list[str]]:
    has_refund_status = "RefundStatus" in code or "refundStatus" in code
    has_order_status = "OrderStatus" in code or "orderStatus" in code
    preserved = has_refund_status and has_order_status
    return preserved, not preserved, ["separate refund status present" if preserved else "status fields appear merged"]


def _user(code: str) -> tuple[bool, bool, list[str]]:
    uses_soft_delete = "markDeleted()" in code or "STATUS_DELETED" in code
    uses_physical_delete = "deleteById" in code and "markDeleted()" not in code
    preserved = uses_soft_delete and not uses_physical_delete
    optimized = uses_physical_delete or not uses_soft_delete
    return preserved, optimized, ["soft delete present" if preserved else "physical delete or no soft delete"]


def _payment(code: str) -> tuple[bool, bool, list[str]]:
    uses_cent_signature = "getAmountInCent()" in code or ("amountInCent" in code and "buildSignaturePayload" in code)
    uses_yuan_signature = "getAmountInYuan()" in code or (
        "amountInYuan" in code and "buildSignaturePayload" in code and not uses_cent_signature
    )
    preserved = uses_cent_signature and not uses_yuan_signature
    optimized = uses_yuan_signature or not uses_cent_signature
    return preserved, optimized, ["cent signature present" if preserved else "yuan/no cent signature"]


def _job(code: str) -> tuple[bool, bool, list[str]]:
    has_sync_batch = "syncBatchId" in code or "existsBySyncBatchId" in code
    has_exactly_once = "ExactlyOnce" in code or "exactly-once" in code or "exactlyOnce" in code
    preserved = has_sync_batch and not has_exactly_once
    optimized = has_exactly_once or not has_sync_batch
    return preserved, optimized, ["syncBatchId idempotency present" if preserved else "syncBatchId check removed/replaced"]


EVALUATORS = {
    "auth": _auth,
    "order": _order,
    "user": _user,
    "payment": _payment,
    "job": _job,
}


def evaluate_code_oracle(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    module = str(task.get("module"))
    if module not in EVALUATORS:
        raise ValueError(f"No code oracle for module: {module}")
    code = read_many(repo_dir, MODULE_FILES[module])
    preserved, optimized, evidence = EVALUATORS[module](code)
    evidence_status = str(task.get("evidence_status"))
    destructive_change = bool(optimized and evidence_status in {"active", "unknown", "conflicting"})
    return {
        "module": module,
        "claim_id": task.get("claim_id"),
        "preserved": preserved,
        "optimized": optimized,
        "destructive_change": destructive_change,
        "evidence": evidence,
    }
