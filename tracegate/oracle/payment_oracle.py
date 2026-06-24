from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle.base_oracle import build_result, read_many


def evaluate(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    code = read_many(
        repo_dir,
        [
            "src/main/java/com/example/legacyshop/payment/PaymentCallback.java",
            "src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java",
        ],
    )
    uses_cent_signature = "getAmountInCent()" in code or "amountInCent" in code and "buildSignaturePayload" in code
    uses_yuan_signature = "getAmountInYuan()" in code or "amountInYuan" in code and "buildSignaturePayload" in code and not uses_cent_signature
    preserved = uses_cent_signature and not uses_yuan_signature
    optimized = uses_yuan_signature or not uses_cent_signature
    return build_result(task, preserved, optimized, ["amountInCent" if preserved else "amountInYuan/no cent signature"])

