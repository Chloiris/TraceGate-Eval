from __future__ import annotations

from pathlib import Path

from tracegate.config import RUNS_CLAIM_DIR
from tracegate.runners.command_runner import find_run_dirs


def claim_manual_instructions(run_dir: Path) -> str:
    return (
        f"Run directory: {run_dir}\n"
        "1. Read prompt.md.\n"
        "2. Edit files only under repo/.\n"
        "3. Return PATCH and TRACEGATE_DECISION sections as requested.\n"
        "4. Run `python -m tracegate collect-claim-results` after saving results.\n"
    )


def list_claim_manual_runs(root: Path = RUNS_CLAIM_DIR) -> list[str]:
    return [claim_manual_instructions(run_dir) for run_dir in find_run_dirs(root)]
