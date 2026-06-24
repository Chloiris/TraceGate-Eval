from __future__ import annotations

from typing import Any


def execution_metrics(deepseek_result: dict[str, Any], test_result: dict[str, Any] | None) -> dict[str, Any]:
    patch_applied = deepseek_result.get("status") in {"ok", "test_failed"} and deepseek_result.get("patch_apply", {}).get("success") is True
    test_success = bool(test_result and test_result.get("success"))
    compile_success = bool(test_result and test_result.get("returncode") == 0)
    junit = (test_result or {}).get("junit", {})
    apply_failed = bool(
        deepseek_result.get("status") == "apply_failed"
        or deepseek_result.get("patch_apply", {}).get("status") == "apply_failed"
    )
    return {
        "patch_applied": patch_applied,
        "compile_success": compile_success,
        "tests_executed": bool(test_result and test_result.get("command") != "not run"),
        "test_success": test_success,
        "junit_failures": int(junit.get("failures", 0)) + int(junit.get("errors", 0)),
        "apply_failed": apply_failed,
    }
