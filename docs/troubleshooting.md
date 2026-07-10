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

