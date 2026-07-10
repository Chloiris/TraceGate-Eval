from __future__ import annotations

import os
import uuid

from sqlalchemy import inspect, text

from tracegate.retrieval import hybrid_retrieve
from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import require_current_revision, upgrade_database
from tracegate.studio.models import IndexVersion, IndexedFile, Repository


def main() -> None:
    database_url = os.environ.get("TRACEGATE_MYSQL_TEST_URL")
    if not database_url or not database_url.startswith("mysql+pymysql://"):
        raise SystemExit("TRACEGATE_MYSQL_TEST_URL must be an explicit mysql+pymysql test URL")
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    try:
        revision = require_current_revision(database.engine, database_url)
        tables = set(inspect(database.engine).get_table_names())
        required = {"repositories", "index_versions", "indexed_files", "indexed_content_fts"}
        if not required.issubset(tables):
            raise RuntimeError(f"MySQL migration is missing tables: {sorted(required - tables)}")
        with database.session_factory() as session:
            repository = Repository(
                id=str(uuid.uuid4()),
                owner="tracegate-ci",
                name="mysql-smoke",
                full_name=f"tracegate-ci/mysql-smoke-{uuid.uuid4().hex[:8]}",
                connection_status="ready",
            )
            session.add(repository)
            session.flush()
            version = IndexVersion(
                id=str(uuid.uuid4()),
                repository_id=repository.id,
                commit_sha=uuid.uuid4().hex + uuid.uuid4().hex[:8],
                status="ready",
                file_count=1,
                symbol_count=0,
                changed_count=1,
                deleted_count=0,
                duration_ms=1,
            )
            session.add(version)
            session.flush()
            file_id = str(uuid.uuid4())
            content = "tracegateuniquesymbol mysql full text verification"
            session.add(
                IndexedFile(
                    id=file_id,
                    index_version_id=version.id,
                    path="src/mysql_smoke.py",
                    language="python",
                    content_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    size_bytes=len(content),
                    capabilities_json=["token_scan"],
                    imports_json=[],
                    references_json=[],
                    content=content,
                )
            )
            session.flush()
            session.execute(
                text(
                    "INSERT INTO indexed_content_fts(index_version_id, file_id, path, content) "
                    "VALUES (:version, :file_id, :path, :content)"
                ),
                {
                    "version": version.id,
                    "file_id": file_id,
                    "path": "src/mysql_smoke.py",
                    "content": content,
                },
            )
            session.commit()
            result = hybrid_retrieve(session, repository.id, "tracegateuniquesymbol")
            if not any(hit.source == "mysql_fulltext" for hit in result.hits):
                raise RuntimeError("MySQL FULLTEXT result was not returned or was mislabeled")
        print(f"mysql_smoke=passed revision={revision}")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
