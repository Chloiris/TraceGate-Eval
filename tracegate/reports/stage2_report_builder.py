from __future__ import annotations

from pathlib import Path

from tracegate.config import REPORTS_STAGE2_DIR, RUNS_STAGE2_DIR
from tracegate.dataio import read_json
from tracegate.reports.stage2_csv_report import write_stage2_csv
from tracegate.reports.stage2_html_report import write_stage2_html
from tracegate.reports.stage2_markdown_report import write_stage2_markdown


def generate_stage2_reports(runs_dir: Path = RUNS_STAGE2_DIR, reports_dir: Path = REPORTS_STAGE2_DIR) -> list[Path]:
    results = read_json(runs_dir / "results.json", default=[])
    if not results:
        raise FileNotFoundError("No Stage2 results found. Run collect-stage2-results first.")
    reports_dir.mkdir(parents=True, exist_ok=True)
    return [
        write_stage2_markdown(results, reports_dir / "stage2_report.md"),
        write_stage2_csv(results, reports_dir / "stage2_results.csv"),
        write_stage2_html(results, reports_dir / "stage2_report.html"),
    ]

