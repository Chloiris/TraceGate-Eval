from __future__ import annotations

import re

from .indexer import IndexSnapshot
from .parser import CodeSymbol, map_changed_symbols


_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def changed_line_numbers(unified_diff: str) -> dict[str, frozenset[int]]:
    """Return exact Head-side added/replacement line numbers from a Git unified diff."""
    changed: dict[str, set[int]] = {}
    current_path: str | None = None
    new_line: int | None = None
    for raw in unified_diff.splitlines():
        if raw.startswith("+++ "):
            marker = raw[4:]
            current_path = None if marker == "/dev/null" else marker.removeprefix("b/")
            if current_path is not None:
                changed.setdefault(current_path, set())
            new_line = None
            continue
        header = _HUNK_HEADER.match(raw)
        if header:
            new_line = int(header.group(1))
            continue
        if current_path is None or new_line is None or raw.startswith("\\"):
            continue
        if raw.startswith("+"):
            changed[current_path].add(new_line)
            new_line += 1
        elif raw.startswith("-"):
            continue
        else:
            new_line += 1
    return {path: frozenset(lines) for path, lines in changed.items()}


def changed_symbols(
    snapshot: IndexSnapshot,
    unified_diff: str,
) -> dict[str, tuple[CodeSymbol, ...]]:
    """Map Head-side changed lines to parser-confirmed symbol ranges."""
    lines_by_path = changed_line_numbers(unified_diff)
    return {
        path: map_changed_symbols(indexed.parsed, lines_by_path.get(path, ()))
        for path, indexed in snapshot.files.items()
        if path in lines_by_path
    }
