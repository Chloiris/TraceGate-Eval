from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.runners.deepseek_runner import apply_model_patch


def apply_patch_if_present(run_dir: Path, patch_present: bool) -> dict[str, Any]:
    if not patch_present:
        return {
            "status": "no_patch_needed",
            "success": False,
            "patch_present": False,
        }
    result = apply_model_patch(run_dir)
    result["patch_present"] = True
    return result
