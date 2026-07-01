# Limitations

- The real dataset is small: 12 normalized cases and 12 scored cases in the current run.
- Current evidence labels are heuristic, not manually adjudicated ground truth.
- Current data covers `active` evidence only; stale, unknown, and conflicting real cases still need curated sources.
- GitHub API fields may be incomplete for some repositories or PRs.
- The advisor is deterministic baseline logic, not a final LLM agent.
- The benchmark is a smoke benchmark, not statistically significant.
- TraceGate does not guarantee discovery of all high-risk changes.
- The GitHub Action is warning-only and does not block merges by default.
- Claim extraction is not fully automated.
- This branch is not an enterprise governance platform.
