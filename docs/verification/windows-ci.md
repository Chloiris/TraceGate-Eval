# Windows x86_64 CI verification

> **Historical verification record.** This source-bound pre-Autofix CI record
> remains valid only for its recorded commit, runs and automated scope.

- Status: `VERIFIED_WINDOWS_CI`
- Verified at: 2026-07-12T02:53:11Z
- Source commit: `a7466ce69441871df229a5ed1cdf32ec594ba935`
- Branch: `feat/tracegate-studio-fullstack`
- Runner: `windows-latest`
- Target: `x86_64-pc-windows-msvc`
- Signing: unsigned test artifacts; no Authenticode certificate

This record proves native Windows compilation, automated tests, Sidecar health,
Tauri packaging, checksum generation, and artifact upload. It does **not** prove
installation, tray, notification, autostart, WebView2, uninstall, or any other
graphical interaction on a real Windows desktop. Those remain in
[`windows-manual-acceptance.md`](../windows-manual-acceptance.md).

## Authoritative runs

- Push workflow:
  [Build Windows x86_64 · 29176975492](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29176975492)
- Pull Request workflow:
  [Build Windows x86_64 · 29176976588](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29176976588)
- Pull Request:
  [#16 · feat: deliver TraceGate Studio full-stack coding agent](https://github.com/Chloiris/TraceGate-Eval/pull/16)

Both Windows runs completed successfully. The push artifact is used below
because its embedded build SHA is the exact branch commit; the Pull Request
artifact embeds the temporary merge SHA.

## Automated job evidence

The `Unsigned Windows x86_64 installers` job completed successfully and proved:

1. Node.js 24.14.0, pnpm 11.7.0, Python 3.12, uv 0.11.28, and Rust 1.97.0
   x86_64 MSVC were installed and checked.
2. 212 Python tests passed on the Windows runner.
3. Shared types: 5 Vitest tests passed.
4. API client: 7 Vitest tests passed.
5. Web client: 18 Vitest tests passed across 6 files; lint, strict typecheck,
   and production build also passed.
6. Rust desktop ordinary suite: 22 tests passed and the explicit native
   secure-store mutation test was ignored in that ordinary invocation; fmt and
   clippy passed.
7. The workflow then explicitly reran
   `credentials::tests::native_secure_store_round_trip -- --ignored`; its 1/1
   native Windows Credential Manager write/read/delete round-trip passed.
8. PyInstaller produced the native Windows Sidecar and the workflow exercised
   its authenticated loopback health endpoint.
9. Tauri produced NSIS and MSI bundles for the x86_64 target.
10. The portable archive contains both `tracegate-studio.exe` and
   `tracegate-backend.exe`.
11. Artifact hashes, build metadata, test summary, and the artifact archive
    were uploaded successfully.

The workflow emitted a non-failing annotation that several upstream actions
still declare the deprecated Node.js 20 action runtime while GitHub forced them
to Node.js 24. This did not change the successful job result, but the actions
should be upgraded when newer major versions are available.

## Artifact

- Artifact ID: `8255326332`
- Artifact name:
  `TraceGate-Studio-Windows-x86_64-unsigned-a7466ce69441871df229a5ed1cdf32ec594ba935`
- Uploaded size: 110,679,649 bytes
- GitHub retention expiry reported by the API: 2026-07-26T02:53:02Z
- Ignored local download path: `artifacts/windows/a7466ce/`

Files downloaded and inspected on macOS without attempting to execute them:

| File | SHA-256 |
| --- | --- |
| `TraceGate-Studio-Setup.exe` | `c005d26cb370c42c009bcdebbef176b723b1cb25da4d4ebf6724a857c2eabafc` |
| `TraceGate-Studio.msi` | `c680f619f7c734017397d8bf875c77c8103bbd50c3be5ce35b01550368cb120e` |
| `TraceGate-Studio-portable-x86_64.zip` | `6814766262e2a4016c616046b1eb03cdb2f3d7e5274c86667d4abf7978f5f7f6` |
| `build-info.json` | `8c1e13099bb1e4aba66308a72fa4f979a14cf01df84924f3805a12f8cec0f828` |

`SHA256SUMS.txt` was normalized from Windows CRLF only in the verification
stream; every listed digest matched the downloaded file. `build-info.json`
binds the artifact to the exact source commit, Windows runner, and MSVC target.
The accompanying `test-summary.txt` explicitly states that the packages are
unsigned and are not Windows manual-acceptance evidence.

The downloaded Setup executable was identified as a Windows NSIS PE; the MSI
was identified as an x64 Windows Installer database. The portable archive
passed an integrity test and contained two PE32+ x86-64 binaries:
`tracegate-backend.exe` and `tracegate-studio.exe`. They were inspected on
macOS but were not executed there.
