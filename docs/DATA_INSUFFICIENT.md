# Data Insufficient: hard real-data mini benchmark

Generated on: 2026-07-02T08:34:33.441341+00:00

The current committed scored dataset remains the active-only real-data smoke dataset. Automatically mined hard candidates were not promoted into scored metrics because they require manual review.

## Current Scored Dataset

- active: `12`
- stale: `0`
- unknown: `0`
- conflicting: `0`

## Manual Review Queue

- queue_path: `datasets/real_min/labels/manual_review_queue.jsonl`
- stale candidates: `13`
- unknown candidates: `11`
- conflicting candidates: `16`

## Why hard_benchmark_ready is false

- Minimum scored distribution is `active>=8`, `unknown>=3`, `conflicting>=2`, `stale>=1`, `scored_cases>=14`.
- Hard candidates need manual adjudication before promotion.
- TraceGate does not fill missing hard cases with synthetic, mock, or fallback data.

## Next Fix

Review `datasets/real_min/labels/manual_review_queue.jsonl`, write confirmed labels to `datasets/real_min/labels/manual_labels.jsonl`, then run `python -m tracegate data promote-labels`.
