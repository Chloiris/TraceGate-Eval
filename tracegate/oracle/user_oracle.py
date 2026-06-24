from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle.base_oracle import build_result, read


def evaluate(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    service = read(repo_dir, "src/main/java/com/example/legacyshop/user/UserService.java")
    has_soft_delete = "markDeleted" in service or "STATUS_DELETED" in service or "status = 2" in service
    uses_physical_delete = "deleteById(" in service or ".delete(" in service
    preserved = has_soft_delete and not uses_physical_delete
    optimized = uses_physical_delete
    return build_result(task, preserved, optimized, ["deleteById" if optimized else "soft delete"])

