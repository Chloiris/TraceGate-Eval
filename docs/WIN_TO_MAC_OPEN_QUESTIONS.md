# Windows To Mac Open Questions

Date: 2026-07-01

These questions were not resolved during the Windows handoff pass.

## Publish Boundary

- Should the untracked `docs/我看/` interview/prep documents remain local only,
  or should a sanitized subset be published later?

Current handoff decision: do not stage this folder automatically. It includes
interview-oriented markdown/docx files and placeholder key examples such as
`DEEPSEEK_API_KEY="your-key"`, but no real token-shaped secret was detected.

## Historical Report Normalization

- Should checked-in historical reports be regenerated on Mac so `run_dir` values
  use POSIX separators everywhere?

Current handoff decision: do not regenerate reports on Windows. The code path for
future generated metrics was fixed, but existing CSV/Markdown/HTML artifacts were
left unchanged to avoid altering benchmark artifacts during handoff.

## CI Scope

- Should GitHub Actions run Python-only smoke tests, Java/Maven sample tests, or
  both?

Current handoff decision: leave CI design to the Mac phase after the M5
environment validates Python, Java, Maven, and package install behavior.
