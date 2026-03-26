from services.grant_writer_service import GrantWriterService
from models.repository import InMemoryOpportunityRepository


def test_grant_writer_service_scan_records_results() -> None:
    repository = InMemoryOpportunityRepository()
    service = GrantWriterService(repository)

    result = service.run_scan(user_id="user-1")
    dashboard = service.dashboard_payload(user_id="user-1")

    assert result["scanned_count"] >= 1
    assert len(dashboard["scan_results"]) >= 1


def test_apply_rules_rejects_explicit_location_mismatch() -> None:
    repository = InMemoryOpportunityRepository()
    service = GrantWriterService(repository)

    normalized = [
        {
            "normalized_id": "n-1",
            "source_id": "src-test",
            "industry": ["technology"],
            "location": "QLD",
            "criteria_locations": ["QLD"],
            "criteria_industries": ["technology"],
            "criteria_business_size": "",
            "criteria_not_allowed": [],
            "min_size": 0,
            "max_size": 2000,
            "deadline": "2026-12-31",
        }
    ]
    profile = {"industries": ["technology"], "state_territory": "NSW", "headcount": 10}

    candidates = service._apply_rules(user_id="user-1", run_id="run-1", normalized=normalized, profile=profile)

    assert candidates[0]["rule_status"] == "fail"
    assert "location mismatch" in candidates[0]["rule_reasons"]
