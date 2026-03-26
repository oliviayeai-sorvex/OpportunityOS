from api.router import ControlPlaneAPI


def test_command_center_e2e_rank_filter_verify() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"], trace_id="trace-e2e-cc")

    rows = api.list_opportunities(role="viewer", filters={"min_score": 70})["items"]
    assert rows == sorted(rows, key=lambda row: row["score_card"]["total"], reverse=True)

    chosen = rows[0]
    api.verify_opportunity(
        role="operator",
        opportunity_id=chosen["id"],
        actor_id="ops-2",
        status="verified",
        reason="dashboard validated",
    )

    summary = api.dashboard_summary(role="viewer")
    assert summary["verified"] == 1
