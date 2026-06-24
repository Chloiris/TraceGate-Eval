from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle import auth_oracle, job_oracle, order_oracle, payment_oracle, user_oracle


ORACLES = {
    "auth": auth_oracle.evaluate,
    "order": order_oracle.evaluate,
    "user": user_oracle.evaluate,
    "payment": payment_oracle.evaluate,
    "job": job_oracle.evaluate,
}


def evaluate_oracle(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    module = task.get("module")
    if module not in ORACLES:
        raise ValueError(f"No oracle for module: {module}")
    return ORACLES[module](repo_dir, task)

