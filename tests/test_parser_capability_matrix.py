from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tracegate.graph import build_repository_map
from tracegate.indexing import (
    PARSER_CAPABILITY_MATRIX,
    CapabilityStatus,
    ParserFeature,
    RelationStatus,
    RepositoryIndexer,
    SymbolKind,
    UnifiedCodeParser,
    changed_symbols,
    map_changed_symbols,
)
from tracegate.repository import RepositoryBoundary
from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import IndexedFile, Repository


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "parser_repositories"
LANGUAGES = ("python", "javascript", "typescript", "java")


def _git(workspace: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repository(tmp_path: Path, language: str) -> Path:
    workspace = tmp_path / language
    shutil.copytree(FIXTURE_ROOT / language, workspace)
    _git(workspace, "init", "-q")
    _git(workspace, "config", "user.email", "parser-tests@tracegate.invalid")
    _git(workspace, "config", "user.name", "TraceGate Parser Tests")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"{language} parser fixture")
    return workspace


def _edge_paths(repository_map):  # type: ignore[no-untyped-def]
    nodes = {node.id: node for node in repository_map.nodes}
    return {
        (nodes[edge.source].path, nodes[edge.target].path, edge.kind)
        for edge in repository_map.edges
    }


def test_capability_matrix_is_complete_and_never_overstates_reference_or_call_support() -> None:
    expected_features = set(ParserFeature)
    assert set(PARSER_CAPABILITY_MATRIX) == set(LANGUAGES)
    for language, assessments in PARSER_CAPABILITY_MATRIX.items():
        assert set(assessments) == expected_features
        for assessment in assessments.values():
            assert assessment.status in CapabilityStatus
            if assessment.status == CapabilityStatus.PARTIAL:
                assert assessment.limitation
        if language != "python":
            assert assessments[ParserFeature.SYMBOL_REFERENCE].status == CapabilityStatus.UNSUPPORTED
            assert assessments[ParserFeature.FUNCTION_CALL].status == CapabilityStatus.UNSUPPORTED


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        ("module.py", "python"),
        ("module.js", "javascript"),
        ("module.jsx", "javascript"),
        ("module.ts", "typescript"),
        ("module.tsx", "typescript"),
        ("Module.java", "java"),
    ],
)
def test_file_recognition_is_explicit(filename: str, language: str) -> None:
    assert UnifiedCodeParser().language_for(Path(filename)) == language


def test_unknown_extension_is_not_mislabeled_as_a_supported_language() -> None:
    parsed = UnifiedCodeParser().parse("module.go", "package example")
    assert parsed.language == "unknown"
    assert not parsed.symbols


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_parser_fixture_is_a_real_commit_bound_git_repository(
    tmp_path: Path,
    language: str,
) -> None:
    workspace = _repository(tmp_path, language)
    snapshot = RepositoryIndexer(RepositoryBoundary(workspace)).build()

    assert snapshot.commit_sha == _git(workspace, "rev-parse", "HEAD")
    assert snapshot.files
    assert {item.parsed.language for item in snapshot.files.values()} == {language}


def test_python_ast_definitions_references_relations_and_ranges(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "python")
    parsed = UnifiedCodeParser().parse(
        "src/service.py",
        (workspace / "src" / "service.py").read_text(encoding="utf-8"),
    )
    symbols = {symbol.qualified_name: symbol for symbol in parsed.symbols}

    assert parsed.imports == (".helper",)
    assert parsed.exports == ()
    assert symbols["BaseService"].kind == SymbolKind.CLASS
    assert symbols["Service.run"].kind == SymbolKind.METHOD
    assert symbols["normalize"].kind == SymbolKind.FUNCTION
    assert symbols["Service.run"].end_line > symbols["Service.run"].start_line
    assert any(
        reference.target == "normalize"
        and reference.resolved
        and reference.status == RelationStatus.CONFIRMED
        for reference in parsed.references
    )
    assert any(
        reference.target == "helper"
        and not reference.resolved
        and reference.status == RelationStatus.UNKNOWN
        for reference in parsed.references
    )
    assert any(
        relation.source_symbol == "Service"
        and relation.target == "BaseService"
        and relation.status == RelationStatus.CONFIRMED
        for relation in parsed.relationships
    )


@pytest.mark.parametrize("language", ("javascript", "typescript"))
def test_ecmascript_adapters_report_only_partial_declarations(
    tmp_path: Path,
    language: str,
) -> None:
    workspace = _repository(tmp_path, language)
    extension = "js" if language == "javascript" else "ts"
    parsed = UnifiedCodeParser().parse(
        f"src/service.{extension}",
        (workspace / "src" / f"service.{extension}").read_text(encoding="utf-8"),
    )

    assert parsed.imports == (f"./helper{'.js' if language == 'javascript' else ''}",)
    assert {"BaseService", "Service", "normalize"} <= set(parsed.exports)
    assert {"BaseService", "Service", "normalize"} <= {symbol.name for symbol in parsed.symbols}
    assert "run" not in {symbol.name for symbol in parsed.symbols}
    assert not parsed.references
    assert parsed.relationships
    assert all(relation.status == RelationStatus.INFERRED for relation in parsed.relationships)
    normalize = next(symbol for symbol in parsed.symbols if symbol.name == "normalize")
    assert normalize.start_line == normalize.end_line


def test_typescript_interface_is_detected_but_not_semantically_resolved(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "typescript")
    parsed = UnifiedCodeParser().parse(
        "src/helper.ts",
        (workspace / "src" / "helper.ts").read_text(encoding="utf-8"),
    )
    source = next(symbol for symbol in parsed.symbols if symbol.name == "ValueSource")
    assert source.kind == SymbolKind.INTERFACE
    assert source.start_line == source.end_line


