from api.router import ControlPlaneAPI


def test_full_watchlist_action_e2e() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"], trace_id="trace-e2e-wl")

    rows = api.list_opportunities(role="viewer", filters={})["items"]
    chosen = rows[0]

    api.add_watchlist(role="operator", user_id="ops-3", opportunity_id=chosen["id"])
    api.create_action(
        role="operator",
        opportunity_id=chosen["id"],
        owner_id="ops-3",
        summary="Prepare investment memo",
        due_date="2026-04-02",
    )

    watchlist = api.list_watchlist(role="operator", user_id="ops-3")["items"]
    actions = api.list_actions(role="operator", owner_id="ops-3")["items"]
    assert len(watchlist) == 1
    assert len(actions) == 1
