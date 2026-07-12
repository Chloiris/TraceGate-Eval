# Security policy

TraceGate processes untrusted repositories, Pull Request text and model output,
and may hold GitHub and model-provider credentials. Security reports are
welcome while TraceGate Studio is under active development.

## Supported versions

The current development branch and the most recent tagged alpha release receive
best-effort security fixes. Alpha builds are not yet recommended for unattended
production use.

## Reporting a vulnerability

If GitHub private vulnerability reporting is available for this repository,
use a private security advisory. Otherwise, open a minimal issue asking the
maintainers for a private contact channel. Do not include credentials, private
source code, exploit payloads or personal data in a public issue.

Include, when safe:

- affected commit and platform;
- the trust boundary crossed;
- minimal reproduction steps using a disposable repository;
- expected and actual behaviour;
- whether a credential, file outside the enrolled repository, command, or
  network destination became reachable.

Maintainers should acknowledge a complete report within seven days, provide a
status update within fourteen days, and coordinate disclosure after a fix is
available. These are response targets, not a warranty.

## In-scope examples

- local API authentication or CORS bypass;
- path traversal or symlink escape from an enrolled repository;
- prompt injection that enables a forbidden tool action;
- credential exposure in UI, logs, traces, crash reports or artifacts;
- command allowlist bypass or unsafe environment inheritance;
- GitHub webhook signature or replay bypass;
- Tauri capability escalation or Sidecar process takeover;
- cross-repository data leakage;
- unsafe archive, patch or repository parsing.

## Safe research rules

Use repositories and accounts you control. Do not access other users' data,
degrade shared services, publish secrets, or run destructive payloads. Stop once
the boundary has been demonstrated and preserve redacted evidence.

The current threat model and control status are documented in
`docs/security-model.md`. Privacy behaviour is documented in
`docs/privacy.md`.
