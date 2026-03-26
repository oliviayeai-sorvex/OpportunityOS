from __future__ import annotations

from models.entities import FilterCriteria, VerificationEvent
from models.repository_protocol import OpportunityRepository


class DashboardService:
    def __init__(self, repository: OpportunityRepository) -> None:
        self._repository = repository

    def ranked_opportunities(self, criteria: FilterCriteria) -> list:
        return self._repository.list_opportunities(criteria)

    def verify(self, opportunity_id: str, actor_id: str, status: str, reason: str) -> None:
        event = VerificationEvent(
            opportunity_id=opportunity_id,
            actor_id=actor_id,
            status=status,
            reason=reason,
        )
        self._repository.set_verification(event)

    def summary(self) -> dict:
        return self._repository.dashboard_summary()
