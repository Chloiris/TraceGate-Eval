from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def parse_surefire_reports(repo_dir: Path) -> dict[str, Any]:
    report_dir = repo_dir / "target" / "surefire-reports"
    summary: dict[str, Any] = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "failed_tests": [],
        "report_files": [],
    }
    if not report_dir.exists():
        return summary

    for report in sorted(report_dir.glob("TEST-*.xml")):
        summary["report_files"].append(str(report))
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError:
            continue
        summary["tests"] += int(root.attrib.get("tests", 0))
        summary["failures"] += int(root.attrib.get("failures", 0))
        summary["errors"] += int(root.attrib.get("errors", 0))
        summary["skipped"] += int(root.attrib.get("skipped", 0))
        for case in root.findall("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                summary["failed_tests"].append(
                    {
                        "class": case.attrib.get("classname", ""),
                        "name": case.attrib.get("name", ""),
                    }
                )
    return summary

