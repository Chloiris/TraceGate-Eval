from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
SAMPLE_REPOS_DIR = PROJECT_ROOT / "sample_repos"
SAMPLE_REPO_DIR = SAMPLE_REPOS_DIR / "legacy-shop-spring"
RUNS_DIR = PROJECT_ROOT / "runs"
REPORTS_DIR = PROJECT_ROOT / "reports"
MAVEN_REPO_DIR = PROJECT_ROOT / ".m2" / "repository"
SAMPLE_REPO_V2_DIR = SAMPLE_REPOS_DIR / "legacy-shop-spring-v2"
RUNS_STAGE2_DIR = PROJECT_ROOT / "runs_stage2"
REPORTS_STAGE2_DIR = PROJECT_ROOT / "reports_stage2"
SAMPLE_REPO_CLAIM_DIR = SAMPLE_REPOS_DIR / "legacy-shop-spring-claim"
RUNS_CLAIM_DIR = PROJECT_ROOT / "runs_claim"
REPORTS_CLAIM_DIR = PROJECT_ROOT / "reports_claim"

STAGE2_TASKS_FILE = EXPERIMENTS_DIR / "stage2_tasks.yaml"
STAGE2_CONTEXTS_FILE = EXPERIMENTS_DIR / "stage2_contexts.yaml"
STAGE2_ORACLES_FILE = EXPERIMENTS_DIR / "stage2_oracles.yaml"
STAGE2_MODELS_FILE = EXPERIMENTS_DIR / "stage2_models.yaml"
CLAIM_TASKS_FILE = EXPERIMENTS_DIR / "claim_tasks.yaml"
CLAIM_CONTEXTS_FILE = EXPERIMENTS_DIR / "claim_contexts.yaml"
CLAIMS_FILE = EXPERIMENTS_DIR / "claims.yaml"
CLAIM_MODELS_FILE = EXPERIMENTS_DIR / "claim_models.yaml"

TASKS_FILE = EXPERIMENTS_DIR / "tasks.yaml"
CONTEXT_ITEMS_FILE = EXPERIMENTS_DIR / "context_items.yaml"
HISTORICAL_FAILURES_FILE = EXPERIMENTS_DIR / "historical_failures.yaml"

CONTEXT_GROUPS = [
    "no_context",
    "result_history",
    "full_process",
    "routed_process",
    "irrelevant_context",
]

CONTEXT_LABELS = {
    "no_context": "No Context",
    "result_history": "Result-History Context",
    "full_process": "Full Process Context",
    "routed_process": "Routed Process Context",
    "irrelevant_context": "Irrelevant / Stale Context",
}

STAGE2_CONTEXT_GROUPS = [
    "no_context",
    "result_history",
    "full_process",
    "routed_process",
    "stale_unfiltered",
    "irrelevant_context",
]

CLAIM_CONTEXT_GROUPS = [
    "no_context",
    "result_history",
    "plain_claim",
    "claim_with_evidence",
    "tracegate_routed",
    "tracegate_verify_first",
    "misleading_same_scope",
    "full_unfiltered_claims",
]

CLAIM_EVIDENCE_STATUSES = [
    "active",
    "stale",
    "unknown",
    "conflicting",
]

RUN_REPO_DIRNAME = "repo"
BASELINE_DIRNAME = "baseline"
