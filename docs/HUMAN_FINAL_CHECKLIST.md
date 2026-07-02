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

## Rejected False Positives

- `hard_candidate:pytest-dev__pytest:pull:14662`: rejected. The regression/concern wording is a mitigated context because tests verify no typing regressions; there is no reviewer contradiction.
- `hard_candidate:psf__requests:pull:7513`: rejected. Reviewer concern was followed by a fixed/covered response.
- `hard_candidate:pytest-dev__pytest:pull:14639`: rejected. Merged bugfix with approvals, not conflicting.
- `hard_candidate:pytest-dev__pytest:pull:14053`: rejected. Documentation-only clarification, not unknown high risk.
