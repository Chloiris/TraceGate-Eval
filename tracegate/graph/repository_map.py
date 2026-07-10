from __future__ import annotations

import hashlib
from dataclasses import dataclass

from tracegate.indexing import IndexSnapshot


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    label: str
    path: str
    symbol: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    kind: str
    confirmed: bool = True


@dataclass(frozen=True)
class RepositoryMap:
    repository_id: str
    commit_sha: str
    index_version: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


def _id(prefix: str, value: str) -> str:
    return f"{prefix}:{hashlib.sha256(value.encode()).hexdigest()[:20]}"


def build_repository_map(repository_id: str, snapshot: IndexSnapshot) -> RepositoryMap:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    file_nodes: dict[str, str] = {}
    module_to_path: dict[str, str] = {}

    for path, indexed in sorted(snapshot.files.items()):
        file_id = _id("file", path)
        file_nodes[path] = file_id
        module_to_path[path.rsplit(".", 1)[0].replace("/", ".")] = path
        nodes.append(GraphNode(file_id, "file", path.rsplit("/", 1)[-1], path, language=indexed.parsed.language))
        for symbol in indexed.parsed.symbols:
            symbol_id = _id("symbol", f"{path}:{symbol.qualified_name}")
            nodes.append(
                GraphNode(
                    symbol_id,
                    symbol.kind.value,
                    symbol.name,
                    path,
                    symbol=symbol.qualified_name,
                    language=indexed.parsed.language,
                )
            )
            edges.append(GraphEdge(_id("edge", f"{file_id}:{symbol_id}:contains"), file_id, symbol_id, "contains"))

    for path, indexed in sorted(snapshot.files.items()):
        source = file_nodes[path]
        for imported in indexed.parsed.imports:
            normalized = imported.lstrip(".")
            target_path = module_to_path.get(normalized)
            if target_path:
                target = file_nodes[target_path]
                edges.append(GraphEdge(_id("edge", f"{source}:{target}:import"), source, target, "import"))
        symbols_by_name = {symbol.name: symbol for symbol in indexed.parsed.symbols}
        symbol_ids = {
            symbol.name: _id("symbol", f"{path}:{symbol.qualified_name}")
            for symbol in indexed.parsed.symbols
        }
        for reference in indexed.parsed.references:
            simple_target = reference.target.rsplit(".", 1)[-1]
            if reference.source_symbol and simple_target in symbols_by_name:
                source_id = _id("symbol", f"{path}:{reference.source_symbol}")
                target_id = symbol_ids[simple_target]
                edges.append(GraphEdge(_id("edge", f"{source_id}:{target_id}:call"), source_id, target_id, "call"))

    return RepositoryMap(
        repository_id=repository_id,
        commit_sha=snapshot.commit_sha,
        index_version=snapshot.id,
        nodes=tuple(nodes),
        edges=tuple(edges),
    )
