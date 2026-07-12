# TraceGate Studio current baseline

> **Historical verification record.** This file intentionally preserves the
> pre-Studio baseline, including its original branch, SHA and test counts.

- Audit date: 2026-07-10 (Asia/Shanghai)
- Audited commit: `76a23abb8c626af85ca2fdd05cb249d7be8040af`
- Starting branch: `main` (clean and aligned with `origin/main`)
- Working branch created: `feat/tracegate-studio-fullstack`
- Repository root: `/Users/chologonia/projects/TraceGate Eval/TraceGate-Eval`
- Host: macOS 26.5.1, Apple M5, arm64

This document records the repository before TraceGate Studio implementation.
It is evidence, not a target-state feature list.

## Current directory structure

```text
.github/workflows/         Linux/macOS Python CI and two PR advisory workflows
datasets/real_min/         public real-PR cases, provenance and accepted labels
docs/                      benchmark, audit, release and handoff documentation
examples/                  minimal inputs/outputs and advisory examples
experiments/               Stage1/2/3 task, context, model and oracle YAML
reports*/                  checked-in benchmark report artifacts
results/                   checked-in metric summaries and figures
sample_repos/              controlled Java/Spring ClaimBench repositories
scripts/                   dataset, report, advisory and developer scripts
tests/                     Python tests
tracegate/                 Python package and CLI
  claims/                  claim extraction, routing and evidence resolution
  context(s)/              prompt context selection/building
  core/                    policies, models, metrics and guardrails
  data/                    public dataset discovery/normalization/validation
  dataset/                 controlled benchmark generation
  metrics/                 execution, semantic, safety and evidence metrics
  pr_advisor/              live EvidencePacket, DeepSeek judge and verifier
  reports/                 Markdown/CSV/HTML report builders
  runners/                 benchmark and command runners
  web/                     server-rendered lightweight FastAPI dashboard
```

At baseline there is no React workspace, TypeScript package, Tauri/Rust crate,
SQLAlchemy model layer, Alembic directory, Sidecar packaging, or pnpm/Cargo/uv
lock file.

## Current entry points

- Installed CLI: `tracegate = tracegate.cli:main`
- Module CLI: `python -m tracegate`
- Legacy web app: `tracegate.web.app:app`
- Legacy web command: `python -m tracegate web`
- Rule PR advisory: `python -m tracegate run ...`
- Semantic PR advisory: `python -m tracegate pr analyze ...`
- Existing GitHub Actions: `.github/workflows/ci.yml`,
  `tracegate-advisory.yml`, and `tracegate-semantic-advisory.yml`

The FastAPI app exposes unversioned `/api/*` benchmark routes. It is a
lightweight dashboard, not the requested Studio service.

## Current run method

