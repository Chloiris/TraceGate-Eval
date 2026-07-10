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

Command and result:

```text
pnpm test:e2e
4 passed (6.3s)
```

Backend and package verification:

```text
python -m pytest -q
110 passed, 1 third-party deprecation warning

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

Production Vite build passed. Repository Map plus deterministic exports is an
8.81 kB lazy chunk. Monaco
is a separately loaded local chunk with a local editor worker; it never waits
for a CDN.

Current Rust/native gates:

```text
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
15 passed, 1 explicit native-credential mutation test ignored

./scripts/build-macos.sh
native arm64 Sidecar health-check passed; Tauri release .app bundled
SHA-256 d77ff3520d143392d25736a890a47ce15d5da627ae3e757ae57fd11ed8e0aa39
```

The official Tauri notification/autostart plugins compile in that package, but
the OS notification click path and login-time launch were not manually
exercised and remain `IMPLEMENTED_UNVERIFIED`.

## Screenshots

- `docs/screenshots/p1-pr-diff-macos.png`
- `docs/screenshots/p1-review-map-macos.png`
- `docs/screenshots/p1-eval-center-macos.png`
- `docs/screenshots/p1-registry-macos.png`

## Explicit limitations

- No real model credential exists, so a successful live semantic-model run is
  `BLOCKED`; tests prove the explicit failure path and use dependency-injected
  model doubles only inside unit tests.
- Windows code and workflows do not count as Windows CI evidence until the
  current workflow run is inspected with user permission.
- No Windows graphical machine is available, so no Windows manual status is
  claimed.
- MySQL runtime smoke remains unverified because Docker is unavailable on this
  Mac. Notification display/click, autostart-at-login and OS deep-link launch
  remain target-platform manual gates; their code must not be reported as
  manual acceptance.
