from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.check_docs_consistency import (
    ROOT,
    check_current_document_claims,
    check_historical_markers,
    check_relative_links,
    load_facts,
    run_checks,
    validate_facts_schema,
)


def test_current_repository_documentation_is_consistent() -> None:
    assert run_checks(ROOT) == []


def test_project_facts_schema_rejects_version_and_registry_drift() -> None:
    facts = deepcopy(load_facts(ROOT))
    facts["version"] = "v0.4"
    facts["tool_registry"]["tool_count"] += 1

    errors = validate_facts_schema(facts)

    assert any("stable MAJOR.MINOR.PATCH" in error for error in errors)
    assert any("tool_registry.tool_count" in error for error in errors)


def test_relative_link_check_covers_markdown_and_html(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "[missing](docs/missing.md)\n<img src=\"images/missing.png\" />\n",
        encoding="utf-8",
    )

    errors = check_relative_links(tmp_path, ["README.md"])

    assert len(errors) == 2
    assert all("missing relative link" in error for error in errors)


def test_historical_document_requires_explicit_marker(tmp_path: Path) -> None:
    record = tmp_path / "record.md"
    record.write_text("# Old run\n\n- SHA: deadbeef\n", encoding="utf-8")
    assert check_historical_markers(
        tmp_path, ["record.md"], "Historical verification record"
    )

    record.write_text(
        "# Old run\n\n> Historical verification record. Immutable evidence.\n",
        encoding="utf-8",
    )
    assert check_historical_markers(
        tmp_path, ["record.md"], "Historical verification record"
    ) == []


def test_current_claim_check_rejects_stale_branch_windows_state_mix_and_overclaim(
    tmp_path: Path,
) -> None:
    (tmp_path / "current.md").write_text(
        """# Current

Branch: `feat/old-work`
`VERIFIED_WINDOWS_CI` and `VERIFIED_WINDOWS_MANUAL` are complete.
Vector search is enabled.
""",
        encoding="utf-8",
    )
    facts = {
        "platforms": {
            "verified": {"windows_x86_64_manual": {"status": "BLOCKED"}}
        },
        "current_limitations": [],
        "documentation_policy": {
            "current_facing_documents": ["current.md"],
            "forbidden_stale_branches": ["feat/old-work"],
            "forbidden_unqualified_claim_patterns": [
                r"\bvector (?:search|retrieval) (?:is|was) (?:enabled|used|supported|verified)\b"
            ],
            "required_readme_limitations": {},
        },
    }

    errors = check_current_document_claims(tmp_path, facts)

    assert any("stale branch" in error for error in errors)
    assert any("mixes Windows CI/manual" in error for error in errors)
    assert any("forbidden unqualified" in error for error in errors)


def test_historical_scope_allows_an_old_branch_in_a_current_status_table(
    tmp_path: Path,
) -> None:
    (tmp_path / "current.md").write_text(
        "Historical: `feat/old-work` created the archived baseline.\n",
        encoding="utf-8",
    )
    facts = {
        "platforms": {
            "verified": {"windows_x86_64_manual": {"status": "BLOCKED"}}
        },
        "current_limitations": [],
        "documentation_policy": {
            "current_facing_documents": ["current.md"],
            "forbidden_stale_branches": ["feat/old-work"],
            "forbidden_unqualified_claim_patterns": [],
            "required_readme_limitations": {},
        },
    }

    assert check_current_document_claims(tmp_path, facts) == []
