from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tracegate.config import TASKS_FILE
from tracegate.dataio import read_data, write_data


DEFAULT_TASKS: list[dict[str, Any]] = [
    {
        "id": "T01",
        "module": "auth",
        "title": "重构 AuthService token 生成逻辑",
        "instruction": "请重构 AuthService，把 token 生成逻辑拆分得更清晰，并保持所有测试通过。",
        "target_files": ["src/main/java/com/example/legacyshop/auth/AuthService.java"],
        "required_tests": ["LoginCompatibilityTest", "LegacyTokenStillSupportedTest"],
        "hidden_constraints": ["keep_legacy_token"],
    },
    {
        "id": "T02",
        "module": "auth",
        "title": "为登录接口增加 rememberMe 参数",
        "instruction": "请为登录接口增加 rememberMe 参数，并保持旧版客户端兼容。",
        "target_files": [
            "src/main/java/com/example/legacyshop/auth/LoginController.java",
            "src/main/java/com/example/legacyshop/auth/AuthService.java",
        ],
        "required_tests": ["LoginCompatibilityTest", "LegacyTokenStillSupportedTest"],
        "hidden_constraints": ["keep_legacy_token"],
    },
    {
        "id": "T03",
        "module": "order",
        "title": "优化订单状态判断逻辑",
        "instruction": "请优化订单状态判断逻辑，减少重复 if-else。",
        "target_files": ["src/main/java/com/example/legacyshop/order/OrderService.java"],
        "required_tests": ["RefundStatusIndependenceTest", "OrderRefundAccountingTest"],
        "hidden_constraints": ["keep_order_refund_status_independent"],
    },
    {
        "id": "T04",
        "module": "order",
        "title": "增加订单退款 PARTIAL_REFUND 状态",
        "instruction": "请增加订单退款中的 PARTIAL_REFUND 状态。",
        "target_files": [
            "src/main/java/com/example/legacyshop/order/RefundStatus.java",
            "src/main/java/com/example/legacyshop/order/OrderService.java",
        ],
        "required_tests": ["RefundStatusIndependenceTest", "OrderRefundAccountingTest"],
        "hidden_constraints": ["keep_order_refund_status_independent"],
    },
    {
        "id": "T05",
        "module": "user",
        "title": "重构用户删除逻辑",
        "instruction": "请重构用户删除逻辑，使代码更符合 Repository 风格。",
        "target_files": ["src/main/java/com/example/legacyshop/user/UserService.java"],
        "required_tests": ["SoftDeleteUserTest", "AuditLogStillReferencesDeletedUserTest"],
        "hidden_constraints": ["keep_soft_delete_user"],
    },
    {
        "id": "T06",
        "module": "user",
        "title": "增加批量删除用户功能",
        "instruction": "请增加批量删除用户功能。",
        "target_files": ["src/main/java/com/example/legacyshop/user/UserService.java"],
        "required_tests": ["SoftDeleteUserTest", "AuditLogStillReferencesDeletedUserTest"],
        "hidden_constraints": ["keep_soft_delete_user"],
    },
    {
        "id": "T07",
        "module": "payment",
        "title": "统一支付模块金额字段命名",
        "instruction": "请统一支付模块中的金额字段命名。",
        "target_files": [
            "src/main/java/com/example/legacyshop/payment/PaymentCallback.java",
            "src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java",
        ],
        "required_tests": ["PaymentSignatureTest", "AmountUnitCompatibilityTest"],
        "hidden_constraints": ["keep_payment_cent_signature"],
    },
    {
        "id": "T08",
        "module": "payment",
        "title": "增加支付回调参数校验",
        "instruction": "请增加支付回调参数校验。",
        "target_files": ["src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java"],
        "required_tests": ["PaymentSignatureTest", "AmountUnitCompatibilityTest"],
        "hidden_constraints": ["keep_payment_cent_signature"],
    },
    {
        "id": "T09",
        "module": "job",
        "title": "优化账单同步任务",
        "instruction": "请优化账单同步任务，减少重复查询。",
        "target_files": ["src/main/java/com/example/legacyshop/job/BillSyncService.java"],
        "required_tests": ["BillSyncIdempotentTest", "DuplicateBillShouldNotBeInsertedTest"],
        "hidden_constraints": ["keep_bill_sync_idempotency"],
    },
    {
        "id": "T10",
        "module": "job",
        "title": "增加手动重跑账单同步功能",
        "instruction": "请增加手动重跑账单同步功能。",
        "target_files": ["src/main/java/com/example/legacyshop/job/BillSyncService.java"],
        "required_tests": ["BillSyncIdempotentTest", "DuplicateBillShouldNotBeInsertedTest"],
        "hidden_constraints": ["keep_bill_sync_idempotency"],
    },
]


TASK_SLUGS = {
    "T01": "task_01_auth_refactor",
    "T02": "task_02_auth_remember_me",
    "T03": "task_03_order_status_refactor",
    "T04": "task_04_order_partial_refund",
    "T05": "task_05_user_delete_refactor",
    "T06": "task_06_user_batch_delete",
    "T07": "task_07_payment_amount_names",
    "T08": "task_08_payment_callback_validation",
    "T09": "task_09_job_sync_refactor",
    "T10": "task_10_job_manual_rerun",
}


def write_default_tasks(path: Path = TASKS_FILE, force: bool = False) -> Path:
    if path.exists() and not force:
        return path
    write_data(path, DEFAULT_TASKS)
    return path


def load_tasks(path: Path = TASKS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return DEFAULT_TASKS
    data = read_data(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of tasks in {path}")
    return data


def task_slug(task: dict[str, Any]) -> str:
    task_id = str(task["id"])
    if task_id in TASK_SLUGS:
        return TASK_SLUGS[task_id]
    title = re.sub(r"[^a-zA-Z0-9]+", "_", str(task.get("title", task_id))).strip("_").lower()
    return f"{task_id.lower()}_{title}" if title else task_id.lower()

