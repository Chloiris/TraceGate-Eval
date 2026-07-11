from __future__ import annotations

import time
import uuid
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from tracegate.graph import RepositoryMap, build_repository_map
from tracegate.indexing import (
    CodeReference,
    CodeSymbol,
    IndexSnapshot,
    LanguageCapability,
    ParsedFile,
    RelationStatus,
    RepositoryIndexer,
    TypeRelation,
)
from tracegate.indexing.indexer import IndexedFile as SnapshotFile
from tracegate.indexing.parser import SymbolKind
from tracegate.repository import RepositoryBoundary

from .models import (
    GraphEdgeRecord,
    GraphNodeRecord,
    IndexVersion,
    IndexedFile,
    IndexedSymbol,
    Repository,
)


class RepositoryIndexError(RuntimeError):
    """Raised when no commit-bound repository index can be persisted or loaded."""


def _latest_snapshot(session: Session, repository_id: str) -> IndexSnapshot | None:
    version = session.scalar(
        select(IndexVersion)
        .where(IndexVersion.repository_id == repository_id, IndexVersion.status == "ready")
        .order_by(IndexVersion.created_at.desc())
        .limit(1)
    )
    if version is None:
        return None
    rows = list(session.scalars(select(IndexedFile).where(IndexedFile.index_version_id == version.id)))
    files: dict[str, SnapshotFile] = {}
    for row in rows:
        symbols = list(session.scalars(select(IndexedSymbol).where(IndexedSymbol.indexed_file_id == row.id)))
        parsed = ParsedFile(
            path=row.path,
            language=row.language,
            capabilities=tuple(LanguageCapability(item) for item in row.capabilities_json),
            imports=tuple(row.imports_json),
            exports=tuple(row.exports_json),
            symbols=tuple(
                CodeSymbol(
                    name=item.name,
                    qualified_name=item.qualified_name,
                    kind=SymbolKind(item.kind),
                    signature=item.signature,
                    start_line=item.start_line,
                    end_line=item.end_line,
                )
                for item in symbols
            ),
            references=tuple(
                CodeReference(
                    **{
                        **item,
                        "status": RelationStatus(item.get("status", "unknown")),
                    }
                )
                for item in row.references_json
            ),
            relationships=tuple(
                TypeRelation(
                    **{
                        **item,
                        "status": RelationStatus(item.get("status", "unknown")),
                    }
                )
                for item in row.relationships_json
            ),
        )
        files[row.path] = SnapshotFile(row.path, row.content_hash, row.size_bytes, parsed)
    return IndexSnapshot(
        id=version.id,
        commit_sha=version.commit_sha,
        created_at_epoch=version.created_at.timestamp(),
        files=files,
        changed_paths=(),
        deleted_paths=(),
    )


