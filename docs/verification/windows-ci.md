# Windows x86_64 CI verification

- Status: `VERIFIED_WINDOWS_CI`
- Verified at: 2026-07-11T18:44:45Z
- Source commit: `ef6c2f2fd49c57d06f4fa21784127e4f9b3bb904`
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
  [Build Windows x86_64 · 29163495677](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29163495677)
- Pull Request workflow:
  [Build Windows x86_64 · 29163496649](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29163496649)
- Pull Request:
  [#16 · feat: deliver TraceGate Studio full-stack coding agent](https://github.com/Chloiris/TraceGate-Eval/pull/16)

Both Windows runs completed successfully. The push run is the artifact source
used below because its `head_sha` is the exact source commit rather than the
temporary Pull Request merge commit.

## Automated job evidence

The `Unsigned Windows x86_64 installers` job completed successfully and proved:

1. Node.js 24.14.0, pnpm 11.7.0, Python 3.12, uv 0.11.28, and Rust 1.97.0
   x86_64 MSVC were installed and checked.
2. 163 Python tests passed on the Windows runner.
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

- Artifact ID: `8251618586`
- Artifact name:
  `TraceGate-Studio-Windows-x86_64-unsigned-ef6c2f2fd49c57d06f4fa21784127e4f9b3bb904`
- Uploaded size: 110,642,436 bytes
- GitHub retention expiry reported by the API: 2026-07-25T18:44:29Z
- Ignored local download path: `artifacts/windows/ef6c2f2/`

Files downloaded and inspected on macOS without attempting to execute them:

| File | SHA-256 |
| --- | --- |
| `TraceGate-Studio-Setup.exe` | `a004ddebd59358d4f4a6799f1c560066cc3850c3ab43c982f1b07287fa3ef6b7` |
| `TraceGate-Studio.msi` | `2117d892cfb6ff77ac6c9e4f0cc12a563a789fead681d76879e51ef1a149029a` |
| `TraceGate-Studio-portable-x86_64.zip` | `ea1a9cd0d66af834ac786dd9b6953f4ed30bea66908efd4b1b0ccfbfa4f8c764` |
| `build-info.json` | `cce8c7f5d3b75a99dbd885f2b9aa03f33165ad7958fbee189ebbe0f351017dd2` |

`SHA256SUMS.txt` was normalized from Windows CRLF only in the verification
stream; every listed digest matched the downloaded file. `build-info.json`
binds the artifact to the exact source commit, Windows runner, and MSVC target.
The accompanying `test-summary.txt` explicitly states that the packages are
unsigned and are not Windows manual-acceptance evidence.
