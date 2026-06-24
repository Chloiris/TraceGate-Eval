# TraceGate Eval Project Introduction

TraceGate Eval is an evaluation framework for AI coding agents that work on legacy code with historical engineering context. It focuses on whether an agent can judge the current validity of historical experience and make a safe maintenance decision.

The project is intentionally framed around context safety rather than raw patch generation. A patch can compile and pass tests while still deleting a compatibility path that production clients need, over-preserving stale code, or following misleading context into unrelated edits.

## Core Idea

Historical engineering experience often appears as incident reports, old rollback notes, compatibility warnings, chat summaries, failed patches, and comments. These artifacts are not equally trustworthy:

- Some claims are still active and should be preserved.
- Some claims are stale and should no longer block cleanup.
- Some claims are unknown because current evidence is missing.
- Some claims are conflicting because signals disagree.

TraceGate Eval turns this into a controlled benchmark where the model must decide whether to preserve, optimize, verify first, or escalate a conflict.

## Current Version

v0.1 is a controlled benchmark release, not a production data platform. The main experiment is Stage3 Controlled Claim Benchmark:

- 5 modules: Auth, Order, User, Payment, Job
- 4 evidence statuses: active, stale, unknown, conflicting
- 8 context groups
- 20 tasks x 8 context groups = 160 runs
- Complete `deepseek-v4-pro` result summary available under `reports_claim/` and `results/`

## Why It Matters

For AI coding agents, more context is not automatically better. TraceGate Eval measures whether context is:

- relevant to the current task,
- supported by current evidence,
- routed into a safe decision,
- free from pollution,
- paired with an adequate verification plan when certainty is low.

That makes the project useful as a software-engineering experiment around AI coding-agent safety, context routing, and benchmark design.

## Current Result Snapshot

The current `deepseek-v4-pro` Stage3 run contains 160 records. The model produced a decision for every run and passed tests in 152/160 runs, but only reached 68/160 `safe_success`. This gap is the main point of the benchmark: test success and context safety are different outcomes.

`tracegate_routed` had the strongest context-group safe success at 14/20. `misleading_same_scope` triggered 15/20 pollution cases. `conflicting` evidence was the hardest status, with only 4/40 correct evidence-aware decisions.
