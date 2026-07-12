# P1 macOS verification evidence

- Date: 2026-07-10
- Platform: macOS arm64
- Branch: `feat/tracegate-studio-fullstack`
- Remote GitHub mutation: paused at user request

## Verified product path

The browser client was run in Google Chrome against the real authenticated
FastAPI service, an isolated SQLite database, and a real two-commit local Git
repository generated below ignored `build/e2e/`. The fixture is test-only and
is never available through the production application.

Playwright exercised:

- authenticated startup and explicit unconfigured GitHub/model states;
- checked-in TraceGate Eval and ClaimBench artifacts (19 cases, 160 runs);
- repository enrollment and real incremental indexing;
- PR Inbox and persisted Pull Request detail;
- real Git revision content in Monaco Diff without a CDN dependency;
- Review Map derived from Git diff, static index, and persisted Evidence;
- Finding-to-Diff navigation;
- Agent Step and Tool Call trace;
- explicit retry failure when the model is not configured;
- Agent/Tool Registry, including disabled `apply_patch` write mode.
- persistent Agent Registry disable/enable with execution-time policy;
- full Change Tour symbols, Evidence and checkpoints;
- diagnostic provider/index/graph/model/retrieval/notification metrics and an
  honest unconfigured Relay state.

Command and result:

```text
pnpm test:e2e
4 passed (7.8s)
```

Backend and package verification:

```text
python -m pytest -q
125 passed, 1 third-party deprecation warning

pnpm typecheck
passed: shared-types, api-client, web

pnpm lint
passed: shared-types, api-client, web

pnpm --filter @tracegate/shared-types test
5 passed

pnpm --filter @tracegate/api-client test
7 passed

pnpm --filter @tracegate/web test
8 passed
```

Production Vite build passed. Repository Map and PR Detail are lazy chunks.
Monaco is a separately loaded local chunk with a local editor worker; it never
waits for a CDN. The large Monaco chunk still produces a build-size warning and
remains a performance optimization target.

Current Rust/native gates:

```text
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
20 passed, 1 explicit native-credential mutation test ignored

./scripts/build-macos.sh
native arm64 Sidecar health-check passed; Tauri release .app bundled
SHA-256 bd29c2b7c587cdb4d285e91423a2d1535866dc073f013959508da24a807d0324
```

The official Tauri notification/autostart plugins compile in that package, but
the OS notification click path and login-time launch were not manually
exercised and remain `IMPLEMENTED_UNVERIFIED`.

The latest `.app` launch produced one Tauri process plus the expected
PyInstaller bootloader/worker, migrated through `20260710_0004`, logged
`api_ready`, then shut down cleanly on termination with database disposal and
no remaining app-owned process. The local Computer Use interface reported the
application running but could not inspect a window/status item, so this pass
does not upgrade window/tray interaction status.

Local browser/data-ready and 100/1000-file benchmark measurements are recorded
in `docs/performance.md` and `docs/performance-results.json`.

## Screenshots

- `docs/screenshots/p1-pr-diff-macos.png`
- `docs/screenshots/p1-review-map-macos.png`
- `docs/screenshots/p1-eval-center-macos.png`
- `docs/screenshots/p1-registry-macos.png`

## Explicit limitations

- The missing-model limitation recorded during this P1 pass was cleared by the
  later production-path verification in
  `docs/verification/real-model-e2e-macos.md`. This historical pass itself used
  dependency-injected model doubles only inside unit tests.
- Windows code and workflows do not count as Windows CI evidence until the
  current workflow run is inspected with user permission.
- No Windows graphical machine is available, so no Windows manual status is
  claimed.
- MySQL runtime smoke remains unverified because Docker is unavailable on this
  Mac. Notification display/click, autostart-at-login and OS deep-link launch
  remain target-platform manual gates; their code must not be reported as
  manual acceptance.
