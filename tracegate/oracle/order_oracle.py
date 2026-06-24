from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle.base_oracle import build_result, read_many


def evaluate(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    code = read_many(
        repo_dir,
        [
            "src/main/java/com/example/legacyshop/order/ShopOrder.java",
            "src/main/java/com/example/legacyshop/order/OrderService.java",
            "src/main/java/com/example/legacyshop/order/RefundStatus.java",
        ],
    )
    has_order = "OrderStatus" in code or "orderStatus" in code
    has_refund = "RefundStatus" in code or "refundStatus" in code
    preserved = has_order and has_refund and ("getRefundStatus" in code or "refundStatus" in code)
    optimized = not preserved
    return build_result(task, preserved, optimized, ["dual statuses" if preserved else "merged/no separate refund status"])

