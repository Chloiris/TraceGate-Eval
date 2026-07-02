# Evidence Pack Round 1

AI-assisted draft suggestions for the manual review queue. These are not human-verified labels and are excluded from scored metrics.

## Summary

- generated_at: `2026-07-02T11:10:26.356251+00:00`
- evidence_packs: `10`
- promote_suggestions: `3`
- reject_suggestions: `0`
- needs_more_evidence_suggestions: `7`
- suggested_label_distribution: `{'none': 7, 'stale': 2, 'unknown': 1}`
- label_source: `ai_suggested` only
- modifies_manual_labels_jsonl: `false`
- modifies_cases_jsonl: `false`
- used_mock_model: `false`
- used_synthetic_data: `false`
- used_fallback_data: `false`

## 1. hard_candidate:psf__requests:pull:7555

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7555
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- state: `CLOSED`
- created_at: `2026-07-01T21:58:05Z`
- merged_at: `None`
- labels: `[]`

### PR Summary

- title: HTTPDigestAuth: use urlsplit for the digest URI
- body: The Effective Request URI in the Digest Authorization header is computed from `urlparse(url).path`. `urlparse()` treats `;` as a path-parameter separator and strips everything from the first `;` in the path, so a request to a URL like `https://api.example.org/ws/2/collection/abc/releases/p1;p2?fmt=json` ends up with a truncated `/ws/2/collection/abc/releases/p1` path in the Authorization header. The server then computes a different digest and rejects the request, even though the path is legitimate per RFC 3986 (the `;` character is a sub-delim that is allowed unencoded in path segments). Switch the HTTPDigestAuth init from `urlparse` to `urlsplit`. `urlsplit()` does not split on `;` inside the path, so the p...

### Changed Files

- `src/requests/auth.py`
- `src/requests/structures.py`
- `tests/test_lowlevel.py`
- `tests/test_structures.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7555: HTTPDigestAuth: use urlsplit for the digest URI The Effective Request URI in the Digest Authorization header is computed from `urlparse(url).path`. `urlparse()` treats `;` as a path-parameter separator and strips everything from the first `;` in the path, so a request to a URL...
- `commit` https://github.com/psf/requests/commit/717e54e78a70afb8ce70133742cad63034a236c3: CaseInsensitiveDict: reject non-string keys with TypeError instead of… … leaking AttributeError
- `commit` https://github.com/psf/requests/commit/5bce0b088393108e3a0c54a844446f91fbc54869: HTTPDigestAuth: use urlsplit for the digest URI so semicolons in the … …path are preserved The Effective Request URI in the Digest Authorization header is computed from urlparse(url).path, but urlparse() strips path parameters at the first ';' in the path component, so a reque...

### Linked Refs

- No closingIssuesReferences or linked refs returned by GitHub.

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 2. hard_candidate:psf__requests:pull:7549

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7549
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- state: `CLOSED`
- created_at: `2026-06-29T13:45:57Z`
- merged_at: `None`
- labels: `[]`

### PR Summary

- title: Remove method cookies set to None
- body: Summary - Treat method-level cookie mappings with value None as removals after session cookies are merged. - Leave the session cookie jar unchanged while omitting those cookies from the prepared request. - Add regression coverage for the malformed Cookie header reported in #2716. Closes #2716 Tests - `.venv\Scripts\python.exe -m pytest tests/test_requests.py -q -k request_cookie_none_removes_session_cookie` - `.venv\Scripts\python.exe -m pytest tests/test_requests.py -q -k cookie` - `.venv\Scripts\python.exe -m ruff check src/requests/sessions.py tests/test_requests.py` - `git diff --check` I also ran `.venv\Scripts\python.exe -m pytest tests/test_requests.py -q`; it reached 337 passed, 1 skipped, and 1 xpas...

### Changed Files

- `src/requests/sessions.py`
- `tests/test_requests.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7549: Remove method cookies set to None Summary - Treat method-level cookie mappings with value None as removals after session cookies are merged. - Leave the session cookie jar unchanged while omitting those cookies from the prepared request. - Add regression coverage for the malfo...
- `commit` https://github.com/psf/requests/commit/1e884f825cf895889ba1199d750b41bf480da0ed: Remove method cookies set to None
- `linked_ref` https://github.com/psf/requests/issues/2716: (empty)

### Linked Refs

