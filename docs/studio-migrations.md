# TraceGate Studio database migrations

Studio uses Alembic through `tracegate/studio/migrations`. Startup upgrades an
explicit database URL to `head`; it does not create missing production tables
with ORM `create_all`.

| Revision | Purpose | SQLite / MySQL notes |
| --- | --- | --- |
| `20260710_0001` | Settings, onboarding, repositories, syncs, PRs/snapshots, runs/steps/tools, findings/evidence and events | Shared relational foundation and singleton settings/onboarding rows. |
| `20260710_0002` | Commit-bound index versions/files/symbols, graph nodes/edges and searchable document store | SQLite creates FTS5 virtual storage; MySQL creates an InnoDB table plus `FULLTEXT(path, content)`. |
| `20260710_0003` | Durable GitHub webhook delivery IDs, payload hashes, processing state and target PR metadata | Unique delivery identity supports replay deduplication on both engines. |

Local SQLite verification:

```bash
TRACEGATE_LOCAL_API_TOKEN="$(openssl rand -hex 32)" \
TRACEGATE_DATA_DIR="$PWD/.tracegate-dev" \
  uv run tracegate-studio serve
uv run pytest -q tests/test_studio_database.py
```

Sidecar startup calls the programmatic Alembic runner before accepting API
traffic. Migration-only automation may import
`tracegate.studio.migration_runner.upgrade_database` with an explicit URL.

MySQL 8 verification (requires Docker, unavailable on the recorded macOS host):

```bash
docker compose -f docker-compose.mysql.yml up -d --wait
TRACEGATE_DATABASE_URL='mysql+pymysql://tracegate:tracegate@127.0.0.1:3306/tracegate' \
  uv run python scripts/mysql_smoke.py
docker compose -f docker-compose.mysql.yml down -v
```

CI runs the MySQL 8.4 service/profile independently. Offline dialect SQL can be
compiled without a server and is useful for reviewing generated DDL, but it is
not a substitute for the integration smoke or a production backup/restore
test.
