from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.oracle.base_oracle import build_result, read_many


def evaluate(repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    code = read_many(
        repo_dir,
        [
            "src/main/java/com/example/legacyshop/job/BillSyncService.java",
            "src/main/java/com/example/legacyshop/job/BillRepository.java",
            "src/main/java/com/example/legacyshop/job/ExactlyOnceQueue.java",
        ],
    )
    has_sync_batch_check = "existsBySyncBatchId" in code and "syncBatchId" in code
    has_exactly_once = "exactlyOnceQueue" in code or "ExactlyOnceQueue" in code
    preserved = has_sync_batch_check and not has_exactly_once
    optimized = has_exactly_once or not has_sync_batch_check
    return build_result(task, preserved, optimized, ["syncBatchId check" if preserved else "exactlyOnce/no old check"])

