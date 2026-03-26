from api.router import ControlPlaneAPI


def test_ingestion_and_filtered_opportunity_listing() -> None:
    api = ControlPlaneAPI()

    ingest = api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"], trace_id="trace-int-1")
    assert ingest["trace_id"] == "trace-int-1"
    assert ingest["ingested_count"] == 3

    listing = api.list_opportunities(role="viewer", filters={"min_score": 70})
    assert len(listing["items"]) >= 1
    assert all(item["score_card"]["total"] >= 70 for item in listing["items"])


def test_unsupported_source_reports_error() -> None:
    api = ControlPlaneAPI()
    ingest = api.run_ingestion(role="admin", sources=["unknown"], trace_id="trace-int-2")
    assert ingest["ingested_count"] == 0
    assert ingest["provider_results"][0]["status"] == "error"
