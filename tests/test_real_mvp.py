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
from tracegate.core.serialization import read_json, stable_hash_text, write_cases, write_jsonl
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
            "source_url": f"https://github.com/example/repo/pull/{index}" if is_real else "",
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
            "rationale": "Concrete GitHub PR evidence supports this scored test case.",
            "is_real": is_real,
            "is_synthetic": synthetic,
            "excluded_from_real_metrics": excluded,
        }
    )


def make_hard_case(index: int, status: str) -> EvalCase:
    data = make_case(index, status=status).to_dict()
    if status == "conflicting":
        data["expected_decision"] = "detect_conflict"
    elif status == "stale":
        data["expected_decision"] = "verify_first"
    if status in {"stale", "conflicting"}:
        data["evidence_items"].append(
            {
                "evidence_id": f"{data['case_id']}:evidence:review",
                "evidence_type": "review",
                "evidence_text_excerpt": "Reviewer evidence adds a second concrete GitHub URL for hard-case adjudication.",
                "evidence_url": f"https://github.com/example/repo/pull/{index}#discussion_r{index}",
                "file_path": None,
                "commit_sha": "merge",
                "timestamp": "2026-01-02T00:00:00Z",
                "supports_or_contradicts": "contradicts" if status == "conflicting" else "unclear",
                "provenance_hash": stable_hash_text(f"{data['case_id']}:review"),
            }
        )
    if status == "unknown":
        data["rationale"] = "Insufficient evidence: the PR touches a risky path but lacks enough current support."
    return EvalCase.from_dict(data)


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


def test_no_concrete_pr_url_fails_strict_validation(tmp_path: Path) -> None:
    case = make_case(1)
    data = case.to_dict()
    data["source_url"] = "https://docs.github.com/en/rest/pulls/pulls"
    data["pr_url"] = None
    data["issue_url"] = None
    data["claim"]["claim_source_url"] = "https://docs.github.com/en/rest/pulls/pulls"
    data["evidence_items"][0]["evidence_url"] = "https://api.github.com/repos/example/repo/pulls/1"
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [EvalCase.from_dict(data)])
    with pytest.raises(DatasetValidationError, match="concrete github.com"):
        validate_dataset(dataset, strict=True, min_cases=1)


def test_conflicting_requires_multiple_evidence_items(tmp_path: Path) -> None:
    case = make_case(1, status="conflicting")
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [case])
    with pytest.raises(DatasetValidationError, match="requires at least 2 evidence_items"):
        validate_dataset(dataset, strict=True, min_cases=1)


def test_low_confidence_and_manual_review_excluded_from_scored_metrics(tmp_path: Path) -> None:
    low_confidence = make_case(1)
    low_data = low_confidence.to_dict()
    low_data["label_confidence"] = 0.4
    low_data["excluded_from_real_metrics"] = True
    manual_review = make_case(2, status="needs_manual_review", excluded=True)
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [EvalCase.from_dict(low_data), manual_review])
    _, summary = validate_dataset(dataset, strict=True, min_cases=0)
    assert summary["num_cases_scored"] == 0


def test_manual_verified_requires_manual_labels_confirmation(tmp_path: Path) -> None:
    data = make_case(1).to_dict()
    data["label_source"] = "manual_verified"
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [EvalCase.from_dict(data)])
    with pytest.raises(DatasetValidationError, match="manual_labels.jsonl confirmation"):
        validate_dataset(dataset, strict=True, min_cases=1)

    labels_path = tmp_path / "labels" / "manual_labels.jsonl"
    write_jsonl(
        labels_path,
        [
            {
                "candidate_id": data["case_id"],
                "review_decision": "promote",
                "label_source": "manual_verified",
                "label_confidence": 0.85,
                "reviewer": "human",
            }
        ],
    )
    _, summary = validate_dataset(dataset, strict=True, min_cases=1)
    assert summary["confirmed_manual_labels"] == 1


def test_unconfirmed_review_queue_candidate_cannot_be_scored(tmp_path: Path) -> None:
    data = make_case(1).to_dict()
    data["case_id"] = "hard_candidate:example__repo:pull:1"
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, [EvalCase.from_dict(data)])
    write_jsonl(
        tmp_path / "labels" / "manual_review_queue.jsonl",
        [
            {
                "candidate_id": data["case_id"],
                "repo": "example/repo",
                "pr_url": "https://github.com/example/repo/pull/1",
                "suspected_status": "unknown",
            }
        ],
    )
    with pytest.raises(DatasetValidationError, match="cannot be scored before manual"):
        validate_dataset(dataset, strict=True, min_cases=1)


def test_cli_review_queue_writes_markdown(tmp_path: Path) -> None:
    queue = tmp_path / "manual_review_queue.jsonl"
    output = tmp_path / "round_1.md"
    write_jsonl(
        queue,
        [
            {
                "candidate_id": "hard_candidate:example__repo:pull:1",
                "repo": "example/repo",
                "pr_url": "https://github.com/example/repo/pull/1",
                "issue_url": "https://github.com/example/repo/issues/1",
                "comment_url": None,
                "review_url": None,
                "commit_url": None,
                "suspected_status": "unknown",
                "why_suspected": "High-risk topic keywords found in PR title/body: auth",
                "questions_for_reviewer": ["Is there enough evidence to preserve safely?"],
                "evidence_items": [
                    {
                        "evidence_id": "hard_candidate:example__repo:pull:1:evidence:pr",
                        "evidence_type": "pr",
                        "evidence_text_excerpt": "Auth behavior changed.",
                        "evidence_url": "https://github.com/example/repo/pull/1",
                        "supports_or_contradicts": "unclear",
                    }
                ],
            }
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tracegate",
            "data",
            "review-queue",
            "--input",
            queue.as_posix(),
            "--output",
            output.as_posix(),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Manual Label Review Round 1" in text
    assert "## Unknown Candidates" in text
    assert "hard_candidate:example__repo:pull:1" in text
    assert "promote recommendation" in text
    assert "output_path" in result.stdout


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
    assert manifest["active_only"] is True
    assert manifest["hard_benchmark_ready"] is False
    assert report["metrics"]["num_cases_scored"] == 8
    assert report["metrics"]["active_only"] is True
    assert report["metrics"]["hard_benchmark_ready"] is False


def test_hard_benchmark_report_generation_marks_ready(tmp_path: Path) -> None:
    cases = [make_case(index) for index in range(1, 9)]
    cases.extend(make_hard_case(index, "unknown") for index in range(9, 12))
    cases.extend(make_hard_case(index, "conflicting") for index in range(12, 14))
    cases.append(make_hard_case(14, "stale"))
    dataset = tmp_path / "cases.jsonl"
    write_cases(dataset, cases)
    manifest = run_real_advisory(
        dataset_path=dataset,
        advisor="rule",
        run_dir=tmp_path / "run",
        real_only=True,
        no_mock=True,
        no_fallback=True,
        command="test hard run",
        min_cases=14,
    )
    report = read_json(tmp_path / "run" / "report.json")
    assert manifest["active_only"] is False
    assert manifest["hard_benchmark_ready"] is True
    assert report["metrics"]["scored_status_distribution"] == {
        "active": 8,
        "conflicting": 2,
        "stale": 1,
        "unknown": 3,
    }


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


def test_cli_mine_hard_help_works() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tracegate", "data", "mine-hard", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--repos" in result.stdout
    assert "--no-fallback" in result.stdout


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
