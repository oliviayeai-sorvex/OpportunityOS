from adapters.providers import normalize_record
from models.entities import Opportunity
from services.scoring_service import ScoringService


def test_normalize_record_required_fields() -> None:
    row = normalize_record(
        "stocks",
        {
            "external_id": "x1",
            "domain": "stocks",
            "title": "test",
            "value_estimate": 100,
            "risk_level": "low",
        },
    )
    assert isinstance(row, Opportunity)
    assert row.source == "stocks"


def test_scoring_service_produces_scorecard() -> None:
    service = ScoringService(
        policy_path="/Users/olivia/.gemini/antigravity/playground/OpportunityOS/apps/control-plane/src/config/scoring_policy.json"
    )
    opportunity = normalize_record(
        "grants",
        {
            "external_id": "x2",
            "domain": "grants",
            "title": "grant",
            "value_estimate": 500000,
            "risk_level": "low",
        },
    )
    score = service.score(opportunity)
    assert score.total > 0
    assert 0 <= score.confidence <= 1
