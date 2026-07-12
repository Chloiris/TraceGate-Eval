# Real-model macOS E2E verification

> **Historical verification record.** This immutable record proves one review
> workflow run; it is not evidence of the new Autofix workflow.

- Status: `VERIFIED_MACOS`
- Measured at: 2026-07-11T01:54:08Z
- Platform: macOS arm64
- Credential status: `configured`
- Credential source: macOS Keychain service `deepseek-api-key`
- API key value: never printed, logged, persisted, screenshotted, or committed

## Real inputs and production path

- Repository: `psf/requests`
- Pull Request: [#7565](https://github.com/psf/requests/pull/7565)
- Title: `fix: raise FileNotFoundError for missing TLS material`
- Base SHA: `4c800e9aea2059660b8306b0fc8f9e9a4232cb3e`
- Head SHA: `97e629e2490de7006122c150492a27784c2b3d82`
- Change size: 1 file, +9/-5
- Model: `deepseek-chat`
- Provider profile: `openai-compatible:deepseek-chat:json-compatibility:nonstream:compatibility-tools`
- Provider mode: JSON compatibility; native Tool Calling was not claimed
- Run ID: `f3273e5e-ef34-4370-800d-63ee107fd7a4`

The run used a fresh real Git checkout, a fresh migrated SQLite database, the
production repository index/graph builder, the production
`OpenAICompatibleProvider`, the seven-node LangGraph workflow, and the real
read-only Tool Registry. It did not use a fixture, mock, cached result, or rule
fallback.

## Persisted result

| Measurement | Result |
| --- | ---: |
| Workflow wall time | 12,362 ms |
| Accumulated model latency | 11,998 ms |
| Real model requests | 4 |
| Input tokens | 2,926 |
| Output tokens | 900 |
| Total tokens | 3,826 |
| Retries | 0 |
| Tool Calls | 3 completed `search_code` calls |
| Evidence rows | 1 |
| Finding rows | 1 |
| Agent Trace rows | 7 |

All stages completed: `INGEST`, `PLAN`, `RETRIEVE`, `ANALYZE`, `VERIFY`, and
`REPORT`. The Finding and Evidence are bound to the exact Head SHA and
`src/requests/adapters.py`. The Finding is persisted as `needs_confirmation`;
this verification proves real persistence and traceability, not human
acceptance of the model's conclusion.

The persisted `model_profiles` schema was independently inspected and contains
no API-key, secret, access-token, or credential column. The live connection
probe completed with 128 input tokens, 5 output tokens, 745 ms latency, and no
retry before the full workflow was run.

## Command and local result paths

The credential substitution below passes the Keychain value directly to the
child process. It does not echo or write the value.

```bash
DEEPSEEK_API_KEY="$(security find-generic-password -s 'deepseek-api-key' -w)" \
uv run python scripts/real_model_e2e.py \
  --workspace runs/studio_real_e2e/20260711T015245Z-psf-requests-7565/repository \
  --database runs/studio_real_e2e/20260711T015245Z-psf-requests-7565/studio-diff.db \
  --output runs/studio_real_e2e/20260711T015245Z-psf-requests-7565/result-diff.json \
  --repository psf/requests --pr 7565 \
  --title 'fix: raise FileNotFoundError for missing TLS material' \
  --url 'https://github.com/psf/requests/pull/7565' \
  --base-sha 4c800e9aea2059660b8306b0fc8f9e9a4232cb3e \
  --head-sha 97e629e2490de7006122c150492a27784c2b3d82 \
  --author muhamedfazalps --additions 9 --deletions 5 --changed-files 1 \
  --model deepseek-chat
```

Ignored local evidence paths:

- `runs/studio_real_e2e/20260711-model-connection-live.json`
- `runs/studio_real_e2e/20260711T015245Z-psf-requests-7565/result-diff.json`
- `runs/studio_real_e2e/20260711T015245Z-psf-requests-7565/studio-diff.db`

## Failures found and fixed during the live run

1. Real `psf/requests` indexing initially failed because repeated calls and
   conditional symbol redeclarations produced duplicate graph identities. The
   graph builder now gives redeclared symbols line-bound IDs and deduplicates
   identical edges. Two regression tests cover both cases.
2. A completed first model run produced zero Findings because changed-file
   fallback context used the beginning of a large file rather than the changed
   hunk. Changed-file scope now supplies a bounded real Base-to-Head diff for
   every indexed changed file. The workflow test asserts the persisted Evidence
   source is `changed_file_diff` and contains the real hunk.
3. `psf/requests#7545` was retained as an honest completed zero-Finding run; it
   was not relabelled or reused as success. The final verification used the
   independent PR and fresh database listed above.
