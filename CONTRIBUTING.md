# Contributing to TraceGate

## Principles

- Preserve real-data provenance and existing metric definitions.
- Expose missing configuration and failures; never add a silent fallback,
  fixture-backed production path, or fabricated semantic result.
- Keep credentials, private repository content, databases, logs, raw model
  output, and local run artifacts out of Git.
- Bind indexes, Evidence, Findings, and reports to a real commit identity.

## Local setup

```bash
./scripts/bootstrap.sh
./scripts/dev.sh
```

Before committing:

```bash
./scripts/test.sh
pnpm test:e2e
```

Schema changes must include an Alembic migration, Python response schema,
shared Zod contract, API-client update, and SQLite migration tests. Platform
claims need platform evidence: local macOS results do not verify Windows, and
Windows CI does not replace Windows GUI/manual acceptance.

Use Conventional Commits and keep each commit focused. Document architecture
changes in `docs/architecture/` and update `docs/implementation-status.md` with
the exact test, artifact, log, screenshot, API response, database record, or
commit that supports the status.

