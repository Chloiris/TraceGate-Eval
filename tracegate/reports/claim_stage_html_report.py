from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from tracegate.reports.claim_stage_markdown_report import build_claim_stage_markdown


def write_claim_stage_html(results: list[dict[str, Any]], output_path: Path) -> Path:
    content = html.escape(build_claim_stage_markdown(results))
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TraceGate ClaimBench Report</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; line-height: 1.55; }}
    pre {{ white-space: pre-wrap; background: #f6f8fa; padding: 16px; border-radius: 6px; }}
  </style>
</head>
<body><pre>{content}</pre></body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
