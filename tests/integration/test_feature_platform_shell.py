from api.router import ControlPlaneAPI


def test_settings_and_home_shell_flow() -> None:
    api = ControlPlaneAPI()

    settings = api.get_settings(role="operator", user_id="u-1", email="u1@example.com")
    assert settings["profile"]["timezone"] == "Australia/Sydney"

    api.update_settings(
        role="operator",
        user_id="u-1",
        email="u1@example.com",
        updates={"name": "U One", "billing_plan": "pro", "digest_time": "07:00"},
    )

    api.scheduler_run_now(role="operator", user_id="u-1", vertical="grants", job_type="scan")
    api.scheduler_process(role="admin")

    home = api.home_shell(role="operator", user_id="u-1")
    assert "grants" in home["vertical_summary"]


def test_notifications_and_search() -> None:
    api = ControlPlaneAPI()
    api.run_ingestion(role="operator", sources=["stocks", "real_estate", "grants"])
    api.scheduler_run_now(role="operator", user_id="u-2", vertical="grants", job_type="digest")
    api.scheduler_process(role="admin")

    notifications = api.notifications(role="operator", user_id="u-2")
    assert len(notifications["items"]) >= 1

    search = api.global_search(role="operator", user_id="u-2", query="grant")
    assert "results" in search


def test_settings_accepts_json_objects_for_profile_fields() -> None:
    api = ControlPlaneAPI()
    result = api.update_settings(
        role="operator",
        user_id="u-3",
        email="u3@example.com",
        updates={
            "notification_preferences": {"email": True, "in_app": False},
            "active_verticals": ["grants", "stocks"],
            "digest_enabled_verticals": {"grants": True, "stocks": False},
        },
    )
    profile = result["profile"]
    assert profile["notification_preferences"].startswith("{")
    assert profile["active_verticals"].startswith("[")
    assert profile["digest_enabled_verticals"].startswith("{")
