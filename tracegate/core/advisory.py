from __future__ import annotations

from tracegate.core.models import AdvisoryDecision, EvalCase
from tracegate.core.policy import advise_case


def run_rule_advisor(cases: list[EvalCase]) -> list[AdvisoryDecision]:
    return [advise_case(case) for case in cases if case.is_scored_real_case]
