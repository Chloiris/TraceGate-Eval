from __future__ import annotations

import subprocess
import sys
import importlib.util
from pathlib import Path

import pytest

from tracegate.core.models import EvalCase
from tracegate.core.policy import advise_case
from tracegate.core.guardrails import scan_guardrails
from tracegate.core.run import RealRunError, run_real_advisory
from tracegate.core.serialization import read_json, stable_hash_text, write_cases
from tracegate.data.validate import DatasetValidationError, validate_dataset


def load_action_build_summary():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "github_action_advisory.py"
    spec = importlib.util.spec_from_file_location("tracegate_github_action_advisory", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_summary


def make_case(index: int, *, status: str = "active", synthetic: bool = False, excluded: bool = False) -> EvalCase:
    case_id = f"test:case:{index}"
    is_real = not synthetic
    return EvalCase.from_dict(
        {
            "case_id": case_id,
            "source_dataset": "github_api" if is_real else "test_fixture",
            "source_url": "https://api.github.com/repos/example/repo/pulls" if is_real else "",
            "repo": "example/repo",
            "repo_url": "https://github.com/example/repo" if is_real else "",
            "issue_url": None,
            "pr_url": f"https://github.com/example/repo/pull/{index}" if is_real else None,
            "base_commit": "base",
            "head_commit": "head",
            "commit_sha": "merge",
            "created_at": "2026-01-01T00:00:00Z",
            "files_changed": ["src/auth/token.py" if index % 2 else "docs/config.md"],
            "diff_summary": "Changed a real file",
            "problem_statement": "Merged PR records a historical compatibility change.",
            "claim": {
                "claim_id": f"{case_id}:claim",
                "claim_text": "Preserve compatibility unless current evidence says otherwise.",
                "validity_condition": "Applies when matching files change.",
                "claim_source": "pr",
                "claim_source_url": f"https://github.com/example/repo/pull/{index}" if is_real else "fixture",
            },
            "evidence_items": [
                {
                    "evidence_id": f"{case_id}:evidence",
                    "evidence_type": "pr",
                    "evidence_text_excerpt": "Merged Pull Request with changed-file provenance.",
                    "evidence_url": f"https://github.com/example/repo/pull/{index}" if is_real else "fixture",
                    "file_path": None,
                    "commit_sha": "merge",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "supports_or_contradicts": "supports",
                    "provenance_hash": stable_hash_text(case_id),
                }
            ],
            "evidence_status": status,
            "expected_decision": "preserve" if status == "active" else "verify_first",
            "label_source": "heuristic_verified" if is_real and not excluded else "unknown",
            "label_confidence": 0.8 if is_real and not excluded else 0.0,
            "is_real": is_real,
            "is_synthetic": synthetic,
            "excluded_from_real_metrics": excluded,
        }
    )


def test_eval_case_enum_validation_rejects_unknown_status() -> None:
    data = make_case(1).to_dict()
    data["evidence_status"] = "invented"
    with pytest.raises(ValueError):
        EvalCase.from_dict(data)


def test_policy_preserves_active_and_requires_verification_for_unknown() -> None:
    active = make_case(1, status="active")
    unknown = make_case(2, status="unknown")
    active_decision = advise_case(active)
    unknown_decision = advise_case(unknown)
    assert active_decision.decision == "preserve"
    assert active_decision.risk_level in {"medium", "high", "critical"}
    assert unknown_decision.decision == "verify_first"
    assert unknown_decision.requires_human_review is True


def test_validate_dataset_requires_min_scored_real_cases(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [make_case(1), make_case(2)])
    with pytest.raises(DatasetValidationError, match="at least 8"):
        validate_dataset(dataset, strict=True, min_cases=8)


def test_synthetic_fixture_is_excluded_from_real_metrics(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [make_case(1, synthetic=True, excluded=True)])
    cases, summary = validate_dataset(dataset, strict=True, min_cases=0)
    assert cases[0].is_synthetic is True
    assert summary["num_cases_scored"] == 0


def test_missing_provenance_fails_for_scored_case(tmp_path: Path) -> None:
    case = make_case(1)
    data = case.to_dict()
    data["source_url"] = ""
    data["repo_url"] = ""
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [EvalCase.from_dict(data)])
    with pytest.raises(DatasetValidationError, match="missing source_url or repo_url"):
        validate_dataset(dataset, strict=True, min_cases=1)


def test_real_run_writes_manifest_and_reports(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [make_case(index) for index in range(1, 9)])
    manifest = run_real_advisory(
        dataset_path=dataset,
        advisor="rule",
        run_dir=tmp_path / "run",
        real_only=True,
        no_mock=True,
        no_fallback=True,
        command="test real run",
    )
    report = read_json(tmp_path / "run" / "report.json")
    assert manifest["used_real_data"] is True
    assert manifest["used_synthetic_data"] is False
    assert manifest["used_mock_model"] is False
    assert manifest["used_fallback_data"] is False
    assert report["metrics"]["num_cases_scored"] == 8


def test_mock_advisor_is_forbidden_in_real_only_mode(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [make_case(index) for index in range(1, 9)])
    with pytest.raises(RealRunError, match="no mock"):
        run_real_advisory(
            dataset_path=dataset,
            advisor="mock",
            run_dir=tmp_path / "run",
            real_only=True,
            no_mock=True,
            no_fallback=True,
            command="test mock",
        )


def test_empty_dataset_cannot_produce_success_report(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("", encoding="utf-8")
    with pytest.raises(RealRunError, match="at least 8"):
        run_real_advisory(
            dataset_path=dataset,
            advisor="rule",
            run_dir=tmp_path / "run",
            real_only=True,
            no_mock=True,
            no_fallback=True,
            command="test empty",
        )


def test_guardrail_scan_detects_dangerous_runtime_fallback(tmp_path: Path) -> None:
    runtime_file = tmp_path / "tracegate" / "runtime.py"
    runtime_file.parent.mkdir()
    runtime_file.write_text("def load_data():\n    return []\n", encoding="utf-8")
    findings = scan_guardrails(root=tmp_path)
    dangerous = [item for item in findings if item.classification == "dangerous_runtime_path"]
    assert dangerous


def test_cli_help_exposes_real_data_commands() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tracegate", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "data" in result.stdout
    assert "guardrails" in result.stdout


def test_github_action_summary_matches_claim_files() -> None:
    build_summary = load_action_build_summary()
    summary = build_summary(
        {
            "claims": [
                {
                    "claim_id": "legacy-token-compat",
                    "claim_text": "Do not remove legacy token compatibility.",
                    "evidence_status": "unknown",
                    "recommended_decision": "verify_first",
                    "files": ["src/auth/**"],
                }
            ]
        },
        ["src/auth/token.py", "README.md"],
    )
    assert "legacy-token-compat" in summary
    assert "verify_first" in summary