- https://github.com/psf/requests/issues/2716

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 3. hard_candidate:psf__requests:pull:7546

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7546
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: regression
- state: `CLOSED`
- created_at: `2026-06-27T05:55:06Z`
- merged_at: `None`
- labels: `['spam', 'mass-automation-pr']`

### PR Summary

- title: [Fix] response.content losing read errors on second access (#4965)
- body: ## Problem Accessing `response.content` twice after a stream read error returns empty bytes on the second access instead of re-raising the error. **Reproduction:** ```python response = requests.post("http://connreset.biz/get/incomplete/chunked", stream=True) try: response.content # raises ChunkedEncodingError except Exception: pass content = response.content # BUG: returns b"" instead of re-raising ``` **Root cause:** In the `content` property, when `b"".join(self.iter_content(...))` raises mid-stream, both `_content` stays `False` and `_content_consumed` stays `False` (the generator's `_content_consumed = True` line at the end of `generate()` is never reached because the generator dies mid-iteration). On se...

### Changed Files

- `src/requests/models.py`
- `tests/test_lowlevel.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7546: [Fix] response.content losing read errors on second access (#4965) ## Problem Accessing `response.content` twice after a stream read error returns empty bytes on the second access instead of re-raising the error. **Reproduction:** ```python response = requests.post("http://con...
- `commit` https://github.com/psf/requests/commit/a8e6a7cec6215eca83586a70180474a0c96a4efe: Fix response.content caching read errors (#4965) When response.content raises during stream consumption, the error was lost on subsequent accesses — returning empty bytes instead of re-raising. This happened because _content stayed False and _content_consumed stayed False afte...
- `linked_ref` https://github.com/psf/requests/issues/4965: (empty)

### Linked Refs

- https://github.com/psf/requests/issues/4965

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 4. hard_candidate:psf__requests:pull:7424

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7424
- suspected_status: `unknown`
- why_suspected: High-risk topic keywords found in PR title/body: auth
- state: `CLOSED`
- created_at: `2026-05-11T14:14:21Z`
- merged_at: `None`
- labels: `[]`

### PR Summary

- title: Fix HTTPDigestAuth failing on non-ASCII credentials
- body: ## Summary When `HTTPDigestAuth` credentials contain non-ASCII characters (e.g. Czech username `Ondřej`), authentication fails because the digest header encodes the bytes representation rather than the decoded string. ## Root Cause In `build_digest_header()`, the A1 string was constructed using an f-string directly with `self.username` and `self.password`: ```python A1 = f"{self.username}:{realm}:{self.password}" ``` When these are `bytes` objects (e.g. `'Ondřej'.encode('utf-8')`), Python's f-string formatting embeds the `repr()` of bytes, producing: ``` Digest username="b'Ond\xc5\x99ej'" ``` instead of the correct: ``` Digest username="Ondřej" ``` This causes the server to reject the credentials as the user...

### Changed Files

- `src/requests/auth.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7424: Fix HTTPDigestAuth failing on non-ASCII credentials ## Summary When `HTTPDigestAuth` credentials contain non-ASCII characters (e.g. Czech username `Ondřej`), authentication fails because the digest header encodes the bytes representation rather than the decoded string. ## Root...
- `comment` https://github.com/psf/requests/pull/7424#issuecomment-4423494561: Hi @CatfishGG, I think this unfortunately does not address #6102. This breaks the default case for latin-1. There's already other PRs open with alternative approaches so we'll close this as a duplicate.
- `commit` https://github.com/psf/requests/commit/653ceef90382258ae2ae64c4e944509e8fd5a4db: Fix HTTPDigestAuth failing on non-ASCII credentials When username/password are passed as bytes (e.g. 'Ondřej'.encode('utf-8')), the digest header was correctly including the bytes repr as a string literal (e.g. username="b'Ond\xc5\x99ej'"), causing auth to fail. The fix wraps...
- `linked_ref` https://github.com/psf/requests/issues/6102: (empty)

### Linked Refs

- https://github.com/psf/requests/issues/6102

### Draft Suggestion

- recommended_action: `promote`
- recommended_label: `unknown`
- recommended_expected_decision: `verify_first`
- confidence: `0.72`
- rationale: AI draft found evidence consistent with `unknown`; human confirmation is still required.

### Missing Evidence

- No sufficient PR body/comment/review evidence was found for the high-risk area.

### Human Confirmation Questions

- Is there enough evidence to preserve or optimize safely?
- Which current test, owner note, or doc confirms the behavior?
- Should this be scored as verify_first after review?

## 5. hard_candidate:psf__requests:pull:7355

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7355
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated, no longer
- state: `CLOSED`
- created_at: `2026-04-11T20:17:27Z`
- merged_at: `None`
- labels: `['mass-automation-pr']`

### PR Summary

- title: Add missing stacklevel to all warnings.warn() calls
- body: ## Summary All 9 `warnings.warn()` calls in the codebase are missing `stacklevel`, causing warning messages to point to internal lines inside Requests rather than the caller's code. ### Example Before (without stacklevel): ``` .../site-packages/requests/auth.py:36: DeprecationWarning: Non-string usernames will no longer be supported... ``` After (with stacklevel=2): ``` my_app.py:15: DeprecationWarning: Non-string usernames will no longer be supported... ``` ## Changes | File | Calls Fixed | Warning Types | |------|-----------|---------------| | `auth.py` | 2 | `DeprecationWarning` for non-string username/password | | `__init__.py` | 3 | `RequestsDependencyWarning` for missing/old dependencies | | `utils.py`...

### Changed Files

- `src/requests/__init__.py`
- `src/requests/adapters.py`
- `src/requests/auth.py`
- `src/requests/utils.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7355: Add missing stacklevel to all warnings.warn() calls ## Summary All 9 `warnings.warn()` calls in the codebase are missing `stacklevel`, causing warning messages to point to internal lines inside Requests rather than the caller's code. ### Example Before (without stacklevel): ``...
- `comment` https://github.com/psf/requests/pull/7355#issuecomment-4230257215: Nice cleanup — fixing `stacklevel` on all `warnings.warn()` calls is a real QoL improvement for library users debugging their own code. One thing to double-check: if there are existing tests that assert on warning output (file paths or line numbers), they may need updating sin...
- `comment` https://github.com/psf/requests/pull/7355#issuecomment-4233514897: Thanks for the review @afurm! > Have you run the test suite to confirm nothing breaks? Yes — the existing warning tests only assert on warning **count** and **category** (e.g. `test_file` in `test_utils.py` checks `len(recwarn)`, and `test_https_warnings` checks `category.__na...
- `commit` https://github.com/psf/requests/commit/7e9316a147f87915a678e964ea8b8ba331f36156: Add missing stacklevel to all warnings.warn() calls All 9 warnings.warn() calls across the codebase were missing stacklevel, causing warning messages to point to internal lines inside Requests rather than the caller's code. Files fixed: - auth.py: 2 calls (DeprecationWarning f...

### Linked Refs

- No closingIssuesReferences or linked refs returned by GitHub.

### Draft Suggestion

- recommended_action: `promote`
- recommended_label: `stale`
- recommended_expected_decision: `verify_first`
- confidence: `0.74`
- rationale: AI draft found evidence consistent with `stale`; human confirmation is still required.

### Missing Evidence

- None identified by the AI draft.

### Human Confirmation Questions

- Find the older claim URL and the newer superseding evidence URL.
- Are the timestamps clearly ordered?
- Should this remain excluded until both evidence URLs are present?

## 6. hard_candidate:psf__requests:pull:7466

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7466
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: incompatible
- state: `CLOSED`
- created_at: `2026-05-21T07:53:54Z`
- merged_at: `None`
- labels: `[]`

### PR Summary

- title: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any]
- body: ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Mapping[str, "JsonType"] ) ``` This causes mypy to reject valid JSON arguments. For example: ```python def fn(d: dict[str, str]) -> None: j = {"foo": d, "bar": "hi"} requests.post("https://example.com", json=j) # error ``` mypy reports: ``` Argument "json" to "post" has incompatible type "dict[str, Collection[str]]"; expected "JsonType" Argument "json" to "post" has incompatible type "dict[str, object]"; expected "JsonType" ``` The root cause is that mypy cannot resolve the recursive constraint — `Collection[str]` is not `Sequence[JsonType]` (w...

