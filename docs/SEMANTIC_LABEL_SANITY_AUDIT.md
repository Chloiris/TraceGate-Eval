# Semantic Label Sanity Audit

This document supersedes the v1 promote list in `docs/CODEX_FULL_LABEL_AUDIT_REPORT.md`.

The purpose of this pass was to re-check every v1 `action=promote` row with a semantic reading of the GitHub evidence. The review focused on whether each apparent risk was unresolved, resolved by later discussion/tests, or merely a keyword hit.

## Overview

- total candidates still covered in `manual_labels.jsonl`: `40`
- original promote count: `13`
- new promote count: `5`
- downgraded to reject: `8`
- downgraded to needs_more_evidence: `0`
- original conflicting promote count: `6`
- new conflicting promote count: `2`
- new unknown promote count: `1`
- new stale promote count: `2`
- label_source: `codex_evidence_audit_semantic_v2`
- modifies_cases_jsonl: `false`
- ran_promote_labels: `false`
- used_mock_data: `false`
- used_synthetic_data: `false`
- used_fallback_data: `false`

## Downgraded False Positives

| candidate_id | new action | reason class | semantic reason |
|---|---:|---|---|
| `hard_candidate:psf__requests:pull:7546` | `reject` | linked issue supports PR; insufficient evidence | The linked issue describes the same `response.content` bugfix direction. The historical revert of an older PR is not an unresolved contradiction on this PR. |
| `hard_candidate:psf__requests:pull:7513` | `reject` | concern resolved | The reviewer raised a duplicate-cookie removal concern, then the author replied that it was fixed and added regression coverage. |
| `hard_candidate:psf__requests:pull:7491` | `reject` | ordinary duplicate/accidental PR | Maintainer noted other PRs existed and the author described this as an accidental agent PR, not a substantive unresolved conflict. |
| `hard_candidate:pytest-dev__pytest:pull:14668` | `reject` | no reviewer contradiction | The PR and linked issue both describe the same `RaisesGroup` bugfix and regression coverage. |
| `hard_candidate:pytest-dev__pytest:pull:14662` | `reject` | concern resolved; no reviewer contradiction | The phrase about typing regressions says tests verify the prior concern was covered. It is not unresolved conflicting evidence. |
| `hard_candidate:pytest-dev__pytest:pull:14639` | `reject` | ordinary bugfix | The PR is a merged off-by-one bugfix with maintainer approvals; the linked issue supports the PR. |
| `hard_candidate:pytest-dev__pytest:pull:8251` | `reject` | concern resolved | This public API/deprecation migration had review discussion, requested changes, later approval, and merge evidence. It is not an unknown change lacking validation. |
| `hard_candidate:pytest-dev__pytest:pull:14053` | `reject` | ordinary docs/refactor | This is a documentation-only clarification with maintainer review and approval; CI concerns were unrelated. |

## Preserved Promote Suggestions

| candidate_id | evidence_status | expected_decision | key evidence |
|---|---:|---:|---|
| `hard_candidate:psf__requests:pull:7424` | `conflicting` | `detect_conflict` | PR proposes changing HTTPDigestAuth non-ASCII handling; maintainer says it does not address #6102 and breaks the default latin-1 case. |
| `hard_candidate:psf__requests:pull:6265` | `stale` | `verify_first` | Old setup.cfg deprecation-warning PR is later described as obsoleted by #7012 and no longer relevant. |
| `hard_candidate:psf__requests:pull:7538` | `conflicting` | `detect_conflict` | PR proposes preserving username-only URL auth; maintainer says the behavior is a 15-year edge case and arguably breaking for 2.x. |
| `hard_candidate:psf__requests:pull:6965` | `unknown` | `verify_first` | PR changes netrc credential lookup from a GHSA patch, but public validation detail is intentionally sparse. |
| `hard_candidate:pytest-dev__pytest:pull:11844` | `stale` | `verify_first` | Old chdir-removal proposal is later described as solved or sorted by #11826. |

## Conflicting Evidence Kept

| candidate_id | support URL | contradiction URL | why unresolved |
|---|---|---|---|
| `hard_candidate:psf__requests:pull:7424` | https://github.com/psf/requests/pull/7424 | https://github.com/psf/requests/pull/7424#issuecomment-4423494561 | The maintainer says the proposed auth fix breaks latin-1 and closes the PR as a duplicate; there is no later resolution in this PR. |
| `hard_candidate:psf__requests:pull:7538` | https://github.com/psf/requests/pull/7538 | https://github.com/psf/requests/pull/7538#issuecomment-4793357685 | The maintainer says the URL auth behavior change is arguably breaking and would not be accepted for 2.x without a strong reason. |

## Unknown Evidence Kept

| candidate_id | high-risk change | missing evidence |
|---|---|---|
| `hard_candidate:psf__requests:pull:6965` | `src/requests/utils.py` changes netrc credential lookup behavior for a GHSA patch. | The public PR does not expose the GHSA analysis or a full validation plan, so a human should verify the hidden security context before scoring. |

## Stale Evidence Kept

| candidate_id | older claim URL | newer evidence URL | time ordering |
|---|---|---|---|
| `hard_candidate:psf__requests:pull:6265` | https://github.com/psf/requests/pull/6265 | https://github.com/psf/requests/pull/6265#issuecomment-3950145511 | The PR was opened in 2022; the obsoleted-by-#7012 comment is from 2026. |
| `hard_candidate:pytest-dev__pytest:pull:11844` | https://github.com/pytest-dev/pytest/pull/11844 | https://github.com/pytest-dev/pytest/pull/11844#issuecomment-2180174227 | The PR was opened in 2024; later maintainer comments say #11826 is assumed to have fixed the issue. |

## Safety Statement

- This semantic sanity pass did not modify `datasets/real_min/cases.jsonl`.
- This semantic sanity pass did not run `promote-labels`.
- This semantic sanity pass did not use mock, synthetic, or fallback data.
- No row was marked `manual_verified`; every row still requires human final review.
