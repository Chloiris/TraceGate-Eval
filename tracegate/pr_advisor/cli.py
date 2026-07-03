from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .deepseek_client import DeepSeekClientError, load_deepseek_settings_from_env
from .llm_judge import SemanticJudgeError, judge_with_deepseek
from .render import advisory_payload, write_advisory
from .retrieve import build_evidence_packet
from .verifier import verify_judgment


class SemanticAdvisorError(RuntimeError):
    """Raised when v0.3 semantic PR advisory cannot produce a real result."""


@dataclass(frozen=True)
class AnalyzeOptions:
    repo: str
    pr_number: int
    mode: str
    provider: str
    real_only: bool
    no_mock: bool
    no_fallback: bool
    output: Path
    json_output: Path


def _enforce_real_semantic(options: AnalyzeOptions) -> None:
    if options.mode != "semantic":
        raise SemanticAdvisorError("--mode semantic is required for v0.3 PR advisor")
    if options.provider != "deepseek":
        raise SemanticAdvisorError("--provider deepseek is required for semantic mode")
    if not options.real_only:
        raise SemanticAdvisorError("semantic PR advisor requires --real-only")
    if not options.no_mock:
        raise SemanticAdvisorError("semantic PR advisor requires --no-mock")
    if not options.no_fallback:
        raise SemanticAdvisorError("semantic PR advisor requires --no-fallback")


def analyze_pr(options: AnalyzeOptions) -> dict[str, Any]:
    _enforce_real_semantic(options)
    try:
        load_deepseek_settings_from_env()
    except DeepSeekClientError as exc:
        raise SemanticAdvisorError(str(exc)) from exc
    packet = build_evidence_packet(options.repo, options.pr_number)
    try:
        judge = judge_with_deepseek(
            packet,
            provider=options.provider,
            no_mock=options.no_mock,
            no_fallback=options.no_fallback,
        )
    except SemanticJudgeError as exc:
        raise SemanticAdvisorError(str(exc)) from exc
    verified = verify_judgment(packet, judge.judgment)
    payload = advisory_payload(
        packet=packet,
        judgment=verified,
        raw_llm_json=judge.raw_llm_json,
        provider=judge.provider,
        model=judge.model,
        semantic_api_called=judge.semantic_api_called,
        attempts=judge.attempts,
    )
    write_advisory(payload, options.output, options.json_output)
    return payload


def parse_case_spec(spec: str) -> tuple[str, int]:
    if "#" not in spec:
        raise SemanticAdvisorError(f"live-smoke case must be owner/name#number: {spec}")
    repo, number_text = spec.rsplit("#", 1)
    if "/" not in repo or not number_text.isdigit():
        raise SemanticAdvisorError(f"live-smoke case must be owner/name#number: {spec}")
    return repo, int(number_text)


def _case_slug(repo: str, pr_number: int) -> str:
    return f"{repo.replace('/', '__')}__{pr_number}"


