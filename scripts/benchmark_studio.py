from __future__ import annotations

import argparse
import json
import platform
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from tracegate.studio.api import _review_map
from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import PullRequest, Repository


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.stdout.strip()


def _source(index: int) -> str:
    dependency = (
        f"from src.module_{index - 1:04d} import function_{index - 1:04d}\n\n"
        if index
        else ""
    )
    body = (
        f"    return function_{index - 1:04d}(value) + 1\n"
        if index
        else "    return value + 1\n"
    )
    return dependency + f"def function_{index:04d}(value: int) -> int:\n" + body


def _prepare_repository(workspace: Path, file_count: int) -> tuple[str, str]:
    source_root = workspace / "src"
    source_root.mkdir(parents=True)
    (source_root / "__init__.py").write_text("", encoding="utf-8")
    for index in range(file_count - 1):
        (source_root / f"module_{index:04d}.py").write_text(_source(index), encoding="utf-8")
    _git(workspace, "init", "-q")
    _git(workspace, "config", "user.email", "benchmark@tracegate.invalid")
    _git(workspace, "config", "user.name", "TraceGate Benchmark")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"base with {file_count} files")
    base_sha = _git(workspace, "rev-parse", "HEAD")
    changed = min(10, file_count - 1)
    for index in range(changed):
        path = source_root / f"module_{index:04d}.py"
        path.write_text(path.read_text(encoding="utf-8") + "\nBENCHMARK_MARKER = True\n", encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "benchmark pull request head")
    return base_sha, _git(workspace, "rev-parse", "HEAD")


def benchmark(file_count: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"tracegate-benchmark-{file_count}-") as raw:
        root = Path(raw)
        workspace = root / "repository"
        workspace.mkdir()
        base_sha, head_sha = _prepare_repository(workspace, file_count)
        database_url = f"sqlite+pysqlite:///{(root / 'studio.db').as_posix()}"
        upgrade_database(database_url)
        database = StudioDatabase(database_url)
        try:
            with database.session_factory() as session:
                repository = Repository(
                    owner="tracegate-benchmark",
                    name=f"files-{file_count}",
                    full_name=f"tracegate-benchmark/files-{file_count}",
                    local_path=str(workspace),
                    connection_status="ready",
                )
                session.add(repository)
                session.commit()
                session.refresh(repository)

                started = time.perf_counter()
                version, repository_map = persist_repository_index(session, repository)
                persisted_elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                pull_request = PullRequest(
                    repository_id=repository.id,
                    number=1,
                    title="Local benchmark change",
                    state="open",
                    url="https://github.invalid/tracegate-benchmark/pull/1",
                    base_sha=base_sha,
                    head_sha=head_sha,
                    changed_files=min(10, file_count - 1),
                )
                session.add(pull_request)
                session.commit()
                session.refresh(pull_request)

                review_started = time.perf_counter()
                review_map = _review_map(pull_request.id, session)
                review_elapsed_ms = round((time.perf_counter() - review_started) * 1000, 2)
                return {
                    "requested_file_count": file_count,
                    "indexed_file_count": version.file_count,
                    "symbol_count": version.symbol_count,
                    "repository_map_nodes": len(repository_map.nodes),
                    "repository_map_edges": len(repository_map.edges),
                    "index_and_persist_wall_ms": persisted_elapsed_ms,
                    "production_index_duration_ms": version.index_duration_ms,
                    "production_graph_duration_ms": version.graph_duration_ms,
                    "production_total_duration_ms": version.duration_ms,
                    "review_map_wall_ms": review_elapsed_ms,
                    "review_map_nodes": len(review_map.nodes),
                    "review_map_edges": len(review_map.edges),
                    "review_map_truncated": review_map.truncated,
                }
        finally:
            database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local TraceGate Studio production-path benchmarks.")
    parser.add_argument("--files", type=int, nargs="+", default=[100, 1000])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if any(count < 10 or count > 5000 for count in args.files):
        raise SystemExit("--files values must be between 10 and 5000")
    payload = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "operating_system": platform.platform(),
            "architecture": platform.machine(),
            "processor": platform.processor() or "not reported by platform module",
            "python": platform.python_version(),
        },
        "method": "Temporary local Git repositories; production RepositoryIndexer, persistence, Repository Map, and Review Map paths; one warm-free run per size.",
        "limitations": [
            "Synthetic source layout is deterministic and is not a substitute for a large polyglot repository.",
            "One run per size is a smoke benchmark, not a statistically stable latency distribution.",
            "GitHub PR synchronization and UI time-to-interactive are not measured by this local Python benchmark.",
        ],
        "results": [benchmark(count) for count in args.files],
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
