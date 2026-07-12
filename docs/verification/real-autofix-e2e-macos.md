# Real-model controlled Autofix E2E on macOS

- Scoped status: `VERIFIED_MACOS`
- Public-PR Fix E2E: `BLOCKED`
- Platform: macOS arm64
- Verification time: 2026-07-12 13:19:02 UTC / 21:19:02 Asia/Shanghai
- Verification type: production ModelProvider + production Review/Fix LangGraph
  workflows + production Tool Registry

This is a real DeepSeek model run over a real temporary Git repository created
for the test. The repository content is a synthetic test fixture. It is **not**
a public PR, benchmark accuracy result, or production-repository claim.

## Scope decision

| Field | Recorded value |
| --- | --- |
| Repository | `tracegate-e2e/real-model-autofix-repository` (synthetic, temporary local Git repository) |
| Public Pull Request | `BLOCKED` — no small public PR with both a defensible existing defect and stable local test path was selected |
| Base SHA | `a6a9fd2765d204294dbd71b2c1d1b9f0a8c2c7be` |
| Head SHA | `6a57e7e55c7f621e23daab6ead6e411cbe14a6b6` |
| Finding | `4e1b3e7d-d662-4fcd-b99d-4a7b1957c0a0` — removed zero-denominator check |
| Finding location | `calculator.py:1-3`, high, confidence `1.0`, verifier `verified` |
| Review Run ID | `fbf9f6e3-004a-4682-b1ee-946d4225409c` |
| Fix Session ID | `72b398b7-dce0-4ac6-9319-93354be30cd8` |
| Model | `deepseek-chat` |
| Model profile | `openai-compatible:deepseek-chat:json-compatibility:nonstream:compatibility-tools` |
| Provider mode | `compatibility_json` |
| Credential record | `configured` only; no value or prefix was logged |

## Measured result

| Metric | Recorded value |
| --- | --- |
| End-to-end duration | 18,011 ms |
| Logical real-model requests | 7; provider retries 0 |
| Real Tool Calls | 4 total: 3 Review `search_code`, 1 Fix `read_file` |
| Evidence / Findings | 1 / 1 |
| Review tokens | 2,385 input / 686 output |
| Fix tokens | 2,869 input / 671 output |
| Total tokens | 6,611 |
| Aggregate model latency | 16,567 ms |
| Patch Hash | `4d90df204adc840537796a586ceb805f357d20b8cc6db6840625bf5977776945` |
| Changed files / lines | 1 / 2 (`calculator.py`) |
| Confirmation | explicit automated E2E authorization bound to the exact Patch Hash |
| Re-review | `ORIGINAL_FINDING_NOT_SUPPORTED` |
| Resolution | `RESOLVED` |
| Residual Findings / risks | 0 / 0 |
| Original workspace | unchanged, clean, still at the exact Head SHA |
| Rollback / cleanup | recorded; final session `ROLLED_BACK`, workspace `DELETED` |

Validation facts:

| Command | Return code | Result | Duration |
| --- | ---: | --- | ---: |
| `git diff --check` | 0 | `PASSED` | 8 ms |
| `python -m pytest -q tests/test_calculator.py` | 0 | `PASSED` | 246 ms |
| `python -m pytest -q` | 0 | `PASSED` | 244 ms |

All eleven Fix nodes persisted as `COMPLETED`: `LOAD_FINDING`,
`CHECK_FIX_ELIGIBILITY`, `PLAN_FIX`, `GENERATE_PATCH`, `VALIDATE_PATCH`,
`AWAIT_USER_CONFIRMATION`, `APPLY_PATCH`, `RUN_VALIDATION`,
`REINDEX_CHANGES`, `RE_REVIEW`, and `FINALIZE`.

## Exact command

The value returned by Keychain was passed only to the child process environment;
the run printed `credential configured`, never the value.

```bash
DEEPSEEK_API_KEY="$(security find-generic-password -s deepseek-api-key -w 2>/dev/null)" \
  uv run python scripts/real_autofix_e2e.py \
  --workspace /tmp/tracegate-real-autofix-20260712-10/repository \
  --database /tmp/tracegate-real-autofix-20260712-10/studio.db \
  --worktree-root /tmp/tracegate-real-autofix-20260712-10/fix-workspaces \
  --output runs/studio_real_autofix_e2e/20260712T-real-autofix-10/result.json \
  --model deepseek-chat
```

## Evidence artifacts

These result artifacts are intentionally ignored by Git because they contain
runtime repository/model data. The verification document records their exact
local locations without committing the database or logs.

- `runs/studio_real_autofix_e2e/20260712T-real-autofix-10/result.json`
- `runs/studio_real_autofix_e2e/20260712T-real-autofix-10/autofix.patch`
- `runs/studio_real_autofix_e2e/20260712T-real-autofix-10/post-fix-report.json`
- `runs/studio_real_autofix_e2e/20260712T-real-autofix-10/model-output-records.json`
- `/tmp/tracegate-real-autofix-20260712-10/studio.db`

The result JSON explicitly records `mock_used=false`, `cache_result_used=false`,
`rule_fallback_used=false`, `fixture_used=true`, and
`synthetic_test_repository_used=true`.

## Failed gates before the final run

Earlier fresh runs were retained as failure evidence rather than rewritten:

- shortened/bracketed Evidence IDs were rejected until exact display-bracket
  normalization and current-Head line context were implemented;
- an out-of-range model line number made eligibility fail;
- a changed Finding ID made Fix Plan binding fail;
- malformed diffs failed `git apply --check`;
- model changed-line estimates differed from the authoritative diff count and
  are now surfaced as warnings while actual limits use the parsed diff;
- one otherwise successful run exposed an E2E artifact-directory bug; its
  worktree was recovered with the product rollback/cleanup manager.

No failed attempt applied an unconfirmed or statically rejected patch.

## What this proves—and does not prove

This run proves the scoped production transaction on macOS: real Review,
Evidence/Finding persistence, real Fix model calls, a real read-only Tool Call,
hash-bound authorization, isolated apply, real tests, workspace-drift checks,
transient reindex, advisory re-review plus deterministic resolution, artifact
export, rollback, and cleanup.

It does not prove public-PR Autofix quality, a bug-fix success rate, safety of
executing arbitrary public-repository tests, Windows GUI behavior, or general
model reliability. Validation commands execute repository code with the local
user's privileges; argv/cwd/environment controls are not an OS/container
sandbox. Public-PR Fix E2E therefore remains `BLOCKED`, and Windows GUI manual
acceptance remains separate from Windows CI.

Related documents: [guide](../autofix-guide.md),
[safety model](../autofix-safety.md), and
[ADR-003](../architecture/ADR-003-autofix-workflow.md).
