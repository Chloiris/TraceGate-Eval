# TraceGate Studio troubleshooting

## The dashboard says GitHub is not connected

This is expected until a Fine-grained PAT or desktop OAuth Device Flow token is
stored. Browser mode reads `GITHUB_TOKEN` or `GH_TOKEN` from the backend process;
desktop mode stores the credential in Keychain/Credential Manager. Tokens are
never accepted by `/settings` or returned by diagnostics.

## The model is not configured

Set provider, Base URL, model name, runtime parameters, and model context scope
in Settings, then store the API key through the desktop secure-credential
bridge or `TRACEGATE_LLM_API_KEY`/`DEEPSEEK_API_KEY` in browser development.
TraceGate will not fall back to a fake model or a rule result.

## Analysis says the index does not match the PR Head

The local workspace must contain the PR Head commit. Check out/fetch it outside
TraceGate, then reindex. Analysis intentionally refuses an index bound to a
different commit.

## A required Agent or Tool is disabled

Open Registry. Enable every required Agent before starting a new run, and
enable the read/command Tools needed by the workflow. Active runs retain their
launch-time Registry snapshot. `apply_patch` remains confirmation-only even if
other Tools are enabled.

## Webhook Relay says not configured

Local ETag polling still works. Relay requires an HTTPS URL (loopback HTTP is
allowed for development), a device ID, and a securely paired device token. See
[`webhook-relay.md`](webhook-relay.md).

## Sidecar does not start

Run:

```bash
./scripts/build-sidecar.sh
```

The script builds the native artifact and performs an authenticated loopback
health check. Inspect the redacted JSON log under the platform application-data
directory. The local API only binds to `127.0.0.1`; wildcard binding is rejected.

## The macOS app opens without an inspectable window

Confirm the Tauri process and Sidecar are running and inspect the redacted log.
The menu-bar application may have restored a hidden window state; use the tray
Open action. If automation cannot access the status item, keep tray/window
acceptance as `IMPLEMENTED_UNVERIFIED` instead of inferring success from process
state.

## The Windows installer triggers SmartScreen

Current CI is designed to produce an unsigned test package when no signing
certificate exists. SmartScreen is therefore expected. Do not describe the
artifact as signed. Follow [`windows-manual-acceptance.md`](windows-manual-acceptance.md)
on a real Windows graphical environment.

## Tests fail after a schema change

Update the Alembic migration, Python response schema, shared Zod schema, API
client, seed/fixture, and UI together. Then run:

```bash
./scripts/test.sh
pnpm test:e2e
```

## Generate Fix is unavailable

Autofix starts only from a persisted Finding whose repository, PR, source Run,
Head SHA, index and Evidence still match. Check the Finding's verifier status,
sync the PR, fetch/check out its exact Head outside TraceGate, and reindex.
Unsupported/binary/sensitive targets and insufficient Evidence remain explicit
eligibility failures; `force_eligibility` cannot disable hard boundaries.

## Patch generation failed

Open Fix Session detail and the Agent/Fix trace. A production proposal requires
a configured real model, valid structured output, matching Finding/base/head,
a valid unified diff, bounded paths/files/lines, and successful
`git apply --check`. Provider HTTP errors and schema/patch errors remain real
failures—do not replace them with a fixture, cached response, or rule patch.

## Confirmation expired or the Patch Hash changed

Generate/review the current proposal again and confirm the exact full SHA-256
shown by the server. Confirmation is single-use and bound to session,
repository, PR, Finding, Head SHA, Patch Hash, nonce, and expiry. Do not retry
apply with an old hash. If the PR Head changed, the session is stale and must
not be revived against different code.

## The API says `expected_lock_version` is stale

Another request or browser tab advanced the session. Reload
`GET /api/v1/fix-sessions/{id}`, inspect its server `allowed_actions`, and send
the returned lock version. Never increment it locally or skip a state.

## Patch apply failed

Confirm that the Fix session is in isolated-workspace mode, the managed
worktree exists at the recorded Head, it is clean, and the stored patch still
matches its hash. TraceGate intentionally refuses to apply to the enrolled
workspace. Export the patch/report before cleanup when diagnosis is needed.

## Validation reports `NO_TEST_COMMAND_AVAILABLE`

TraceGate did not find a recognized real test command in repository manifests
or controlled presets. Lint/typecheck do not count as tests, and a model-
suggested shell string is not executed. Add or expose a real repository test
script outside TraceGate, then start a new properly reviewed session; otherwise
the correct outcome remains `NEEDS_HUMAN_REVIEW`.

## Validation timed out, was cancelled, or truncated output

Detail stores the argument vector, purpose/source, return code/error code,
duration, truncation flag, and bounded stdout/stderr summaries. The output cap
does not change the return status. Fix the repository test/runtime condition or
adjust only the bounded product setting; never convert timeout/cancel to pass.

## Tests passed but the result is not `RESOLVED`

This is expected when reindex/re-review is incomplete, the original Finding
still has verifier support, new risk appears, or Evidence/parser certainty is
insufficient. Passing tests cover only their assertions. Review the residual
Findings/risks and Post-Fix report instead of overriding the deterministic
resolution.

## Rollback or cleanup failed

Rollback and delete are restricted to registered paths below the managed
Autofix root. Do not manually point them at the source workspace. Open
Diagnostics or `GET /api/v1/fix-workspaces` for `CLEANUP_FAILED`, retained, or
orphaned entries. Preserve the redacted report/log, stop active validation,
then retry the server action. Manual deletion should be a last resort after
verifying the path is a Fix-owned worktree.

## Fix events repeat after reconnect

Reconnect using the last persisted `Last-Event-ID`. The typed client
deduplicates sequence/event IDs; a custom client must do the same. A cursor
from a different Fix Session returns an explicit conflict. Do not treat SSE
heartbeats as workflow events.

## The original repository appears modified

Stop immediately and compare the enrolled source path with the Fix Session's
managed `workspace_path`. Expected Autofix changes exist only below the managed
Autofix root. Save redacted `git status`/path evidence without source content
or credentials and report a security issue if TraceGate wrote to the enrolled
workspace. Do not run reset/clean in the source repository.

More detail: [Autofix guide](autofix-guide.md) and
[Autofix safety](autofix-safety.md).
