from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = [
    ("deepseek-v4-flash", ROOT / "archives" / "deepseek-v4-flash-20260605-2310"),
    ("deepseek-v4-pro", ROOT / "archives" / "deepseek-v4-pro-20260605-2330"),
    ("deepseek-v4-pro-thinking-high", ROOT / "archives" / "deepseek-v4-pro-thinking-high-20260606-0005"),
    ("deepseek-v4-pro-thinking-max", ROOT / "archives" / "deepseek-v4-pro-thinking-max-20260606-0050"),
]


def load_results(archive: Path) -> list[dict]:
    return json.loads((archive / "runs" / "results.json").read_text(encoding="utf-8"))


def load_statuses(archive: Path) -> Counter:
    statuses = Counter()
    for path in (archive / "runs").rglob("deepseek_run.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        statuses[data.get("status", "unknown")] += 1
    return statuses


def rows() -> list[dict]:
    output = []
    for label, archive in ARCHIVES:
        data = load_results(archive)
        statuses = load_statuses(archive)
        for context in [
            "no_context",
            "result_history",
            "full_process",
            "routed_process",
            "irrelevant_context",
        ]:
            items = [item for item in data if item["context_group"] == context]
            output.append(
                {
                    "experiment": label,
                    "context": context,
                    "runs": len(items),
                    "success": sum(item["success"] is True for item in items),
                    "failed": sum(item["success"] is False for item in items),
                    "constraint_violations": sum(bool(item["violated_history_constraint"]) for item in items),
                    "pollution": sum(bool(item["pollution_flag"]) for item in items),
                    "avg_context_tokens": round(sum(item["context_tokens"] for item in items) / len(items), 1),
                    "ok": statuses.get("ok", 0),
                    "test_failed": statuses.get("test_failed", 0),
                    "apply_failed": statuses.get("apply_failed", 0),
                    "no_patch": statuses.get("no_patch", 0),
                }
            )
    return output


def main() -> None:
    report_dir = ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    output_rows = rows()
    csv_path = report_dir / "archive_comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    lines = [
        "# DeepSeek Archive Comparison",
        "",
        "| Experiment | Context | Success | Failed | Violations | Pollution | OK | Test Failed | Apply Failed | No Patch |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in output_rows:
        lines.append(
            "| {experiment} | {context} | {success}/{runs} | {failed}/{runs} | {constraint_violations} | {pollution} | {ok} | {test_failed} | {apply_failed} | {no_patch} |".format(
                **row
            )
        )
    md_path = report_dir / "archive_comparison.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md_path)
    print(csv_path)


if __name__ == "__main__":
    main()

