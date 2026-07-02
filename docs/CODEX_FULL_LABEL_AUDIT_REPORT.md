# Codex Full Label Audit Report

> Semantic v2 note: the promote list in this v1 report has been superseded by `docs/SEMANTIC_LABEL_SANITY_AUDIT.md`. Final semantic-v2 counts are `promote=5`, `reject=8`, `needs_more_evidence=27`; `hard_candidate:pytest-dev__pytest:pull:14662` is now rejected as a false positive.

This report is a Codex evidence audit for the full manual review queue. It does not promote labels into the scored dataset.

## Overview

- total_candidates: `40`
- promote: `13`
- reject: `0`
- needs_more_evidence: `27`
- suspected_status_distribution: `{'conflicting': 16, 'stale': 13, 'unknown': 11}`
- final_evidence_status_distribution: `{'conflicting': 6, 'none': 27, 'stale': 1, 'unknown': 6}`
- modifies_cases_jsonl: `false`
- ran_promote_labels: `false`
- used_mock_data: `false`
- used_synthetic_data: `false`
- used_fallback_data: `false`

## Top Promote Candidates

| candidate_id | evidence_status | confidence | key URLs |
|---|---:|---:|---|
| `hard_candidate:psf__requests:pull:7546` | `conflicting` | `0.78` | https://github.com/psf/requests/pull/7546<br>https://github.com/psf/requests/issues/4965 |
| `hard_candidate:psf__requests:pull:7513` | `conflicting` | `0.78` | https://github.com/psf/requests/pull/7513<br>https://github.com/psf/requests/pull/7513#issuecomment-4715750402 |
| `hard_candidate:psf__requests:pull:7491` | `conflicting` | `0.78` | https://github.com/psf/requests/pull/7491<br>https://github.com/psf/requests/commit/0a04af26d265a19d3c64de455b5a5bf64140a390 |
| `hard_candidate:pytest-dev__pytest:pull:14668` | `conflicting` | `0.78` | https://github.com/pytest-dev/pytest/pull/14668<br>https://github.com/pytest-dev/pytest/issues/14324 |
| `hard_candidate:pytest-dev__pytest:pull:14662` | `conflicting` | `0.78` | https://github.com/pytest-dev/pytest/pull/14662<br>https://github.com/pytest-dev/pytest/pull/14662#issuecomment-4835239496 |
| `hard_candidate:pytest-dev__pytest:pull:14639` | `conflicting` | `0.78` | https://github.com/pytest-dev/pytest/pull/14639<br>https://github.com/pytest-dev/pytest/issues/14637 |
| `hard_candidate:psf__requests:pull:6265` | `stale` | `0.74` | https://github.com/psf/requests/pull/6265<br>https://github.com/psf/requests/pull/6265#issuecomment-3950145511 |
| `hard_candidate:psf__requests:pull:7424` | `unknown` | `0.68` | https://github.com/psf/requests/pull/7424<br>https://github.com/psf/requests/pull/7424#issuecomment-4423494561 |
| `hard_candidate:psf__requests:pull:7538` | `unknown` | `0.68` | https://github.com/psf/requests/pull/7538<br>https://github.com/psf/requests/pull/7538#issuecomment-4793357685 |
| `hard_candidate:psf__requests:pull:6965` | `unknown` | `0.68` | https://github.com/psf/requests/pull/6965<br>https://github.com/psf/requests/pull/6965#pullrequestreview-2897244847 |

## Top Needs More Evidence Candidates

| candidate_id | suspected_status | missing evidence |
|---|---|---|
| `hard_candidate:psf__requests:pull:7555` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7549` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7355` | `stale` | Needs older claim URL plus newer superseding evidence URL with timestamps. |
| `hard_candidate:psf__requests:pull:7466` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7467` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7441` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7492` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7552` | `conflicting` | Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim. |
| `hard_candidate:psf__requests:pull:7524` | `stale` | Needs older claim URL plus newer superseding evidence URL with timestamps. |
| `hard_candidate:psf__requests:pull:7545` | `unknown` | Needs clearer evidence that the changed area is high risk and lacks validation. |

## Candidate Details

