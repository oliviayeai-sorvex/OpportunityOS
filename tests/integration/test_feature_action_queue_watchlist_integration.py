from api.router import ControlPlaneAPI


def test_watchlist_and_action_creation_flow() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    target = api.list_opportunities(role="viewer", filters={})["items"][0]

    api.add_watchlist(role="operator", user_id="ops-2", opportunity_id=target["id"])
    watchlist = api.list_watchlist(role="operator", user_id="ops-2")["items"]
    assert len(watchlist) == 1

    created = api.create_action(
        role="operator",
        opportunity_id=target["id"],
        owner_id="ops-2",
        summary="Schedule diligence call",
        due_date="2026-03-31",
    )
    assert created["item"]["status"] == "open"

    listed = api.list_actions(role="operator", owner_id="ops-2")["items"]
    assert len(listed) == 1
