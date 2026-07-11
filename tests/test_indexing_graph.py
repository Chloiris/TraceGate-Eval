from __future__ import annotations

import subprocess
from pathlib import Path

from tracegate.graph import build_repository_map
from tracegate.indexing import LanguageCapability, RepositoryIndexer, UnifiedCodeParser
from tracegate.repository import RepositoryBoundary


def test_parser_capability_matrix_is_explicit() -> None:
    parser = UnifiedCodeParser()
    python = parser.parse(
        "service.py", "import helper\n\ndef run():\n    return helper.work()\n"
    )
    typescript = parser.parse(
        "client.ts", "import {x} from './x';\nexport function load() {}"
    )
    java = parser.parse("Widget.java", "import java.util.List;\npublic class Widget {}")

    assert LanguageCapability.CALL_LEVEL in python.capabilities
    assert python.references[0].target == "helper.work"
    assert LanguageCapability.PARTIAL_ANALYSIS in typescript.capabilities
    assert LanguageCapability.PARTIAL_ANALYSIS in java.capabilities
    assert "./x" in typescript.imports
    assert "java.util.List" in java.imports


def _git(command: list[str], cwd: Path) -> None:
    subprocess.run(["git", *command], cwd=cwd, check=True, capture_output=True)


def test_incremental_index_and_map_use_real_commit_and_content(tmp_path: Path) -> None:
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "tracegate@example.invalid"], tmp_path)
    _git(["config", "user.name", "TraceGate Test"], tmp_path)
    (tmp_path / "helper.py").write_text("def work():\n    return 1\n", encoding="utf-8")
    (tmp_path / "service.py").write_text(
        "import helper\n\ndef run():\n    return helper.work()\n", encoding="utf-8"
    )
    _git(["add", "."], tmp_path)
    _git(["commit", "-qm", "initial"], tmp_path)

    indexer = RepositoryIndexer(RepositoryBoundary(tmp_path))
    first = indexer.build()
    assert first.commit_sha
    assert first.file_count == 2
    assert first.symbol_count == 2
    assert first.changed_paths == ("helper.py", "service.py")

    (tmp_path / "helper.py").write_text("def work():\n    return 2\n", encoding="utf-8")
    (tmp_path / "service.py").unlink()
    _git(["add", "-A"], tmp_path)
    _git(["commit", "-qm", "change"], tmp_path)
    second = indexer.build(first)
    assert second.changed_paths == ("helper.py",)
    assert second.deleted_paths == ("service.py",)

    repository_map = build_repository_map("repository-1", first)
    assert repository_map.commit_sha == first.commit_sha
    assert any(
        node.kind == "function" and node.label == "run" for node in repository_map.nodes
    )
    assert any(edge.kind == "import" for edge in repository_map.edges)


def test_repository_map_deduplicates_repeated_call_edges(tmp_path: Path) -> None:
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "tracegate@example.invalid"], tmp_path)
    _git(["config", "user.name", "TraceGate Test"], tmp_path)
    (tmp_path / "service.py").write_text(
        "def helper():\n    return 1\n\ndef run():\n    return helper() + helper()\n",
        encoding="utf-8",
    )
    _git(["add", "."], tmp_path)
    _git(["commit", "-qm", "repeated call"], tmp_path)

    snapshot = RepositoryIndexer(RepositoryBoundary(tmp_path)).build()
    repository_map = build_repository_map("repository-duplicate-calls", snapshot)
    call_edges = [edge for edge in repository_map.edges if edge.kind == "call"]

    assert len(call_edges) == 1
    assert len(repository_map.edges) == len({edge.id for edge in repository_map.edges})


def test_repository_map_distinguishes_redeclared_symbols(tmp_path: Path) -> None:
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "tracegate@example.invalid"], tmp_path)
    _git(["config", "user.name", "TraceGate Test"], tmp_path)
    (tmp_path / "compat.py").write_text(
        "if True:\n    def load():\n        return 1\nelse:\n    def load():\n        return 2\n",
        encoding="utf-8",
    )
    _git(["add", "."], tmp_path)
    _git(["commit", "-qm", "conditional declarations"], tmp_path)

    snapshot = RepositoryIndexer(RepositoryBoundary(tmp_path)).build()
    repository_map = build_repository_map("repository-redeclared-symbols", snapshot)
    load_nodes = [node for node in repository_map.nodes if node.label == "load"]

    assert len(load_nodes) == 2
    assert len({node.id for node in load_nodes}) == 2
