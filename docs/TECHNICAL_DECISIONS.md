# Technical Decisions

## Use GitHub REST API For P0

Chosen because it is public, stable, provenance-rich, and accessible with Python standard-library HTTP tooling. This avoids large downloads and new heavy dependencies.

## Keep `python -m tracegate`

The existing project already supports `python -m tracegate`. This branch extends the existing CLI instead of introducing a new module entrypoint.

## Deterministic Advisor First

P0 uses rules so the pipeline can prove data provenance, guardrails, and reproducibility before adding an LLM provider. No mock LLM is available in real-only mode.

## Commit Normalized Data, Ignore Raw Cache

Small normalized public cases and manifest are committed for reproducibility. Raw GitHub API cache stays ignored.

## Warning-Only GitHub Action

The action surfaces evidence-aware warnings but does not block merges by default. Blocking policy needs more real cases and human calibration.
