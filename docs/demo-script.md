# TraceGate Studio interview demo (6–8 minutes)

## Before the call

```bash
./scripts/bootstrap.sh
./scripts/test.sh
pnpm test:e2e
./scripts/dev.sh
```

Use a disposable public repository or the checked-in E2E preparation script;
never expose a private repository, token, prompt, or local log during a screen
share. If no model key is available, keep the UI in the honest `模型尚未配置`
state and use the persisted failed-run trace to explain the boundary.

## Story

1. **Why (45 seconds).** Normal coding-agent evaluation rewards tests passing.
   TraceGate asks whether an agent used current, stale, unknown, or conflicting
   engineering evidence safely. Show Eval Center: 19 real PR cases and 160
   ClaimBench runs are read from checked-in artifacts with hashes.
2. **Local trust boundary (45 seconds).** Show Diagnostics/Settings. The API is
   loopback + bearer authenticated, provider secrets stay in Keychain/
   Credential Manager, telemetry is off, and missing providers are explicit.
3. **Repository truth (60 seconds).** Enroll a real local Git workspace, run the
   incremental index, then open Repository Map. Explain commit/content-hash
   binding, parser capability levels, the 800-node view cap, and JSON/SVG/PNG
   export.
4. **PR review loop (2 minutes).** Open PR Inbox and the selected PR. In Files &
   Diff show the local Monaco editor. Jump Finding → exact diff line, then open
   Review Map and Change Tour. Emphasize that edges come from Git/static index/
   persisted Evidence; the model cannot invent dependencies.
5. **Observable Agent (90 seconds).** Open Agent Runs. Walk through the seven
   LangGraph nodes, ToolCalls, permissions, bounded retry/cancellation and the
   Agent Evidence Graph. Show `apply_patch` disabled by default and explain the
   exact write confirmation gate.
6. **Desktop/cross-platform (60 seconds).** Show the Tauri tray menu, native
   capability bridge, Sidecar lifecycle and the Windows build workflow. State
   clearly that macOS packaging was run locally and Windows CI produced and
   hash-verified unsigned NSIS, MSI, and portable packages. Do not present that
   CI result as Windows installation, tray, notification, autostart, or GUI
   acceptance; those remain a manual checklist.

## Evidence ready for slides

- [PR Diff screenshot](screenshots/p1-pr-diff-macos.png)
- [Review Map screenshot](screenshots/p1-review-map-macos.png)
- [Eval Center screenshot](screenshots/p1-eval-center-macos.png)
- [Registry screenshot](screenshots/p1-registry-macos.png)
- [macOS verification](verification/p1-macos.md)
- [Real-model macOS E2E](verification/real-model-e2e-macos.md)
- [Windows CI verification](verification/windows-ci.md)
- [Windows manual checklist](windows-manual-acceptance.md)

## Safe answers to likely questions

- **“Is the semantic result real?”** One production-path DeepSeek run is
  `VERIFIED_MACOS`: `psf/requests#7565` completed all six required stages
  with 4 real model requests, 3 completed Tool Calls, 1 persisted Evidence,
  1 Finding, and 7 Agent Trace rows. This proves execution/traceability, not
  model accuracy. Without a configured provider, analysis still fails
  explicitly; production does not substitute a test double or rule fallback.
- **“Is the Java graph precise?”** No. Python is AST-backed but explicitly
  bounded to the implemented symbol/reference subset; JS/TS/Java are
  intentionally labelled partial or unsupported per capability. The UI shows
  the parser capability rather than inflating it.
- **“Did Windows pass?”** Yes for the exact automated build boundary: push run
  [29163495677](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29163495677)
  and PR run
  [29163496649](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29163496649)
  succeeded and the unsigned artifact was downloaded and hash-checked. No for
  Windows GUI/manual acceptance, which still requires installation, tray,
  notification, autostart, single-instance, WebView2, and uninstall checks.
- **“Can the Agent edit or push?”** Read-only analysis is the default. Patch is
  disabled until a scoped exact confirmation; commit/comment/push are not
  automatic actions.
