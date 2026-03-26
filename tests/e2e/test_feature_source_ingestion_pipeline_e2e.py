from api.router import ControlPlaneAPI


def test_full_request_path_and_dashboard_verification_flow() -> None:
    api = ControlPlaneAPI()

    ingest = api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"], trace_id="trace-e2e-1")
    assert ingest["pipeline_path"] == ["gateway", "router", "provider", "logging", "policy"]

    rows = api.list_opportunities(role="viewer", filters={})["items"]
    assert len(rows) == 3

    target_id = rows[0]["id"]
    api.verify_opportunity(
        role="operator",
        opportunity_id=target_id,
        actor_id="user-1",
        status="verified",
        reason="validated on dashboard",
    )

    summary = api.dashboard_summary(role="viewer")
    assert summary["verified"] == 1
    assert summary["total"] == 3
