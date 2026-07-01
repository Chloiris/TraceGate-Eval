# Fallback Risk Handoff

Date: 2026-07-01
Branch: `chore/win11-to-m5-handoff`

Scope: checked-in repository files plus local documentation review. Ignored run
artifacts, virtual environments, archives, and generated caches were excluded.

## Bottom Line

No path was found that turns a failed real model run into a successful result.

The main runtime risk to preserve during Mac development is semantic clarity:
current Web/API fallback behavior is only an aggregate presentation fallback and
must not become a real-data or run-level fallback.

## Keyword Scan

Representative command:

```powershell
rg -n -i '(fallback|mock|dummy|synthetic|fake|demo|sample|placeholder|except Exception|return \[\]|pass|TODO|FIXME|random|hardcoded|default result)' .
```

The scan excluded ignored/generated run artifacts and local environments.

## Findings

| File / Location | Keyword(s) | Classification | Finding | Fixed This Round |
| --- | --- | --- | --- | --- |
| `tracegate/runners/deepseek_runner.py:312`, `tracegate/runners/claim_runner.py:321` | `synthetic` | suspicious_runtime_path | `_write_synthetic_test_failure()` creates synthetic failure test records when no patch exists or patch application fails. It records `success: False`, `returncode: 125`, and an explicit `skip_reason`. | no |
| `tracegate/runners/deepseek_runner.py:367`, `tracegate/runners/deepseek_runner.py:380`, `tracegate/runners/claim_runner.py:368` | `synthetic` | suspicious_runtime_path | Runtime calls to the synthetic failure helper prevent missing tests from looking successful. This is acceptable because failure remains failure. | no |
| `tracegate/web/data_loader.py:92`, `tracegate/web/data_loader.py:120`, `tracegate/web/data_loader.py:196` | `fallback` | allowed_demo | Web/API summary fallback returns aggregate project-summary data if structured summary files are missing. Responses are marked `project_summary_fallback`; it does not fabricate run-level logs. | no |
| `tracegate/web/data_loader.py:242` | `return []` | allowed_demo | `load_results()` returns an empty list if `reports_claim/claim_stage_results.csv` is missing. The dataset source then indicates fallback rather than real run results. | no |
| `tracegate/web/service.py:71`, `tracegate/web/service.py:127` | `demo` | allowed_demo | `/api/analyze-demo` is rule-based and returns `data_source: "rule_based_demo"`. It does not call a model or create patches. | no |
| `tracegate/dataio.py:10` | `except Exception` | unknown_needs_review | Optional `yaml` import fallback. If PyYAML is absent, YAML files may not parse as JSON. Requirements include PyYAML, so this is not currently a fake-success path. | no |
| `tracegate/runners/deepseek_runner.py:68` | `except Exception` | allowed_documentation | Windows registry env-var lookup is best-effort and returns `None` when unavailable. Missing API keys still raise before real calls. | no |
| `tracegate/runners/deepseek_runner.py:451`, `tracegate/runners/claim_runner.py:455` | `except Exception` | suspicious_runtime_path | Worker-level exceptions are caught and written as `status: "error"` result records. This is not success, but Mac-side guardrail work should preserve the explicit error status. | no |
| `scripts/build_tracegate_project_intro_docx.py:167` | `return []` | allowed_documentation | Document-generation helper returns an empty list for table rows in a formatting helper. Not a benchmark/runtime success path. | no |
| `README.md:20`, `README.md:338`, `docs/limitations_and_roadmap.md:9` | `synthetic` | allowed_documentation | Docs explicitly say the legacy-shop benchmark is synthetic. | no |
| `docs/api.md:46`, `docs/api.md:186`, `README.md:303`, `RELEASE_NOTES_web_v0.1.md:64` | `fallback` | allowed_documentation | Docs state fallback summaries are aggregate and not fabricated full logs. | no |
| `.env.example:13` | `placeholder` | allowed_documentation | Empty placeholder env variables only. | no |
| `sample_repos/*/PaymentCallbackService.java:10` | `SECRET` | allowed_test_fixture | Hardcoded `legacy-secret` exists inside controlled Java sample repos. It is fixture code, not a real credential. | no |
| `experiments/claim_tasks.yaml:316`, `experiments/claim_tasks.yaml:345`, `experiments/claim_tasks.yaml:369`, `experiments/claim_tasks.yaml:371`, `experiments/claim_tasks.yaml:392` | `sample` | allowed_test_fixture | Payment evidence text references provider/callback samples as controlled task content. | no |
| `docs/我看/*` | `demo`, `fallback`, `DEEPSEEK_API_KEY="your-key"` | allowed_documentation | Local untracked interview/prep docs contain placeholder key examples and explanations. They were not staged for this handoff. | no |

## Mac-Side Must-Review Items

- Preserve fail-fast behavior for real-data adapters. If real data is missing,
  do not fallback to demo/mock/synthetic data.
- Keep Web/API `project_summary_fallback` clearly separated from real run data.
- If a real Pull Request advisory CLI is added, require explicit provenance and
  do not reuse Web/API demo behavior as runtime evidence.
- Keep worker exceptions visible as `status: "error"` or hard failures, not
  skipped successes.
- Revisit optional YAML import behavior if dependency packaging changes.

## Fake Success Assessment

- `used_synthetic_data_as_real`: false
- `used_mock_as_real`: false
- `used_fallback_data_as_real`: false
- Possible fake-success path found: no

The only synthetic runtime helper creates explicit failure records. The only
fallback data path is a labeled Web/API presentation fallback, not a run-level
benchmark result.