def test_java_adapter_reports_partial_types_methods_and_inferred_relations(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "java")
    path = workspace / "src" / "main" / "java" / "com" / "example" / "Service.java"
    parsed = UnifiedCodeParser().parse(
        "src/main/java/com/example/Service.java",
        path.read_text(encoding="utf-8"),
    )

    assert parsed.imports == ("com.example.Helper",)
    assert parsed.exports == ()
    assert {"Service", "run", "value"} <= {symbol.name for symbol in parsed.symbols}
    assert not parsed.references
    assert {relation.kind for relation in parsed.relationships} == {"inherit", "implement"}
    assert all(relation.status == RelationStatus.INFERRED for relation in parsed.relationships)
    run = next(symbol for symbol in parsed.symbols if symbol.name == "run")
    assert run.start_line == run.end_line


@pytest.mark.parametrize("language", LANGUAGES)
def test_repository_map_emits_only_confirmed_parser_edges(tmp_path: Path, language: str) -> None:
    workspace = _repository(tmp_path, language)
    snapshot = RepositoryIndexer(RepositoryBoundary(workspace)).build()
    repository_map = build_repository_map(f"parser-{language}", snapshot)
    paths = _edge_paths(repository_map)

    assert all(edge.confirmed for edge in repository_map.edges)
    assert any(kind == "import" for _source, _target, kind in paths)
    assert any(kind == "test" for _source, _target, kind in paths)
    if language == "python":
        assert any(edge.kind == "call" for edge in repository_map.edges)
        assert any(edge.kind == "inherit" for edge in repository_map.edges)
    else:
        assert not any(edge.kind in {"call", "inherit", "implement"} for edge in repository_map.edges)


@pytest.mark.parametrize("language", LANGUAGES)
def test_test_relationship_requires_conventional_test_file_and_resolved_import(
    tmp_path: Path,
    language: str,
) -> None:
    workspace = _repository(tmp_path, language)
    repository_map = build_repository_map(
        f"test-relationship-{language}",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    nodes = {node.id: node for node in repository_map.nodes}
    test_edges = [edge for edge in repository_map.edges if edge.kind == "test"]

    assert test_edges
    assert all(nodes[edge.source].kind == "test" for edge in test_edges)
    assert all(nodes[edge.target].kind == "file" for edge in test_edges)


def test_python_changed_symbol_mapping_uses_real_git_diff_and_ast_range(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "python")
    indexer = RepositoryIndexer(RepositoryBoundary(workspace))
    base = indexer.build()
    base_sha = base.commit_sha
    path = workspace / "src" / "service.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace("    return value\n", "    return value + 1\n", 1),
        encoding="utf-8",
    )
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "change one Python symbol body")
    head = indexer.build(base)
    diff = _git(workspace, "diff", f"{base_sha}...{head.commit_sha}")
    mapped = changed_symbols(head, diff)

    assert [symbol.qualified_name for symbol in mapped["src/service.py"]] == [
        "BaseService",
        "BaseService.identity",
    ]


@pytest.mark.parametrize(
    ("language", "relative_path", "symbol_name", "body_line_offset"),
    [
        ("javascript", "src/service.js", "normalize", 1),
        ("typescript", "src/service.ts", "normalize", 1),
        ("java", "src/main/java/com/example/Service.java", "run", 1),
    ],
)
def test_partial_line_ranges_map_declarations_but_not_function_bodies(
    tmp_path: Path,
    language: str,
    relative_path: str,
    symbol_name: str,
    body_line_offset: int,
) -> None:
    workspace = _repository(tmp_path, language)
    parsed = UnifiedCodeParser().parse(
        relative_path,
        (workspace / relative_path).read_text(encoding="utf-8"),
    )
    symbol = next(item for item in parsed.symbols if item.name == symbol_name)

    assert map_changed_symbols(parsed, [symbol.start_line]) == (symbol,)
    assert map_changed_symbols(parsed, [symbol.start_line + body_line_offset]) == ()


def test_partial_relationship_provenance_survives_incremental_database_index(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "typescript")
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'parser.db').as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    try:
        with database.session_factory() as session:
            repository = Repository(
                owner="tracegate-tests",
                name="typescript-parser",
                full_name="tracegate-tests/typescript-parser",
                local_path=str(workspace),
                connection_status="ready",
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)
            first, first_map = persist_repository_index(session, repository)
            service = (
                session.query(IndexedFile)
                .filter(
                    IndexedFile.index_version_id == first.id,
                    IndexedFile.path == "src/service.ts",
                )
                .one()
            )
            assert {"BaseService", "Service", "normalize"} <= set(service.exports_json)
            assert {item["status"] for item in service.relationships_json} == {"inferred"}
            assert not any(edge.kind in {"inherit", "implement"} for edge in first_map.edges)

        test_path = workspace / "tests" / "service.spec.ts"
        test_path.write_text(test_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        _git(workspace, "add", ".")
        _git(workspace, "commit", "-qm", "change only test file")

        with database.session_factory() as session:
            repository = session.query(Repository).one()
            second, second_map = persist_repository_index(session, repository)
            service = (
                session.query(IndexedFile)
                .filter(
                    IndexedFile.index_version_id == second.id,
                    IndexedFile.path == "src/service.ts",
                )
                .one()
            )
            assert {item["status"] for item in service.relationships_json} == {"inferred"}
            assert not any(edge.kind in {"inherit", "implement"} for edge in second_map.edges)
    finally:
        database.dispose()
