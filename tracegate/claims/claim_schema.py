from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Claim:
    id: str
    module: str
    pitfall: str
    claim_text: str
    validity_condition: str
    key_terms: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        return cls(
            id=str(data["id"]),
            module=str(data["module"]),
            pitfall=str(data["pitfall"]),
            claim_text=str(data["claim_text"]),
            validity_condition=str(data["validity_condition"]),
            key_terms=tuple(str(item) for item in data.get("key_terms", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "module": self.module,
            "pitfall": self.pitfall,
            "claim_text": self.claim_text,
            "validity_condition": self.validity_condition,
            "key_terms": list(self.key_terms),
        }


def expected_decision_for_status(evidence_status: str) -> str:
    mapping = {
        "active": "preserve",
        "stale": "optimize",
        "unknown": "verify_first",
        "conflicting": "conflict_detected",
    }
    try:
        return mapping[evidence_status]
    except KeyError as exc:
        raise ValueError(f"Unsupported evidence status: {evidence_status}") from exc
