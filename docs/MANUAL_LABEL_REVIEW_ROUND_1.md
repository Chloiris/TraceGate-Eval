# Manual Label Review Round 1

Generated from `datasets/real_min/labels/manual_review_queue.jsonl`.

This document is a reviewer aid only. It does not promote candidates into scored cases and does not write `manual_verified` labels.

## Summary

- total candidates: `40`
- stale: `13`
- unknown: `11`
- conflicting: `16`
- promoted cases: `0`
- used_mock_model: `false`
- used_synthetic_data: `false`
- used_fallback_data: `false`

## Recommended Review Order

- `hard_candidate:psf__requests:pull:7441` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7466` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7467` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7486` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7491` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7492` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7513` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7546` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7549` - `conflicting` - `needs_more_evidence`
- `hard_candidate:psf__requests:pull:7552` - `conflicting` - `needs_more_evidence`

## Stale Candidates

### `hard_candidate:psf__requests:pull:7355`

- candidate_id: `hard_candidate:psf__requests:pull:7355`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7355
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated, no longer
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7355
  - pr: https://github.com/psf/requests/pull/7355
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7355 - Add missing stacklevel to all warnings.warn() calls ## Summary All 9 `warnings.warn()` calls in the codebase are missing `stacklevel`, causing warning messages to point to internal lines inside Requests rather than the caller's code. ###...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:psf__requests:pull:6265`

- candidate_id: `hard_candidate:psf__requests:pull:6265`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/6265
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/6265
  - pr: https://github.com/psf/requests/pull/6265
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/6265 - Fix setuptools deprecation warnings Update keys used in `setup.cfg` in order to fix the following setuptools deprecation warnings: > The license_file parameter is deprecated, use license_files instead. > Usage of dash-separated 'provides...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:psf__requests:pull:7524`

