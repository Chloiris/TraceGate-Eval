from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"TraceGate config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"TraceGate config must be a mapping: {path}")
    return data


def load_changed_files(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"Changed-files list not found: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def matches_any(file_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns)


def build_summary(config: dict[str, Any], changed_files: list[str]) -> str:
    claims = config.get("claims") or []
    if not isinstance(claims, list):
        raise SystemExit("TraceGate config field `claims` must be a list")
    lines = [
        "# TraceGate Pull Request Advisory",
        "",
        "TraceGate is running in warning-only advisory mode.",
        "",
        "## Changed Files",
        "",
    ]
    if changed_files:
        lines.extend(f"- `{file_path}`" for file_path in changed_files[:80])
    else:
        lines.append("- No changed files were provided by the workflow.")

    lines.extend(["", "## Claim Matches", ""])
    matched = 0
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "unknown-claim")
        patterns = [str(item) for item in claim.get("files", [])]
        touched = [file_path for file_path in changed_files if matches_any(file_path, patterns)]
        if not touched:
            continue
        matched += 1
        evidence_status = str(claim.get("evidence_status") or "unknown")
        decision = str(claim.get("recommended_decision") or "verify_first")
        lines.extend(
            [
                f"### `{claim_id}`",
                "",
                f"- evidence_status: `{evidence_status}`",
                f"- recommended_decision: `{decision}`",
                f"- claim: {claim.get('claim_text', '')}",
                f"- matched_files: {', '.join(f'`{item}`' for item in touched[:10])}",
                "- advisory: verify the historical constraint before merging risky changes.",
                "",
            ]
        )
    if matched == 0:
        lines.append("No configured claims matched the changed files.")
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "This action does not use mock datasets and does not block the Pull Request by default.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a TraceGate GitHub Action advisory summary.")
    parser.add_argument("--config", type=Path, default=Path("tracegate.yml"))
    parser.add_argument("--changed-files", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    changed_files = load_changed_files(args.changed_files)
    summary = build_summary(config, changed_files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(summary + "\n", encoding="utf-8")
    print(f"TraceGate advisory summary written to {args.output}")


if __name__ == "__main__":
    main()
