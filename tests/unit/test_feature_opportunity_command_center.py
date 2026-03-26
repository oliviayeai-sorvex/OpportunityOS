import pytest

from api.router import ControlPlaneAPI


def test_filters_validate_min_score_range() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])

    with pytest.raises(ValueError):
        api.list_opportunities(role="viewer", filters={"min_score": 120})


def test_score_breakdown_returns_selected_row() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    item_id = api.list_opportunities(role="viewer", filters={})["items"][0]["id"]
    breakdown = api.score_breakdown(role="viewer", opportunity_id=item_id)
    assert breakdown["id"] == item_id
    assert "total" in breakdown["score"]
