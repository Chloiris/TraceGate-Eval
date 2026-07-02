# Human Final Checklist

Use this checklist after reading `docs/SEMANTIC_LABEL_SANITY_AUDIT.md`.

- Only a human should change `label_source` to `manual_verified`.
- If you disagree with a Codex suggestion, change the row to `reject` or `needs_more_evidence`.
- Keep `cases.jsonl` unchanged until after final human verification.

## Recommended Final-Review Promote Suggestions

## `hard_candidate:psf__requests:pull:6265`

- suggested evidence_status: `stale`
- expected_decision: `verify_first`
- confidence: `0.86`
- key URL: https://github.com/psf/requests/pull/6265
- key URL: https://github.com/psf/requests/pull/6265#issuecomment-3950145511
- key URL: https://github.com/psf/requests/pull/6265#issuecomment-4122466701
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7424`

- suggested evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.84`
- key URL: https://github.com/psf/requests/pull/7424
- key URL: https://github.com/psf/requests/pull/7424#issuecomment-4423494561
- key URL: https://github.com/psf/requests/issues/6102
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7538`

- suggested evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.84`
- key URL: https://github.com/psf/requests/pull/7538
- key URL: https://github.com/psf/requests/pull/7538#issuecomment-4793357685
- key URL: https://github.com/psf/requests/pull/7538#issuecomment-4793362640
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:pytest-dev__pytest:pull:11844`

- suggested evidence_status: `stale`
- expected_decision: `verify_first`
- confidence: `0.8`
- key URL: https://github.com/pytest-dev/pytest/pull/11844
- key URL: https://github.com/pytest-dev/pytest/pull/11826
- key URL: https://github.com/pytest-dev/pytest/pull/11844#issuecomment-2180174227
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:6965`

- suggested evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.72`
- key URL: https://github.com/psf/requests/pull/6965
- key URL: https://github.com/psf/requests/pull/6965#pullrequestreview-2897244847
- key URL: https://github.com/psf/requests/commit/57acb7c26d809cf864ec439b8bcd6364702022d5
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## Sampled Semantic-V2 Spot Checks

## `hard_candidate:pytest-dev__pytest:pull:14662`

- suggested action: `reject`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.95`
- key URL: https://github.com/pytest-dev/pytest/pull/14662
- key URL: https://github.com/pytest-dev/pytest/pull/14662#issuecomment-4835239496
- key URL: https://github.com/pytest-dev/pytest/issues/14186
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7513`

- suggested action: `reject`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.93`
- key URL: https://github.com/psf/requests/pull/7513
- key URL: https://github.com/psf/requests/pull/7513#pullrequestreview-4502775948
- key URL: https://github.com/psf/requests/pull/7513#issuecomment-4715750402
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:pytest-dev__pytest:pull:14639`

- suggested action: `reject`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.94`
- key URL: https://github.com/pytest-dev/pytest/pull/14639
- key URL: https://github.com/pytest-dev/pytest/issues/14637
- key URL: https://github.com/pytest-dev/pytest/pull/14639#pullrequestreview-4576584925
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7355`

- suggested action: `needs_more_evidence`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- key URL: https://github.com/psf/requests/pull/7355
- key URL: https://github.com/psf/requests/pull/7355#issuecomment-4230257215
- key URL: https://github.com/psf/requests/pull/7355#issuecomment-4233514897
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7555`

- suggested action: `needs_more_evidence`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- key URL: https://github.com/psf/requests/pull/7555
- key URL: https://github.com/psf/requests/commit/717e54e78a70afb8ce70133742cad63034a236c3
- key URL: https://github.com/psf/requests/commit/5bce0b088393108e3a0c54a844446f91fbc54869
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## Additional Sampled Queue Checks

## `hard_candidate:psf__requests:pull:7546`

- suggested action: `reject`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.91`
- key URL: https://github.com/psf/requests/pull/7546
- key URL: https://github.com/psf/requests/issues/4965
- key URL: https://github.com/psf/requests/commit/a8e6a7cec6215eca83586a70180474a0c96a4efe
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7491`

- suggested action: `reject`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.92`
- key URL: https://github.com/psf/requests/pull/7491
- key URL: https://github.com/psf/requests/commit/0a04af26d265a19d3c64de455b5a5bf64140a390
- key URL: https://github.com/psf/requests/pull/7491#issuecomment-4606223587
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7549`

- suggested action: `needs_more_evidence`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- key URL: https://github.com/psf/requests/pull/7549
- key URL: https://github.com/psf/requests/commit/1e884f825cf895889ba1199d750b41bf480da0ed
- key URL: https://github.com/psf/requests/issues/2716
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## `hard_candidate:psf__requests:pull:7441`

- suggested action: `needs_more_evidence`
- suggested evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- key URL: https://github.com/psf/requests/pull/7441
- key URL: https://github.com/psf/requests/pull/7441#pullrequestreview-4289038802
- key URL: https://github.com/psf/requests/commit/412f581d7e7c27bfee4f042fcac89bae9a804afe
- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`

## Rejected False Positives

- `hard_candidate:pytest-dev__pytest:pull:14662`: rejected. The regression/concern wording is a mitigated context because tests verify no typing regressions; there is no reviewer contradiction.
- `hard_candidate:psf__requests:pull:7513`: rejected. Reviewer concern was followed by a fixed/covered response.
- `hard_candidate:pytest-dev__pytest:pull:14639`: rejected. Merged bugfix with approvals, not conflicting.
- `hard_candidate:pytest-dev__pytest:pull:14053`: rejected. Documentation-only clarification, not unknown high risk.
