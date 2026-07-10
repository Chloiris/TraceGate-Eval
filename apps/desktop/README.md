# TraceGate Studio desktop shell

This directory owns the Tauri 2 shell only. The shared React application is
served from `apps/web` in development and bundled from `apps/web/dist`.

## Sidecar contract

The Rust process starts the packaged Python backend with a filtered
environment and these values:

- `TRACEGATE_HOST=127.0.0.1`
- `TRACEGATE_PORT=<ephemeral loopback port>`
- `TRACEGATE_LOCAL_API_TOKEN=<fresh 256-bit token>`
- `TRACEGATE_DATA_DIR=<platform application-data directory>`

The token is never placed in argv, status payloads, events, or normal logs.
After the health check succeeds, the WebView can request it only through the
narrow `get_api_connection` IPC command. Health checks call
`GET /api/v1/health` with an Authorization Bearer header. The supervisor makes
three total launch attempts and then surfaces a failed state; it never retries
forever.
The packaged CLI is started with the `serve` subcommand.

Tauri resolves `binaries/tracegate-backend` to exactly one of:

- `tracegate-backend-aarch64-apple-darwin`
- `tracegate-backend-x86_64-pc-windows-msvc.exe`

No placeholder executable is committed. Stage a real PyInstaller output with
the platform script in `scripts/` before building a bundle.

## Local checks

From this directory, after installing Node, pnpm, and Rust 1.77.2 or newer:

```text
pnpm install
pnpm fmt:check
pnpm clippy
pnpm test
```

The source-check scripts temporarily remove `externalBin` from Tauri's merged
configuration so unit tests do not require a fake executable. `pnpm build`
does not apply that override and therefore still fails unless the real target
Sidecar has been staged.

A desktop build also requires the built web assets and the correct native
Sidecar. macOS output does not validate Windows packaging or Windows UI
behavior.
