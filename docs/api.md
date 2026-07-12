# TraceGate APIs

## TraceGate Studio `/api/v1`

Studio is the authenticated production API used by the React browser client
and Tauri Sidecar. It listens on loopback by default. Every `/api/v1` request
except health requires `Authorization: Bearer <per-launch-token>`; browser
development must supply that token explicitly and packaged mode obtains it
through the native HostBridge. The token is not returned by status or
diagnostics.

Start a development service with the same settings used by `scripts/dev.sh`:

```bash
export TRACEGATE_LOCAL_API_TOKEN="$(openssl rand -hex 32)"
export TRACEGATE_DATA_DIR="$PWD/.tracegate-dev"
uv run tracegate-studio serve
```

Core endpoints:

| Method and path | Real source / behavior |
| --- | --- |
| `GET /api/v1/health` | Process health and version; no secret-bearing details. |
| `GET /api/v1/system/status` | Explicit API, database, GitHub, model and Eval capability states. |
| `GET /api/v1/diagnostics` | Redacted versions, paths, process/port, queues, monitoring, provider/index/graph/model/retrieval timing and notification outcomes. |
| `GET /api/v1/system/update` | Signed-update interface status; currently explicitly unconfigured. |
| `GET/PUT /api/v1/settings` | Non-secret theme, locale, monitoring, model metadata and startup preference. |
| `GET/PUT /api/v1/onboarding` | Persisted first-run progress without credentials. |
| `GET/POST /api/v1/repositories` | List/enroll controlled repository workspaces. |
| `GET/PUT/DELETE /api/v1/repositories/{id}` | Read, update monitoring, or remove enrollment (never repository files). |
| `POST /api/v1/repositories/{id}/sync` | ETag/rate-limit-aware GitHub PR synchronization. |
| `POST /api/v1/repositories/{id}/index` | Persist a commit-bound incremental parser/index snapshot. |
| `GET /api/v1/repositories/{id}/graph` | Static Repository Map from the current index. |
| `GET /api/v1/repositories/{id}/search` | Labeled ripgrep/symbol/FTS hybrid retrieval. |
| `GET /api/v1/pull-requests` | Persisted PR Inbox with filters. |
| `GET /api/v1/pull-requests/{id}` | Persisted PR metadata and commit identity. |
| `GET /api/v1/pull-requests/{id}/commits` | Structured persisted commit history from GitHub synchronization. |
| `GET /api/v1/pull-requests/{id}/files` | Structured changed files and parsed changed hunks bound to Head SHA. |
| `GET /api/v1/pull-requests/{id}/diff` | Real local Git content for the selected changed file. |
| `GET /api/v1/pull-requests/{id}/graph` | Review Map from Git diff + static index + Agent Evidence. |
| `GET /api/v1/pull-requests/{id}/tour` | Bounded Change Tour with explicit incomplete/confidence state. |
| `POST /api/v1/pull-requests/{id}/analyze` | Enqueue the real LangGraph workflow or fail if model/index prerequisites are absent. |
| `GET /api/v1/runs` | Durable Agent Run list. |
| `GET /api/v1/runs/{id}` | Run, Step and ToolCall detail. |
| `GET /api/v1/runs/{id}/graph` | Run-owned Agent Evidence Graph. |
| `POST /api/v1/runs/{id}/cancel` | Persist and request bounded cancellation. |
| `POST /api/v1/runs/{id}/retry` | Explicit retry; does not suppress the original failure. |
| `GET /api/v1/runs/{id}/events` | Authenticated SSE run updates. |
| `GET /api/v1/findings` / `evidence` | Run/PR-scoped traceability records. |
| `GET /api/v1/evaluations` | Checked-in real benchmark/ClaimBench artifacts plus SHA-256 provenance. |
| `GET /api/v1/agents` / `tools` | Actual workflow and Tool Registry schemas/permissions/stats. |
| `PUT /api/v1/agents/{name}` | Persistently enable/disable a production Agent; disabled required Agents block new runs. |
| `PUT /api/v1/tools/{name}` | Persistently enable/disable a Tool; write-confirmation Tools cannot be globally enabled. |
| `GET/POST /api/v1/notifications` | Read or record actual OS handoff/failure outcomes; an attempted notification is not called displayed. |
| `POST /api/v1/webhooks/github` | Optional direct HMAC-SHA256 GitHub delivery with durable deduplication. |
| `GET/POST /api/v1/fix-sessions` | List/create Finding-bound controlled Fix Sessions. |
| `GET /api/v1/fix-sessions/{id}` | Full state, eligibility, plan, proposal, confirmation, validation, persisted Fix Steps/Tool Calls, re-review, result and server-authoritative allowed actions. |
| `POST /api/v1/fix-sessions/{id}/{action}` | Stateful `plan`, `generate`, `confirm`, `apply`, `validate`, `re-review`, `cancel`, or `rollback` actions with optimistic lock checks. |
| `GET /api/v1/fix-sessions/{id}/patch` | Authoritative unified diff/hash/file view or `.patch` download. |
| `GET /api/v1/fix-sessions/{id}/report` | Authoritative Post-Fix result or JSON download. |
| `GET /api/v1/fix-sessions/{id}/events` | Persisted/resumable SSE using `Last-Event-ID`. |
| `DELETE /api/v1/fix-sessions/{id}/workspace` | Delete only the registered managed Fix worktree. |
| `GET /api/v1/fix-workspaces` | Redacted managed-worktree diagnostics and expiry state. |
| `DELETE /api/v1/fix-workspaces/{id}` | Idempotently clean one selected persisted/orphaned worktree after managed-root and activity checks. |

