from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from tracegate.studio.models import GraphEdgeRecord, GraphNodeRecord, IndexedFile, IndexedSymbol, IndexVersion


@dataclass(frozen=True)
class RetrievalHit:
    kind: str
    path: str
    score: float
    source: str
    snippet: str
    symbol: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class HybridRetrievalResult:
    repository_id: str
    index_version: str
    commit_sha: str
    query: str
    hits: tuple[RetrievalHit, ...]
    vector_search_enabled: bool = False
    vector_search_message: str = "Vector semantic retrieval is not enabled; no keyword result is labelled as vector search."


def _fts_expression(query: str) -> str:
    tokens = re.findall(r"[\w.-]+", query, flags=re.UNICODE)[:12]
    if not tokens:
        raise ValueError("retrieval query must contain searchable characters")
    return " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens)


def hybrid_retrieve(
    session: Session,
    repository_id: str,
    query: str,
    *,
    limit: int = 30,
) -> HybridRetrievalResult:
    version = session.scalar(
        select(IndexVersion)
        .where(IndexVersion.repository_id == repository_id, IndexVersion.status == "ready")
        .order_by(IndexVersion.created_at.desc())
        .limit(1)
    )
    if version is None:
        raise ValueError("repository has no ready index")
    bounded_limit = max(1, min(limit, 100))
    hits: dict[tuple[str, str, str | None], RetrievalHit] = {}

    exact_files = list(
        session.scalars(
            select(IndexedFile).where(
                IndexedFile.index_version_id == version.id,
                IndexedFile.path.contains(query),
            ).limit(bounded_limit)
        )
    )
    for row in exact_files:
        key = ("file", row.path, None)
        hits[key] = RetrievalHit("file", row.path, 100.0, "path", row.path)

    symbol_rows = session.execute(
        select(IndexedSymbol, IndexedFile)
        .join(IndexedFile, IndexedFile.id == IndexedSymbol.indexed_file_id)
        .where(
            IndexedFile.index_version_id == version.id,
            IndexedSymbol.name.contains(query),
        )
        .limit(bounded_limit)
    ).all()
    for symbol, file_row in symbol_rows:
        key = ("symbol", file_row.path, symbol.qualified_name)
        hits[key] = RetrievalHit(
            "symbol",
            file_row.path,
            90.0,
            "symbol",
            symbol.signature,
            symbol.qualified_name,
            symbol.start_line,
        )

    dialect = session.get_bind().dialect.name
    if dialect == "mysql":
        rows = session.execute(
            text(
                "SELECT path, LEFT(content, 2000) AS snippet, "
                "MATCH(path, content) AGAINST (:query IN NATURAL LANGUAGE MODE) AS relevance_score "
                "FROM indexed_content_fts WHERE index_version_id = :version "
                "AND MATCH(path, content) AGAINST (:query IN NATURAL LANGUAGE MODE) "
                "ORDER BY relevance_score DESC LIMIT :limit"
            ),
            {"query": query, "version": version.id, "limit": bounded_limit},
        ).all()
    else:
        rows = session.execute(
            text(
                "SELECT path, snippet(indexed_content_fts, 3, '[', ']', ' … ', 24) AS snippet, "
                "bm25(indexed_content_fts) AS rank "
                "FROM indexed_content_fts WHERE indexed_content_fts MATCH :query "
                "AND index_version_id = :version ORDER BY rank LIMIT :limit"
            ),
            {"query": _fts_expression(query), "version": version.id, "limit": bounded_limit},
        ).all()
    for path, snippet, rank in rows:
        key = ("file", path, None)
        score = 70.0 + max(-20.0, min(20.0, float(rank) if dialect == "mysql" else -float(rank)))
        current = hits.get(key)
        candidate = RetrievalHit(
            "file",
            path,
            score,
            "mysql_fulltext" if dialect == "mysql" else "fts5",
            str(snippet)[:2000],
        )
        if current is None or candidate.score > current.score:
            hits[key] = candidate

    matching_nodes = list(
        session.scalars(
            select(GraphNodeRecord).where(
                GraphNodeRecord.index_version_id == version.id,
                GraphNodeRecord.label.contains(query),
            ).limit(bounded_limit)
        )
    )
    node_ids = [node.id for node in matching_nodes]
    if node_ids:
        edges = session.execute(
            select(GraphEdgeRecord).where(
                GraphEdgeRecord.index_version_id == version.id,
                (GraphEdgeRecord.source.in_(node_ids) | GraphEdgeRecord.target.in_(node_ids)),
            ).limit(bounded_limit)
        ).scalars()
        neighbor_ids = {edge.target if edge.source in node_ids else edge.source for edge in edges}
        neighbors = session.scalars(
            select(GraphNodeRecord).where(
                GraphNodeRecord.index_version_id == version.id,
                GraphNodeRecord.id.in_(neighbor_ids),
            )
        )
        for node in neighbors:
            key = ("graph_neighbor", node.path, node.symbol)
            hits.setdefault(
                key,
                RetrievalHit("graph_neighbor", node.path, 45.0, "graph", node.label, node.symbol),
            )

    ordered = tuple(sorted(hits.values(), key=lambda item: (-item.score, item.path, item.symbol or ""))[:bounded_limit])
    return HybridRetrievalResult(repository_id, version.id, version.commit_sha, query, ordered)
