from api.router import ControlPlaneAPI


def test_grant_writer_default_sources_and_schedule() -> None:
    api = ControlPlaneAPI()
    payload = api.grant_writer_dashboard(role="viewer", user_id="user-1")
    assert payload["schedule"] in {"daily", "weekly"}
    names = {row["name"] for row in payload["sources"]}
    assert "business.gov.au Grants Finder" in names
    assert "GrantConnect (Federal)" in names
    assert "State: South Australia Grants" not in names
    assert "State: Western Australia Grants" not in names
    assert "ATO R&D Tax Incentive" not in names
    assert "State: Business Victoria" in names
    assert "MedTech Grants" in names


def test_grant_writer_source_edit_schedule_and_scan() -> None:
    api = ControlPlaneAPI()
    api.update_settings(
        role="operator",
        user_id="user-1",
        email="user1@example.com",
        updates={
            "company_size": "small",
            "interest_industries": ["technology", "clean_energy"],
        },
    )

    api.grant_writer_upsert_source(
        role="operator",
        user_id="user-1",
        source_id="src-custom-industry",
        name="Custom Industry Grants",
        url="https://example.com/grants",
        access="Public",
        active=True,
    )
    api.grant_writer_set_schedule(role="operator", user_id="user-1", frequency="weekly")
    scan = api.grant_writer_run_scan(role="operator", user_id="user-1")

    payload = api.grant_writer_dashboard(role="operator", user_id="user-1")
    names = {row["name"] for row in payload["sources"]}

    assert "Custom Industry Grants" in names
    assert payload["schedule"] == "weekly"
    assert scan["scanned_count"] >= 1
    assert scan["eligible_count"] >= 1
    assert len(payload["scan_results"]) >= 1
    first = payload["scan_results"][0]
    assert "published_at" in first
    assert "location" in first
    assert "industry" in first
    assert "details" in first
    assert "due_date" in first
    assert "grant_amount" in first
    assert "eligible" in first


def test_grant_board_and_draft_flow() -> None:
    api = ControlPlaneAPI()
    api.update_settings(
        role="operator",
        user_id="user-9",
        email="u9@example.com",
        updates={
            "company_name": "Acme",
            "abn": "12345678901",
            "anzsic_code": "6201",
            "business_stage": "growth",
            "headcount": 20,
            "state_territory": "NSW",
            "business_objectives": "Scale revenue and create jobs",
            "company_size": "small",
            "interest_industries": ["technology"],
        },
    )
    scan = api.grant_writer_run_scan(role="operator", user_id="user-9")
    assert scan["scanned_count"] >= 1
    dashboard = api.grant_writer_dashboard(role="operator", user_id="user-9")
    first_id = dashboard["scan_results"][0]["id"]
    api.grant_writer_move_status(role="operator", user_id="user-9", grant_result_id=first_id, workflow_status="Shortlisted")
    board = api.grant_writer_board(role="operator", user_id="user-9", filters={"min_score": 0}, sort_by="score")
    assert "Shortlisted" in board["board"]
    draft = api.grant_writer_draft(role="operator", user_id="user-9", grant_result_id=first_id, prompt="")
    assert "draft" in draft
