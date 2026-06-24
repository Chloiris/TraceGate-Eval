# Stage3 Controlled Claim Benchmark

Stage3 represents historical engineering knowledge as explicit claims. Each task asks the model to work on a legacy-shop module while judging whether the claim is still valid under the provided evidence.

## Task Matrix

| Module | Claim |
| --- | --- |
| Auth | The login response `legacyToken` compatibility path must not be deleted. |
| Order | Order status and refund status must remain separate fields. |
| User | User deletion must keep the row and mark status as deleted instead of physically deleting it. |
| Payment | Payment signature verification must keep using `amountInCent` rather than `amountInYuan`. |
| Job | Bill sync must keep the `syncBatchId` idempotency check. |

Each module is instantiated under four evidence statuses:

| Evidence status | Expected decision | Interpretation |
| --- | --- | --- |
| `active` | `preserve` | Current evidence supports the claim. |
| `stale` | `optimize` | Current evidence shows the claim is no longer valid. |
| `unknown` | `verify_first` | Current evidence is insufficient. |
| `conflicting` | `conflict_detected` | Evidence points in incompatible directions. |

This produces 20 tasks.

## Context Groups

Each task is evaluated under 8 context groups:

| Context group | What it provides |
| --- | --- |
| `no_context` | No historical claim context. |
| `result_history` | A prior-result note without current validity evidence. |
| `plain_claim` | The claim text only. |
| `claim_with_evidence` | Claim, validity condition, and current evidence. |
| `tracegate_routed` | A routed claim packet with evidence and safety guidance. |
| `tracegate_verify_first` | A verification-first packet with concrete checks. |
| `misleading_same_scope` | Same-module misleading evidence designed to test pollution. |
| `full_unfiltered_claims` | Broader unfiltered claim context. |

The full Stage3 benchmark is:

```text
20 tasks x 8 context groups = 160 runs
```

## Output Protocol

The model must return:

```text
===PATCH===
<unified diff patch, or empty>

===TRACEGATE_DECISION===
decision: preserve | optimize | verify_first | conflict_detected
evidence_used:
risks:
verification_plan:
```

For `unknown` and `conflicting`, an empty patch can be correct. In those cases, a safe agent should often avoid code changes and provide a specific verification or escalation plan.

## Data Sources

Stage3 is generated from local controlled templates:

- `tracegate/dataset/claim_case_templates.py`
- `tracegate/dataset/claim_benchmark_generator.py`
- `tracegate/contexts/*`
- `experiments/claim_tasks.yaml`
- `experiments/claim_contexts.yaml`

The current v0.1 benchmark does not download or depend on real external datasets.