def validate_live_smoke_payload(case_spec: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    final = payload.get("final") or {}
    if payload.get("used_real_pr") is not True:
        errors.append(f"{case_spec}: used_real_pr must be true")
    if payload.get("used_real_llm") is not True or payload.get("semantic_api_called") is not True:
        errors.append(f"{case_spec}: real DeepSeek API was not called")
    if payload.get("used_mock") is not False:
        errors.append(f"{case_spec}: used_mock must be false")
    if payload.get("used_fallback") is not False:
        errors.append(f"{case_spec}: used_fallback must be false")
    evidence_items = (payload.get("evidence_packet") or {}).get("evidence_items") or []
    if not any(item.get("url") for item in evidence_items):
        errors.append(f"{case_spec}: evidence URLs are missing")
    status = final.get("evidence_status")
    decision = final.get("expected_decision")
    if case_spec == "pytest-dev/pytest#14662":
        if status not in {"no_relevant_claim", "unknown", "needs_more_evidence"}:
            errors.append(
                f"{case_spec}: expected no_relevant_claim, unknown, or needs_more_evidence; got {status}"
            )
        if status == "conflicting":
            errors.append(f"{case_spec}: final status must not be conflicting")
    if case_spec in {"psf/requests#7545", "psf/requests#7555"}:
        acceptable_unknown = status == "unknown" and decision == "verify_first"
        acceptable_needs_more = status == "needs_more_evidence"
        if not (acceptable_unknown or acceptable_needs_more):
            errors.append(
                f"{case_spec}: expected unknown+verify_first or needs_more_evidence, got {status}+{decision}"
            )
        if status == "conflicting":
            errors.append(f"{case_spec}: final status must not be conflicting")
        if status in {"active", "stale"} and not final.get("evidence_used"):
            errors.append(f"{case_spec}: active/stale without evidence is not acceptable")
    return errors


def _render_live_smoke_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# TraceGate v0.3 Semantic PR Advisor Live Smoke",
        "",
        f"- used_real_pr: `{summary['used_real_pr']}`",
        f"- used_real_llm: `{summary['used_real_llm']}`",
        f"- used_mock: `{summary['used_mock']}`",
        f"- used_fallback: `{summary['used_fallback']}`",
        f"- provider: `{summary['provider']}`",
        f"- models: `{', '.join(summary['models'])}`",
        "",
        "## Cases",
        "",
    ]
    for case in summary["cases"]:
        lines.extend(
            [
                f"### {case['case']}",
                "",
                f"- evidence_packet_size: `{case['evidence_packet_size']}`",
                f"- deepseek_model: `{case['model']}`",
                f"- semantic_api_called: `{case['semantic_api_called']}`",
                f"- final_evidence_status: `{case['final_evidence_status']}`",
                f"- final_expected_decision: `{case['final_expected_decision']}`",
                f"- verifier_result: `{case['verifier_result']}`",
                "- evidence_urls:",
            ]
        )
        for url in case["evidence_urls"][:20]:
            lines.append(f"  - {url}")
        lines.extend(
            [
                "- deepseek_raw_json_response:",
                "",
                "```json",
                json.dumps(case["deepseek_raw_json_response"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    if summary.get("errors"):
        lines.extend(["## Errors", ""])
        lines.extend(f"- {item}" for item in summary["errors"])
        lines.append("")
    return "\n".join(lines)


def run_live_smoke(
    *,
    provider: str,
    real_only: bool,
    no_mock: bool,
    no_fallback: bool,
    cases: str,
    output: Path,
    json_output: Path,
) -> dict[str, Any]:
    if provider != "deepseek" or not real_only or not no_mock or not no_fallback:
        raise SemanticAdvisorError("live-smoke requires --provider deepseek --real-only --no-mock --no-fallback")
    case_specs = [item.strip() for item in cases.split(",") if item.strip()]
    if not case_specs:
        raise SemanticAdvisorError("live-smoke requires at least one case")
    case_outputs_dir = json_output.parent / "cases"
    summary_cases: list[dict[str, Any]] = []
    errors: list[str] = []
    for spec in case_specs:
        repo, pr_number = parse_case_spec(spec)
        slug = _case_slug(repo, pr_number)
        payload = analyze_pr(
            AnalyzeOptions(
                repo=repo,
                pr_number=pr_number,
                mode="semantic",
                provider=provider,
                real_only=real_only,
                no_mock=no_mock,
                no_fallback=no_fallback,
                output=case_outputs_dir / slug / "advisory.md",
                json_output=case_outputs_dir / slug / "advisory.json",
            )
        )
        errors.extend(validate_live_smoke_payload(spec, payload))
        final = payload["final"]
        evidence_urls = [
            item.get("url")
            for item in payload["evidence_packet"]["evidence_items"]
            if item.get("url")
        ]
        summary_cases.append(
            {
                "case": spec,
                "evidence_packet_size": payload["evidence_packet_size"],
                "model": payload["model"],
                "deepseek_raw_json_response": payload["raw_llm_json"],
                "verifier_result": "notes" if final.get("verifier_notes") else "no_downgrade",
                "verifier_notes": final.get("verifier_notes", []),
                "final_evidence_status": final.get("evidence_status"),
                "final_expected_decision": final.get("expected_decision"),
                "evidence_urls": evidence_urls,
                "semantic_api_called": payload["semantic_api_called"],
                "used_real_pr": payload["used_real_pr"],
                "used_real_llm": payload["used_real_llm"],
                "used_mock": payload["used_mock"],
                "used_fallback": payload["used_fallback"],
            }
        )
    summary = {
        "provider": provider,
        "models": sorted({case["model"] for case in summary_cases}),
        "cases": summary_cases,
        "used_real_pr": all(case["used_real_pr"] for case in summary_cases),
        "used_real_llm": all(case["used_real_llm"] for case in summary_cases),
        "used_mock": any(case["used_mock"] for case in summary_cases),
        "used_fallback": any(case["used_fallback"] for case in summary_cases),
        "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_live_smoke_markdown(summary), encoding="utf-8")
    json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise SemanticAdvisorError("live-smoke failed:\n" + "\n".join(errors))
    if not summary["used_real_llm"]:
        raise SemanticAdvisorError("live-smoke failed: DeepSeek API was not called")
    if summary["used_mock"] or summary["used_fallback"]:
        raise SemanticAdvisorError("live-smoke failed: mock or fallback was used")
    return summary