### hard_candidate:psf__requests:pull:7555

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7555
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: HTTPDigestAuth: use urlsplit for the digest URI
- state: `CLOSED`
- created_at: `2026-07-01T21:58:05Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7555
- https://github.com/psf/requests/commit/717e54e78a70afb8ce70133742cad63034a236c3
- https://github.com/psf/requests/commit/5bce0b088393108e3a0c54a844446f91fbc54869

Key discussion summary:
- pr: HTTPDigestAuth: use urlsplit for the digest URI The Effective Request URI in the Digest Authorization header is computed from `urlparse(url).path`. `urlparse()` treats `;` as a path-parameter separator and strips everything from the firs...
- commit: CaseInsensitiveDict: reject non-string keys with TypeError instead of… … leaking AttributeError
- commit: HTTPDigestAuth: use urlsplit for the digest URI so semicolons in the … …path are preserved The Effective Request URI in the Digest Authorization header is computed from urlparse(url).path, but urlparse() strips path parameters at the fir...

Changed files:
- `src/requests/auth.py`
- `src/requests/structures.py`
- `tests/test_lowlevel.py`
- `tests/test_structures.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7549

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7549
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Remove method cookies set to None
- state: `CLOSED`
- created_at: `2026-06-29T13:45:57Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7549
- https://github.com/psf/requests/commit/1e884f825cf895889ba1199d750b41bf480da0ed
- https://github.com/psf/requests/issues/2716
- https://github.com/psf/requests/issues/2716#issuecomment-129175679
- https://github.com/psf/requests/issues/2716#issuecomment-129198695
- https://github.com/psf/requests/issues/2716#issuecomment-129687694
- https://github.com/psf/requests/issues/2716#issuecomment-135841019

Key discussion summary:
- pr: Remove method cookies set to None Summary - Treat method-level cookie mappings with value None as removals after session cookies are merged. - Leave the session cookie jar unchanged while omitting those cookies from the prepared request....
- commit: Remove method cookies set to None
- linked_ref:
- related_ref: Strange behavior when setting cookie value to None in the method-level parameter After running the following code ``` s = requests.Session() s.cookies.update({'from-my': 'browser'}) r = s.get('http://httpbin.org/cookies', cookies={'anoth...
- related_ref_comment: Because I recently updated that section of the docs, I examined this behavior in order to make sure I didn't add incorrect/misleading documentation. I believe this is because the pattern of _"Remove a Value From a Dict Parameter by setti...

Changed files:
- `src/requests/sessions.py`
- `tests/test_requests.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7546

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7546
- suspected_status: `conflicting`
- final action: `promote`
- final evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.78`
- title: [Fix] response.content losing read errors on second access (#4965)
- state: `CLOSED`
- created_at: `2026-06-27T05:55:06Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7546
- https://github.com/psf/requests/issues/4965
- https://github.com/psf/requests/commit/a8e6a7cec6215eca83586a70180474a0c96a4efe
- https://github.com/psf/requests/issues/4965#issuecomment-587939384
- https://github.com/psf/requests/issues/4965#issuecomment-4340305378

Key discussion summary:
- pr: [Fix] response.content losing read errors on second access (#4965) ## Problem Accessing `response.content` twice after a stream read error returns empty bytes on the second access instead of re-raising the error. **Reproduction:** ```pyt...
- commit: Fix response.content caching read errors (#4965) When response.content raises during stream consumption, the error was lost on subsequent accesses — returning empty bytes instead of re-raising. This happened because _content stayed False...
- linked_ref:
- related_ref: Accessing response.content twice removes forgets read error I had a hard debugging time today because an error in the response stream is only reported when accessing `response.content` for the first time. This is especially irritating wh...
- related_ref_comment: It looks like we never closed the issue after the PR was merged. I'm reverting #5087 because it doesn't cover all of our read APIs (`content`, `iter_content`, `iter_lines`, `text`, `__iter__`) uniformly. I took a quick pass but the edge...

Changed files:
- `src/requests/models.py`
- `tests/test_lowlevel.py`

Why this action: Codex found at least two GitHub URLs with opposing safety/compatibility signals: support=https://github.com/psf/requests/pull/7546 concern=https://github.com/psf/requests/issues/4965.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:psf__requests:pull:7424

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7424
- suspected_status: `unknown`
- final action: `promote`
- final evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.68`
- title: Fix HTTPDigestAuth failing on non-ASCII credentials
- state: `CLOSED`
- created_at: `2026-05-11T14:14:21Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7424
- https://github.com/psf/requests/pull/7424#issuecomment-4423494561
- https://github.com/psf/requests/commit/653ceef90382258ae2ae64c4e944509e8fd5a4db
- https://github.com/psf/requests/issues/6102
- https://github.com/psf/requests/issues/6102#issuecomment-1087186718
- https://github.com/psf/requests/issues/6102#issuecomment-1087221857
- https://github.com/psf/requests/issues/6102#issuecomment-2061735957
- https://github.com/psf/requests/issues/6102#issuecomment-4022677528

Key discussion summary:
- pr: Fix HTTPDigestAuth failing on non-ASCII credentials ## Summary When `HTTPDigestAuth` credentials contain non-ASCII characters (e.g. Czech username `Ondřej`), authentication fails because the digest header encodes the bytes representation...
- comment: Hi @CatfishGG, I think this unfortunately does not address #6102. This breaks the default case for latin-1. There's already other PRs open with alternative approaches so we'll close this as a duplicate.
- commit: Fix HTTPDigestAuth failing on non-ASCII credentials When username/password are passed as bytes (e.g. 'Ondřej'.encode('utf-8')), the digest header was correctly including the bytes repr as a string literal (e.g. username="b'Ond\xc5\x99ej'...
- linked_ref:
- related_ref: HTTPDigestAuth fails on non-latin credentials There was issue reported, which is closed with bad results. https://github.com/psf/requests/blob/4f6c0187150af09d085c03096504934eb91c7a9e/requests/auth.py#L59-L63 Don't pass unicode strings i...

Changed files:
- `src/requests/auth.py`

Why this action: Codex found high-risk change evidence but insufficient safety/verification discussion: high_risk_hits=auth.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:psf__requests:pull:7355

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7355
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Add missing stacklevel to all warnings.warn() calls
- state: `CLOSED`
- created_at: `2026-04-11T20:17:27Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7355
- https://github.com/psf/requests/pull/7355#issuecomment-4230257215
- https://github.com/psf/requests/pull/7355#issuecomment-4233514897
- https://github.com/psf/requests/commit/7e9316a147f87915a678e964ea8b8ba331f36156

Key discussion summary:
- pr: Add missing stacklevel to all warnings.warn() calls ## Summary All 9 `warnings.warn()` calls in the codebase are missing `stacklevel`, causing warning messages to point to internal lines inside Requests rather than the caller's code. ###...
- comment: Nice cleanup — fixing `stacklevel` on all `warnings.warn()` calls is a real QoL improvement for library users debugging their own code. One thing to double-check: if there are existing tests that assert on warning output (file paths or l...
- comment: Thanks for the review @afurm! > Have you run the test suite to confirm nothing breaks? Yes — the existing warning tests only assert on warning **count** and **category** (e.g. `test_file` in `test_utils.py` checks `len(recwarn)`, and `te...
- commit: Add missing stacklevel to all warnings.warn() calls All 9 warnings.warn() calls across the codebase were missing stacklevel, causing warning messages to point to internal lines inside Requests rather than the caller's code. Files fixed:...

Changed files:
- `src/requests/__init__.py`
- `src/requests/adapters.py`
- `src/requests/auth.py`
- `src/requests/utils.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7466

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7466
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any]
- state: `CLOSED`
- created_at: `2026-05-21T07:53:54Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7466
- https://github.com/psf/requests/commit/1986df35f43327dd26c7bea9b92e3a85f7a4748d
- https://github.com/psf/requests/issues/7443
- https://github.com/psf/requests/issues/7443#issuecomment-4447179488
- https://github.com/psf/requests/issues/7443#issuecomment-4447452841
- https://github.com/psf/requests/issues/7443#issuecomment-4448009353

Key discussion summary:
- pr: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Ma...
- commit: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] The previous recursive JsonType definition used Sequence["JsonType"] and Mapping[str, "JsonType"], which caused mypy to reject valid JSON arguments like dict[str, Collec...
- linked_ref:
- related_ref: mypy warns about invalid types for json argument <!-- Summary. --> I have warnings about invalid types for the json argument, that didn't occur when using types-requests. The changes in v2.34.1 changed the errors, but did not fix them. <...
- related_ref_comment: This looks like a current limitation of `mypy`. `pyright` and `ty` are both able to detect the typing is correct for these cases. `mypy` seems to be trying to group all possible types into the single highest common type. That's why we ge...

Changed files:
- `src/requests/_types.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7467

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7467
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any]
- state: `CLOSED`
- created_at: `2026-05-21T07:56:01Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7467
- https://github.com/psf/requests/commit/1986df35f43327dd26c7bea9b92e3a85f7a4748d
- https://github.com/psf/requests/issues/7443
- https://github.com/psf/requests/issues/7443#issuecomment-4447179488
- https://github.com/psf/requests/issues/7443#issuecomment-4447452841
- https://github.com/psf/requests/issues/7443#issuecomment-4448009353

Key discussion summary:
- pr: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Ma...
- commit: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] The previous recursive JsonType definition used Sequence["JsonType"] and Mapping[str, "JsonType"], which caused mypy to reject valid JSON arguments like dict[str, Collec...
- linked_ref:
- related_ref: mypy warns about invalid types for json argument <!-- Summary. --> I have warnings about invalid types for the json argument, that didn't occur when using types-requests. The changes in v2.34.1 changed the errors, but did not fix them. <...
- related_ref_comment: This looks like a current limitation of `mypy`. `pyright` and `ty` are both able to detect the typing is correct for these cases. `mypy` seems to be trying to group all possible types into the single highest common type. That's why we ge...

Changed files:
- `src/requests/_types.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7441

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7441
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Move Request.headers back to Mapping
- state: `MERGED`
- created_at: `2026-05-13T21:23:44Z`
- merged_at: `2026-05-14T16:16:26Z`

Evidence URLs:
- https://github.com/psf/requests/pull/7441
- https://github.com/psf/requests/pull/7441#pullrequestreview-4289038802
- https://github.com/psf/requests/commit/412f581d7e7c27bfee4f042fcac89bae9a804afe
- https://github.com/psf/requests/issues/7442
- https://github.com/psf/requests/pull/7431
- https://github.com/psf/requests/pull/7431#issuecomment-4444744937
- https://github.com/psf/requests/pull/7431#issuecomment-4445040684
- https://github.com/psf/requests/pull/7431#issuecomment-4445182838

Key discussion summary:
- pr: Move Request.headers back to Mapping This PR partially reverts #7431, moving it back to `Mapping` instead of `MutableMapping`. While we typically expect the input to be mutable, dicts inferred to be `dict[str, str]` at creation are incom...
- review:
- commit: Move Request.headers back to Mapping
- linked_ref:
- related_ref: Fix mutability issues with headers input types We already got a helpful email, lack of header mutability in the typing contract is creating friction for some code bases. I think we'd started to go down this route but it got lost in the c...

Changed files:
- `src/requests/_types.py`
- `src/requests/models.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7492

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7492
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group
- state: `MERGED`
- created_at: `2026-06-03T00:27:12Z`
- merged_at: `2026-06-03T00:44:54Z`

Evidence URLs:
- https://github.com/psf/requests/pull/7492
- https://github.com/psf/requests/pull/7492#pullrequestreview-4414649181
- https://github.com/psf/requests/commit/2a480a1f56b6e32fd2ef0bcd6048ff468e2768ee
- https://github.com/psf/requests/issues/3894
- https://github.com/psf/requests/issues/3894#issuecomment-282972853
- https://github.com/psf/requests/issues/3894#issuecomment-282975738
- https://github.com/psf/requests/issues/3894#issuecomment-283361385
- https://github.com/psf/requests/pull/3893

Key discussion summary:
- pr: Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group Bumps the actions group with 1 update: [github/codeql-action](https://github.com/github/codeql-action). Updates `github/codeql-action` from 4.35.1 to 4.36.0 <details> <...
- review:
- commit: Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group Bumps the actions group with 1 update: [github/codeql-action](https://github.com/github/codeql-action). Updates `github/codeql-action` from 4.35.1 to 4.36.0 - [Release...
- related_ref: Documentation issue: requests.request behavior unclear when 'data' parameter is dictionary The [documentation for 'requests.request' ](http://docs.python-requests.org/en/master/api/#requests.request) lists a parameter 'data': > data -- (...
- related_ref_comment: > "Dictionary objects will be serialized as JSON using the 'json' module", along with any restrictions on the content of the dictionary. Heh, the fact that you wrote this suggests that it might be worthwhile, given that that's exactly *n...

Changed files:
- `.github/workflows/codeql-analysis.yml`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:6265

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/6265
- suspected_status: `stale`
- final action: `promote`
- final evidence_status: `stale`
- expected_decision: `verify_first`
- confidence: `0.74`
- title: Fix setuptools deprecation warnings
- state: `CLOSED`
- created_at: `2022-10-23T05:24:51Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/6265
- https://github.com/psf/requests/pull/6265#issuecomment-3950145511
- https://github.com/psf/requests/pull/6265#issuecomment-1396967411
- https://github.com/psf/requests/pull/6265#issuecomment-4122466701
- https://github.com/psf/requests/commit/e321c73f73d74c240b50108b93ee8b366245c8f3
- https://github.com/psf/requests/pull/7012
- https://github.com/psf/requests/pull/7012#issuecomment-3194494937
- https://github.com/psf/requests/pull/7012#issuecomment-3194630856

Key discussion summary:
- pr: Fix setuptools deprecation warnings Update keys used in `setup.cfg` in order to fix the following setuptools deprecation warnings: > The license_file parameter is deprecated, use license_files instead. > Usage of dash-separated 'provides...
- comment: Thanks for the efforts, but I have updated as you instructed but still getting this error: <redacted-local-path>
- comment: Looks like this has been obsoleted by #7012.
- comment: Resolving since the setup.cfg is no longer relevant.
- commit: Fix setuptools deprecation warnings Update keys used in `setup.cfg` in order to fix the following setuptools deprecation warnings: > The license_file parameter is deprecated, use license_files instead. > Usage of dash-separated 'provides...

Changed files:
- `setup.cfg`

Why this action: Codex found an older claim and newer superseding evidence with time ordering: older=https://github.com/psf/requests/pull/6265 newer=https://github.com/psf/requests/pull/6265#issuecomment-3950145511.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:psf__requests:pull:7552

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7552
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Fix RFC 6265 DQUOTE handling in RequestsCookieJar.set_cookie
- state: `CLOSED`
- created_at: `2026-06-29T17:32:10Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7552
- https://github.com/psf/requests/pull/7552#issuecomment-4835331893
- https://github.com/psf/requests/commit/4250e6b32b48e94860a3a0dc19c168ecc90086c6

Key discussion summary:
- pr: Fix RFC 6265 DQUOTE handling in RequestsCookieJar.set_cookie ## Summary `RequestsCookieJar.set_cookie` mishandles cookie values wrapped in DQUOTEs per [RFC 6265 section 5.2.3](https://datatracker.ietf.org/doc/html/rfc6265#section-5.2.3)....
- comment: Closing as duplicate.
- commit: Fix RFC 6265 DQUOTE handling in RequestsCookieJar.set_cookie Strip outer DQUOTE characters and unescape backslash-escaped quotes (") inside cookie values, per RFC 6265 section 5.2.3. Previously the code blindly removed all \" sequences w...

Changed files:
- `src/requests/cookies.py`
- `tests/test_requests.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7513

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7513
- suspected_status: `conflicting`
- final action: `promote`
- final evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.78`
- title: Make RequestsCookieJar.popitem() work
- state: `OPEN`
- created_at: `2026-06-13T09:53:28Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7513
- https://github.com/psf/requests/pull/7513#issuecomment-4715750402
- https://github.com/psf/requests/pull/7513#issuecomment-4803293714
- https://github.com/psf/requests/pull/7513#issuecomment-4812850391
- https://github.com/psf/requests/pull/7513#pullrequestreview-4502775948
- https://github.com/psf/requests/commit/76cbba45b9c98832f2d3e2e6caf46e36b1090491
- https://github.com/psf/requests/commit/6aa944469926f4eba9c4f535b7fe4039370ceef3
- https://github.com/psf/requests/commit/254195ec43d7045b4061d29649e543ccb3882183

Key discussion summary:
- pr: Make RequestsCookieJar.popitem() work Closes #6190 `RequestsCookieJar` subclasses both `CookieJar` and `MutableMapping[str, str | None]`. Its `__iter__` is inherited from `CookieJar` and yields `Cookie` objects rather than names. The `po...
- comment: Good catch, fixed. popitem() now selects the cookie via the iterator and removes that exact object with `clear(cookie.domain, cookie.path, cookie.name)`, so it can no longer drop other cookies that happen to share the name on a different...
- comment: Nice to see `RequestsCookieJar.popitem()` behaving like a mapping again. A follow-up test for the empty-jar `KeyError` path might be useful if downstream code depends on that exception.
- comment: Good call, added `test_cookie_popitem_on_empty_jar_raises_keyerror` covering exactly that: `popitem()` on a freshly constructed jar raises `KeyError`, matching `dict.popitem()`. (The existing `test_cookie_popitem` reaches the empty case...
- review: `popitem()` removes by cookie name only (`del self[name]`) after reading the first `(name, value)` pair. That can remove more than the single cookie returned when the jar contains multiple cookies with the same name on different domains/...

Changed files:
- `src/requests/cookies.py`
- `tests/test_requests.py`

Why this action: Codex found at least two GitHub URLs with opposing safety/compatibility signals: support=https://github.com/psf/requests/pull/7513 concern=https://github.com/psf/requests/pull/7513#issuecomment-4715750402.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:psf__requests:pull:7524

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7524
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: fix: empty params no longer produce empty body (#6122)
- state: `CLOSED`
- created_at: `2026-06-18T01:46:39Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7524
- https://github.com/psf/requests/commit/5f63c02876fce0caf045c2b19abb57cd2447cec7
- https://github.com/psf/requests/pull/6122
- https://github.com/psf/requests/pull/6122#issuecomment-1118907570
- https://github.com/psf/requests/pull/6122#issuecomment-1118982054
- https://github.com/psf/requests/pull/6122#issuecomment-1118987814
- https://github.com/psf/requests/pull/6122#issuecomment-1118988153

Key discussion summary:
- pr: fix: empty params no longer produce empty body (#6122) Closes #6122. Co-Authored-By: Claude <<redacted-email>>
- commit: fix: empty params no longer produce empty body (#6122)
- related_ref: Request with data which consists of empty values only sends bad request Case - request with data which consists of empty values only ```python get('http://localhost:80', data={'foo': None}) ``` Response in nginx: ``` 172.17.0.1 - - [05/M...
- related_ref_comment: Hi @romanyakovlev, can you provide some more information about why you believe this needs to be changed? The original input data _is_ `application/x-www-form-urlencoded`, it just happens that the serialized version is an empty string in...
- related_ref_comment: @nateprewitt the reason why I pushed this PR is the problem with nginx. When this type of request was sent to it I saw this in logs: ``` 172.17.0.1 - - [05/May/2022:19:34:30 +0000] "GET / HTTP/1.1" 200 615 "-" "python-requests/2.27.1" "-...

Changed files:
- `src/requests/models.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7545

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7545
- suspected_status: `unknown`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `verify_first`
- confidence: `0.35`
- title: fix: HTTPDigestAuth properly handles bytes credentials
- state: `CLOSED`
- created_at: `2026-06-27T05:32:07Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7545
- https://github.com/psf/requests/commit/1bca59850306ad36b31730746dcd23ed8754f437
- https://github.com/psf/requests/issues/6102
- https://github.com/psf/requests/issues/6102#issuecomment-1087186718
- https://github.com/psf/requests/issues/6102#issuecomment-1087221857
- https://github.com/psf/requests/issues/6102#issuecomment-2061735957
- https://github.com/psf/requests/issues/6102#issuecomment-4022677528

Key discussion summary:
- pr: fix: HTTPDigestAuth properly handles bytes credentials ## Problem When bytes are passed as username/password to `HTTPDigestAuth`, the digest header contains the bytes repr instead of the decoded string: ```python HTTPDigestAuth('Ondřej'....
- commit: fix: HTTPDigestAuth properly handles bytes credentials When bytes are passed as username/password to HTTPDigestAuth, the digest header was containing the bytes repr (e.g. b'Ond\xc5\x99ej') instead of the decoded string. Fix by decoding b...
- linked_ref:
- related_ref: HTTPDigestAuth fails on non-latin credentials There was issue reported, which is closed with bad results. https://github.com/psf/requests/blob/4f6c0187150af09d085c03096504934eb91c7a9e/requests/auth.py#L59-L63 Don't pass unicode strings i...
- related_ref_comment: Hi @ondratu, Could you please clarify what you believe is wrong in this case? `ř` is the byte-sequence `\xc5\x99` in UTF-8, so we'd expect the bytes object to be `Ond\xc5\x99ej`. We can quickly verify this by checking: ```python 'Ondřej'...

Changed files:
- `src/requests/auth.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7538

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7538
- suspected_status: `unknown`
- final action: `promote`
- final evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.68`
- title: Preserve username-only URL auth
- state: `CLOSED`
- created_at: `2026-06-24T14:13:11Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7538
- https://github.com/psf/requests/pull/7538#issuecomment-4793357685
- https://github.com/psf/requests/pull/7538#issuecomment-4793362640
- https://github.com/psf/requests/commit/c5749bc4a8a2884aaf2209c7fc27551375dd7465

Key discussion summary:
- pr: Preserve username-only URL auth ## Summary get_auth_from_url() now keeps a URL username when the URL has no password component instead of dropping the username. ## Why A username-only URL authority still carries authentication informatio...
- comment: Hi @lin-hongkuan, do you have a concrete scenario where you've actually encountered this or is it something that Codex derived? Given this code has been in place for ~15 years with billions of downloads and no one has hit this issue, we'...
- comment: Nevermind, I see this is an OpenClaw agent on the loose.
- commit: Preserve username-only URL auth

Changed files:
- `src/requests/utils.py`
- `tests/test_utils.py`

Why this action: Codex found high-risk change evidence but insufficient safety/verification discussion: high_risk_hits=auth.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:psf__requests:pull:7232

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7232
- suspected_status: `unknown`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `verify_first`
- confidence: `0.35`
- title: feat: add RFC 7616 support for non-Latin credentials in HTTPDigestAuth
- state: `CLOSED`
- created_at: `2026-03-01T08:05:53Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7232
- https://github.com/psf/requests/pull/7232#pullrequestreview-3989720191
- https://github.com/psf/requests/commit/ad19d27eb5f0e16131a0f4f7d93853a9cacd9703
- https://github.com/psf/requests/issues/6102
- https://github.com/psf/requests/issues/6102#issuecomment-1087186718
- https://github.com/psf/requests/issues/6102#issuecomment-1087221857
- https://github.com/psf/requests/issues/6102#issuecomment-2061735957
- https://github.com/psf/requests/issues/6102#issuecomment-4022677528

Key discussion summary:
- pr: feat: add RFC 7616 support for non-Latin credentials in HTTPDigestAuth ## Summary Implement [RFC 7616](https://www.rfc-editor.org/rfc/rfc7616) extensions to fix `HTTPDigestAuth` failing with non-Latin-1 usernames (e.g., Cyrillic, Czech d...
- review: nit: digest username* encoding depends on `urllib.parse.quote` plus the custom `safe` set; a regression test for edge chars (e.g. backtick) would lock RFC5987/Digest grammar assumptions.
- commit: feat: add RFC 7616 support for non-Latin credentials in HTTPDigestAuth HTTPDigestAuth currently fails when usernames contain non-Latin-1 characters (e.g., Cyrillic, Czech diacritics). The username is directly interpolated into the Digest...
- linked_ref:
- related_ref: HTTPDigestAuth fails on non-latin credentials There was issue reported, which is closed with bad results. https://github.com/psf/requests/blob/4f6c0187150af09d085c03096504934eb91c7a9e/requests/auth.py#L59-L63 Don't pass unicode strings i...

Changed files:
- `src/requests/auth.py`
- `tests/test_digest_rfc7616.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7520

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7520
- suspected_status: `unknown`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `verify_first`
- confidence: `0.35`
- title: Keep Link header parameter values that contain '='
- state: `OPEN`
- created_at: `2026-06-16T21:44:40Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7520
- https://github.com/psf/requests/pull/7520#issuecomment-4803293355
- https://github.com/psf/requests/commit/028edad469bae290e643e027439286c67719f0c9

Key discussion summary:
- pr: Keep Link header parameter values that contain '=' ## Summary `parse_header_links` splits each `Link` header parameter on `=` with `key, value = param.split("=")` (no `maxsplit`). RFC 8288 permits quoted parameter **values** that themsel...
- comment: Good fix for quoted parameters containing `=`. I like that the test covers the RFC 8288-style case; it might also be worth checking a quoted value that contains both `=` and `;` to prove the split stays local.
- commit: Keep Link header parameter values that contain '=' parse_header_links split each parameter on '=' without a maxsplit, so a quoted value containing '=' (allowed by RFC 8288) produced 3+ parts and raised ValueError. The bare 'except ValueE...

Changed files:
- `src/requests/utils.py`
- `tests/test_utils.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7535

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7535
- suspected_status: `unknown`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `verify_first`
- confidence: `0.35`
- title: parse_list_header and parse_dict_header: do not unquote tokens that lack a balanced closing quote
- state: `CLOSED`
- created_at: `2026-06-22T15:30:26Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7535
- https://github.com/psf/requests/commit/984bf08a77c85e7a29884425f45748886aa88aa5

Key discussion summary:
- pr: parse_list_header and parse_dict_header: do not unquote tokens that lack a balanced closing quote ## What `parse_list_header` and `parse_dict_header` in `src/requests/utils.py` used `item[:1] == item[-1:] == '"'` to test whether an item...
- commit: parse_list_header and parse_dict_header: do not unquote tokens that l… …ack a balanced closing quote The check `if item[:1] == item[-1:] == '"':` matched for any single-character `"`, because a length-1 string and a length-1 string-slice...

Changed files:
- `src/requests/utils.py`
- `tests/test_utils.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7486

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7486
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: fix: check callable before tuple in prepare_auth
- state: `CLOSED`
- created_at: `2026-05-25T09:06:57Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7486
- https://github.com/psf/requests/pull/7486#issuecomment-4537786052
- https://github.com/psf/requests/commit/48e151d4c62b4f4a9f906f75182e60b1cb8c40e1

Key discussion summary:
- pr: fix: check callable before tuple in prepare_auth ## Summary `prepare_auth` currently checks `isinstance(auth, tuple)` before `callable(auth)`. Any auth object that is both a 2-element tuple subclass **and** callable — for example an `Aut...
- comment: Hi @qizwiz, thanks for the PR. The TODO was a note for ourselves and intentionally left for 2.34.x to keep the surface area of the change smaller. We already have a patch prepared for when we do the flip. I'll close this out as it won't...
- commit: fix: check callable before tuple in prepare_auth When auth is both callable and a 2-element tuple subclass (e.g. a namedtuple-based AuthBase subclass), the previous code took the isinstance(auth, tuple) branch first and silently construc...

Changed files:
- `src/requests/models.py`
- `tests/test_requests.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7540

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7540
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Bump actions/checkout from 6.0.2 to 7.0.0 in the actions group
- state: `MERGED`
- created_at: `2026-06-24T22:41:17Z`
- merged_at: `2026-06-24T22:47:15Z`

Evidence URLs:
- https://github.com/psf/requests/pull/7540
- https://github.com/psf/requests/pull/7540#pullrequestreview-4566502158
- https://github.com/psf/requests/commit/a5935d2f63450adae9663c92036a9a45ee1842ac
- https://github.com/psf/requests/issues/2467
- https://github.com/psf/requests/issues/2467#issuecomment-76901637
- https://github.com/psf/requests/issues/2467#issuecomment-76901732
- https://github.com/psf/requests/issues/2467#issuecomment-76901915
- https://github.com/psf/requests/issues/2467#issuecomment-76901960

Key discussion summary:
- pr: Bump actions/checkout from 6.0.2 to 7.0.0 in the actions group Bumps the actions group with 1 update: [actions/checkout](https://github.com/actions/checkout). Updates `actions/checkout` from 6.0.2 to 7.0.0 <details> <summary>Release note...
- review:
- commit: Bump actions/checkout from 6.0.2 to 7.0.0 in the actions group Bumps the actions group with 1 update: [actions/checkout](https://github.com/actions/checkout). Updates `actions/checkout` from 6.0.2 to 7.0.0 - [Release notes](https://githu...
- related_ref: timeout issues for chunked responses When I set a timeout value for my simple GET request, the `requests.get` call takes a really long time to complete when I don't iterate over the returned content. If I iterate over the content, the `r...
- related_ref_comment: Can you post your values? Because I don't see this at all: T=10, stream iter took: 0.515799999237 T=10, stream all took: 0.428910970688 T=10, no stream took: 0.423730134964 T=None, stream iter took: 0.422012805939 T=None, stream all took...

Changed files:
- `.github/workflows/codeql-analysis.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/publish.yml`
- `.github/workflows/run-tests.yml`
- `.github/workflows/typecheck.yml`
- `.github/workflows/zizmor.yml`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:psf__requests:pull:7491

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/7491
- suspected_status: `conflicting`
- final action: `promote`
- final evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.78`
- title: fix: restore urlparse path params in digest auth uri (#6990)
- state: `CLOSED`
- created_at: `2026-06-02T19:13:13Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/psf/requests/pull/7491
- https://github.com/psf/requests/commit/0a04af26d265a19d3c64de455b5a5bf64140a390
- https://github.com/psf/requests/pull/7491#issuecomment-4606223587
- https://github.com/psf/requests/pull/7491#issuecomment-4616527678
- https://github.com/psf/requests/commit/4f31071da2cf1c7ed2c6d7b4b73a12cc676406f0

Key discussion summary:
- pr: fix: restore urlparse path params in digest auth uri (#6990) ## Problem `urlparse()` from `urllib.parse` treats semicolons as path parameter delimiters per RFC 1808. For a URL like: ``` /ws/2/collection/xxx/releases/aaa;bbb?fmt=json ```...
- comment: I believe there are already other open PRs for this.
- comment: This is a complete glitch. I'm just testing Von. My sincerest apologies. I'm going to have to restrict Von's permissions as it went completely off the rails here. Von was to supposed to just optimize it's bug fixing abilities not interac...
- commit: Fix uri field in digest auth to include semicolons in path (GH-6990) urlparse() discards semicolon-delimited path params per RFC 1808, but RFC 7616 §3.4 requires the uri directive to contain the full Effective Request URI. Reconstruct th...
- commit: fix: correct test assertion for digest auth semicolon URI (#6990)

Changed files:
- `src/requests/auth.py`
- `tests/test_requests.py`

Why this action: Codex found at least two GitHub URLs with opposing safety/compatibility signals: support=https://github.com/psf/requests/pull/7491 concern=https://github.com/psf/requests/commit/0a04af26d265a19d3c64de455b5a5bf64140a390.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:psf__requests:pull:6965

- repo: `psf/requests`
- PR URL: https://github.com/psf/requests/pull/6965
- suspected_status: `unknown`
- final action: `promote`
- final evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.68`
- title: Only use hostname to do netrc lookup instead of netloc
- state: `MERGED`
- created_at: `2025-06-04T15:00:33Z`
- merged_at: `2025-06-04T15:39:25Z`

Evidence URLs:
- https://github.com/psf/requests/pull/6965
- https://github.com/psf/requests/pull/6965#pullrequestreview-2897244847
- https://github.com/psf/requests/pull/6965#pullrequestreview-3577157683
- https://github.com/psf/requests/commit/57acb7c26d809cf864ec439b8bcd6364702022d5

Key discussion summary:
- pr: Only use hostname to do netrc lookup instead of netloc Applies the patch generated from the GHSA which we couldn't merge as no one on the team had sufficient permissions.
- review:
- review: @copilot review impliment
- commit: Only use hostname to do netrc lookup instead of netloc

Changed files:
- `src/requests/utils.py`

Why this action: Codex found high-risk change evidence but insufficient safety/verification discussion: high_risk_hits=permission.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:14668

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14668
- suspected_status: `conflicting`
- final action: `promote`
- final evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.78`
- title: Handle RaisesGroup check errors during suggestions
- state: `OPEN`
- created_at: `2026-07-01T01:16:38Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14668
- https://github.com/pytest-dev/pytest/issues/14324
- https://github.com/pytest-dev/pytest/commit/5610d09c56f22ae23c2f704ab42291aa3faa35df
- https://github.com/pytest-dev/pytest/commit/fda161635bdf5f01ccdbfb355999eaf67f2be5b5
- https://github.com/pytest-dev/pytest/commit/672df22661b2e551bf4b466b0f58f122d47ae80e
- https://github.com/pytest-dev/pytest/issues/14324#issuecomment-4365515799
- https://github.com/pytest-dev/pytest/issues/14324#issuecomment-4420136650

Key discussion summary:
- pr: Handle RaisesGroup check errors during suggestions ## Summary - prevent the speculative `RaisesGroup` suggestion check from surfacing exceptions raised by a group-level `check` callable - keep the existing helpful suggestion when the cal...
- commit: Handle RaisesGroup check errors during suggestions
- commit: Add changelog for RaisesGroup check fix
- commit: Cover RaisesGroup check suggestion branch
- linked_ref:

Changed files:
- `changelog/14324.bugfix.rst`
- `src/_pytest/raises.py`
- `testing/python/raises_group.py`

Why this action: Codex found at least two GitHub URLs with opposing safety/compatibility signals: support=https://github.com/pytest-dev/pytest/pull/14668 concern=https://github.com/pytest-dev/pytest/issues/14324.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:14662

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14662
- suspected_status: `conflicting`
- final action: `promote`
- final evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.78`
- title: Expose CaptureManager as public API (#14186)
- state: `OPEN`
- created_at: `2026-06-29T14:59:18Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14662
- https://github.com/pytest-dev/pytest/pull/14662#issuecomment-4835239496
- https://github.com/pytest-dev/pytest/commit/7be379452b6e920d5830be0a54e8dda683181395
- https://github.com/pytest-dev/pytest/issues/14186
- https://github.com/pytest-dev/pytest/issues/14186#issuecomment-3919349685
- https://github.com/pytest-dev/pytest/issues/14186#issuecomment-4175465285

Key discussion summary:
- pr: Expose CaptureManager as public API (#14186) Expose `CaptureManager` as a public API type. This exposes `CaptureManager` via `pytest.CaptureManager` so plugin authors can annotate capture-manager lookups without importing from `_pytest.c...
- comment: Bit of an old issue, but I think I have a fix for it. Tests verify no typing regressions as well since that was a concern. Mind taking a review whenever you have some time? @RonnyPfannschmidt
- commit: Expose CaptureManager as public API (#14186)
- linked_ref:
- related_ref: Expose CaptureManager as public API #### What's the problem this feature will solve? Plugins that need to temporarily disable capture to write directly to the terminal reporter must reference `CaptureManager` for type annotations. The on...

Changed files:
- `changelog/14186.improvement.rst`
- `doc/en/reference/reference.rst`
- `src/pytest/__init__.py`
- `testing/test_capture.py`
- `testing/typing_checks.py`

Why this action: Codex found at least two GitHub URLs with opposing safety/compatibility signals: support=https://github.com/pytest-dev/pytest/pull/14662 concern=https://github.com/pytest-dev/pytest/pull/14662#issuecomment-4835239496.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:14639

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14639
- suspected_status: `conflicting`
- final action: `promote`
- final evidence_status: `conflicting`
- expected_decision: `detect_conflict`
- confidence: `0.78`
- title: Fix off-by-one in trailing assertion diff skipping (#14637)
- state: `MERGED`
- created_at: `2026-06-22T15:48:02Z`
- merged_at: `2026-06-27T14:29:07Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14639
- https://github.com/pytest-dev/pytest/issues/14637
- https://github.com/pytest-dev/pytest/pull/14639#issuecomment-4805024770
- https://github.com/pytest-dev/pytest/pull/14639#issuecomment-4818408905
- https://github.com/pytest-dev/pytest/pull/14639#pullrequestreview-4576584925
- https://github.com/pytest-dev/pytest/pull/14639#pullrequestreview-4576605547
- https://github.com/pytest-dev/pytest/commit/2767c4c1fd797f56055c54a4e3d3b56985879bcd
- https://github.com/pytest-dev/pytest/commit/71f3403c79d2eb6218f13ceb6c50eb6fe86649d4

Key discussion summary:
- pr: Fix off-by-one in trailing assertion diff skipping (#14637) Closes #14637 Fix an off-by-one in trailing text diff skipping so pytest compares from the last character first instead of accidentally checking the first character via `-0`. Th...
- comment: @RonnyPfannschmidt could I please get a reviewal for this?
- comment: > Good work thanks How do we go about merging this? On my end it says unable to merge at this time.
- review: Good work thanks
- review:

Changed files:
- `AUTHORS`
- `changelog/14637.bugfix.rst`
- `src/_pytest/assertion/compare_text.py`
- `testing/test_assertion.py`

Why this action: Codex found at least two GitHub URLs with opposing safety/compatibility signals: support=https://github.com/pytest-dev/pytest/pull/14639 concern=https://github.com/pytest-dev/pytest/issues/14637.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:14641

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14641
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: fix(config): remove `as Name` re-export pattern to support PYTHON_LAZY_IMPORTS=all (Python 3.15)
- state: `OPEN`
- created_at: `2026-06-22T18:27:39Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14641
- https://github.com/pytest-dev/pytest/commit/859c39ed7d2e3cd9a3ea00903f59011ce4858365
- https://github.com/pytest-dev/pytest/issues/14632
- https://github.com/pytest-dev/pytest/issues/14632#issuecomment-4762291706

Key discussion summary:
- pr: fix(config): remove `as Name` re-export pattern to support PYTHON_LAZY_IMPORTS=all (Python 3.15) ## Problem `pytest` crashes when run with Python 3.15's `PYTHON_LAZY_IMPORTS=all` environment variable: ``` $ PYTHON_LAZY_IMPORTS=all pytest...
- commit: fix(config): remove `as Name` re-export pattern to support PYTHON_LAZ… …Y_IMPORTS=all
- linked_ref:
- related_ref: `pytest` does not work with `PYTHON_LAZY_IMPORTS=all` Python version: 3.15.0b2+dev Pytest version: 9.1.1 `PYTHON_LAZY_IMPORTS=all pytest --help` produces: ```python Traceback (most recent call last): File "<redacted-local-path>
- related_ref_comment: Assertion rewrite doesn't expect it's import hook to Recurse that way We may need a hardheaded skip list for that import mode

Changed files:
- `src/_pytest/config/__init__.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:8251

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/8251
- suspected_status: `unknown`
- final action: `promote`
- final evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.68`
- title: implement Node.path as pathlib.Path
- state: `MERGED`
- created_at: `2021-01-17T20:21:26Z`
- merged_at: `2021-03-07T14:10:07Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/8251
- https://github.com/pytest-dev/pytest/pull/8251#issuecomment-773286118
- https://github.com/pytest-dev/pytest/pull/8251#issuecomment-779473211
- https://github.com/pytest-dev/pytest/pull/8251#issuecomment-779481971
- https://github.com/pytest-dev/pytest/pull/8251#issuecomment-792049509
- https://github.com/pytest-dev/pytest/pull/8251#issuecomment-796852908
- https://github.com/pytest-dev/pytest/pull/8251#issuecomment-796914731
- https://github.com/pytest-dev/pytest/pull/8251#discussion_r559233363

Key discussion summary:
- pr: implement Node.path as pathlib.Path there is a bug in module collection left that i dont see tonight, lets retry tommorow <!-- Thanks for submitting a PR, your contribution is really appreciated! Here is a quick checklist that should be...
- comment: Im hopeful that I will be able to pick up the remaining issue this weekend
- comment: Found the problem: the `plugins_integration` directory has its own `pytest.ini` file. 😁
- comment: > Found the problem: the `plugins_integration` directory has its own `pytest.ini` file. 😁 I knew I'd face-palm the moment someone solved it, thanks a lot
- comment: @nicoddemus i squashed, should be good to merge after green

Changed files:
- `.pre-commit-config.yaml`
- `changelog/8251.deprecation.rst`
- `changelog/8251.feature.rst`
- `doc/en/deprecations.rst`
- `src/_pytest/_code/code.py`
- `src/_pytest/cacheprovider.py`
- `src/_pytest/compat.py`
- `src/_pytest/config/__init__.py`
- `src/_pytest/deprecated.py`
- `src/_pytest/doctest.py`
- `src/_pytest/fixtures.py`
- `src/_pytest/hookspec.py`
- ... 18 more files

Why this action: Codex found high-risk change evidence but insufficient safety/verification discussion: high_risk_hits=auth, config, public api.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:14180

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14180
- suspected_status: `conflicting`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Clarify retention policy
- state: `OPEN`
- created_at: `2026-02-11T08:48:31Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14180
- https://github.com/pytest-dev/pytest/pull/14180#issuecomment-3885755426
- https://github.com/pytest-dev/pytest/pull/14180#issuecomment-3889185929
- https://github.com/pytest-dev/pytest/pull/14180#discussion_r2792110891
- https://github.com/pytest-dev/pytest/pull/14180#discussion_r2792116295
- https://github.com/pytest-dev/pytest/pull/14180#discussion_r2792118422
- https://github.com/pytest-dev/pytest/pull/14180#discussion_r2792252778
- https://github.com/pytest-dev/pytest/pull/14180#discussion_r2792254916

Key discussion summary:
- pr: Clarify retention policy While debugging a test session that ran out of diskspace in CI tried different retention policies. From reading the docs I would have expected that both `failed` and `none` would remove tmp files during teardown...
- comment: Wait dir retention of none should be dropping them
- comment: > Wait dir retention of none should be dropping them @RonnyPfannschmidt the logic here https://github.com/pytest-dev/pytest/blob/main/src/_pytest/tmpdir.py#L274 only removes files if retention policy is explicitly set to failed. If the p...
- review_comment: Maybe link the fixture instead of having it as plain text?
- review_comment: How about linking the respective settings in the docs? Also, there's an accidental double backtick on this line that breaks render: https://pytest--14180.org.readthedocs.build/en/14180/changelog.html#improved-documentation

Changed files:
- `changelog/14180.doc.rst`
- `doc/en/reference/reference.rst`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:13370

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/13370
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: fix #6881 - add policies for too long ids from a str and use short as default
- state: `OPEN`
- created_at: `2025-04-11T19:27:45Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/13370
- https://github.com/pytest-dev/pytest/pull/13370#discussion_r3301752567
- https://github.com/pytest-dev/pytest/pull/13370#discussion_r3301752624
- https://github.com/pytest-dev/pytest/pull/13370#discussion_r3301752650
- https://github.com/pytest-dev/pytest/pull/13370#discussion_r3301752680
- https://github.com/pytest-dev/pytest/pull/13370#discussion_r3306852188
- https://github.com/pytest-dev/pytest/pull/13370#discussion_r3306852219
- https://github.com/pytest-dev/pytest/pull/13370#pullrequestreview-2761414646

Key discussion summary:
- pr: fix #6881 - add policies for too long ids from a str and use short as default <!-- Thanks for submitting a PR, your contribution is really appreciated! Here is a quick checklist that should be present in PRs. - [ ] Include documentation...
- review_comment: The new ini help text doesn’t match the implemented behavior: the `short` strategy doesn’t “shorten the value normally” — it falls back to `<argname><index>` when `len(val) > 100`. Also, this new config option is currently undocumented i...
- review_comment: Returning `None` for long `str|bytes` in `_idval_from_value` changes behavior beyond “IDs derived from parameter values”: this method is also used by `_idval_from_value_required` for explicit `ids=[...]` entries and by the `ids=` callabl...
- review_comment: The `disallow` branch raises a bare `ValueError("too long as id", len(val), val)` which is not very actionable and includes the full (potentially huge) value in the exception args. This can flood tracebacks/output and reintroduce “too lo...
- review_comment: This test currently asserts `ValueError` for the `disallow` strategy. If the implementation is adjusted to use pytest’s normal collection failures (`fail(..., pytrace=False)` / `Collector.CollectError`) with a clearer message (recommende...

Changed files:
- `changelog/6881.feature.rst`
- `doc/en/reference/reference.rst`
- `src/_pytest/python.py`
- `testing/python/metafunc.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14322

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14322
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Enable record_property for junit_family=xunit2
- state: `CLOSED`
- created_at: `2026-03-24T18:22:20Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14322
- https://github.com/pytest-dev/pytest/pull/14322#issuecomment-4134660973
- https://github.com/pytest-dev/pytest/commit/2419df89398dc9b70fde1582b5cff0aa6f0a6a90
- https://github.com/pytest-dev/pytest/issues/14315
- https://github.com/pytest-dev/pytest/issues/14315#issuecomment-4134658819

Key discussion summary:
- pr: Enable record_property for junit_family=xunit2 Refs #14315 ## Summary This change enables `record_property` when `junit_family=xunit2` is used. ## What changed - removed the xunit2 incompatibility warning for `record_property` - added a...
- comment: Close as per https://github.com/pytest-dev/pytest/issues/14315#issuecomment-4134658819
- commit: Enable record_property for junit_family=xunit2
- related_ref: [junitxml] Add support for record_property fixture for xunit2 junit_family <!-- Thanks for suggesting a feature! Quick check-list while suggesting features: --> #### What's the problem this feature will solve? When using `junit_family=xu...
- related_ref_comment: We have a warning in place that the attributes added by record_property are not part of the xunit2 schema. Even if other tools support it, seems they support it even though the official schema does not. (I have not double checked the xun...

Changed files:
- `changelog/14315.improvement.rst`
- `src/_pytest/junitxml.py`
- `testing/test_junitxml.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14053

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14053
- suspected_status: `unknown`
- final action: `promote`
- final evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.68`
- title: docs: clarify capture fixture precedence over -s
- state: `MERGED`
- created_at: `2025-12-20T17:12:24Z`
- merged_at: `2025-12-28T19:43:42Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14053
- https://github.com/pytest-dev/pytest/pull/14053#issuecomment-3678003661
- https://github.com/pytest-dev/pytest/pull/14053#issuecomment-3678003956
- https://github.com/pytest-dev/pytest/pull/14053#issuecomment-3693995291
- https://github.com/pytest-dev/pytest/pull/14053#issuecomment-3694994235
- https://github.com/pytest-dev/pytest/pull/14053#discussion_r2649154995
- https://github.com/pytest-dev/pytest/pull/14053#discussion_r2649846867
- https://github.com/pytest-dev/pytest/pull/14053#pullrequestreview-3601388195

Key discussion summary:
- pr: docs: clarify capture fixture precedence over -s closes #13731 Clarify in the capturing tutorial that using capture fixtures such as `capsys` or `capfd` re-enables capturing for the duration of the test, even when global capturing is dis...
- comment: The docs build failure appears to be unrelated to this change. It looks like an incompatibility between Sphinx 9.0.4 and sphinxcontrib-trio (KeyError: 'autofunction'). Happy to rebase or update once the docs toolchain is fixed.
- comment: @Zac-HD Could you please check if that what you had in mind for the issue?
- comment: The CI failure is being addressed in https://github.com/pytest-dev/pytest/pull/14067.
- comment: ### Backport to 9.0.x: 💚 backport PR created ✅ Backport PR branch: `patchback/backports/9.0.x/8f5b07d87bf803622bb96227ed939f3c95f8809b/pr-14053` Backported as https://github.com/pytest-dev/pytest/pull/14073 <sub><sup> -- 🤖 @patchback I'm...

Changed files:
- `changelog/13731.doc.rst`
- `doc/en/how-to/capture-stdout-stderr.rst`

Why this action: Codex found high-risk change evidence but insufficient safety/verification discussion: high_risk_hits=auth, compatibility, config.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:14625

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14625
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: [PR #14596/a07c31a9 backport][9.1.x] doc,testing: fix `scope="class"` instance methods
- state: `MERGED`
- created_at: `2026-06-19T09:16:57Z`
- merged_at: `2026-06-19T09:40:45Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14625
- https://github.com/pytest-dev/pytest/pull/14625#pullrequestreview-4531663683
- https://github.com/pytest-dev/pytest/commit/501c4bc784da3b08bfcaa64858eba5d15dc59e53
- https://github.com/pytest-dev/pytest/pull/14596
- https://github.com/pytest-dev/pytest/pull/14596#issuecomment-4750219733

Key discussion summary:
- pr: [PR #14596/a07c31a9 backport][9.1.x] doc,testing: fix `scope="class"` instance methods **This is a backport of PR #14596 as merged into main (a07c31a97d0a412c09b1f2f5953adb4b4a75d04d).** This is deprecated, we should use classmethods for...
- review:
- commit: Merge pull request #14596 from bluetech/doc-classmethod doc,testing: fix `scope="class"` instance methods (cherry picked from commit a07c31a97d0a412c09b1f2f5953adb4b4a75d04d)
- related_ref: doc,testing: fix `scope="class"` instance methods This is deprecated, we should use classmethods for that.
- related_ref_comment: ### Backport to 9.1.x: 💚 backport PR created ✅ Backport PR branch: `patchback/backports/9.1.x/a07c31a97d0a412c09b1f2f5953adb4b4a75d04d/pr-14596` Backported as https://github.com/pytest-dev/pytest/pull/14625 <sub><sup> -- 🤖 @patchback I'm...

Changed files:
- `doc/en/how-to/fixtures.rst`
- `testing/python/fixtures.py`
- `testing/python/metafunc.py`
- `testing/test_unittest.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14596

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14596
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: doc,testing: fix `scope="class"` instance methods
- state: `MERGED`
- created_at: `2026-06-14T07:37:35Z`
- merged_at: `2026-06-19T09:16:43Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14596
- https://github.com/pytest-dev/pytest/pull/14596#issuecomment-4750219733
- https://github.com/pytest-dev/pytest/commit/cc3a25d1a6c16e6d533e579122b91a51dae33e62

Key discussion summary:
- pr: doc,testing: fix `scope="class"` instance methods This is deprecated, we should use classmethods for that.
- comment: ### Backport to 9.1.x: 💚 backport PR created ✅ Backport PR branch: `patchback/backports/9.1.x/a07c31a97d0a412c09b1f2f5953adb4b4a75d04d/pr-14596` Backported as https://github.com/pytest-dev/pytest/pull/14625 <sub><sup> -- 🤖 @patchback I'm...
- commit: doc,testing: fix `scope="class"` instance methods This is deprecated, we should use classmethods for that.

Changed files:
- `doc/en/how-to/fixtures.rst`
- `testing/python/fixtures.py`
- `testing/python/metafunc.py`
- `testing/test_unittest.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14293

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14293
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: outcomes: remove deprecated `importorskip` `ImportError` behavior
- state: `MERGED`
- created_at: `2026-03-15T11:38:04Z`
- merged_at: `2026-03-17T10:34:36Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14293
- https://github.com/pytest-dev/pytest/pull/14293#issuecomment-4707276895
- https://github.com/pytest-dev/pytest/pull/14293#issuecomment-4707899534
- https://github.com/pytest-dev/pytest/pull/14293#pullrequestreview-3954725678
- https://github.com/pytest-dev/pytest/pull/14293#pullrequestreview-3959485917
- https://github.com/pytest-dev/pytest/commit/10929dcd8ac8484331be9f686a85ce02d09fefdf
- https://github.com/pytest-dev/pytest/issues/13893

Key discussion summary:
- pr: outcomes: remove deprecated `importorskip` `ImportError` behavior Deprecated scheduled for removal in pytest 9. Part of #13893.
- comment: It would be nice if this was called out in the [9.1 changelog](https://docs.pytest.org/en/latest/changelog.html#removals-and-backward-incompatible-breaking-changes). (for the record, this has just broken the Apache Arrow CI)
- comment: Indeed, it was our bad about not mentioning it in the changelog. :+1:
- review:
- review:

Changed files:
- `doc/en/deprecations.rst`
- `src/_pytest/outcomes.py`
- `testing/test_runner.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14523

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14523
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: Use streaming in all assertion comparisons consumers
- state: `OPEN`
- created_at: `2026-05-26T08:00:41Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14523
- https://github.com/pytest-dev/pytest/pull/14523#issuecomment-4544508630
- https://github.com/pytest-dev/pytest/pull/14523#issuecomment-4584592945
- https://github.com/pytest-dev/pytest/pull/14523#issuecomment-4847862438
- https://github.com/pytest-dev/pytest/pull/14523#discussion_r3313417994
- https://github.com/pytest-dev/pytest/pull/14523#discussion_r3313426311
- https://github.com/pytest-dev/pytest/pull/14523#discussion_r3313441593
- https://github.com/pytest-dev/pytest/pull/14523#discussion_r3313523104

Key discussion summary:
- pr: Use streaming in all assertion comparisons consumers Follow-up to the streaming-comparison chain: #14521 (comparators → generators), #14546 (base comparisons return an iterator), #14587 (set comparison → `Iterator[str]`), #14588 (`Pretty...
- comment: Thank you ! Do you have an opinion about the next step ? (3 options in the PR description)
- comment: I removed the number of removed line in the message. Benchmark on pathological case with very big set show big improvement, but I benchmarked on pylint test suite for a realistic perf change: round1-upstream: 118.29s round1-HEAD : 115.39...
- comment: @bluetech @nicoddemus this is ready to review ! I could separate the first commit into its own MR, but I don't think it's worth it.
- review_comment: Is the annotation needed?

Changed files:
- `changelog/14523.improvement.rst`
- `doc/en/example/reportingdemo.rst`
- `doc/en/how-to/output.rst`
- `src/_pytest/assertion/__init__.py`
- `src/_pytest/assertion/_compare_any.py`
- `src/_pytest/assertion/_compare_mapping.py`
- `src/_pytest/assertion/_compare_sequence.py`
- `src/_pytest/assertion/_typing.py`
- `src/_pytest/assertion/compare_text.py`
- `src/_pytest/assertion/truncate.py`
- `src/_pytest/assertion/util.py`
- `testing/python/approx.py`
- ... 1 more files

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14633

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14633
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: assertion rewrite: use sys.stdlib_module_names to skip stdlib modules early, replacing the _in_find_spec flag
- state: `OPEN`
- created_at: `2026-06-21T14:36:17Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14633
- https://github.com/pytest-dev/pytest/pull/14633#issuecomment-4762321149
- https://github.com/pytest-dev/pytest/pull/14633#issuecomment-4762361783
- https://github.com/pytest-dev/pytest/pull/14633#discussion_r3448599568
- https://github.com/pytest-dev/pytest/pull/14633#pullrequestreview-4539863674
- https://github.com/pytest-dev/pytest/commit/b939cb4ef12c1c826bd83ea63196d9300fbedb20
- https://github.com/pytest-dev/pytest/commit/3fdbf0b06a74facefa4ddf168089c4ac5a9fdbe1
- https://github.com/pytest-dev/pytest/commit/f50d6958cf6d1aecb1660438f4c94a3dc10dee28

Key discussion summary:
- pr: assertion rewrite: use sys.stdlib_module_names to skip stdlib modules early, replacing the _in_find_spec flag With `PYTHON_LAZY_IMPORTS=all` (Python 3.15+), accessing a lazily-imported attribute inside `find_spec` triggers a recursive `f...
- comment: @RonnyPfannschmidt Thanks for the suggestion! Hopefully this works 🙏
- comment: @soxofaan @ofek I'm on the playground with my daughter id appreciate if you guys gave this one a spin to see if it works in practice
- review_comment: this is not technically required. on < 3.15, it does just does nothing. it can still be checked.
- review:

Changed files:
- `src/_pytest/assertion/rewrite.py`
- `testing/test_assertrewrite.py`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:11844

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/11844
- suspected_status: `unknown`
- final action: `promote`
- final evidence_status: `unknown`
- expected_decision: `verify_first`
- confidence: `0.68`
- title: delete silly chdir
- state: `CLOSED`
- created_at: `2024-01-18T22:52:24Z`
- merged_at: `None`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/11844
- https://github.com/pytest-dev/pytest/pull/11844#issuecomment-1899820112
- https://github.com/pytest-dev/pytest/pull/11844#issuecomment-1900483686
- https://github.com/pytest-dev/pytest/pull/11844#issuecomment-1900681132
- https://github.com/pytest-dev/pytest/pull/11844#issuecomment-2180174227
- https://github.com/pytest-dev/pytest/pull/11844#issuecomment-2690662149
- https://github.com/pytest-dev/pytest/pull/11844#pullrequestreview-2518608538
- https://github.com/pytest-dev/pytest/pull/11844#pullrequestreview-2518608769

Key discussion summary:
- pr: delete silly chdir This line causes the below insane behavior. I hypothesize that it's here for no really good reason. https://gist.github.com/bukzor/085b1c2bdaa5bc6033db50d718c48bd3 Here is a quick checklist that should be present in PR...
- comment: Can you explain what you mean by silly behavior I recall this was added to prevent breakage if pytest was invoked multiple times and the test suite wasn't cleaning up correctly
- comment: If you run the test in the gist in the OP, and ctrl-c during its sleep, the test fails due to a seemingly inexplicable chdir. I see the failing tests. I made this PR in hope that there was none :). I'll of course need to find a better so...
- comment: https://github.com/pytest-dev/pytest/pull/11826 might have solved this
- comment: This is assumed fixed by #11826 for quite a while now - @bukzor all good now? Can we close this one?

Changed files:
- `src/_pytest/main.py`

Why this action: Codex found high-risk change evidence but insufficient safety/verification discussion: high_risk_hits=auth.

Most important human final-check point:
- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.

### hard_candidate:pytest-dev__pytest:pull:13210

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/13210
- suspected_status: `unknown`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `verify_first`
- confidence: `0.35`
- title: build(deps): Bump django from 5.1.5 to 5.1.6 in /testing/plugins_integration
- state: `MERGED`
- created_at: `2025-02-10T03:29:23Z`
- merged_at: `2025-02-10T07:45:40Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/13210
- https://github.com/pytest-dev/pytest/pull/13210#pullrequestreview-2604908257
- https://github.com/pytest-dev/pytest/commit/935e11082108dc38990846cd16bf2c86d87c4bac

Key discussion summary:
- pr: build(deps): Bump django from 5.1.5 to 5.1.6 in /testing/plugins_integration Bumps [django](https://github.com/django/django) from 5.1.5 to 5.1.6. <details> <summary>Commits</summary> <ul> <li><a href="https://github.com/django/django/co...
- review:
- commit: build(deps): Bump django in /testing/plugins_integration Bumps [django](https://github.com/django/django) from 5.1.5 to 5.1.6. - [Commits](https://github.com/django/django/compare/5.1.5...5.1.6) --- updated-dependencies: - dependency-nam...
- related_ref_error: GitHub command failed: gh api repos/pytest-dev/pytest/issues/35612: gh: Not Found (HTTP 404)
- related_ref_error: GitHub command failed: gh api repos/pytest-dev/pytest/issues/36140: gh: Not Found (HTTP 404)

Changed files:
- `testing/plugins_integration/requirements.txt`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14143

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14143
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: build(deps): Bump actions/cache from 5.0.1 to 5.0.2
- state: `MERGED`
- created_at: `2026-01-26T03:04:40Z`
- merged_at: `2026-02-01T16:20:03Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14143
- https://github.com/pytest-dev/pytest/pull/14143#pullrequestreview-3704770611
- https://github.com/pytest-dev/pytest/commit/10ea09ff18a950fcc6d95b134dab5de4f98c5850
- https://github.com/pytest-dev/pytest/pull/1692
- https://github.com/pytest-dev/pytest/pull/1692#issuecomment-229780884
- https://github.com/pytest-dev/pytest/issues/1685
- https://github.com/pytest-dev/pytest/issues/1685#issuecomment-228936602
- https://github.com/pytest-dev/pytest/issues/1685#issuecomment-228944037

Key discussion summary:
- pr: build(deps): Bump actions/cache from 5.0.1 to 5.0.2 Bumps [actions/cache](https://github.com/actions/cache) from 5.0.1 to 5.0.2. <details> <summary>Release notes</summary> <p><em>Sourced from <a href="https://github.com/actions/cache/rel...
- review:
- commit: build(deps): Bump actions/cache from 5.0.1 to 5.0.2 Bumps [actions/cache](https://github.com/actions/cache) from 5.0.1 to 5.0.2. - [Release notes](https://github.com/actions/cache/releases) - [Changelog](https://github.com/actions/cache/...
- related_ref: Add changelog to requirements for pytest-dev plugins (meh, seems like the github web editor (which I like to use for simple things like this) doesn't let me branch in my fork if I have push access...) See #1691.
- related_ref_comment: [![Coverage Status](https://coveralls.io/builds/6824808/badge)](https://coveralls.io/builds/6824808) Coverage remained the same at 92.29% when pulling **e3c43a14626b097fb114659e4720d94728573421 on changelog** into **75ecd942944645c58baa1...

Changed files:
- `.github/workflows/update-plugin-list.yml`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

### hard_candidate:pytest-dev__pytest:pull:14659

- repo: `pytest-dev/pytest`
- PR URL: https://github.com/pytest-dev/pytest/pull/14659
- suspected_status: `stale`
- final action: `needs_more_evidence`
- final evidence_status: `none`
- expected_decision: `none`
- confidence: `0.35`
- title: build(deps): Bump actions/checkout from 6.0.3 to 7.0.0
- state: `MERGED`
- created_at: `2026-06-29T03:03:11Z`
- merged_at: `2026-06-29T03:45:15Z`

Evidence URLs:
- https://github.com/pytest-dev/pytest/pull/14659
- https://github.com/pytest-dev/pytest/pull/14659#pullrequestreview-4588771503
- https://github.com/pytest-dev/pytest/commit/a1b2e9ac591a4c9451e715f2bde737c3643aef55
- https://github.com/pytest-dev/pytest/issues/2467
- https://github.com/pytest-dev/pytest/issues/2464
- https://github.com/pytest-dev/pytest/issues/2464#issuecomment-305800358
- https://github.com/pytest-dev/pytest/issues/2464#issuecomment-305804254
- https://github.com/pytest-dev/pytest/issues/2464#issuecomment-305821922

Key discussion summary:
- pr: build(deps): Bump actions/checkout from 6.0.3 to 7.0.0 Bumps [actions/checkout](https://github.com/actions/checkout) from 6.0.3 to 7.0.0. <details> <summary>Release notes</summary> <p><em>Sourced from <a href="https://github.com/actions/...
- review:
- commit: build(deps): Bump actions/checkout from 6.0.3 to 7.0.0 Bumps [actions/checkout](https://github.com/actions/checkout) from 6.0.3 to 7.0.0. - [Release notes](https://github.com/actions/checkout/releases) - [Changelog](https://github.com/ac...
- related_ref: Error with console output in Python 3.6 on Windows xref: pytest-dev/py#103 Creating a cross-reference here for the CHANGELOG.
- related_ref: Incorrect number of collected items reported when specific class methods are provided - [x] Include a detailed description of the bug or suggestion It seems that the number of collected tests is displayed incorrectly when the "class meth...

Changed files:
- `.github/workflows/deploy.yml`
- `.github/workflows/doc-check-links.yml`
- `.github/workflows/prepare-release-pr.yml`
- `.github/workflows/test.yml`
- `.github/workflows/update-plugin-list.yml`

Why this action: Evidence was not strong enough for a Codex promote recommendation.

Most important human final-check point:
- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.

## Stale Candidate Evidence Check

- `hard_candidate:psf__requests:pull:6265` older/newer/time ordering: `True`; urls: ['https://github.com/psf/requests/pull/6265', 'https://github.com/psf/requests/pull/6265#issuecomment-3950145511']

## Conflicting Candidate Evidence Check

- `hard_candidate:psf__requests:pull:7546` support=https://github.com/psf/requests/pull/7546 concern=https://github.com/psf/requests/issues/4965
- `hard_candidate:psf__requests:pull:7513` support=https://github.com/psf/requests/pull/7513 concern=https://github.com/psf/requests/pull/7513#issuecomment-4715750402
- `hard_candidate:psf__requests:pull:7491` support=https://github.com/psf/requests/pull/7491 concern=https://github.com/psf/requests/commit/0a04af26d265a19d3c64de455b5a5bf64140a390
- `hard_candidate:pytest-dev__pytest:pull:14668` support=https://github.com/pytest-dev/pytest/pull/14668 concern=https://github.com/pytest-dev/pytest/issues/14324
- `hard_candidate:pytest-dev__pytest:pull:14662` support=https://github.com/pytest-dev/pytest/pull/14662 concern=https://github.com/pytest-dev/pytest/pull/14662#issuecomment-4835239496
- `hard_candidate:pytest-dev__pytest:pull:14639` support=https://github.com/pytest-dev/pytest/pull/14639 concern=https://github.com/pytest-dev/pytest/issues/14637

## Unknown Candidate Evidence Check

- `hard_candidate:psf__requests:pull:7424` high_risk_hits=['auth'] missing=[]
- `hard_candidate:psf__requests:pull:7538` high_risk_hits=['auth'] missing=[]
- `hard_candidate:psf__requests:pull:6965` high_risk_hits=['permission'] missing=[]
- `hard_candidate:pytest-dev__pytest:pull:8251` high_risk_hits=['auth', 'config', 'public api'] missing=[]
- `hard_candidate:pytest-dev__pytest:pull:14053` high_risk_hits=['auth', 'compatibility', 'config'] missing=[]
- `hard_candidate:pytest-dev__pytest:pull:11844` high_risk_hits=['auth'] missing=[]

## Safety Statement

- This audit did not modify `datasets/real_min/cases.jsonl`.
- This audit did not run `promote-labels`.
- `datasets/real_min/labels/manual_labels.jsonl` uses `label_source=codex_evidence_audit`, not `manual_verified`.
- Human final review is required before any label can be promoted into scored metrics.
