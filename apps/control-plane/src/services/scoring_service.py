from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from models.entities import Opportunity, ScoreCard


@dataclass(frozen=True)
class ScoringPolicy:
    value_weight: float
    risk_weight: float
    risk_factors: dict[str, float]
    domain_bonus: dict[str, float]
    max_value_estimate: float
    base_confidence: float
    value_confidence_weight: float
    risk_confidence_weight: float


class ScoringService:
    def __init__(self, policy_path: str) -> None:
        with Path(policy_path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self._policy = ScoringPolicy(**payload)

    def score(self, item: Opportunity) -> ScoreCard:
        p = self._policy
        value_factor = min(item.value_estimate / p.max_value_estimate, 1.0)
        risk_factor = p.risk_factors.get(item.risk_level, 0.5)
        domain_bonus = p.domain_bonus.get(item.domain, 0.0)
        total = round((p.value_weight * value_factor + p.risk_weight * risk_factor + domain_bonus) * 100, 2)
        confidence = round(
            min(p.base_confidence + value_factor * p.value_confidence_weight + risk_factor * p.risk_confidence_weight, 0.99),
            2,
        )
        return ScoreCard(
            total=total,
            factors={
                "value_factor": round(value_factor, 2),
                "risk_factor": round(risk_factor, 2),
                "domain_bonus": domain_bonus,
            },
            confidence=confidence,
        )
