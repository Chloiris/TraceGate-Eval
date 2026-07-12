#!/usr/bin/env python3
"""Fail when current product facts, versions, or documentation drift.

`docs/project-facts.yaml` intentionally contains JSON, which is valid YAML 1.2.
Keeping this checker on the Python standard library lets it run before optional
documentation tooling is installed. Historical records are never rewritten by
this script; they are required to label their immutable scope explicitly.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
FACTS_RELATIVE_PATH = Path("docs/project-facts.yaml")
STATUS_VALUES = {
    "IMPLEMENTED_UNVERIFIED",
    "VERIFIED_MACOS",
    "VERIFIED_WINDOWS_CI",
    "VERIFIED_WINDOWS_MANUAL",
    "BLOCKED",
}
PARSER_STATUS_VALUES = {"SUPPORTED", "PARTIAL", "UNSUPPORTED"}
CANONICAL_NAMES = {
    "repository_name": "TraceGate-Eval",
    "product_name": "TraceGate Studio",
    "eval_module_name": "TraceGate Eval",
    "claimbench_name": "ClaimBench",
    "semantic_pr_advisor_name": "Semantic PR Advisor",
}
REQUIRED_FACT_KEYS = {
    "schema_version",
    "canonical_naming",
    "version",
    "version_history",
    "baseline",
    "review_workflow",
    "tool_registry",
    "test_counts",
    "benchmark_counts",
    "parser_boundaries",
    "platforms",
    "delivery_artifacts",
    "current_limitations",
    "verification_documents",
    "documentation_policy",
}
PARSER_FEATURES = {
    "file_recognition",
    "import_export",
    "class_interface",
    "function_method",
    "symbol_definition",
    "symbol_reference",
    "inheritance_implementation",
    "file_level_dependency",
    "function_level_call",
    "test_relationship",
    "changed_symbol_mapping",
    "line_range_accuracy",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
HTML_LINK = re.compile(r"(?:href|src)=[\"']([^\"']+)[\"']")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    errors.append(f"{label} must be an object")
    return {}


def _sequence(value: Any, label: str, errors: list[str]) -> list[Any]:
    if isinstance(value, list):
        return value
    errors.append(f"{label} must be an array")
    return []


def load_facts(root: Path = ROOT) -> dict[str, Any]:
    path = root / FACTS_RELATIVE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON-compatible project facts: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise ValueError("project facts must contain one JSON object")
    return payload


def validate_facts_schema(facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FACT_KEYS.difference(facts))
    if missing:
        errors.append("project facts missing keys: " + ", ".join(missing))
    if facts.get("schema_version") != 1:
        errors.append("project facts schema_version must be 1")

    naming = _mapping(facts.get("canonical_naming"), "canonical_naming", errors)
    for key, expected in CANONICAL_NAMES.items():
        if naming.get(key) != expected:
            errors.append(f"canonical_naming.{key} must be {expected!r}")
    description = naming.get("product_description")
    if not isinstance(description, str) or not description.strip():
        errors.append("canonical_naming.product_description must be non-empty")

    version = facts.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("version must be a stable MAJOR.MINOR.PATCH SemVer")
    version_history = _mapping(facts.get("version_history"), "version_history", errors)
    milestones = _sequence(
        version_history.get("historical_research_milestones"),
        "version_history.historical_research_milestones",
        errors,
    )
    if milestones != ["v0.2-alpha", "v0.3-alpha"]:
        errors.append("historical research milestones must preserve v0.2-alpha and v0.3-alpha")

    baseline = _mapping(facts.get("baseline"), "baseline", errors)
    if not isinstance(baseline.get("main_sha"), str) or not SHA40.fullmatch(baseline["main_sha"]):
        errors.append("baseline.main_sha must be a full lowercase Git SHA")
    if not isinstance(baseline.get("development_branch"), str) or not baseline["development_branch"]:
        errors.append("baseline.development_branch must be non-empty")

    review = _mapping(facts.get("review_workflow"), "review_workflow", errors)
    nodes = _sequence(review.get("nodes"), "review_workflow.nodes", errors)
    if review.get("node_count") != len(nodes) or len(set(nodes)) != len(nodes):
        errors.append("review_workflow.node_count must equal the unique node list length")

    registry = _mapping(facts.get("tool_registry"), "tool_registry", errors)
    tools = _sequence(registry.get("tools"), "tool_registry.tools", errors)
    if registry.get("tool_count") != len(tools) or len(set(tools)) != len(tools):
        errors.append("tool_registry.tool_count must equal the unique tool list length")

    tests = _mapping(facts.get("test_counts"), "test_counts", errors)
    if not isinstance(tests.get("source_sha"), str) or not SHA40.fullmatch(tests["source_sha"]):
        errors.append("test_counts.source_sha must be a full lowercase Git SHA")
    typescript = _mapping(tests.get("typescript"), "test_counts.typescript", errors)
    expected_ts_total = sum(
        int(typescript.get(key, -1)) for key in ("shared_types", "api_client", "web")
    )
    if typescript.get("total") != expected_ts_total:
        errors.append("test_counts.typescript.total must equal its three package counts")

    benchmark = _mapping(facts.get("benchmark_counts"), "benchmark_counts", errors)
    real_distribution = _mapping(
        benchmark.get("real_pr_status_distribution"),
        "benchmark_counts.real_pr_status_distribution",
        errors,
    )
    if benchmark.get("real_pr_cases") != sum(real_distribution.values()):
        errors.append("benchmark real-PR status distribution does not sum to real_pr_cases")
    for label in (
        "claimbench_modules",
        "claimbench_evidence_states",
        "claimbench_models",
    ):
        distribution = _mapping(benchmark.get(label), f"benchmark_counts.{label}", errors)
        if benchmark.get("claimbench_runs") != sum(distribution.values()):
            errors.append(f"benchmark_counts.{label} does not sum to claimbench_runs")

    parser = _mapping(facts.get("parser_boundaries"), "parser_boundaries", errors)
    if set(parser) != {"python", "javascript", "typescript", "java"}:
        errors.append("parser_boundaries must contain exactly python/javascript/typescript/java")
    for language, raw_assessments in parser.items():
        assessments = _mapping(raw_assessments, f"parser_boundaries.{language}", errors)
        if set(assessments) != PARSER_FEATURES:
            errors.append(f"parser_boundaries.{language} must assess all 12 parser features")
        invalid = sorted(set(assessments.values()).difference(PARSER_STATUS_VALUES))
        if invalid:
            errors.append(f"parser_boundaries.{language} has invalid statuses: {invalid}")

    platforms = _mapping(facts.get("platforms"), "platforms", errors)
    verified = _mapping(platforms.get("verified"), "platforms.verified", errors)
    for platform, raw_record in verified.items():
        record = _mapping(raw_record, f"platforms.verified.{platform}", errors)
        if record.get("status") not in STATUS_VALUES:
            errors.append(f"platforms.verified.{platform}.status is invalid")

    limitations = _sequence(facts.get("current_limitations"), "current_limitations", errors)
    limitation_ids: list[str] = []
    for index, raw_record in enumerate(limitations):
        record = _mapping(raw_record, f"current_limitations[{index}]", errors)
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"current_limitations[{index}].id must be non-empty")
        else:
            limitation_ids.append(identifier)
        if record.get("status") not in STATUS_VALUES:
            errors.append(f"current_limitations[{index}].status is invalid")
        if not isinstance(record.get("summary"), str) or not record["summary"].strip():
            errors.append(f"current_limitations[{index}].summary must be non-empty")
    if len(limitation_ids) != len(set(limitation_ids)):
        errors.append("current_limitations IDs must be unique")

    policy = _mapping(facts.get("documentation_policy"), "documentation_policy", errors)
    required_limitations = _mapping(
        policy.get("required_readme_limitations"),
        "documentation_policy.required_readme_limitations",
        errors,
    )
    referenced_ids = {
        identifier
        for raw_requirements in required_limitations.values()
        for identifier in _mapping(raw_requirements, "required_readme_limitations entry", errors)
    }
    unknown_ids = sorted(referenced_ids.difference(limitation_ids))
    if unknown_ids:
        errors.append("README requirements use unknown limitation IDs: " + ", ".join(unknown_ids))

    verification_documents = _sequence(
        facts.get("verification_documents"), "verification_documents", errors
    )
    declared_historical = set(
        _sequence(policy.get("historical_documents"), "historical_documents", errors)
    )
    for index, raw_record in enumerate(verification_documents):
        record = _mapping(raw_record, f"verification_documents[{index}]", errors)
        if record.get("status") not in STATUS_VALUES:
            errors.append(f"verification_documents[{index}].status is invalid")
        if record.get("historical") is True and record.get("path") not in declared_historical:
            errors.append(
                f"historical verification document {record.get('path')!r} is absent from historical_documents"
            )
    return errors


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def check_versions(root: Path, facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = str(facts["version"])
    version_sources: dict[str, Any] = {}

    pyproject = _read_toml(root / "pyproject.toml")
    version_sources["pyproject.toml"] = pyproject.get("project", {}).get("version")
    for relative in (
        "package.json",
        "apps/web/package.json",
        "apps/desktop/package.json",
        "packages/shared-types/package.json",
        "packages/api-client/package.json",
        "apps/desktop/src-tauri/tauri.conf.json",
    ):
        payload = json.loads((root / relative).read_text(encoding="utf-8"))
        version_sources[relative] = payload.get("version")

    cargo = _read_toml(root / "apps/desktop/src-tauri/Cargo.toml")
    version_sources["apps/desktop/src-tauri/Cargo.toml"] = cargo.get("package", {}).get("version")
    cargo_lock = _read_toml(root / "apps/desktop/src-tauri/Cargo.lock")
    local_cargo = [
        package
        for package in cargo_lock.get("package", [])
        if package.get("name") == "tracegate-desktop"
    ]
    version_sources["apps/desktop/src-tauri/Cargo.lock:tracegate-desktop"] = (
        local_cargo[0].get("version") if len(local_cargo) == 1 else None
    )
    uv_lock = _read_toml(root / "uv.lock")
    local_python = [
        package for package in uv_lock.get("package", []) if package.get("name") == "tracegate-eval"
    ]
    version_sources["uv.lock:tracegate-eval"] = (
        local_python[0].get("version") if len(local_python) == 1 else None
    )

    init_text = (root / "tracegate/__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_text, re.MULTILINE)
    version_sources["tracegate.__version__"] = init_match.group(1) if init_match else None
    relay_text = (root / "services/webhook-relay/app.py").read_text(encoding="utf-8")
    relay_match = re.search(r'FastAPI\(title="TraceGate Webhook Relay", version="([^"]+)"\)', relay_text)
    version_sources["services/webhook-relay/app.py"] = relay_match.group(1) if relay_match else None

    for source, actual in version_sources.items():
        if actual != expected:
            errors.append(f"version drift: {source} is {actual!r}, expected {expected!r}")

    mcp_text = (root / "tracegate/mcp/client.py").read_text(encoding="utf-8")
    if "from tracegate import __version__" not in mcp_text or '"version": __version__' not in mcp_text:
        errors.append("MCP clientInfo must consume tracegate.__version__")
    for relative in ("tracegate/github/oauth.py", "tracegate/github/provider.py"):
        text = (root / relative).read_text(encoding="utf-8")
        if "from tracegate import __version__" not in text or "TraceGate-Studio/{__version__}" not in text:
            errors.append(f"{relative} User-Agent must consume tracegate.__version__")
    for relative in (
        "apps/desktop/src-tauri/src/github_oauth.rs",
        "apps/desktop/src-tauri/src/relay_pairing.rs",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        if 'env!("CARGO_PKG_VERSION")' not in text or "TraceGate-Studio/0." in text:
            errors.append(f"{relative} User-Agent must consume CARGO_PKG_VERSION")

    workflow_requirements = {
        ".github/workflows/build-macos.yml": (
            "docs/project-facts.yaml",
            '"version": "$product_version"',
            "build-info.json",
        ),
        ".github/workflows/build-windows.yml": (
            "docs/project-facts.yaml",
            "version = $ProductVersion",
            "build-info.json",
        ),
    }
    for relative, requirements in workflow_requirements.items():
        text = (root / relative).read_text(encoding="utf-8")
        if not all(requirement in text for requirement in requirements):
            errors.append(f"{relative} build-info must consume the canonical project version")
    return errors


def check_naming(root: Path, facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    naming = facts["canonical_naming"]
    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject["project"].get("name") != "tracegate-eval":
        errors.append("pyproject distribution name must remain tracegate-eval")
    if pyproject["project"].get("description") != naming["product_description"]:
        errors.append("pyproject description does not match canonical product_description")
    root_package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    if root_package.get("name") != "tracegate-studio":
        errors.append("root workspace package name must be tracegate-studio")
    tauri = json.loads((root / "apps/desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    if tauri.get("productName") != naming["product_name"]:
        errors.append("Tauri productName does not match canonical product name")
    windows = tauri.get("app", {}).get("windows", [])
    if not windows or windows[0].get("title") != naming["product_name"]:
        errors.append("Tauri main window title does not match canonical product name")
    for relative in ("README.md", "docs/README_CN.md"):
        text = (root / relative).read_text(encoding="utf-8")
        for key in (
            "repository_name",
            "product_name",
            "eval_module_name",
            "claimbench_name",
            "semantic_pr_advisor_name",
        ):
            if naming[key] not in text:
                errors.append(f"{relative} does not name canonical {key}: {naming[key]}")
    return errors


def check_runtime_facts(root: Path, facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sys.path.insert(0, str(root))
    try:
        from tracegate.agent.workflow import NODE_NAMES, PROMPT_VERSION, WORKFLOW_VERSION
        from tracegate.indexing import PARSER_CAPABILITY_MATRIX
        from tracegate.tools.registry import create_read_only_registry
    finally:
        if sys.path and sys.path[0] == str(root):
            sys.path.pop(0)

    review = facts["review_workflow"]
    if list(NODE_NAMES) != review["nodes"] or len(NODE_NAMES) != review["node_count"]:
        errors.append("project facts review nodes do not match the production workflow")
    if WORKFLOW_VERSION != review["version"] or PROMPT_VERSION != review["prompt_version"]:
        errors.append("project facts review workflow/prompt versions do not match production")
    tool_names = [descriptor.name for descriptor in create_read_only_registry().descriptors()]
    registry = facts["tool_registry"]
    if tool_names != registry["tools"] or len(tool_names) != registry["tool_count"]:
        errors.append("project facts tools do not exactly match the production Registry")

    parser = {
        language: {
            feature.value: assessment.status.value
            for feature, assessment in assessments.items()
        }
        for language, assessments in PARSER_CAPABILITY_MATRIX.items()
    }
    if parser != facts["parser_boundaries"]:
        errors.append("project facts parser boundaries do not match PARSER_CAPABILITY_MATRIX")

    manifest = json.loads((root / "datasets/real_min/manifest.json").read_text(encoding="utf-8"))
    with (root / "reports_claim/claim_stage_results.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    benchmark = facts["benchmark_counts"]
    actual_benchmark = {
        "real_pr_cases": manifest.get("num_cases_scored"),
        "real_pr_status_distribution": manifest.get("status_distribution"),
        "claimbench_runs": len(rows),
        "claimbench_modules": dict(sorted(Counter(row["task_module"] for row in rows).items())),
        "claimbench_evidence_states": dict(
            sorted(Counter(row["evidence_status"] for row in rows).items())
        ),
        "claimbench_context_groups": len({row["context_group"] for row in rows}),
        "claimbench_models": dict(sorted(Counter(row["model"] for row in rows).items())),
    }
    if actual_benchmark != benchmark:
        errors.append("project facts benchmark counts do not match checked-in artifacts")
    return errors


def _link_target(raw_reference: str) -> str:
    reference = raw_reference.strip()
    if reference.startswith("<") and ">" in reference:
        reference = reference[1 : reference.index(">")]
    else:
        reference = reference.split(maxsplit=1)[0]
    return unquote(reference.split("#", 1)[0].split("?", 1)[0])


def check_relative_links(root: Path, documents: list[str]) -> list[str]:
    errors: list[str] = []
    for relative in documents:
        path = root / relative
        if not path.is_file():
            errors.append(f"relative-link document does not exist: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        references = [match.group(1) for match in MARKDOWN_LINK.finditer(text)]
        references.extend(match.group(1) for match in HTML_LINK.finditer(text))
        for raw_reference in references:
            target = _link_target(raw_reference)
            if not target or target.startswith("#") or re.match(
                r"^(?:https?:|mailto:|data:|tel:)", target, re.IGNORECASE
            ):
                continue
            if Path(target).is_absolute():
                errors.append(f"{relative} contains an absolute local link: {raw_reference}")
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{relative} has a missing relative link: {raw_reference}")
    return errors


def check_historical_markers(
    root: Path, documents: list[str], marker: str
) -> list[str]:
    errors: list[str] = []
    for relative in documents:
        path = root / relative
        if not path.is_file():
            errors.append(f"historical document does not exist: {relative}")
            continue
        header = "\n".join(path.read_text(encoding="utf-8").splitlines()[:12])
        if marker not in header:
            errors.append(f"historical document lacks {marker!r} marker: {relative}")
    return errors


def check_current_document_claims(root: Path, facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = facts["documentation_policy"]
    current_documents = policy["current_facing_documents"]
    stale_branches = policy["forbidden_stale_branches"]
    manual_status = facts["platforms"]["verified"]["windows_x86_64_manual"]["status"]
    boundary_words = (
        "never",
        "does not",
        "not equivalent",
        "not imply",
        "不等于",
        "不代表",
        "不能",
    )
    forbidden_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in policy["forbidden_unqualified_claim_patterns"]
    ]
    for relative in current_documents:
        path = root / relative
        if not path.is_file():
            errors.append(f"current-facing document does not exist: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for branch in stale_branches:
                if branch in line and "historical" not in line.lower():
                    errors.append(
                        f"{relative}:{line_number} contains stale branch {branch!r} without Historical scope"
                    )
            if "VERIFIED_WINDOWS_CI" in line and "VERIFIED_WINDOWS_MANUAL" in line:
                lowered = line.lower()
                if not any(word in lowered for word in boundary_words):
                    errors.append(
                        f"{relative}:{line_number} mixes Windows CI/manual states without an explicit boundary"
                    )
            if manual_status != "VERIFIED_WINDOWS_MANUAL" and re.search(
                r"\|\s*`?VERIFIED_WINDOWS_MANUAL`?\s*\|", line
            ):
                errors.append(
                    f"{relative}:{line_number} claims Windows manual verification without evidence"
                )
        for pattern in forbidden_patterns:
            match = pattern.search(text)
            if match:
                errors.append(
                    f"{relative} contains forbidden unqualified capability claim: {match.group(0)!r}"
                )

    limitation_ids = {record["id"] for record in facts["current_limitations"]}
    for relative, requirements in policy["required_readme_limitations"].items():
        path = root / relative
        if not path.is_file():
            errors.append(f"README limitation document does not exist: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        normalized_text = re.sub(r"\s+", " ", text)
        for limitation_id, accepted_phrases in requirements.items():
            if limitation_id not in limitation_ids:
                errors.append(f"README requirement references unknown limitation: {limitation_id}")
                continue
            if not any(
                re.sub(r"\s+", " ", phrase) in normalized_text
                for phrase in accepted_phrases
            ):
                errors.append(
                    f"{relative} does not state required limitation {limitation_id!r}"
                )
    return errors


def check_declared_documents(root: Path, facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for record in facts["verification_documents"]:
        if not (root / record["path"]).is_file():
            errors.append(f"verification document does not exist: {record['path']}")
    return errors


def run_checks(root: Path = ROOT) -> list[str]:
    try:
        facts = load_facts(root)
    except ValueError as exc:
        return [str(exc)]
    errors = validate_facts_schema(facts)
    if errors:
        return errors
    policy = facts["documentation_policy"]
    errors.extend(check_versions(root, facts))
    errors.extend(check_naming(root, facts))
    errors.extend(check_runtime_facts(root, facts))
    errors.extend(check_relative_links(root, policy["relative_link_documents"]))
    errors.extend(
        check_historical_markers(
            root, policy["historical_documents"], policy["historical_marker"]
        )
    )
    errors.extend(check_current_document_claims(root, facts))
    errors.extend(check_declared_documents(root, facts))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    arguments = parser.parse_args(argv)
    root = arguments.root.expanduser().resolve()
    errors = run_checks(root)
    if errors:
        print(f"documentation consistency: FAILED ({len(errors)} issue(s))", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    facts = load_facts(root)
    print(
        "documentation consistency: PASS "
        f"(version={facts['version']}, review_nodes={facts['review_workflow']['node_count']}, "
        f"tools={facts['tool_registry']['tool_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
