# Project Overview

TraceGate is an AI-generated Pull Request advisory and EvalOps project focused on historical claim validity and evidence-aware safety.

It is not a Public Relations product, not a general-purpose code review bot, and not a full enterprise governance platform. The current P0 branch builds a small real-data path on top of the existing controlled ClaimBench work.

## Current P0 Shape

- Real-data source: public GitHub REST API Pull Request metadata.
- Normalized schema: claim, evidence items, evidence status, expected decision, provenance, and real/demo flags.
- Advisor: deterministic rule baseline.
- Guardrails: strict scan/audit for fallback/mock/synthetic leakage.
- Reports: `runs/latest/report.md` and `runs/latest/report.json`.
- GitHub Action: warning-only advisory skeleton.

## Differentiation

TraceGate focuses on:

- Whether a historical claim still appears valid.
- Which evidence supports, contradicts, or fails to resolve that claim.
- Whether stale or conflicting context pollutes a change rationale.
- Whether a PR should preserve, optimize, verify first, detect conflict, or request manual review.

## Current Boundary

The real-data smoke benchmark is small and heuristic-labeled. It is useful for validating the pipeline and guardrails, not for model leaderboard claims.
