# TraceGate Studio privacy

- Last updated: 2026-07-10
- Product stage: development alpha

TraceGate Studio is designed as a local-first application. This document
describes intended product behaviour and the data boundaries that implementation
and tests must enforce.

## Data stored locally

Depending on enabled features, TraceGate may store:

- enrolled repository paths and Git metadata;
- GitHub repository and Pull Request metadata;
- commit-bound file/symbol indexes and graph relationships;
- analysis runs, tool traces, evidence and findings;
- evaluation reports imported from this repository;
- non-secret settings, logs and diagnostic records.

The desktop default database is SQLite in the platform application-data
directory. Local repository files remain in their original workspace; indexes
contain bounded excerpts only where needed for retrieval and traceability.

## Data sent to GitHub

TraceGate calls GitHub only for actions the user configured: public repository
reads, authenticated repository/PR reads, polling, or separately confirmed
external mutations. GitHub receives the normal API request metadata and the
credential required for that operation. The UI never receives the credential.

Posting a review, comment, commit or push is not part of read-only analysis and
requires a separate confirmation path.

## Data sent to model providers

No model call occurs until a provider is configured and an analysis requiring
that provider is started. The user selects the permitted source-code scope.
A request may contain the task, changed hunks, selected source excerpts,
symbols, Git/PR evidence and safety instructions. The configured provider's own
privacy and retention terms apply.

When no model is configured, TraceGate reports “模型尚未配置”. It does not send
data, create a synthetic semantic result, or substitute a keyword rule and call
it model analysis.

Secrets, denied files and unrelated repositories are excluded from model
context. Trace/log views should show what evidence was selected without
revealing stored credentials.

## Telemetry

Telemetry is off by default. No source code, prompt, PR body, evidence text or
credential may be uploaded as telemetry. If optional telemetry is added, it
requires explicit opt-in, a visible destination and a deletion/disable path.

## Credentials

Packaged applications store provider credentials in macOS Keychain, Windows
Credential Manager, or an equivalent platform secure store. Credentials are not
stored in the application database, returned by APIs, committed to Git or
written to ordinary logs. Development environment variables remain the
developer's responsibility and are represented in status only as configured or
not configured.

## Retention and deletion

Users can remove an enrolled repository and delete its local index, PR
snapshots, runs, evidence and findings. Logs and backups use bounded retention.
Exports are user-created files and remain until the user deletes them. Removing
local TraceGate data does not delete data already held by GitHub or a configured
model provider.

Before deletion ships, it must be transactional where possible and report any
file it could not remove; silent partial deletion is not acceptable.

## Sensitive and third-party data

Repository owners are responsible for having authority to analyze the code and
PR data they enroll. Public GitHub data can still contain personal information.
Users should minimize provider scope, avoid unnecessary private repositories,
and follow employer and repository policies.

TraceGate treats repository content as untrusted and denies common credential
paths such as `.env`, SSH keys and cloud credential files. Detection is a
defence-in-depth control, not permission to commit secrets to a repository.

## Current limitations

TraceGate Studio is under implementation. The existing TraceGate Eval
repository contains public benchmark artifacts and a lightweight dashboard; it
does not yet implement every storage, secure-credential, deletion or retention
control described above. Actual verification status is recorded in
`docs/implementation-status.md`.
