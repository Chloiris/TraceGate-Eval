from __future__ import annotations

import hashlib
import posixpath
from dataclasses import dataclass

from tracegate.indexing import IndexSnapshot, RelationStatus


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


def symbol_node_id(path: str, qualified_name: str, start_line: int) -> str:
    # Conditional or compatibility branches may declare the same qualified
    # symbol more than once in one file. The declaration line keeps each real
    # graph node stable and distinct.
    return _id("symbol", f"{path}:{qualified_name}:{start_line}")


def _is_test_file(path: str) -> bool:
    basename = path.rsplit("/", 1)[-1]
    stem = basename.rsplit(".", 1)[0]
    return (
        basename.startswith("test_")
        or basename.endswith(
            (".test.js", ".test.jsx", ".test.ts", ".test.tsx", ".spec.js", ".spec.ts")
        )
        or stem.endswith(("Test", "Tests"))
        or "/tests/" in f"/{path}/"
        or "/test/" in f"/{path}/"
    )


def _resolve_import_path(
    source_path: str,
    imported: str,
    language: str,
    available_paths: set[str],
) -> str | None:
    """Resolve only exact, unique local module paths; external/ambiguous imports stay absent."""
    if language == "python":
        leading = len(imported) - len(imported.lstrip("."))
        suffix = imported.lstrip(".")
        if leading:
            source_parts = source_path.rsplit("/", 1)[0].split("/") if "/" in source_path else []
            keep = max(0, len(source_parts) - (leading - 1))
            parts = [*source_parts[:keep], *([item for item in suffix.split(".") if item])]
        else:
            parts = [item for item in suffix.split(".") if item]
        if not parts:
            return None
        candidates = {"/".join(parts) + ".py", "/".join(parts) + "/__init__.py"}
    elif language in {"javascript", "typescript"}:
        if not imported.startswith("."):
            return None
        parent = source_path.rsplit("/", 1)[0] if "/" in source_path else ""
        base = posixpath.normpath(posixpath.join(parent, imported))
        candidates = {base}
        if not any(base.endswith(extension) for extension in (".js", ".jsx", ".ts", ".tsx")):
            candidates.update(
                {
                    *(base + extension for extension in (".js", ".jsx", ".ts", ".tsx")),
                    *(base + "/index" + extension for extension in (".js", ".jsx", ".ts", ".tsx")),
                }
            )
    elif language == "java":
        if imported.endswith(".*"):
            return None
        suffix = imported.replace(".", "/") + ".java"
        candidates = {path for path in available_paths if path.endswith(suffix)}
    else:
        return None
    matches = sorted(candidates & available_paths)
    return matches[0] if len(matches) == 1 else None


def build_repository_map(repository_id: str, snapshot: IndexSnapshot) -> RepositoryMap:
    repository_node = _id("repository", repository_id)
    nodes: list[GraphNode] = [
        GraphNode(repository_node, "repository", "Repository", ".")
    ]
    edges: list[GraphEdge] = []
    file_nodes: dict[str, str] = {}
    directory_nodes: dict[str, str] = {}
    available_paths = set(snapshot.files)

    def ensure_directory(path: str) -> str:
        existing = directory_nodes.get(path)
        if existing:
            return existing
        node_id = _id("directory", path)
        directory_nodes[path] = node_id
        nodes.append(GraphNode(node_id, "directory", path.rsplit("/", 1)[-1], path))
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        parent_id = ensure_directory(parent) if parent else repository_node
        edges.append(
            GraphEdge(
                _id("edge", f"{parent_id}:{node_id}:contains"),
                parent_id,
                node_id,
                "contains",
            )
        )
        return node_id

    for path, indexed in sorted(snapshot.files.items()):
        file_id = _id("file", path)
        file_nodes[path] = file_id
        basename = path.rsplit("/", 1)[-1]
        test_file = _is_test_file(path)
        nodes.append(
            GraphNode(
                file_id,
                "test" if test_file else "file",
                basename,
                path,
                language=indexed.parsed.language,
            )
        )
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        parent_id = ensure_directory(parent) if parent else repository_node
        edges.append(
            GraphEdge(
                _id("edge", f"{parent_id}:{file_id}:contains"),
                parent_id,
                file_id,
                "contains",
            )
        )
        for symbol in indexed.parsed.symbols:
            symbol_id = symbol_node_id(path, symbol.qualified_name, symbol.start_line)
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
            edges.append(
                GraphEdge(
                    _id("edge", f"{file_id}:{symbol_id}:contains"),
                    file_id,
                    symbol_id,
                    "contains",
                )
            )

    for path, indexed in sorted(snapshot.files.items()):
        source = file_nodes[path]
        for imported in indexed.parsed.imports:
            target_path = _resolve_import_path(
                path,
                imported,
                indexed.parsed.language,
                available_paths,
            )
            if target_path:
                target = file_nodes[target_path]
                kind = "test" if _is_test_file(path) else "import"
                edges.append(
                    GraphEdge(
                        _id("edge", f"{source}:{target}:{kind}"),
                        source,
                        target,
                        kind,
                    )
                )
        symbols_by_name = {symbol.name: symbol for symbol in indexed.parsed.symbols}
        type_symbols_by_name = {
            symbol.name: symbol
            for symbol in indexed.parsed.symbols
            if symbol.kind.value in {"class", "interface"}
        }
        symbol_ids = {
            symbol.name: symbol_node_id(path, symbol.qualified_name, symbol.start_line)
            for symbol in indexed.parsed.symbols
        }
        symbol_ids_by_qualified: dict[str, str] = {}
        for symbol in indexed.parsed.symbols:
            symbol_ids_by_qualified.setdefault(
                symbol.qualified_name,
                symbol_node_id(path, symbol.qualified_name, symbol.start_line),
            )
        for reference in indexed.parsed.references:
            if not reference.resolved or reference.status != RelationStatus.CONFIRMED:
                continue
            simple_target = reference.target.rsplit(".", 1)[-1]
            if reference.source_symbol and simple_target in symbols_by_name:
                source_id = symbol_ids_by_qualified.get(reference.source_symbol)
                if source_id is None:
                    continue
                target_id = symbol_ids[simple_target]
                edges.append(
                    GraphEdge(
                        _id("edge", f"{source_id}:{target_id}:call"),
                        source_id,
                        target_id,
                        "call",
                    )
                )
        for relation in indexed.parsed.relationships:
            if relation.status != RelationStatus.CONFIRMED:
                continue
            source_id = symbol_ids_by_qualified.get(relation.source_symbol)
            target_symbol = type_symbols_by_name.get(relation.target)
            if source_id is None or target_symbol is None:
                continue
            target_id = symbol_node_id(
                path,
                target_symbol.qualified_name,
                target_symbol.start_line,
            )
            edges.append(
                GraphEdge(
                    _id("edge", f"{source_id}:{target_id}:{relation.kind}"),
                    source_id,
                    target_id,
                    relation.kind,
                )
            )

    unique_edges = tuple(dict.fromkeys(edges))
    return RepositoryMap(
        repository_id=repository_id,
        commit_sha=snapshot.commit_sha,
        index_version=snapshot.id,
        nodes=tuple(nodes),
        edges=unique_edges,
    )