- candidate_id: `hard_candidate:psf__requests:pull:7524`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7524
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: no longer
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7524
  - pr: https://github.com/psf/requests/pull/7524
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7524 - fix: empty params no longer produce empty body (#6122) Closes #6122. Co-Authored-By: Claude <[redacted-email]>
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:psf__requests:pull:7540`

- candidate_id: `hard_candidate:psf__requests:pull:7540`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7540
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: cleanup
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7540
  - pr: https://github.com/psf/requests/pull/7540
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7540 - Bump actions/checkout from 6.0.2 to 7.0.0 in the actions group Bumps the actions group with 1 update: [actions/checkout](https://github.com/actions/checkout). Updates `actions/checkout` from 6.0.2 to 7.0.0 <details> <summary>Release note...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:13370`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:13370`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/13370
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: legacy
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/13370
  - pr: https://github.com/pytest-dev/pytest/pull/13370
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/13370 - fix #6881 - add policies for too long ids from a str and use short as default <!-- Thanks for submitting a PR, your contribution is really appreciated! Here is a quick checklist that should be present in PRs. - [ ] Include documentation ...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14322`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14322`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14322
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: removed
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14322
  - pr: https://github.com/pytest-dev/pytest/pull/14322
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14322 - Enable record_property for junit_family=xunit2 Refs #14315 ## Summary This change enables `record_property` when `junit_family=xunit2` is used. ## What changed - removed the xunit2 incompatibility warning for `record_property` - added a ...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14625`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14625`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14625
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14625
  - pr: https://github.com/pytest-dev/pytest/pull/14625
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14625 - [PR #14596/a07c31a9 backport][9.1.x] doc,testing: fix `scope="class"` instance methods **This is a backport of PR #14596 as merged into main (a07c31a97d0a412c09b1f2f5953adb4b4a75d04d).** This is deprecated, we should use classmethods for...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14596`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14596`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14596
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14596
  - pr: https://github.com/pytest-dev/pytest/pull/14596
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14596 - doc,testing: fix `scope="class"` instance methods This is deprecated, we should use classmethods for that.
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14293`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14293`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14293
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14293
  - pr: https://github.com/pytest-dev/pytest/pull/14293
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14293 - outcomes: remove deprecated `importorskip` `ImportError` behavior Deprecated scheduled for removal in pytest 9. Part of #13893.
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14523`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14523`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14523
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: no longer
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14523
  - pr: https://github.com/pytest-dev/pytest/pull/14523
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14523 - Use streaming in all assertion comparisons consumers Follow-up to the streaming-comparison chain: #14521 (comparators → generators), #14546 (base comparisons return an iterator), #14587 (set comparison → `Iterator[str]`), #14588 (`Pretty...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14633`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14633`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14633
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: no longer
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14633
  - pr: https://github.com/pytest-dev/pytest/pull/14633
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14633 - assertion rewrite: use sys.stdlib_module_names to skip stdlib modules early, replacing the _in_find_spec flag With `PYTHON_LAZY_IMPORTS=all` (Python 3.15+), accessing a lazily-imported attribute inside `find_spec` triggers a recursive `f...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14143`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14143`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14143
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated, legacy
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14143
  - pr: https://github.com/pytest-dev/pytest/pull/14143
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14143 - build(deps): Bump actions/cache from 5.0.1 to 5.0.2 Bumps [actions/cache](https://github.com/actions/cache) from 5.0.1 to 5.0.2. <details> <summary>Release notes</summary> <p><em>Sourced from <a href="https://github.com/actions/cache/rel...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

### `hard_candidate:pytest-dev__pytest:pull:14659`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14659`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14659
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: cleanup
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14659
  - pr: https://github.com/pytest-dev/pytest/pull/14659
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14659 - build(deps): Bump actions/checkout from 6.0.3 to 7.0.0 Bumps [actions/checkout](https://github.com/actions/checkout) from 6.0.3 to 7.0.0. <details> <summary>Release notes</summary> <p><em>Sourced from <a href="https://github.com/actions/...
- manual confirmation questions:
  - Find the older claim URL and the newer superseding evidence URL.
  - Are the timestamps clearly ordered?
  - Should this remain excluded until both evidence URLs are present?

## Unknown Candidates

### `hard_candidate:psf__requests:pull:7424`

- candidate_id: `hard_candidate:psf__requests:pull:7424`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7424
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7424
  - pr: https://github.com/psf/requests/pull/7424
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7424 - Fix HTTPDigestAuth failing on non-ASCII credentials ## Summary When `HTTPDigestAuth` credentials contain non-ASCII characters (e.g. Czech username `Ondřej`), authentication fails because the digest header encodes the bytes representation...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:psf__requests:pull:7545`

- candidate_id: `hard_candidate:psf__requests:pull:7545`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7545
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7545
  - pr: https://github.com/psf/requests/pull/7545
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7545 - fix: HTTPDigestAuth properly handles bytes credentials ## Problem When bytes are passed as username/password to `HTTPDigestAuth`, the digest header contains the bytes repr instead of the decoded string: ```python HTTPDigestAuth('Ondřej'....
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:psf__requests:pull:7538`

- candidate_id: `hard_candidate:psf__requests:pull:7538`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7538
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7538
  - pr: https://github.com/psf/requests/pull/7538
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7538 - Preserve username-only URL auth ## Summary get_auth_from_url() now keeps a URL username when the URL has no password component instead of dropping the username. ## Why A username-only URL authority still carries authentication informatio...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:psf__requests:pull:7232`

- candidate_id: `hard_candidate:psf__requests:pull:7232`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7232
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7232
  - pr: https://github.com/psf/requests/pull/7232
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7232 - feat: add RFC 7616 support for non-Latin credentials in HTTPDigestAuth ## Summary Implement [RFC 7616](https://www.rfc-editor.org/rfc/rfc7616) extensions to fix `HTTPDigestAuth` failing with non-Latin-1 usernames (e.g., Cyrillic, Czech d...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:psf__requests:pull:7520`

- candidate_id: `hard_candidate:psf__requests:pull:7520`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7520
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: token
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7520
  - pr: https://github.com/psf/requests/pull/7520
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7520 - Keep Link header parameter values that contain '=' ## Summary `parse_header_links` splits each `Link` header parameter on `=` with `key, value = param.split("=")` (no `maxsplit`). RFC 8288 permits quoted parameter **values** that themsel...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:psf__requests:pull:7535`

- candidate_id: `hard_candidate:psf__requests:pull:7535`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7535
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: token
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7535
  - pr: https://github.com/psf/requests/pull/7535
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/7535 - parse_list_header and parse_dict_header: do not unquote tokens that lack a balanced closing quote ## What `parse_list_header` and `parse_dict_header` in `src/requests/utils.py` used `item[:1] == item[-1:] == '"'` to test whether an item ...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:psf__requests:pull:6965`

- candidate_id: `hard_candidate:psf__requests:pull:6965`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/6965
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: permission
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/6965
  - pr: https://github.com/psf/requests/pull/6965
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/psf/requests/pull/6965 - Only use hostname to do netrc lookup instead of netloc Applies the patch generated from the GHSA which we couldn't merge as no one on the team had sufficient permissions.
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:pytest-dev__pytest:pull:8251`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:8251`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/8251
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/8251
  - pr: https://github.com/pytest-dev/pytest/pull/8251
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/8251 - implement Node.path as pathlib.Path there is a bug in module collection left that i dont see tonight, lets retry tommorow <!-- Thanks for submitting a PR, your contribution is really appreciated! Here is a quick checklist that should be ...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:pytest-dev__pytest:pull:14053`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14053`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14053
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14053
  - pr: https://github.com/pytest-dev/pytest/pull/14053
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/14053 - docs: clarify capture fixture precedence over -s closes #13731 Clarify in the capturing tutorial that using capture fixtures such as `capsys` or `capfd` re-enables capturing for the duration of the test, even when global capturing is dis...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:pytest-dev__pytest:pull:11844`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:11844`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/11844
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/11844
  - pr: https://github.com/pytest-dev/pytest/pull/11844
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/11844 - delete silly chdir This line causes the below insane behavior. I hypothesize that it's here for no really good reason. https://gist.github.com/bukzor/085b1c2bdaa5bc6033db50d718c48bd3 Here is a quick checklist that should be present in PR...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

### `hard_candidate:pytest-dev__pytest:pull:13210`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:13210`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/13210
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth, security
- promote recommendation: `promote`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/13210
  - pr: https://github.com/pytest-dev/pytest/pull/13210
- evidence_items summary:
  - 1. `pr` `unclear` https://github.com/pytest-dev/pytest/pull/13210 - build(deps): Bump django from 5.1.5 to 5.1.6 in /testing/plugins_integration Bumps [django](https://github.com/django/django) from 5.1.5 to 5.1.6. <details> <summary>Commits</summary> <ul> <li><a href="https://github.com/django/django/co...
- manual confirmation questions:
  - Is there enough evidence to preserve or optimize safely?
  - Which current test, owner note, or doc confirms the behavior?
  - Should this be scored as verify_first after review?

## Conflicting Candidates

### `hard_candidate:psf__requests:pull:7555`

- candidate_id: `hard_candidate:psf__requests:pull:7555`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7555
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7555
  - pr: https://github.com/psf/requests/pull/7555
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7555 - HTTPDigestAuth: use urlsplit for the digest URI The Effective Request URI in the Digest Authorization header is computed from `urlparse(url).path`. `urlparse()` treats `;` as a path-parameter separator and strips everything from the firs...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7549`

- candidate_id: `hard_candidate:psf__requests:pull:7549`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7549
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7549
  - pr: https://github.com/psf/requests/pull/7549
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7549 - Remove method cookies set to None Summary - Treat method-level cookie mappings with value None as removals after session cookies are merged. - Leave the session cookie jar unchanged while omitting those cookies from the prepared request....
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7546`

- candidate_id: `hard_candidate:psf__requests:pull:7546`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7546
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7546
  - pr: https://github.com/psf/requests/pull/7546
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7546 - [Fix] response.content losing read errors on second access (#4965) ## Problem Accessing `response.content` twice after a stream read error returns empty bytes on the second access instead of re-raising the error. **Reproduction:** ```pyt...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7466`

- candidate_id: `hard_candidate:psf__requests:pull:7466`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7466
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: incompatible
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7466
  - pr: https://github.com/psf/requests/pull/7466
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7466 - fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Ma...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7467`

- candidate_id: `hard_candidate:psf__requests:pull:7467`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7467
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: incompatible
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7467
  - pr: https://github.com/psf/requests/pull/7467
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7467 - fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Ma...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7441`

- candidate_id: `hard_candidate:psf__requests:pull:7441`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7441
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: incompatible, revert
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7441
  - pr: https://github.com/psf/requests/pull/7441
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7441 - Move Request.headers back to Mapping This PR partially reverts #7431, moving it back to `Mapping` instead of `MutableMapping`. While we typically expect the input to be mutable, dicts inferred to be `dict[str, str]` at creation are incom...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7492`

- candidate_id: `hard_candidate:psf__requests:pull:7492`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7492
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: revert
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7492
  - pr: https://github.com/psf/requests/pull/7492
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7492 - Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group Bumps the actions group with 1 update: [github/codeql-action](https://github.com/github/codeql-action). Updates `github/codeql-action` from 4.35.1 to 4.36.0 <details> <...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7552`

- candidate_id: `hard_candidate:psf__requests:pull:7552`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7552
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7552
  - pr: https://github.com/psf/requests/pull/7552
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7552 - Fix RFC 6265 DQUOTE handling in RequestsCookieJar.set_cookie ## Summary `RequestsCookieJar.set_cookie` mishandles cookie values wrapped in DQUOTEs per [RFC 6265 section 5.2.3](https://datatracker.ietf.org/doc/html/rfc6265#section-5.2.3)....
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7513`

- candidate_id: `hard_candidate:psf__requests:pull:7513`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7513
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7513
  - pr: https://github.com/psf/requests/pull/7513
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7513 - Make RequestsCookieJar.popitem() work Closes #6190 `RequestsCookieJar` subclasses both `CookieJar` and `MutableMapping[str, str | None]`. Its `__iter__` is inherited from `CookieJar` and yields `Cookie` objects rather than names. The `po...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7486`

- candidate_id: `hard_candidate:psf__requests:pull:7486`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7486
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7486
  - pr: https://github.com/psf/requests/pull/7486
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7486 - fix: check callable before tuple in prepare_auth ## Summary `prepare_auth` currently checks `isinstance(auth, tuple)` before `callable(auth)`. Any auth object that is both a 2-element tuple subclass **and** callable — for example an `Aut...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:psf__requests:pull:7491`

- candidate_id: `hard_candidate:psf__requests:pull:7491`
- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7491
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/psf/requests/issues/7491
  - pr: https://github.com/psf/requests/pull/7491
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/psf/requests/pull/7491 - fix: restore urlparse path params in digest auth uri (#6990) ## Problem `urlparse()` from `urllib.parse` treats semicolons as path parameter delimiters per RFC 1808. For a URL like: ``` /ws/2/collection/xxx/releases/aaa;bbb?fmt=json ``` ...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:pytest-dev__pytest:pull:14668`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14668`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14668
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression, failed
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14668
  - pr: https://github.com/pytest-dev/pytest/pull/14668
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/pytest-dev/pytest/pull/14668 - Handle RaisesGroup check errors during suggestions ## Summary - prevent the speculative `RaisesGroup` suggestion check from surfacing exceptions raised by a group-level `check` callable - keep the existing helpful suggestion when the cal...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:pytest-dev__pytest:pull:14662`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14662`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14662
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14662
  - pr: https://github.com/pytest-dev/pytest/pull/14662
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/pytest-dev/pytest/pull/14662 - Expose CaptureManager as public API (#14186) Expose `CaptureManager` as a public API type. This exposes `CaptureManager` via `pytest.CaptureManager` so plugin authors can annotate capture-manager lookups without importing from `_pytest.c...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:pytest-dev__pytest:pull:14639`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14639`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14639
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14639
  - pr: https://github.com/pytest-dev/pytest/pull/14639
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/pytest-dev/pytest/pull/14639 - Fix off-by-one in trailing assertion diff skipping (#14637) Closes #14637 Fix an off-by-one in trailing text diff skipping so pytest compares from the last character first instead of accidentally checking the first character via `-0`. Th...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:pytest-dev__pytest:pull:14641`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14641`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14641
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: breaks
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14641
  - pr: https://github.com/pytest-dev/pytest/pull/14641
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/pytest-dev/pytest/pull/14641 - fix(config): remove `as Name` re-export pattern to support PYTHON_LAZY_IMPORTS=all (Python 3.15) ## Problem `pytest` crashes when run with Python 3.15's `PYTHON_LAZY_IMPORTS=all` environment variable: ``` $ PYTHON_LAZY_IMPORTS=all pytest...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?

### `hard_candidate:pytest-dev__pytest:pull:14180`

- candidate_id: `hard_candidate:pytest-dev__pytest:pull:14180`
- repo: `pytest-dev/pytest`
- pr_url: https://github.com/pytest-dev/pytest/pull/14180
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: failed
- promote recommendation: `needs_more_evidence`
- issue/comment/review/commit evidence URLs:
  - issue_url: https://github.com/pytest-dev/pytest/issues/14180
  - pr: https://github.com/pytest-dev/pytest/pull/14180
- evidence_items summary:
  - 1. `pr` `contradicts` https://github.com/pytest-dev/pytest/pull/14180 - Clarify retention policy While debugging a test session that ran out of diskspace in CI tried different retention policies. From reading the docs I would have expected that both `failed` and `none` would remove tmp files during teardown ...
- manual confirmation questions:
  - Find the supporting evidence URL and the contradicting evidence URL.
  - Does the conflict affect current behavior or only historical discussion?
  - Should this be detect_conflict or needs_manual_review?
