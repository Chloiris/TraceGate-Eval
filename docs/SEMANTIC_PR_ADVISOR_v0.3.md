# TraceGate v0.3 Semantic PR Advisor

TraceGate v0.3 adds a semantic Pull Request advisory path for real GitHub PRs.
It upgrades the v0.2 warning-only rule skeleton with evidence retrieval,
EvidencePacket construction, DeepSeek JSON judging, and verifier guardrails.

The advisor remains warning-only. It is designed to surface evidence-aware
review guidance, not to replace human review or block merges by default.

## v0.2 Rule Skeleton vs v0.3 Semantic Advisor

| Area | v0.2 rule advisory | v0.3 semantic advisory |
| --- | --- | --- |
| Input | Changed-file list and repo-local claim config | Real PR metadata, comments, reviews, files, commits,<br>linked issues, history, docs, tests |
| Model call | None | Real DeepSeek API call in semantic mode |
| Output | Job summary with matched configured claims | Markdown and JSON advisory with evidence status,<br>decision, evidence used, verifier notes |
| Safety | Warning-only | Warning-only plus no mock, no fallback, fork-secret boundary, verifier downgrades |

## DeepSeek Configuration

Semantic mode reads a DeepSeek-compatible API credential from the environment in
this order:

1. `DEEPSEEK_API_KEY`
2. `TRACEGATE_LLM_API_KEY`

Optional settings:

- `DEEPSEEK_BASE_URL`, default `https://api.deepseek.com`
- `DEEPSEEK_MODEL`, default `deepseek-v4-flash`

The client uses OpenAI-compatible chat completions at `/chat/completions`.
If no credential is available, semantic mode fails fast and does not produce a
synthetic result.

## GitHub Secret Setup

For GitHub Actions semantic mode, configure the repository secret:

```bash
gh secret set DEEPSEEK_API_KEY --body "$DEEPSEEK_API_KEY"
```

Do not echo or log the credential value. The workflow passes it only through the
Actions secret context.

## Fork Pull Request Boundary

Fork PRs do not receive LLM secrets. The semantic workflow writes an explicit
skip message:

```text
semantic advisor skipped for fork PR because secrets are unavailable
```

The workflow uses the `pull_request` event, not `pull_request_target`, and
checks out trusted base code. It does not execute untrusted PR code.

For the bootstrap PR that introduces v0.3, the trusted base branch may not yet
contain `tracegate pr analyze`. In that case the workflow emits an explicit
warning-only skip and relies on local real DeepSeek live smoke. After v0.3 is
merged, the same workflow runs semantic mode from trusted base code.

## Evidence Retrieval Scope

For a real PR, the advisor collects:

- PR title, body, URL, state, timestamps, labels
- PR comments
- PR reviews
- PR review line comments
- commits
- changed files
- bounded diff hunk summaries
- linked issues and body/comment `#number` references, up to 5
- touched path and probable symbol hints
- touched-file GitHub commit history, up to 20 items
- related docs, changelog, release-note, and test snippets

Every semantic judgment is required to cite EvidencePacket `evidence_id` values.
Evidence items include concrete URLs, file paths, commit SHAs, timestamps, and
sanitized snippets where available.

## DeepSeek JSON Schema

DeepSeek must return strict JSON:

```json
{
  "evidence_status": "active | stale | unknown | conflicting | no_relevant_claim | needs_more_evidence",
  "expected_decision": "preserve | optimize | verify_first | detect_conflict | none",
  "confidence": 0.0,
  "claim_under_review": "...",
  "rationale": "...",
  "evidence_used": ["evidence_id"],
  "missing_evidence": [],
  "risk_level": "low | medium | high | critical",
  "verification_plan": [],
  "should_block": false
}
```

Invalid JSON is retried once. A second invalid response fails the run.

## Verifier Rules

The verifier runs after DeepSeek and can only use existing EvidencePacket data.
It writes all downgrades or corrections into `verifier_notes`.

- `conflicting` requires at least two cited evidence items.
- `conflicting` requires two distinct concrete URLs, comments, issues, commits,
  or equivalent sources.
- `conflicting` cannot be based only on PR body text.
- Resolved concerns and no-regression test evidence are mitigation, not
  conflict.
- `stale` requires older and newer evidence with timestamp ordering.
- `unknown` requires a detected risk area and missing-evidence rationale.
- Same-PR URL duplication cannot satisfy the conflict evidence count.

## Live Smoke Cases

The required live smoke command is:

```bash
python -m tracegate pr live-smoke \
  --provider deepseek \
  --real-only \
  --no-mock \
  --no-fallback \
  --cases pytest-dev/pytest#14662,psf/requests#7545,psf/requests#7555 \
  --output runs/pr_advisory/live_smoke/report.md \
  --json-output runs/pr_advisory/live_smoke/report.json
```

The report records:

- evidence packet size
- DeepSeek model
- DeepSeek raw JSON response, with no credential value
- verifier result
- final evidence status and expected decision
- evidence URLs
- whether the semantic API was actually called
- `used_real_pr=true`
- `used_real_llm=true`
- `used_mock=false`
- `used_fallback=false`

If DeepSeek is not called, or if any mock or fallback result is used, live smoke
fails.

## Why Warning-Only

Semantic PR review can be helpful but still depends on bounded retrieval,
public evidence availability, and model judgment. TraceGate therefore reports
evidence-aware advisory output without blocking merges by default.

## Limitations

- The advisor does not execute PR code.
- Retrieval is bounded by GitHub API availability and configured limits.
- Public evidence may be incomplete.
- The verifier prevents known unsafe overclaims but cannot create missing
  evidence.
- Human review remains required for high-risk changes.
