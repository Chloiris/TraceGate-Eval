# P0 macOS arm64 verification

> **Historical verification record.** Results below are bound to the recorded
> Studio P0 source and must not be read as current Autofix verification.

- Date: 2026-07-10
- Host: macOS 26.5.1 (25F80), Apple Silicon arm64
- Branch: `feat/tracegate-studio-fullstack`
- Verification scope: P0 browser, API, database, Sidecar, and desktop lifecycle

This record separates observed behavior from code-only implementation. It is
not evidence for Windows and it does not claim that the unsigned development
bundle is ready for public distribution.

## Locked toolchain

| Tool | Version |
| --- | --- |
| Node.js | 24.14.0 |
| pnpm | 11.7.0 |
| Python | 3.12.13 |
| uv | 0.11.28 |
| rustc | 1.97.0 |
| cargo | 1.97.0 |

The repository contains `pnpm-lock.yaml`, `uv.lock`, and Cargo lock files. The
local Codex Node runtime and Homebrew/rustup toolchains were added to `PATH`
when running the commands below.

## Automated checks

The unified test command was run after the P0 implementation:

```text
./scripts/test.sh
Python: 81 passed, 1 Starlette/httpx deprecation warning
TypeScript: ESLint and strict typecheck passed
Frontend: 14 Vitest tests passed
Rust: cargo fmt --check, cargo clippy, 14 regular tests, and 1 explicit native Keychain test passed
```

The strict fallback guard was rerun after excluding generated dependency and
build trees. It reported no dangerous production fallback path. The generated
inventory remains in `docs/FALLBACK_AUDIT.md`; findings are review candidates,
not a fabricated zero-count metric.

## Browser and API observations

The browser client was run against an independently started authenticated
FastAPI process. The following were observed through the real UI and API:

- all `/api/v1` endpoints, including health, required the bearer token;
- the Dashboard loaded the real system response and showed explicit
  unconfigured GitHub/model states;
- onboarding advanced from `welcome` to `appearance` and persisted in SQLite;
- Settings saved and subsequently rendered the dark theme;
- a stopped API produced a real request error instead of sample data;
- the development proxy and Tauri origin were accepted only by the configured
  CORS policy.

Evidence:

- `docs/screenshots/p0-dashboard-macos.png`
- `docs/screenshots/p0-settings-macos.png`
- API/database tests under `tests/test_studio_*`

## Sidecar and desktop observations

`./scripts/build-macos.sh` built the React application, a native PyInstaller
Sidecar, and the Tauri application. Both executables are native arm64 Mach-O
files:

```text
apps/desktop/src-tauri/binaries/tracegate-backend-aarch64-apple-darwin
apps/desktop/src-tauri/target/release/bundle/macos/TraceGate Studio.app
```

The packaged `.app` was launched and inspected. The following behavior was
observed:

- the Tauri window waited for the packaged Sidecar and loaded authenticated
  system status;
- a repeated launch activated the single application instance and did not
  create a second Sidecar/database owner;
- closing the main window hid it while the Sidecar remained alive;
- choosing the macOS application Quit command stopped the desktop process and
  both PyInstaller bootloader/worker processes;
- an earlier orphan-process failure was reproduced before the lifecycle
  watchdog/termination fix, and the same true-quit check passed after rebuilding;
- the tray/menu implementation and menu dispatch have Rust tests, but direct
  clicking of the macOS status item was not possible in the available UI
  automation, so tray restore remains `IMPLEMENTED_UNVERIFIED`.

The rebuilt packaged Sidecar also created a real rotating JSONL log at:

```text
~/Library/Application Support/io.tracegate.studio/logs/tracegate-studio.jsonl
```

The observed records included Sidecar start, migration, API ready, Uvicorn
shutdown, database disposal and process-finished events. Tests verify bearer,
provider-token and key-pattern redaction; the handler is capped at 5 MiB with
three backups.

The desktop settings page reported `macOS Keychain` for both credential types
and never returned a secret value. The explicit native integration test wrote,
read and deleted a dedicated verification credential:

```text
cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml \
  credentials::tests::native_secure_store_round_trip -- --ignored
test credentials::tests::native_secure_store_round_trip ... ok
```

Production credentials are injected into the child environment only when the
Sidecar starts; changing one in Settings clearly requires an application
restart. No credential is stored in SQLite, browser storage, frontend state
beyond the password-field submission, API responses, or ordinary logs.

Desktop screenshot:

- `docs/screenshots/p0-desktop-macos.png`

## Artifact

```text
artifacts/macos/TraceGate-Studio-macos-arm64.zip
SHA-256: d77ff3520d143392d25736a890a47ce15d5da627ae3e757ae57fd11ed8e0aa39
```

The artifact was rebuilt from the current worktree after adding the official
Tauri notification/autostart plugins and the P1/P2 frontend. `file` again
reported native arm64 Mach-O executables for both the app and Sidecar.

`artifacts/` is intentionally ignored because these are local build outputs.
The generated `SHA256SUMS.txt` is not used to imply code signing.

## Distribution/signing limitation

`codesign -dv` reports only an ad-hoc/linker signature and no `Authority=`
chain. There is no Apple distribution identity, notarization credential, or
release signature in this environment. Therefore this is an unsigned
development artifact, not a signed/notarized macOS release.

## Platform boundary

No Windows binary was produced on this Mac. Workflow code can be reviewed and
committed locally, but only a successful `windows-latest` run may establish
`VERIFIED_WINDOWS_CI`, and only a real Windows graphical session may establish
`VERIFIED_WINDOWS_MANUAL`.
