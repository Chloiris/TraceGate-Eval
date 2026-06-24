from __future__ import annotations

from pathlib import Path

from tracegate.config import REPORTS_DIR, RUNS_DIR
from tracegate.dataio import read_json
from tracegate.reports.csv_report import write_csv_report
from tracegate.reports.html_report import write_html_report
from tracegate.reports.markdown_report import write_markdown_report


def generate_reports(runs_dir: Path = RUNS_DIR, reports_dir: Path = REPORTS_DIR) -> list[Path]:
    results = read_json(runs_dir / "results.json", default=[])
    if not results:
        raise FileNotFoundError("No collected results found. Run `python -m tracegate collect-results` first.")

    reports_dir.mkdir(parents=True, exist_ok=True)
    return [
        write_markdown_report(results, reports_dir / "report.md"),
        write_csv_report(results, reports_dir / "results.csv"),
        write_html_report(results, reports_dir / "report.html"),
    ]

