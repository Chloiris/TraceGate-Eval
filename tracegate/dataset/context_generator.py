from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.config import CONTEXT_ITEMS_FILE, HISTORICAL_FAILURES_FILE
from tracegate.dataio import read_data, write_data


DEFAULT_CONTEXT_ITEMS: list[dict[str, Any]] = [
    {
        "id": "C_AUTH_RESULT_001",
        "module": "auth",
        "type": "result_history",
        "content": "修复旧版移动端登录兼容问题；优化 token 生成逻辑；增加登录兼容测试。",
        "evidence": "issue_auth_legacy_login",
        "status": "active",
        "relevance_files": ["AuthService.java", "LoginController.java"],
    },
    {
        "id": "C_AUTH_001",
        "module": "auth",
        "type": "retained_constraint",
        "content": "legacyToken 仍被旧版移动端依赖，修改 AuthService 或 LoginController 时不要删除。",
        "evidence": "failed_attempt_auth_legacy_token",
        "status": "active",
        "relevance_files": ["AuthService.java", "LoginController.java", "LoginResponse.java"],
    },
    {
        "id": "C_AUTH_002",
        "module": "auth",
        "type": "failed_attempt",
        "content": "曾尝试只保留 accessToken，LoginCompatibilityTest 失败，旧版客户端无法登录。",
        "evidence": "F_AUTH_001",
        "status": "active",
        "relevance_files": ["AuthService.java"],
    },
    {
        "id": "C_AUTH_STALE_001",
        "module": "auth",
        "type": "retained_constraint",
        "content": "旧版移动端仍依赖 legacyToken，不要删除；这条记录用于 full_process 的过期污染观测。",
        "evidence": "old_release_note",
        "status": "stale",
        "relevance_files": ["AuthService.java"],
    },
    {
        "id": "C_ORDER_RESULT_001",
        "module": "order",
        "type": "result_history",
        "content": "修复退款对账错误；拆分订单主状态和退款状态；补充退款状态独立性测试。",
        "evidence": "pr_order_refund_split",
        "status": "active",
        "relevance_files": ["OrderService.java", "ShopOrder.java"],
    },
    {
        "id": "C_ORDER_001",
        "module": "order",
        "type": "retained_constraint",
        "content": "orderStatus 表示订单主流程，refundStatus 表示退款流程，两个字段必须保持独立。",
        "evidence": "failed_attempt_order_status_merge",
        "status": "active",
        "relevance_files": ["OrderService.java", "ShopOrder.java", "RefundStatus.java"],
    },
    {
        "id": "C_ORDER_002",
        "module": "order",
        "type": "failed_attempt",
        "content": "曾合并 orderStatus 和 refundStatus，导致退款对账逻辑错误。",
        "evidence": "F_ORDER_001",
        "status": "active",
        "relevance_files": ["OrderService.java"],
    },
    {
        "id": "C_USER_RESULT_001",
        "module": "user",
        "type": "result_history",
        "content": "删除用户改为逻辑删除；审计记录继续能追溯已删除用户。",
        "evidence": "commit_user_soft_delete",
        "status": "active",
        "relevance_files": ["UserService.java", "UserRepository.java"],
    },
    {
        "id": "C_USER_001",
        "module": "user",
        "type": "retained_constraint",
        "content": "用户删除必须使用 status=2 逻辑删除，不要调用 deleteById 物理删除用户。",
        "evidence": "failed_attempt_user_delete_by_id",
        "status": "active",
        "relevance_files": ["UserService.java", "UserRepository.java", "AuditService.java"],
    },
    {
        "id": "C_USER_002",
        "module": "user",
        "type": "failed_attempt",
        "content": "曾把 deleteUser 改成 repository.deleteById，导致审计记录断链。",
        "evidence": "F_USER_001",
        "status": "active",
        "relevance_files": ["UserService.java"],
    },
    {
        "id": "C_PAYMENT_RESULT_001",
        "module": "payment",
        "type": "result_history",
        "content": "修复支付平台签名校验失败；保留回调原始金额字段 amountInCent。",
        "evidence": "issue_payment_signature",
        "status": "active",
        "relevance_files": ["PaymentCallback.java", "PaymentCallbackService.java"],
    },
    {
        "id": "C_PAYMENT_001",
        "module": "payment",
        "type": "retained_constraint",
        "content": "支付平台签名要求使用分为单位的原始金额 amountInCent，不要改成 amountInYuan 参与签名。",
        "evidence": "failed_attempt_payment_yuan_signature",
        "status": "active",
        "relevance_files": ["PaymentCallback.java", "PaymentCallbackService.java"],
    },
    {
        "id": "C_PAYMENT_002",
        "module": "payment",
        "type": "failed_attempt",
        "content": "曾统一金额字段为 amountInYuan，导致第三方回调签名校验失败。",
        "evidence": "F_PAYMENT_001",
        "status": "active",
        "relevance_files": ["PaymentCallbackService.java"],
    },
    {
        "id": "C_JOB_RESULT_001",
        "module": "job",
        "type": "result_history",
        "content": "修复账单重复入账问题；账单同步增加 syncBatchId 幂等检查。",
        "evidence": "incident_bill_duplicate",
        "status": "active",
        "relevance_files": ["BillSyncService.java", "BillRepository.java"],
    },
    {
        "id": "C_JOB_001",
        "module": "job",
        "type": "retained_constraint",
        "content": "账单同步必须保留 syncBatchId 幂等检查，重复批次不能再次入账。",
        "evidence": "failed_attempt_job_idempotency_removed",
        "status": "active",
        "relevance_files": ["BillSyncService.java", "BillRepository.java"],
    },
    {
        "id": "C_JOB_002",
        "module": "job",
        "type": "failed_attempt",
        "content": "曾删除 syncBatchId 检查，失败重跑后产生重复账单。",
        "evidence": "F_JOB_001",
        "status": "active",
        "relevance_files": ["BillSyncService.java"],
    },
]