The tracked project metadata requires Python 3.11 or newer. The existing local
virtual environment uses Python 3.12.13:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m tracegate --help
./.venv/bin/python -m tracegate web --host 127.0.0.1 --port 8000
```

The host's default `python3` is 3.9.6 and does not satisfy the project
requirement. The host PATH initially contains no `node`, `pnpm`, `uv`, `rustc`,
or `cargo`. Codex provides a bundled Node and pnpm runtime, but a Rust toolchain
has not yet been confirmed. Java 17 and Maven 3.9.16 are available (Maven itself
reports a separate Java 26 runtime).

## Baseline test results

Commands were executed on the audited commit before product implementation.

| Command | Result |
| --- | --- |
| `./.venv/bin/python -m pip check` | PASS: no broken requirements |
| `./.venv/bin/python -m pytest -q` | PASS: 61 tests in 0.59 s |
| `./.venv/bin/python -m compileall -q tracegate tests scripts` | PASS |
| `./.venv/bin/python -m tracegate --help` | PASS |
| `./.venv/bin/python -m tracegate guardrails scan --strict` | Exit 0; 380 classified keyword findings, 0 dangerous runtime paths |
| `./.venv/bin/python -m tracegate data validate --dataset datasets/real_min/cases.jsonl --strict --min-cases 8` | PASS: total/scored/excluded = 19/19/0 |
| FastAPI TestClient for health, overview, groups, statuses, tasks and results | PASS: HTTP 200; 8 groups, 4 statuses, 20 tasks, 160 result rows |
| Temporary Uvicorn health/overview/dashboard smoke | PASS: HTTP 200 and graceful shutdown |

Pytest emitted one Starlette deprecation warning from the installed FastAPI
test client. The guardrail command regenerated `docs/FALLBACK_AUDIT.md`; the
increase from 319 to 380 entries reflects current files/line locations and is
not a count of confirmed vulnerabilities.

## Current completed modules

- Controlled ClaimBench generation, execution protocol, result collection and
  checked-in 160-run summaries.
- Public real-PR dataset ingestion, provenance, validation, hard-label
  promotion and a 19-case checked-in result set.
- Evidence states `active`, `stale`, `unknown`, and `conflicting` with expected
  safe decisions.
- Rule-based changed-file PR advisory.
- DeepSeek semantic PR advisory with explicit real-only/no-mock/no-fallback
  gates, structured JSON validation, bounded retry and fail-fast missing-key
  behaviour.
- EvidencePacket construction, text/secret redaction and verifier downgrades.
- Reality guardrail scanner and report validation.
- Lightweight FastAPI benchmark dashboard and API.
- Python CI on Ubuntu and macOS plus PR advisory workflows.

## Baseline blockers and subsequent disposition

- The original audit found no model credential in the process environment. On
  2026-07-11, a credential stored under the macOS Keychain service
  `deepseek-api-key` was injected directly into a child process without logging
  its value. The production DeepSeek provider and full public-PR workflow are
  now `VERIFIED_MACOS`; see `docs/verification/real-model-e2e-macos.md`.
- The original authenticated-GitHub blocker was subsequently cleared through
  the existing `gh` session. Public PR metadata and exact Git revisions were
  fetched for the real-model verification without persisting a GitHub token.
- React, TypeScript, browser E2E and Tauri builds do not yet exist at baseline.
- Rust/Tauri tests cannot run until a Rust toolchain is located or installed.
- Windows binaries and Windows manual behaviour cannot be produced or verified
  on this Mac. No Windows CI artifact for Studio exists at baseline.
- SQLite application persistence, Alembic migrations and the optional MySQL
  profile do not exist at baseline.

## Mock, fallback, hard-coded and outdated paths found

The audit distinguishes controlled fixtures and clearly labelled demos from
production risks.

- `tracegate/web/service.py::analyze_demo` is a keyword/rule demonstration. Its
  response says `data_source=rule_based_demo`; it must never feed the Studio
  semantic analysis path or be presented as model output.
- `tracegate/web/data_loader.py` contains hard-coded aggregate and task
  fallbacks. They are labelled `project_summary_fallback` and do not fabricate
  run logs, but they activate silently when result files are absent. Studio
  production APIs must expose a missing-data error/status instead of using
  these fallbacks. Its aggregate `data_source` check can also report
  `real_results` for a mixed real/fallback payload because it does not inspect
  every evidence/task source.
- Tests contain mock/fake/synthetic fixtures by design. Existing real-run gates
  reject them from real metrics; that separation must be preserved.
- Checked-in report and dataset artifacts are historical evidence and must not
  be regenerated or relabelled merely to improve product presentation.
- The legacy app reports API version `v0.1` while the repository README calls
  the overall prototype `v0.3-alpha`; Studio needs one explicit version source.
- Dependencies are lower-bounded but not locked. There is no `uv.lock` at
  baseline, so reproducibility is incomplete.
- The legacy browser script inserts API-derived strings with `innerHTML`, has no
  `response.ok` checks, and silently hides image failures with inline
  `onerror`. The app currently lacks CSP and common hardening headers. It is not
  safe to extend that rendering path to untrusted PR/model text.
- `EvidencePacket` does not carry an explicit base SHA/head SHA or schema
  version. Some retrieval follows a default branch, so the current verifier
  cannot yet prove every conclusion was produced against the PR head commit.
- Historical and semantic components have intentionally different decision
  spellings and meanings (`conflict_detected` versus `detect_conflict`, and
  different stale handling). Historical CSV values cannot be mass-normalized;
  versioned adapters are required.
- Semantic render flags for real/mock/fallback provenance are currently
  constants rather than a complete record of each retrieval step. Some
  retrieval errors become empty result sets, which is insufficient for Studio
  traceability.
- Existing ClaimBench summaries are preserved, but ignored raw run directories
  are not all available. The checked-in reports must be treated as immutable
  archives, not claimed as reproducible from this checkout alone.
- The legacy runner accepts `ANTHROPIC_AUTH_TOKEN` as a DeepSeek credential
  source and can persist raw provider responses/errors. Studio needs
  provider-specific credential resolution and uniform redaction.

## Existing TraceGate core capabilities and source files

| Capability | Main source |
| --- | --- |
| Evidence/claim schema and routing | `tracegate/claims/*.py`, `tracegate/core/models.py` |
| Context selection and compression | `tracegate/context/*.py`, `tracegate/contexts/*.py` |
| EvidencePacket and redaction | `tracegate/pr_advisor/evidence_packet.py` |
| Live GitHub evidence collection | `tracegate/pr_advisor/collect.py`, `tracegate/pr_advisor/retrieve.py` |
| DeepSeek request client | `tracegate/pr_advisor/deepseek_client.py` |
| Structured semantic judgment | `tracegate/pr_advisor/llm_judge.py` |
| Evidence verifier | `tracegate/pr_advisor/verifier.py` |
| Guardrails/reality checks | `tracegate/core/guardrails.py`, `tracegate/data/validate.py` |
| ClaimBench runners | `tracegate/runners/claim_runner.py`, `tracegate/runners/deepseek_runner.py` |
| Metrics | `tracegate/metrics/*.py` |
| Reports and checked-in results | `tracegate/reports/*.py`, `reports*`, `results/` |
| Legacy FastAPI prototype | `tracegate/web/app.py`, `tracegate/web/service.py` |

## Migration and compatibility risks

1. Moving existing Python files would break CLI imports, tests, package data and
   links to benchmark evidence. New Studio modules should be additive first.
2. Reusing the legacy web loader in production would violate the explicit-
   failure requirement because of its summary fallback path.
3. Existing evidence records are dataclasses/dictionaries, while Studio uses
   Pydantic and SQLAlchemy. Adapters must preserve IDs, provenance, commit SHA,
   status semantics and raw checked-in artifacts.
4. Evidence and decision enums differ across benchmark schema generations.
   Studio needs an internal versioned contract plus explicit lossless adapters;
   changing archived values in place would corrupt published evidence.
5. SQLite and MySQL differ in JSON, boolean, text-search and migration details.
   FTS5 remains a SQLite-specific repository implementation.
6. Local repository indexing introduces path traversal, symlink and sensitive-
   file exposure risk not present in the checked-in benchmark loader.
7. Sidecar port/token handoff and process cleanup cross the Rust/Python boundary
   and require packaged-runtime tests, not only unit tests.
8. macOS arm64 and Windows x86_64 PyInstaller outputs are not interchangeable.
9. GitHub polling must respect ETag and rate limits; reusing one-shot PR
   collection without durable snapshots would duplicate work.
10. The current dependency set is intentionally small. Locking and introducing
   SQLAlchemy, Alembic, LangGraph and parser packages may expose conflicts and
   should happen in tested increments.
11. The benchmark's metric definitions and accepted labels are public product
    evidence. UI adapters may visualize them but must not normalize them into
    more favourable metrics.

## Baseline conclusion

The starting repository is a healthy, tested Python evaluation prototype with
valuable real evidence and guardrails, but it is not yet a full-stack desktop
coding-agent product. Studio development will preserve the benchmark package
and build new product boundaries around it.
