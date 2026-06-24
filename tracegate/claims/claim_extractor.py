from __future__ import annotations

import re
from typing import Any


CLAIM_PATTERNS = [
    re.compile(r"\bmust\s+not\s+be\s+deleted\b", re.IGNORECASE),
    re.compile(r"\bmust\s+remain\b", re.IGNORECASE),
    re.compile(r"\bmust\s+keep\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+remove\b", re.IGNORECASE),
]


def extract_claims_from_text(text: str, module: str = "unknown", source: str = "local") -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in CLAIM_PATTERNS):
            claims.append(
                {
                    "id": f"{source}:{module}:{line_no}",
                    "module": module,
                    "pitfall": "external",
                    "claim_text": line,
                    "validity_condition": "Imported claim; validity condition must be resolved from nearby evidence.",
                    "source": source,
                    "line": line_no,
                }
            )
    return claims