### Changed Files

- `src/requests/_types.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7466: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Mapping[str, "JsonType"] ) ``` This causes...
- `commit` https://github.com/psf/requests/commit/1986df35f43327dd26c7bea9b92e3a85f7a4748d: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] The previous recursive JsonType definition used Sequence["JsonType"] and Mapping[str, "JsonType"], which caused mypy to reject valid JSON arguments like dict[str, Collection[str]] or dict[str, object] because...
- `linked_ref` https://github.com/psf/requests/issues/7443: (empty)

### Linked Refs

- https://github.com/psf/requests/issues/7443

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 7. hard_candidate:psf__requests:pull:7467

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7467
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: incompatible
- state: `CLOSED`
- created_at: `2026-05-21T07:56:01Z`
- merged_at: `None`
- labels: `[]`

### PR Summary

- title: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any]
- body: ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Mapping[str, "JsonType"] ) ``` This causes mypy to reject valid JSON arguments. For example: ```python def fn(d: dict[str, str]) -> None: j = {"foo": d, "bar": "hi"} requests.post("https://example.com", json=j) # error ``` mypy reports: ``` Argument "json" to "post" has incompatible type "dict[str, Collection[str]]"; expected "JsonType" Argument "json" to "post" has incompatible type "dict[str, object]"; expected "JsonType" ``` The root cause is that mypy cannot resolve the recursive constraint — `Collection[str]` is not `Sequence[JsonType]` (w...

