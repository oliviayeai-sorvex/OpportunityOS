from api.router import ControlPlaneAPI


def test_verify_updates_dashboard_summary() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    first = api.list_opportunities(role="viewer", filters={})["items"][0]

    api.verify_opportunity(
        role="operator",
        opportunity_id=first["id"],
        actor_id="ops-1",
        status="verified",
        reason="clear due diligence",
    )

    summary = api.dashboard_summary(role="viewer")
    assert summary["verified"] == 1


def test_verify_rejects_short_reason() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    first = api.list_opportunities(role="viewer", filters={})["items"][0]

    try:
        api.verify_opportunity(
            role="operator",
            opportunity_id=first["id"],
            actor_id="ops-1",
            status="rejected",
            reason="no",
        )
    except ValueError as exc:
        assert "at least 4" in str(exc)
    else:
        raise AssertionError("Expected ValueError for short reason")
