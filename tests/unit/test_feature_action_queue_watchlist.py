import pytest

from api.router import ControlPlaneAPI


def test_watchlist_add_is_idempotent() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    opp_id = api.list_opportunities(role="viewer", filters={})["items"][0]["id"]

    api.add_watchlist(role="operator", user_id="ops-1", opportunity_id=opp_id)
    api.add_watchlist(role="operator", user_id="ops-1", opportunity_id=opp_id)

    rows = api.list_watchlist(role="operator", user_id="ops-1")["items"]
    assert len(rows) == 1


def test_create_action_requires_valid_date() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    opp_id = api.list_opportunities(role="viewer", filters={})["items"][0]["id"]

    with pytest.raises(ValueError):
        api.create_action(
            role="operator",
            opportunity_id=opp_id,
            owner_id="ops-1",
            summary="Call broker",
            due_date="03/31/2026",
        )
