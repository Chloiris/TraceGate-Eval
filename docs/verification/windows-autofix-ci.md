# Windows Autofix CI verification

- Status: `VERIFIED_WINDOWS_CI`
- Product version: `0.4.0`
- Branch source SHA: `69402dd7d570b64a36fba883f98b540f8a893ee5`
- Pull Request: [#17](https://github.com/Chloiris/TraceGate-Eval/pull/17)
- Workflow Run: [29196292381](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29196292381)
- Event / final state: `pull_request` / `completed` / `success`
- Started / completed: `2026-07-12T14:28:00Z` / `2026-07-12T14:48:28Z`
- Job: `Unsigned Windows x86_64 installers` — `success`
- Runner target: `windows-latest`, `x86_64-pc-windows-msvc`

## Automated checks

The final source-bound job completed every required step:

- Python: 269 passed, one Starlette deprecation warning.
- Shared types / API client / Web: 15 / 17 / 28 tests passed.
- Rust: 22 passed; one explicit native secure-store mutation test ignored.
- Lint, TypeScript typecheck, Rust fmt and clippy passed.
- PyInstaller Sidecar built and passed its authenticated loopback health check.
- Tauri release build produced both NSIS and MSI bundles.
- Portable ZIP, checksums, build metadata and test summary were produced.

This is automated build evidence. It is not Windows installation or graphical
acceptance evidence; every item in
[`windows-manual-acceptance.md`](../windows-manual-acceptance.md) remains
`BLOCKED`.

## Artifact

- Artifact ID: `8261244145`
- Artifact name:
  `TraceGate-Studio-Windows-x86_64-unsigned-42dca4ac37e4e8da5b8251e0088c922b5fe6e51d`
- Size: 111,275,006 bytes
- Build-info PR merge SHA: `42dca4ac37e4e8da5b8251e0088c922b5fe6e51d`
- Local download directory (ignored by Git):
  `artifacts/github/windows-run-29196292381/`

| File | SHA-256 |
| --- | --- |
| `TraceGate-Studio-Setup.exe` | `bb3e0a7bbb838a2d7a73a0cc2c0c51324592119764ebaa30fcb6e059ee43235e` |
| `TraceGate-Studio.msi` | `2d2407ac2ad07449ec0bdcd1847144f68699d2ef7a9c0b12f59cd6d0f256ba02` |
| `TraceGate-Studio-portable-x86_64.zip` | `a4a954060c87e3c9a251b531a1f905e40fa4f985bc1e2c114e1da9a67d379bcc` |
| `build-info.json` | `90b86339cfb775f6e912ea36125cad00f81e03b3dfdbb4b57041c96f14f7be1b` |

`SHA256SUMS.txt`, `build-info.json`, and `test-summary.txt` are also in the
artifact. Checksums were revalidated after download; the Windows CRLF checksum
file was streamed through line-ending normalization for the macOS verifier
without modifying the downloaded artifact. The portable archive contains
`tracegate-backend.exe` and `tracegate-studio.exe`.

## Failed runs and fixes

Two earlier source-bound attempts failed and remain visible evidence:

1. [Run 29195425601](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29195425601)
   failed 11 Python tests. Windows line-ending semantics caused strict Patch
   application failures; cancellation used an unreliable interpreter name;
   one documentation test compared native path separators.
2. [Run 29195830783](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29195830783)
   reduced the failures to three. Git clean/diff checks still lacked an
   explicit controlled `core.autocrlf` value, and a POSIX fake npm executable
   was not a valid Windows command shim.

The final fix preserves strict Patch context: LF-normalized confirmation hashes
are adapted only to a target file's uniform LF/CRLF convention, mixed or
oversized targets fail closed, index projection reads the actual Git Blob line
ending, and Windows Git subprocesses use explicit controlled autocrlf settings
without trusting global configuration. Windows command lookup resolves an
allowlisted executable through the filtered `PATH`; the test shim uses `.cmd`.
