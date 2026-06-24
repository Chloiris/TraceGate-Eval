from __future__ import annotations

from typing import Any, Callable

from tracegate.config import CLAIM_CONTEXT_GROUPS
from tracegate.context.token_estimator import estimate_tokens
from tracegate.contexts.claim_with_evidence_builder import build_claim_with_evidence
from tracegate.contexts.full_unfiltered_builder import build_full_unfiltered_claims
from tracegate.contexts.misleading_context_builder import build_misleading_same_scope
from tracegate.contexts.plain_claim_builder import build_plain_claim
from tracegate.contexts.result_history_builder import build_result_history
from tracegate.contexts.tracegate_routed_builder import build_tracegate_routed
from tracegate.contexts.tracegate_verify_first_builder import build_tracegate_verify_first


Builder = Callable[[dict[str, Any], list[dict[str, Any]]], tuple[str, list[str]]]


BUILDERS: dict[str, Builder] = {
    "result_history": build_result_history,
    "plain_claim": build_plain_claim,
    "claim_with_evidence": build_claim_with_evidence,
    "tracegate_routed": build_tracegate_routed,
    "tracegate_verify_first": build_tracegate_verify_first,
    "misleading_same_scope": build_misleading_same_scope,
    "full_unfiltered_claims": build_full_unfiltered_claims,
}


def build_claim_context(
    task: dict[str, Any],
    context_group: str,
    contexts: list[dict[str, Any]],
) -> tuple[str, list[str], int]:
    if context_group not in CLAIM_CONTEXT_GROUPS:
        raise ValueError(f"Unsupported ClaimBench context group: {context_group}")
    if context_group == "no_context":
        text = "No historical claim context is supplied for this run."
        return text, [], estimate_tokens(text)
    text, selected_ids = BUILDERS[context_group](task, contexts)
    return text, selected_ids, estimate_tokens(text)
