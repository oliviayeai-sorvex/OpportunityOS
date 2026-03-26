from __future__ import annotations

from datetime import date

from models.repository_protocol import OpportunityRepository


class WatchlistService:
    def __init__(self, repository: OpportunityRepository) -> None:
        self._repository = repository

    def add(self, user_id: str, opportunity_id: str) -> None:
        self._repository.add_watchlist_item(user_id, opportunity_id)

    def list(self, user_id: str) -> list:
        return self._repository.get_watchlist(user_id)

    def create_action(self, opportunity_id: str, owner_id: str, summary: str, due_date: str):
        if len(summary.strip()) < 4:
            raise ValueError("summary must be at least 4 characters")
        try:
            date.fromisoformat(due_date)
        except ValueError as exc:
            raise ValueError("due_date must be ISO format YYYY-MM-DD") from exc
        return self._repository.create_action(opportunity_id, owner_id, summary.strip(), due_date)

    def list_actions(self, owner_id: str):
        return self._repository.list_actions(owner_id)
