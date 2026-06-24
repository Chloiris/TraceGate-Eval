from __future__ import annotations

from typing import Any


EXPECTED_DECISIONS = {
    "active": "preserve",
    "stale": "optimize",
    "unknown": "verify_first",
    "conflicting": "conflict_detected",
}


MODULE_CLAIMS: dict[str, dict[str, Any]] = {
    "auth": {
        "pitfall": "legacyToken",
        "claim_text": "The login response legacyToken compatibility path must not be deleted.",
        "validity_condition": "The claim is valid only while old mobile clients still read the legacyToken response field.",
        "instruction": (
            "Evaluate and optimize AuthService token generation to reduce redundant compatibility branches "
            "while avoiding breakage for compatibility paths that may still be used."
        ),
        "target_files": [
            "src/main/java/com/example/legacyshop/auth/AuthService.java",
            "src/main/java/com/example/legacyshop/auth/LoginResponse.java",
        ],
        "key_terms": ["legacyToken", "generateLegacyToken", "getLegacyToken", "old mobile clients"],
        "evidence": {
            "active": [
                "Mobile gateway logs still show requests from client versions that read the legacyToken field.",
                "The compatibility owner confirmed the old mobile release train has not completed migration.",
            ],
            "stale": [
                "The mobile gateway now blocks versions that depended on the legacyToken field.",
                "Recent login response consumers only validate accessToken in the compatibility audit.",
            ],
            "unknown": [
                "Client version telemetry is unavailable for the legacy mobile release train.",
                "No owner has confirmed whether any login consumer still reads legacyToken.",
            ],
            "conflicting": [
                "Release notes say the old mobile release train was retired.",
                "API access logs still contain login responses with the legacyToken field read by older clients.",
            ],
        },
        "misleading": {
            "active": "A cleanup note says all mobile clients are modern and legacyToken can be removed immediately.",
            "stale": "A stale incident note says old mobile clients still require legacyToken on every login.",
            "unknown": "A chat message claims legacyToken is safe to delete, but it cites no telemetry or owner.",
            "conflicting": "A migration checklist says legacyToken can be deleted without mentioning the remaining API log signal.",
        },
    },
    "order": {
        "pitfall": "orderStatus/refundStatus",
        "claim_text": "Order status and refund status must remain separate fields.",
        "validity_condition": "The claim is valid only while refund reconciliation still depends on separate lifecycle fields.",
        "instruction": (
            "Evaluate and optimize order status handling to reduce duplicated status logic while avoiding "
            "breakage in refund accounting and reconciliation paths."
        ),
        "target_files": [
            "src/main/java/com/example/legacyshop/order/ShopOrder.java",
            "src/main/java/com/example/legacyshop/order/OrderService.java",
        ],
        "key_terms": ["orderStatus", "refundStatus", "RefundStatus", "refund accounting"],
        "evidence": {
            "active": [
                "The refund reconciliation job still reads refundStatus independently from orderStatus.",
                "Finance reports still compare paid orders against refundStatus to detect refund exposure.",
            ],
            "stale": [
                "The new reconciliation service consumes a normalized settlement event instead of refundStatus.",
                "Recent finance exports no longer read the separate refund status field.",
            ],
            "unknown": [
                "There is no current inventory of finance jobs that read refundStatus.",
                "The owning team has not confirmed whether settlement exports have fully migrated.",
            ],
            "conflicting": [
                "The settlement migration checklist is marked complete.",
                "A nightly finance job still references refundStatus in its last successful run note.",
            ],
        },
        "misleading": {
            "active": "A refactor ticket says refundStatus was replaced by a single order lifecycle enum everywhere.",
            "stale": "An old production incident says refundStatus must remain forever for reconciliation.",
            "unknown": "A pull request comment says the two fields are redundant but links no finance evidence.",
            "conflicting": "A dashboard note says settlement migration is complete and omits the nightly job reference.",
        },
    },
    "user": {
        "pitfall": "status=2 soft delete",
        "claim_text": "User deletion must keep the row and mark status as deleted instead of physically deleting it.",
        "validity_condition": "The claim is valid only while audit records require the user row to remain queryable.",
        "instruction": (
            "Evaluate and optimize user deletion behavior to reduce legacy deletion complexity while avoiding "
            "breakage in audit and recovery paths."
        ),
        "target_files": [
            "src/main/java/com/example/legacyshop/user/UserService.java",
            "src/main/java/com/example/legacyshop/user/UserRepository.java",
        ],
        "key_terms": ["markDeleted", "STATUS_DELETED", "deleteById", "audit"],
        "evidence": {
            "active": [
                "Audit drilldown still joins user actions back to the user row after deletion.",
                "Compliance reports require deleted users to remain queryable with a deleted status marker.",
            ],
            "stale": [
                "The audit pipeline now stores immutable user snapshots with each audit event.",
                "Recent compliance checks read snapshot data and no longer query the user row after deletion.",
            ],
            "unknown": [
                "The audit snapshot rollout status is not recorded in the release checklist.",
                "No current compliance owner has confirmed whether physical deletion is allowed.",
            ],
            "conflicting": [
                "The audit snapshot service is marked enabled for new events.",
                "Backfill notes say older audit events still rely on the user row for drilldown.",
            ],
        },
        "misleading": {
            "active": "A storage cleanup ticket says deleted users can now be physically removed.",
            "stale": "An old compliance memo says user rows must never be physically removed.",
            "unknown": "A Slack summary says deleteById is fine but gives no audit migration evidence.",
            "conflicting": "A rollout note says snapshots are enabled while omitting the older audit backfill gap.",
        },
    },
    "payment": {
        "pitfall": "amountInCent",
        "claim_text": "Payment signature verification must keep using amountInCent rather than amountInYuan.",
        "validity_condition": "The claim is valid only while third-party callbacks still sign the amount in cents.",
        "instruction": (
            "Evaluate and optimize payment callback signature handling to reduce amount-unit compatibility "
            "branches while avoiding payment verification regressions."
        ),
        "target_files": [
            "src/main/java/com/example/legacyshop/payment/PaymentCallback.java",
            "src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java",
        ],
        "key_terms": ["amountInCent", "amountInYuan", "signature", "third-party callbacks"],
        "evidence": {
            "active": [
                "The payment provider contract still states callback signatures are calculated with amountInCent.",
                "Recent callback samples fail verification when the signature payload uses amountInYuan.",
            ],
            "stale": [
                "The new payment gateway contract signs callbacks with amountInYuan.",
                "Recent provider samples include decimal yuan values as the canonical signature amount.",
            ],
            "unknown": [
                "The payment gateway migration record does not identify which amount unit is canonical.",
                "There are no recent signed callback samples attached to the migration ticket.",
            ],
            "conflicting": [
                "The new gateway contract says amountInYuan is canonical.",
                "Production callback replay notes still show amountInCent signatures passing verification.",
            ],
        },
        "misleading": {
            "active": "A modernization note says all signatures now use amountInYuan and amountInCent is obsolete.",
            "stale": "An old provider incident says callbacks must always use amountInCent for signatures.",
            "unknown": "A cleanup comment recommends amountInYuan but gives no provider sample.",
            "conflicting": "A contract summary says amountInYuan is canonical and ignores callback replay evidence.",
        },
    },
    "job": {
        "pitfall": "syncBatchId",
        "claim_text": "Bill sync must keep the syncBatchId idempotency check.",
        "validity_condition": "The claim is valid only while reruns can deliver the same bill batch more than once.",
        "instruction": (
            "Evaluate and optimize bill sync idempotency handling to reduce legacy duplicate-checking code "
            "while avoiding duplicate billing during reruns."
        ),
        "target_files": [
            "src/main/java/com/example/legacyshop/job/BillSyncService.java",
            "src/main/java/com/example/legacyshop/job/BillRepository.java",
        ],
        "key_terms": ["syncBatchId", "existsBySyncBatchId", "exactly-once", "rerun"],
        "evidence": {
            "active": [
                "Manual bill reruns can still send the same syncBatchId more than once.",
                "Operations runbooks still use syncBatchId to verify duplicate prevention.",
            ],
            "stale": [
                "The new queue provides exactly-once delivery for bill sync messages.",
                "Recent rerun playbooks rely on queue-level deduplication instead of syncBatchId checks.",
            ],
            "unknown": [
                "The queue migration record does not say whether exactly-once delivery is enabled for bill sync.",
                "There is no current rerun drill proving duplicate bill delivery is impossible.",
            ],
            "conflicting": [
                "The queue migration checklist claims exactly-once delivery is enabled.",
                "The operations runbook still tells engineers to inspect syncBatchId before rerunning bills.",
            ],
        },
        "misleading": {
            "active": "A cleanup ticket says the queue is exactly-once and syncBatchId checks can be removed.",
            "stale": "An old runbook says syncBatchId checks are mandatory during every rerun.",
            "unknown": "A teammate says queue dedupe is enough but provides no migration or rerun evidence.",
            "conflicting": "A queue checklist says exactly-once is done while omitting the rerun runbook warning.",
        },
    },
}


def expected_decision(evidence_status: str) -> str:
    try:
        return EXPECTED_DECISIONS[evidence_status]
    except KeyError as exc:
        raise ValueError(f"Unsupported evidence status: {evidence_status}") from exc
