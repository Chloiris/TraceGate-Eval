# P0 macOS arm64 verification

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
Python: 78 passed, 1 Starlette/httpx deprecation warning
TypeScript: ESLint and strict typecheck passed
Frontend: 12 Vitest tests passed
Rust: cargo fmt --check, cargo clippy, and 12 tests passed
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

Desktop screenshot:

- `docs/screenshots/p0-desktop-macos.png`

## Artifact

```text
artifacts/macos/TraceGate-Studio-macos-arm64.zip
SHA-256: 47424653173a1718a282cbc5eb992f831d3b7a7dd5cc2933aaeca43f1b714791
```

`artifacts/` is intentionally ignored because these are local build outputs.
The checked-in `SHA256SUMS.txt` is not used to imply code signing.

## Distribution/signing limitation

The application launches locally, but strict signature verification fails:

```text
code has no resources but signature indicates they must be present
```

There is no Apple distribution identity, notarization credential, or release
signature in this environment. Therefore this is an unsigned development
artifact, not a signed/notarized macOS release.

## Platform boundary

No Windows binary was produced on this Mac. Workflow code can be reviewed and
committed locally, but only a successful `windows-latest` run may establish
`VERIFIED_WINDOWS_CI`, and only a real Windows graphical session may establish
`VERIFIED_WINDOWS_MANUAL`.