def persist_repository_index(session: Session, repository: Repository) -> tuple[IndexVersion, RepositoryMap]:
    if not repository.local_path:
        raise RepositoryIndexError("Repository has no enrolled local workspace")
    try:
        boundary = RepositoryBoundary(Path(repository.local_path))
    except (OSError, ValueError) as exc:
        raise RepositoryIndexError(f"Repository workspace is unavailable: {exc}") from exc

    previous = _latest_snapshot(session, repository.id)
    started = time.monotonic()
    snapshot = RepositoryIndexer(boundary).build(previous)
    existing = session.scalar(
        select(IndexVersion).where(
            IndexVersion.repository_id == repository.id,
            IndexVersion.commit_sha == snapshot.commit_sha,
        )
    )
    if existing is not None:
        repository.current_commit_sha = existing.commit_sha
        repository.current_index_version = existing.id
        repository.updated_at = _utcnow()
        repository_map = load_repository_map(session, repository.id, existing.id)
        session.commit()
        return existing, repository_map

    version = IndexVersion(
        id=snapshot.id,
        repository_id=repository.id,
        commit_sha=snapshot.commit_sha,
        status="building",
        file_count=snapshot.file_count,
        symbol_count=snapshot.symbol_count,
        changed_count=len(snapshot.changed_paths),
        deleted_count=len(snapshot.deleted_paths),
        duration_ms=0,
        index_duration_ms=0,
        graph_duration_ms=0,
    )
    session.add(version)
    session.flush()

    file_ids: dict[str, str] = {}
    for path, item in sorted(snapshot.files.items()):
        absolute = boundary.resolve(path)
        content = absolute.read_text(encoding="utf-8", errors="replace")
        file_id = str(uuid.uuid4())
        file_ids[path] = file_id
        session.add(
            IndexedFile(
                id=file_id,
                index_version_id=version.id,
                path=path,
                language=item.parsed.language,
                content_hash=item.content_hash,
                size_bytes=item.size_bytes,
                capabilities_json=[capability.value for capability in item.parsed.capabilities],
                imports_json=list(item.parsed.imports),
                exports_json=list(item.parsed.exports),
                references_json=[
                    {
                        "source_symbol": reference.source_symbol,
                        "target": reference.target,
                        "kind": reference.kind,
                        "line": reference.line,
                        "resolved": reference.resolved,
                        "status": reference.status.value,
                    }
                    for reference in item.parsed.references
                ],
                relationships_json=[
                    {
                        "source_symbol": relation.source_symbol,
                        "target": relation.target,
                        "kind": relation.kind,
                        "line": relation.line,
                        "status": relation.status.value,
                    }
                    for relation in item.parsed.relationships
                ],
                content=content,
            )
        )
        for symbol in item.parsed.symbols:
            session.add(
                IndexedSymbol(
                    indexed_file_id=file_id,
                    name=symbol.name,
                    qualified_name=symbol.qualified_name,
                    kind=symbol.kind.value,
                    signature=symbol.signature,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                )
            )
        session.execute(
            text(
                "INSERT INTO indexed_content_fts(index_version_id, file_id, path, content) "
                "VALUES (:version, :file_id, :path, :content)"
            ),
            {"version": version.id, "file_id": file_id, "path": path, "content": content},
        )

    graph_started = time.monotonic()
    version.index_duration_ms = int((graph_started - started) * 1000)
    repository_map = build_repository_map(repository.id, snapshot)
    for node in repository_map.nodes:
        session.add(
            GraphNodeRecord(
                id=node.id,
                index_version_id=version.id,
                kind=node.kind,
                label=node.label,
                path=node.path,
                symbol=node.symbol,
                language=node.language,
            )
        )
    for edge in repository_map.edges:
        session.add(
            GraphEdgeRecord(
                id=edge.id,
                index_version_id=version.id,
                source=edge.source,
                target=edge.target,
                kind=edge.kind,
                confirmed=edge.confirmed,
            )
        )

    version.graph_duration_ms = int((time.monotonic() - graph_started) * 1000)
    version.status = "ready"
    version.duration_ms = int((time.monotonic() - started) * 1000)
    repository.current_commit_sha = snapshot.commit_sha
    repository.current_index_version = version.id
    repository.updated_at = _utcnow()
    session.commit()
    session.refresh(version)
    return version, repository_map


def load_repository_map(session: Session, repository_id: str, index_version_id: str | None = None) -> RepositoryMap:
    version = (
        session.get(IndexVersion, index_version_id)
        if index_version_id
        else session.scalar(
            select(IndexVersion)
            .where(IndexVersion.repository_id == repository_id, IndexVersion.status == "ready")
            .order_by(IndexVersion.created_at.desc())
            .limit(1)
        )
    )
    if version is None or version.repository_id != repository_id:
        raise RepositoryIndexError("Repository has no ready index")
    from tracegate.graph import GraphEdge, GraphNode

    nodes = list(session.scalars(select(GraphNodeRecord).where(GraphNodeRecord.index_version_id == version.id)))
    edges = list(session.scalars(select(GraphEdgeRecord).where(GraphEdgeRecord.index_version_id == version.id)))
    return RepositoryMap(
        repository_id=repository_id,
        commit_sha=version.commit_sha,
        index_version=version.id,
        nodes=tuple(GraphNode(item.id, item.kind, item.label, item.path, item.symbol, item.language) for item in nodes),
        edges=tuple(GraphEdge(item.id, item.source, item.target, item.kind, item.confirmed) for item in edges),
    )


def delete_index_version(session: Session, version_id: str) -> None:
    session.execute(text("DELETE FROM indexed_content_fts WHERE index_version_id = :version"), {"version": version_id})
    session.execute(delete(IndexVersion).where(IndexVersion.id == version_id))


def _utcnow():  # type: ignore[no-untyped-def]
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
