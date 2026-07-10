# TraceGate Studio product tour

## 1. Start with system truth

Open **Overview**. The screen distinguishes ready, unconfigured, unavailable,
and error states. Without credentials it says `GitHub 尚未连接`, `模型尚未配置`,
and `Webhook Relay 未配置`; it does not substitute demo providers.

## 2. Enroll and index a repository

Open **Repositories**, add `owner/name`, and optionally authorize an absolute
local Git workspace. Synchronization reads GitHub snapshots when a credential
or public-repository path is available. **Reindex** parses the checked-out
commit, records capability levels, writes FTS/symbol/graph rows, and binds the
result to a commit SHA.

## 3. Explore the Repository Map

Open **Code Map** from a repository card. Start at directory aggregation, then
filter by path, language, directory, relationship, PR relevance, risk, or
one/two-hop depth. Double-click a directory to collapse it. Select a node to
inspect its commit, symbols, tests, Findings, Evidence, and Diff/VS Code/GitHub
links. JSON, SVG, and PNG exports reflect the current persisted graph.

## 4. Review a Pull Request

Open **PR Inbox** and select a synchronized Pull Request. Overview shows GitHub
refs/SHAs, checks, model/index identity, context scope, duration, tokens, risk,
and the last real analysis error.

- **Files & Diff** uses Monaco with Base/Head/Diff views, hunks, Finding and
  Evidence markers, path copy, GitHub, and bounded VS Code line opening.
- **Review Map** combines real Git diff, confirmed static index relations, and
  persisted Agent Evidence. Unconfirmed edges remain visibly distinct.
- **Change Tour** shows files, symbols, purpose, prerequisite step, risk,
  Evidence, checkpoints, confidence, and a direct Diff jump. Missing static
  relationships are reported as incomplete or not inferred.
- **Checks** and **History** show persisted GitHub Checks, commits, sync state,
  and Agent Runs.

## 5. Run and inspect the Agent

With a real model credential and matching Head-SHA index, start analysis. The
seven LangGraph nodes persist their steps and tool calls. **Agent Runs** streams
state over authenticated SSE, supports cancellation and bounded retry, exports
JSON/Markdown, and links Findings back to steps, files, tools, and Evidence.

If a model is missing or fails, the run exposes the real error. No rule result
is presented as semantic model output.

## 6. Inspect policy and evaluation

**Registry** exposes each production Agent and Tool, schema, permission,
timeout, call/error counts, and persistent enable/disable controls. Disabling a
required Agent blocks new runs. Disabled Tools are rejected by the execution
registry. `apply_patch` cannot be globally enabled and still requires write
mode plus exact per-use confirmation; it never commits or pushes.

**Eval Center** reads the checked-in 19-case real-data set and 160 ClaimBench
runs, displays provenance hashes, unchanged metrics, confusion matrix,
model/context comparisons, error drill-down, and JSON/CSV export.

## 7. Finish with desktop behavior and diagnostics

The Tauri host owns the single instance, loopback Sidecar, per-launch API token,
secure credentials, tray, close-to-hide, deep links, native notifications,
autostart preference, and true-quit cleanup. **Diagnostics** shows redacted
versions, storage paths, queues, rate-limit/backoff, GitHub/index/graph/model
timings, retrieval counts, notification outcomes, and explicit empty values
when no real run exists.

Platform evidence and unresolved manual checks are tracked in
[`implementation-status.md`](implementation-status.md) and
[`windows-manual-acceptance.md`](windows-manual-acceptance.md).

