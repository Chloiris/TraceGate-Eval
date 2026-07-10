from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from tracegate.repository import RepositoryBoundary
from tracegate.vcs import GitProvider

from .parser import ParsedFile, UnifiedCodeParser


@dataclass(frozen=True)
class IndexedFile:
    path: str
    content_hash: str
    size_bytes: int
    parsed: ParsedFile


@dataclass(frozen=True)
class IndexSnapshot:
    id: str
    commit_sha: str
    created_at_epoch: float
    files: dict[str, IndexedFile]
    changed_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def symbol_count(self) -> int:
        return sum(len(item.parsed.symbols) for item in self.files.values())


class RepositoryIndexer:
    def __init__(self, boundary: RepositoryBoundary, parser: UnifiedCodeParser | None = None) -> None:
        self.boundary = boundary
        self.parser = parser or UnifiedCodeParser()

    def build(self, previous: IndexSnapshot | None = None) -> IndexSnapshot:
        commit_sha = GitProvider(self.boundary).head_sha()
        previous_files = previous.files if previous else {}
        files: dict[str, IndexedFile] = {}
        changed: list[str] = []

        for path in self.boundary.iter_files():
            relative = self.boundary.relative(path)
            language = self.parser.language_for(path)
            if language is None:
                continue
            raw = path.read_bytes()
            if b"\0" in raw[:4096]:
                continue
            digest = hashlib.sha256(raw).hexdigest()
            prior = previous_files.get(relative)
            if prior and prior.content_hash == digest:
                files[relative] = prior
                continue
            content = raw.decode("utf-8", errors="replace")
            files[relative] = IndexedFile(
                path=relative,
                content_hash=digest,
                size_bytes=len(raw),
                parsed=self.parser.parse(relative, content),
            )
            changed.append(relative)

        deleted = sorted(set(previous_files) - set(files))
        return IndexSnapshot(
            id=str(uuid.uuid4()),
            commit_sha=commit_sha,
            created_at_epoch=time.time(),
            files=files,
            changed_paths=tuple(sorted(changed)),
            deleted_paths=tuple(deleted),
        )
