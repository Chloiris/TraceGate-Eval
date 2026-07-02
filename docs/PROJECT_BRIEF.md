# Project Brief

TraceGate can be explained as a focused EvalOps/advisory layer for AI-generated Pull Requests.

The core idea: a coding agent may see old incident notes, compatibility warnings, prior PR summaries, or historical fixes. That context can help, but it can also be stale or conflicting. TraceGate measures whether the agent preserves active constraints, verifies uncertain ones, and avoids letting bad context pollute a patch.

Current proof point:

- Real public GitHub PR data is fetched and normalized.
- A deterministic baseline produces advisory decisions.
- Guardrails prove the run did not use mock, synthetic, or fallback data.
- The result is intentionally small and honest about limitations.
