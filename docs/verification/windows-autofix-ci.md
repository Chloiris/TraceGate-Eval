# Windows Autofix CI verification

- Current status: `VERIFIED_WINDOWS_CI`
- Product version: `0.4.0`
- Final delivery PR: [#17](https://github.com/Chloiris/TraceGate-Eval/pull/17) — `MERGED`
- Final `main` merge commit: `35bc8caf66dcc61b6f1559e26405980b4ff1ae5d`
- Source-bound tested implementation: `69402dd7d570b64a36fba883f98b540f8a893ee5`

This record deliberately separates tested implementation source, PR head, the
temporary PR merge ref used by `pull_request` CI, and the final `main` merge
commit. Automated Windows evidence does not establish Windows installation or
graphical acceptance.

## Delivery identity

| Identity | SHA | Meaning |
| --- | --- | --- |
| Pre-Autofix baseline | `a1dcd7d755c25e0f75aac499943a07b759ec30db` | Historical starting `main`; not current delivery. |
| Tested implementation source | `69402dd7d570b64a36fba883f98b540f8a893ee5` | Runtime commit bound to the 269 Python / 60 TypeScript / 22 Rust (+1 ignored) matrix and scoped real Autofix E2E. |
| Final PR head | `74e457704f431bc21ad5b1d29fbfc475fa077be7` | Last contribution on the merged feature branch. |
| Final PR CI merge ref | `456c0914cd214961b9c4265b239e74eb00a6e390` | Temporary merge commit recorded in the final PR-head Windows artifact; not final `main`. |
| Final `main` merge commit | `35bc8caf66dcc61b6f1559e26405980b4ff1ae5d` | PR #17 merged into `main`. |

## Latest post-merge main verification

- Workflow Run: [29197940209](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29197940209)
- Event / branch: `push` / `main`
- Workflow source SHA: `35bc8caf66dcc61b6f1559e26405980b4ff1ae5d`
- Final state: `completed` / `success`
- Started / completed: `2026-07-12T15:18:40Z` / `2026-07-12T15:39:23Z`
- Job: `Unsigned Windows x86_64 installers` — `success`
- Runner target: `windows-latest`, `x86_64-pc-windows-msvc`

The post-merge `main` job completed all required steps:

- Python: 269 passed, with the recorded Starlette deprecation warning.
- Shared types / API client / Web: 15 / 17 / 28 tests passed (60 total).
- Rust: 22 passed; one explicit native secure-store mutation test ignored.
- Lint, TypeScript typecheck, Rust fmt and clippy passed.
- PyInstaller Sidecar built and passed authenticated loopback health.
- Tauri produced unsigned NSIS and MSI bundles.
- Portable ZIP, `SHA256SUMS.txt`, `build-info.json`, and `test-summary.txt`
  were produced and uploaded.

### Latest Artifact

- Artifact ID: `8261706447`
- Artifact name:
  `TraceGate-Studio-Windows-x86_64-unsigned-35bc8caf66dcc61b6f1559e26405980b4ff1ae5d`
- Artifact digest:
  `sha256:e0091e0b3771b823a5d6d0bf729c9c641cc29ab5618a5548a7d932179809cf55`
- Size: 111,274,204 bytes
- Local download directory (ignored by Git):
  `artifacts/github/windows-run-29197940209/TraceGate-Studio-Windows-x86_64-unsigned-35bc8caf66dcc61b6f1559e26405980b4ff1ae5d/`

| File | SHA-256 |
| --- | --- |
| `TraceGate-Studio-Setup.exe` | `bc1eef1f0faed9f157da8c1689d3368e23b519232a8d38c6cda10395dfedc519` |
| `TraceGate-Studio.msi` | `9e9b4342e1adda47f44e9a2a2c1501d4e2a83ad03a8666029bf22bdc557753fe` |
| `TraceGate-Studio-portable-x86_64.zip` | `8f83957941cdc51f50172149e96ff2f66653681aa8fdc65292bdd4d0b2b52d5b` |
| `build-info.json` | `ce4ee4368ec1e601a5a902fa3dc23c6ca38eefea3071520931f22bccb7bb3206` |

The downloaded `SHA256SUMS.txt` verified all four hashed files. Its Windows
CRLF was normalized only in the verifier stream; the Artifact was not changed.
`build-info.json` records product `0.4.0`, commit
`35bc8caf66dcc61b6f1559e26405980b4ff1ae5d`, and unsigned packaging. The
portable ZIP contains `tracegate-backend.exe` and `tracegate-studio.exe`.

## Historical verification record: final PR-head run

Run [29197217259](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29197217259)
completed successfully for the final PR head
`74e457704f431bc21ad5b1d29fbfc475fa077be7`. Its Artifact
`8261513802`,
`TraceGate-Studio-Windows-x86_64-unsigned-456c0914cd214961b9c4265b239e74eb00a6e390`,
records the temporary PR CI merge-ref SHA
`456c0914cd214961b9c4265b239e74eb00a6e390`. This is valid PR integration
evidence, but it is not the final `main` commit or the latest Artifact.

## Historical verification record: source-bound implementation run

Run [29196292381](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29196292381)
completed successfully for tested implementation source
`69402dd7d570b64a36fba883f98b540f8a893ee5`. Artifact `8261244145`,
`TraceGate-Studio-Windows-x86_64-unsigned-42dca4ac37e4e8da5b8251e0088c922b5fe6e51d`,
contains the original source-bound Windows proof. Its recorded hashes and
timestamps remain immutable historical evidence; they were not rewritten as
post-merge values.

Two earlier source-bound attempts also remain visible failure evidence:

1. [Run 29195425601](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29195425601)
   failed 11 Python tests because Windows line-ending semantics broke strict
   Patch application, cancellation used an unreliable interpreter name, and a
   documentation test compared native path separators.
2. [Run 29195830783](https://github.com/Chloiris/TraceGate-Eval/actions/runs/29195830783)
   reduced the failures to three; Git clean/diff checks still lacked explicit
   controlled `core.autocrlf`, and the fake npm executable was not a Windows
   command shim.

The fixes preserved strict Patch context, adapted only uniform LF/CRLF target
content, rejected mixed/oversized targets, used actual Git Blob line endings,
set controlled Windows Git line-ending options, resolved commands through the
filtered `PATH`, and used a `.cmd` test shim.

## Manual and signing boundary

- Windows GUI/manual acceptance remains `BLOCKED`: installation, WebView2,
  tray, notifications, autostart, single-instance, process cleanup, uninstall,
  and residue still require a real graphical target.
- All cited Windows packages are unsigned. Authenticode and SmartScreen remain
  unverified.
- `VERIFIED_WINDOWS_CI` does not imply `VERIFIED_WINDOWS_MANUAL`.
- The checklist remains
  [`windows-manual-acceptance.md`](../windows-manual-acceptance.md).
