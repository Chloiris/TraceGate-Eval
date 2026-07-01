# Cross-Platform Audit

Date: 2026-07-01
Branch: `chore/win11-to-m5-handoff`

Scope: checked-in repository files, excluding ignored local run artifacts,
virtual environments, archives, and the untracked `docs/我看/` prep folder.

## Summary

No checked-in absolute `C:\`, `D:\`, `\Users\`, `AppData`, `Desktop`, or
`Downloads` paths were found outside ignored/generated areas.

The active Python code already uses `pathlib.Path` heavily. The main
cross-platform gaps were repository hygiene, missing shell handoff scripts, and
report path formatting.

## Issues

| Risk | File or Area | Issue Type | Finding | Fixed This Round | Notes |
| --- | --- | --- | --- | --- | --- |
| low | `.gitattributes` | line endings | Existing file only set a global LF rule and did not document per-file expectations for `.py`, `.md`, `.yml`, `.json`, `.sh`, and `.ps1`. | yes | Added explicit text/eol rules while preserving binary image/docx handling. |
| low | `.editorconfig` | editor portability | No `.editorconfig` existed. | yes | Added UTF-8, LF, final newline, 2-space default, and 4-space Python indentation. |
| low | `.gitignore` | publish hygiene | Missing some requested local/build/raw-data ignores such as `node_modules/`, `dist/`, `build/`, and `datasets/real_min/raw|cache`. | yes | Added these while keeping source/config files trackable. |
| low | `scripts/` | Mac entrypoint | No `scripts/dev_check.sh` existed for Mac/Linux handoff validation. | yes | Added Bash dev check. |
| low | `scripts/` | Windows parity | No Windows equivalent handoff check existed. | yes | Added `scripts/dev_check.ps1`. |
| low | `README.md` | setup docs | README was biased toward Windows commands after local edits and did not clearly mark the branch as a handoff branch. | yes | Added handoff scope and restored macOS/Linux setup commands. |
| low | `tracegate/metrics/*_collector.py` | path formatting | Future reports used `str(run_dir)`, which can produce absolute or backslash paths on Windows. | yes | Updated Stage1, Stage2, and ClaimBench collectors to emit repo-relative POSIX paths. |
| low | `tracegate/metrics/junit_parser.py` | path formatting | Surefire report paths used platform-native separators. | yes | Writes paths relative to the sample repo with POSIX separators. |
| low | `reports_claim/claim_stage_results.csv`, `reports_claim/claim_stage_summary.md`, `reports_stage2/stage2_report.*` | historical artifact formatting | Existing checked-in reports contain Windows-style `runs_claim\...` or `runs_stage2\...` display paths. | no | Existing artifacts were not regenerated to avoid changing benchmark results during handoff. Future collectors are fixed. |
| medium | `.github/` | CI coverage | No GitHub Actions workflow exists. | no | Leave to Mac phase after deciding CI scope and whether Java/Maven smoke tests belong in CI. |
| medium | real-data adapters | dependency/provenance | Real external dataset adapters are scaffolded, but no real-data manifest/provenance contract exists. | no | Out of scope for this Windows handoff. |
| low | `tracegate.runners.deepseek_runner._read_windows_user_env` | Windows convenience | Reads Windows user environment via `winreg`. | no | Guarded by `os.name == "nt"` and returns `None` on macOS; not a blocker. |

## Commands Used For Audit

Representative searches:

```powershell
rg -n -F 'C:\' .
rg -n -F 'D:\' .
rg -n -F '\Users\' .
rg -n -F 'AppData' .
rg -n -F 'Downloads' .
rg -n -F 'Desktop' .
rg -n -F 'os.getcwd()' .
rg -n -F 'split("\")' .
rg -n -F "split('/')" .
rg -n -F 'shell=True' .
```

Generated, ignored, archived, and local prep paths were excluded from the
publish-facing audit.

## Left For Mac

- Re-run report generation on macOS after deciding whether historical report
  artifacts should be normalized.
- Add CI only after the Mac environment confirms Python, Java, Maven, and package
  install behavior.
- Decide whether to add Java/Maven smoke coverage to CI or keep it as a manual
  local check.
- Design real-data provenance and fail-fast behavior before wiring real Pull
  Request data.
