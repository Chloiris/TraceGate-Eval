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
   clearly that macOS packaging was run locally, while Windows Setup/portable
   code remains `IMPLEMENTED_UNVERIFIED` until an owner-approved Windows CI run;
   Windows notification/autostart installation remains a manual checklist.

## Evidence ready for slides

- [PR Diff screenshot](screenshots/p1-pr-diff-macos.png)
- [Review Map screenshot](screenshots/p1-review-map-macos.png)
- [Eval Center screenshot](screenshots/p1-eval-center-macos.png)
- [Registry screenshot](screenshots/p1-registry-macos.png)
- [macOS verification](verification/p1-macos.md)
- [Windows manual checklist](windows-manual-acceptance.md)

## Safe answers to likely questions

- **“Is the semantic result real?”** Only when a real provider is configured.
  Otherwise analysis fails explicitly; tests may inject doubles but production
  cannot access them.
- **“Is the Java graph precise?”** No. Python is precise for the implemented
  symbols; JS/TS/Java are intentionally labelled partial. The UI shows the
  parser capability rather than inflating it.
- **“Did Windows pass?”** Workflow code exists and is locally linted. Without
  an inspected runner artifact it is not `VERIFIED_WINDOWS_CI`, and CI would
  still not mean Windows GUI/manual acceptance.
- **“Can the Agent edit or push?”** Read-only analysis is the default. Patch is
  disabled until a scoped exact confirmation; commit/comment/push are not
  automatic actions.
