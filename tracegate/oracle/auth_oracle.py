from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle.base_oracle import build_result, read_many


def evaluate(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    code = read_many(
        repo_dir,
        [
            "src/main/java/com/example/legacyshop/auth/AuthService.java",
            "src/main/java/com/example/legacyshop/auth/LoginResponse.java",
            "src/main/java/com/example/legacyshop/auth/LoginController.java",
        ],
    )
    preserved = "legacyToken" in code or "generateLegacyToken" in code or "getLegacyToken" in code
    optimized = not preserved
    return build_result(task, preserved, optimized, ["legacyToken" if preserved else "legacyToken absent"])

