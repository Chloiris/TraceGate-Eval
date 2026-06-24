from __future__ import annotations

from typing import Any


def evaluate_test_result(test_result: dict[str, Any] | None) -> dict[str, Any]:
    junit = (test_result or {}).get("junit", {})
    return {
        "tests_executed": bool(test_result and test_result.get("command") != "not run"),
        "test_success": bool(test_result and test_result.get("success")),
        "junit_failures": int(junit.get("failures", 0)) + int(junit.get("errors", 0)),
    }