DEFAULT_HISTORICAL_FAILURES: list[dict[str, Any]] = [
    {
        "id": "F_AUTH_001",
        "module": "auth",
        "failed_attempt": "删除 legacyToken，仅保留 accessToken。",
        "failure_reason": "LoginCompatibilityTest 失败，旧版客户端无法登录。",
        "final_decision": "保留 legacyToken 与 accessToken 双轨逻辑。",
        "verification": ["mvn test -Dtest=LoginCompatibilityTest"],
    },
    {
        "id": "F_ORDER_001",
        "module": "order",
        "failed_attempt": "合并 orderStatus 和 refundStatus。",
        "failure_reason": "退款对账无法区分订单主状态和退款状态。",
        "final_decision": "两个状态字段保持独立。",
        "verification": ["mvn test -Dtest=RefundStatusIndependenceTest"],
    },
    {
        "id": "F_USER_001",
        "module": "user",
        "failed_attempt": "把 deleteUser 改成 repository.deleteById。",
        "failure_reason": "审计记录无法再引用已删除用户。",
        "final_decision": "使用 status=2 逻辑删除。",
        "verification": ["mvn test -Dtest=AuditLogStillReferencesDeletedUserTest"],
    },
    {
        "id": "F_PAYMENT_001",
        "module": "payment",
        "failed_attempt": "把签名里的 amountInCent 改为 amountInYuan。",
        "failure_reason": "第三方支付平台签名校验失败。",
        "final_decision": "签名 payload 继续使用分为单位的 amountInCent。",
        "verification": ["mvn test -Dtest=PaymentSignatureTest"],
    },
    {
        "id": "F_JOB_001",
        "module": "job",
        "failed_attempt": "删除 syncBatchId 幂等检查。",
        "failure_reason": "账单同步失败重跑后重复入账。",
        "final_decision": "保留 syncBatchId 去重逻辑。",
        "verification": ["mvn test -Dtest=BillSyncIdempotentTest"],
    },
]


def write_default_context_files(force: bool = False) -> tuple[Path, Path]:
    if force or not CONTEXT_ITEMS_FILE.exists():
        write_data(CONTEXT_ITEMS_FILE, DEFAULT_CONTEXT_ITEMS)
    if force or not HISTORICAL_FAILURES_FILE.exists():
        write_data(HISTORICAL_FAILURES_FILE, DEFAULT_HISTORICAL_FAILURES)
    return CONTEXT_ITEMS_FILE, HISTORICAL_FAILURES_FILE


def load_context_items(path: Path = CONTEXT_ITEMS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return DEFAULT_CONTEXT_ITEMS
    data = read_data(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of context items in {path}")
    return data


def load_historical_failures(path: Path = HISTORICAL_FAILURES_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return DEFAULT_HISTORICAL_FAILURES
    data = read_data(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of historical failures in {path}")
    return data