### Changed Files

- `src/requests/_types.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7467: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] ## Problem The `JsonType` alias in `_types.py` uses a recursive definition: ```python JsonType: TypeAlias = ( None | bool | int | float | str | Sequence["JsonType"] | Mapping[str, "JsonType"] ) ``` This causes...
- `commit` https://github.com/psf/requests/commit/1986df35f43327dd26c7bea9b92e3a85f7a4748d: fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any] The previous recursive JsonType definition used Sequence["JsonType"] and Mapping[str, "JsonType"], which caused mypy to reject valid JSON arguments like dict[str, Collection[str]] or dict[str, object] because...
- `linked_ref` https://github.com/psf/requests/issues/7443: (empty)

### Linked Refs

- https://github.com/psf/requests/issues/7443

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 8. hard_candidate:psf__requests:pull:7441

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7441
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: incompatible, revert
- state: `MERGED`
- created_at: `2026-05-13T21:23:44Z`
- merged_at: `2026-05-14T16:16:26Z`
- labels: `[]`

### PR Summary

- title: Move Request.headers back to Mapping
- body: This PR partially reverts #7431, moving it back to `Mapping` instead of `MutableMapping`. While we typically expect the input to be mutable, dicts inferred to be `dict[str, str]` at creation are incompatible with `MutableMapping[str, str | bytes]` even though they may later have a `bytes` value added. This typing decision is a tradeoff of supporting `update()` calls on `Request.headers` and requiring all users to type their input as `dict[str, str | bytes]`. The latter is significantly more invasive and common for current codebases.

### Changed Files

- `src/requests/_types.py`
- `src/requests/models.py`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7441: Move Request.headers back to Mapping This PR partially reverts #7431, moving it back to `Mapping` instead of `MutableMapping`. While we typically expect the input to be mutable, dicts inferred to be `dict[str, str]` at creation are incompatible with `MutableMapping[str, str |...
- `review` https://github.com/psf/requests/pull/7441#pullrequestreview-4289038802: (empty)
- `commit` https://github.com/psf/requests/commit/412f581d7e7c27bfee4f042fcac89bae9a804afe: Move Request.headers back to Mapping
- `linked_ref` https://github.com/psf/requests/issues/7442: (empty)

### Linked Refs

- https://github.com/psf/requests/issues/7442

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 9. hard_candidate:psf__requests:pull:7492

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7492
- suspected_status: `conflicting`
- why_suspected: Conflict keywords found in PR title/body: revert
- state: `MERGED`
- created_at: `2026-06-03T00:27:12Z`
- merged_at: `2026-06-03T00:44:54Z`
- labels: `['dependencies', 'github_actions']`

### PR Summary

- title: Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group
- body: Bumps the actions group with 1 update: [github/codeql-action](https://github.com/github/codeql-action). Updates `github/codeql-action` from 4.35.1 to 4.36.0 <details> <summary>Release notes</summary> <p><em>Sourced from <a href="https://github.com/github/codeql-action/releases">github/codeql-action's releases</a>.</em></p> <blockquote> <h2>v4.36.0</h2> <ul> <li><em>Breaking change</em>: Bump the minimum required CodeQL bundle version to 2.19.4. <a href="https://redirect.github.com/github/codeql-action/pull/3894">#3894</a></li> <li>Add support for SHA-256 Git object IDs. <a href="https://redirect.github.com/github/codeql-action/pull/3893">#3893</a></li> <li>Update default CodeQL bundle version to <a href="htt...

### Changed Files

- `.github/workflows/codeql-analysis.yml`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/7492: Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group Bumps the actions group with 1 update: [github/codeql-action](https://github.com/github/codeql-action). Updates `github/codeql-action` from 4.35.1 to 4.36.0 <details> <summary>Release notes</summary> <p><em>S...
- `review` https://github.com/psf/requests/pull/7492#pullrequestreview-4414649181: (empty)
- `commit` https://github.com/psf/requests/commit/2a480a1f56b6e32fd2ef0bcd6048ff468e2768ee: Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group Bumps the actions group with 1 update: [github/codeql-action](https://github.com/github/codeql-action). Updates `github/codeql-action` from 4.35.1 to 4.36.0 - [Release notes](https://github.com/github/codeql-...

### Linked Refs

- No closingIssuesReferences or linked refs returned by GitHub.

### Draft Suggestion

- recommended_action: `needs_more_evidence`
- recommended_label: `none`
- recommended_expected_decision: `none`
- confidence: `0.5`
- rationale: AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.

### Missing Evidence

- Need at least one supporting evidence URL and one contradicting evidence URL.

### Human Confirmation Questions

- Find the supporting evidence URL and the contradicting evidence URL.
- Does the conflict affect current behavior or only historical discussion?
- Should this be detect_conflict or needs_manual_review?

## 10. hard_candidate:psf__requests:pull:6265

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/6265
- suspected_status: `stale`
- why_suspected: Stale/deprecation keywords found in PR title/body: deprecated
- state: `CLOSED`
- created_at: `2022-10-23T05:24:51Z`
- merged_at: `None`
- labels: `[]`

### PR Summary

- title: Fix setuptools deprecation warnings
- body: Update keys used in `setup.cfg` in order to fix the following setuptools deprecation warnings: > The license_file parameter is deprecated, use license_files instead. > Usage of dash-separated 'provides-extra' will not be supported > in future versions. Please use the underscore name 'provides_extra' > instead > Usage of dash-separated 'requires-dist' will not be supported > in future versions. Please use the underscore name 'requires_dist' > instead

### Changed Files

- `setup.cfg`

### Possible Evidence Items / Comments / Reviews / Commits

- `pr` https://github.com/psf/requests/pull/6265: Fix setuptools deprecation warnings Update keys used in `setup.cfg` in order to fix the following setuptools deprecation warnings: > The license_file parameter is deprecated, use license_files instead. > Usage of dash-separated 'provides-extra' will not be supported > in futur...
- `comment` https://github.com/psf/requests/pull/6265#issuecomment-1396967411: Thanks for the efforts, but I have updated as you instructed but still getting this error: C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.10_3.10.2544.0_x64__qbz5n2kfra8p0\lib\site-packages\setuptools\dist.py:771: UserWarning: Usage of dash-separated 'provides-...
- `comment` https://github.com/psf/requests/pull/6265#issuecomment-3950145511: Looks like this has been obsoleted by #7012.
- `comment` https://github.com/psf/requests/pull/6265#issuecomment-4122466701: Resolving since the setup.cfg is no longer relevant.
- `commit` https://github.com/psf/requests/commit/e321c73f73d74c240b50108b93ee8b366245c8f3: Fix setuptools deprecation warnings Update keys used in `setup.cfg` in order to fix the following setuptools deprecation warnings: > The license_file parameter is deprecated, use license_files instead. > Usage of dash-separated 'provides-extra' will not be supported > in futur...

### Linked Refs

- No closingIssuesReferences or linked refs returned by GitHub.

### Draft Suggestion

- recommended_action: `promote`
- recommended_label: `stale`
- recommended_expected_decision: `verify_first`
- confidence: `0.74`
- rationale: AI draft found evidence consistent with `stale`; human confirmation is still required.

### Missing Evidence

- None identified by the AI draft.

### Human Confirmation Questions

- Find the older claim URL and the newer superseding evidence URL.
- Are the timestamps clearly ordered?
- Should this remain excluded until both evidence URLs are present?