Errors use a non-success HTTP status and an `{ "error": { "code",
"message" } }` body. Missing GitHub/model/relay capabilities remain explicit;
the API does not switch to fixture data or a normal-looking report.

The separate optional Webhook Relay, device pairing, authenticated SSE, Docker
profile and TLS requirements are documented in
[webhook-relay.md](webhook-relay.md).

## Controlled Autofix API

The Autofix routes are `VERIFIED_MACOS` by the full local matrix and scoped
real-model run. Fresh Windows CI remains a separate gate. They never make
Review writable, and they expose no commit/push/comment/merge operation.

### Transaction identity

`POST /api/v1/fix-sessions` accepts an existing Finding and an explicit mode:

```json
{
  "finding_id": "00000000-0000-0000-0000-000000000000",
  "permission_mode": "APPLY_IN_ISOLATED_WORKSPACE"
}
```

`PROPOSE_ONLY` is the non-mutating alternative. The server resolves and stores
repository, PR, source Agent Run, base/head SHA, and index identity; clients do
not supply those authoritative values.

Every subsequent action contains the latest `expected_lock_version`:

```json
{
  "expected_lock_version": 3
}
```

Confirmation and apply additionally require the full server-reported hash:

```json
{
  "expected_lock_version": 5,
  "patch_hash": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

The all-zero value above is a shape example only. It cannot confirm a different
persisted proposal. Hash, Head SHA, expiry, transaction binding and single-use
state are verified server-side.

### Lifecycle routes

| Route | Precondition / result |
| --- | --- |
| `POST /fix-sessions/{id}/plan` | Created/eligible session; checks Finding/Head/index/Evidence and creates structured plan. `force_eligibility` cannot bypass hard safety rules. |
| `POST /fix-sessions/{id}/generate` | `PLAN_READY`; requests a structured model patch, runs static safety + `git apply --check`, then waits for confirmation. |
| `POST /fix-sessions/{id}/confirm` | Exact current Patch Hash and Head; creates an expiring, single-use confirmation. |
| `POST /fix-sessions/{id}/apply` | Valid confirmation and isolated-workspace mode; applies only to the registered worktree. |
| `POST /fix-sessions/{id}/validate` | `PATCH_APPLIED`; resolves/runs controlled commands and persists return codes/summaries. |
| `POST /fix-sessions/{id}/re-review` | `VALIDATION_COMPLETE`; transient reindex, re-review, deterministic resolution and report. |
| `POST /fix-sessions/{id}/cancel` | Requests/persists cancellation where state permits. |
| `POST /fix-sessions/{id}/rollback` | Resets/cleans only the managed Fix worktree. |
| `DELETE /fix-sessions/{id}/workspace` | Removes only the registered managed worktree after state/lock checks. |

All paths above are below `/api/v1`.

### Detail and authoritative artifacts

Detail includes `status`, `current_node`, `permission_mode`, Head/index/
workspace identity, `lock_version`, token/latency/retry values, redacted error,
and server `allowed_actions`. Nested fields include:

- `eligibility` and structured `plan`;
- proposal summary and `patch_inspection` (not a duplicate untrusted hash);
- current confirmation state;
- `validation_plan`, ordered `validation_runs`, and ordered persisted Fix
  `steps` with bounded Tool Call argument/output summaries and durations;
- `re_review` and deterministic final `result`.

Use `GET /fix-sessions/{id}/patch?download=true` for the persisted diff. The
server recomputes integrity and returns `X-TraceGate-Patch-Hash`. Add `path=`
without download to request bounded original/modified content for one changed
path when the managed worktree exists.

Use `GET /fix-sessions/{id}/report?download=true` for the persisted JSON report
and related artifact metadata. A browser-composed summary is never the
authoritative export.

### SSE

`GET /fix-sessions/{id}/events` emits persisted event envelopes:

```text
id: <persisted-event-id>
event: workflow_step
data: {"event_id":"...","sequence":4,"fix_session_id":"...","type":"workflow_step","data":{...}}
```

Clients reconnect with `Last-Event-ID`. The server validates that a nonnumeric
cursor belongs to the selected session, returns events in sequence, caps each
database page, emits heartbeats, and closes after terminal state. The typed
client bounds input, supports CRLF/multiline SSE, and deduplicates resumed
events.

### Stable failures

Representative failure codes include stale lock/state, Patch Hash or persisted
integrity mismatch, expired/invalid/consumed confirmation, stale PR Head,
unsafe path/patch, failed `git apply --check`, forbidden/no-test validation,
timeout/cancellation, and unavailable workflow/provider. Non-success never
returns a normal-looking report.

See [Autofix guide](autofix-guide.md) and
[Autofix safety](autofix-safety.md).

## Legacy TraceGate Eval Web/API Prototype

The Web/API layer is a local v0.1 presentation shell for TraceGate Eval. It exposes the Stage3 controlled benchmark, task definitions, result summaries, and a rule-based demo decision endpoint. It does not run model calls and does not generate patches.

## Start The Service

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run with uvicorn:

```bash
uvicorn tracegate.web.app:app --reload
```

Or use the CLI shortcut:

```bash
python -m tracegate web --reload
```

Dashboard:

```text
http://127.0.0.1:8000/
```

API docs generated by FastAPI:

```text
http://127.0.0.1:8000/docs
```

## Data Loading

The service uses file-based loading only:

1. `results/context_group_summary.csv`
2. `results/evidence_status_summary.csv`
3. `reports_claim/claim_stage_results.csv`
4. `experiments/claim_tasks.yaml`

`TRACEGATE_RESULTS_DIR` can override the summary directory. If structured summary files are missing, the service falls back to aggregate data from the current project introduction summary and marks responses with `data_source: "project_summary_fallback"`. It does not fabricate full run-level logs.

## Endpoints

### GET /api/health

Service health.

Response:

```json
{
  "status": "ok",
  "project": "TraceGate Eval",
  "version": "v0.1"
}
```

### GET /api/overview

Project and benchmark overview.

Response includes:

- `project_name`
- `one_sentence_intro`
- `current_stage`
- `total_tasks`
- `total_runs`
- `model`
- `key_metrics`
- `context_groups`
- `evidence_statuses`
- `data_source`

### GET /api/context-groups

Returns the 8 Stage3 context groups with descriptions and aggregate result summaries.

Example row:

```json
{
  "name": "tracegate_routed",
  "description": "TraceGate-routed evidence packet and safety-oriented action tendency.",
  "runs": 20,
  "safe_success": 14,
  "destructive_change": 0,
  "pollution": 0,
  "avg_plan_quality": 2.15,
  "data_source": "real_results"
}
```

### GET /api/evidence-status

Returns the 4 evidence statuses with expected decisions and aggregate results.

Example row:

```json
{
  "evidence_status": "unknown",
  "description": "Evidence is insufficient for a destructive compatibility change.",
  "expected_decision": "verify_first",
  "runs": 40,
  "correct_decision": 20,
  "test_success": 38,
  "destructive_change": 0,
  "pollution": 4,
  "avg_plan_quality": 2.25,
  "data_source": "real_results"
}
```

### GET /api/tasks

Returns Stage3 task summaries from `experiments/claim_tasks.yaml`.

### GET /api/tasks/{task_id}

Returns one task with all context groups and available result rows.

Example:

```text
GET /api/tasks/C3T03
```

### GET /api/results

Returns run-level summary rows from `reports_claim/claim_stage_results.csv`.

Supported filters:

- `context_group`
- `evidence_status`
- `module`

Example:

```text
GET /api/results?context_group=tracegate_routed&evidence_status=unknown
```

### POST /api/analyze-demo

Rule-based demo of the TraceGate decision schema. It does not call a model, does not use API keys, and does not create patches.

Request:

```json
{
  "claim": "Payment signature verification must keep using amountInCent.",
  "evidence": "The migration record is unavailable and no owner has confirmed the canonical amount unit.",
  "context_group": "tracegate_verify_first"
}
```

Response:

```json
{
  "suggested_decision": "verify_first",
  "reason": "The evidence is incomplete, so a destructive compatibility change should wait for verification.",
  "verification_plan": [
    "Check current telemetry or owner-confirmed evidence for the claim.",
    "Add or run a characterization test around the compatibility behavior.",
    "Use a feature flag or human review before any destructive cleanup."
  ],
  "risk_flags": ["insufficient_evidence"],
  "data_source": "rule_based_demo"
}
```

## Limitations

- This is a local presentation layer, not an online benchmark runner.
- `/api/analyze-demo` is rule-based and only demonstrates the decision schema.
- The dashboard reads checked-in summaries and does not execute experiments.
- Missing structured result files trigger aggregate fallback summaries, not synthetic run logs.
