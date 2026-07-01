from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class RealDataError(RuntimeError):
    """Raised when a real-data command cannot complete honestly."""


@dataclass(frozen=True)
class FetchResult:
    source: str
    raw_path: Path
    raw_manifest_path: Path
    records_written: int
