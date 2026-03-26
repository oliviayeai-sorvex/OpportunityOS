from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from adapters.connector_registry import ConnectorRegistry
from adapters.repository_sqlite import SQLiteOpportunityRepository
from models.entities import FilterCriteria
from models.repository import InMemoryOpportunityRepository
from services.dashboard_service import DashboardService
from services.ingestion_service import IngestionService
from services.grant_writer_service import GrantWriterService
from services.platform_service import PlatformService
from services.scoring_service import ScoringService
from services.watchlist_service import WatchlistService

ALLOWED_RISKS = {None, "low", "medium", "high"}


def _authorize(role: str, allowed: set[str]) -> None:
    if role not in allowed:
        raise PermissionError(f"role '{role}' is not allowed")


def _validate_filters(filters: dict) -> dict:
    min_score = float(filters.get("min_score", 0.0))
    if not 0 <= min_score <= 100:
        raise ValueError("min_score must be between 0 and 100")

    max_risk = filters.get("max_risk")
    if max_risk not in ALLOWED_RISKS:
        raise ValueError("max_risk must be one of low, medium, high")

    min_value = float(filters.get("min_value_estimate", 0.0))
    if min_value < 0:
        raise ValueError("min_value_estimate must be >= 0")

    domains = filters.get("domains", [])
    if not isinstance(domains, list):
        raise ValueError("domains must be a list")

    limit = int(filters.get("limit", 100))
    offset = int(filters.get("offset", 0))
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("offset must be >= 0")

    return {
        "domains": domains,
        "min_score": min_score,
        "min_value_estimate": min_value,
        "max_risk": max_risk,
        "limit": limit,
        "offset": offset,
    }


class ControlPlaneAPI:
    def __init__(self) -> None:
        src_root = Path(__file__).resolve().parents[1]
        backend = os.getenv("REPOSITORY_BACKEND", "sqlite")
        if backend == "inmemory":
            self.repository = InMemoryOpportunityRepository()
        elif backend == "postgres":
            from adapters.repository_postgres import PostgresOpportunityRepository
            db_url = os.getenv("DATABASE_URL", "postgresql://aigov:aigov_secret@localhost:5433/opportunity_db")
            self.repository = PostgresOpportunityRepository(db_path=db_url)
        else:
            db_path = os.getenv("SQLITE_DB_PATH", str(src_root / "data" / "opportunityos.db"))
            self.repository = SQLiteOpportunityRepository(db_path=db_path)

        policy_path = os.getenv("SCORE_POLICY_PATH", str(src_root / "config" / "scoring_policy.json"))
        scoring = ScoringService(policy_path=policy_path)

        connectors_path = os.getenv("CONNECTORS_CONFIG_PATH", str(src_root / "config" / "connectors.json"))
        adapters = ConnectorRegistry().build_adapters(config_path=connectors_path, src_root=src_root)

        self.ingestion_service = IngestionService(self.repository, adapters, scoring)
        self.dashboard_service = DashboardService(self.repository)
        self.watchlist_service = WatchlistService(self.repository)
        self.grant_writer_service = GrantWriterService(self.repository)
        self.platform_service = PlatformService(self.repository)

    def run_ingestion(self, role: str, sources: Iterable[str], trace_id: str | None = None) -> dict:
        _authorize(role, {"operator", "admin"})
        trace_id = trace_id or str(uuid4())
        response = self.ingestion_service.run(sources, trace_id)
        response["pipeline_path"] = ["gateway", "router", "provider", "logging", "policy"]
        return response

    def list_opportunities(self, role: str, filters: dict | None = None) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        parsed = _validate_filters(filters or {})
        criteria = FilterCriteria(
            domains=parsed["domains"],
            min_score=parsed["min_score"],
            min_value_estimate=parsed["min_value_estimate"],
            max_risk=parsed["max_risk"],
            limit=parsed["limit"],
            offset=parsed["offset"],
        )
        rows = self.dashboard_service.ranked_opportunities(criteria)
        return {"items": [asdict(item) for item in rows], "limit": criteria.limit, "offset": criteria.offset}

    def score_breakdown(self, role: str, opportunity_id: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        rows = self.list_opportunities(role=role, filters={"min_score": 0, "limit": 500})["items"]
        for row in rows:
            if row["id"] == opportunity_id:
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "score": row["score_card"],
                }
        raise KeyError("opportunity not found")

    def verify_opportunity(self, role: str, opportunity_id: str, actor_id: str, status: str, reason: str) -> dict:
        _authorize(role, {"operator", "admin"})
        if len(reason.strip()) < 4:
            raise ValueError("reason must be at least 4 characters")
        self.dashboard_service.verify(opportunity_id, actor_id, status, reason.strip())
        return {"ok": True}

    def dashboard_summary(self, role: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return self.dashboard_service.summary()

    def ingestion_history(self, role: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return {"runs": self.repository.list_ingestion_runs()}

    def add_watchlist(self, role: str, user_id: str, opportunity_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        self.watchlist_service.add(user_id, opportunity_id)
        return {"ok": True}

    def list_watchlist(self, role: str, user_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return {"items": [asdict(item) for item in self.watchlist_service.list(user_id)]}

    def create_action(self, role: str, opportunity_id: str, owner_id: str, summary: str, due_date: str) -> dict:
        _authorize(role, {"operator", "admin"})
        action = self.watchlist_service.create_action(opportunity_id, owner_id, summary, due_date)
        return {"item": asdict(action)}

    def list_actions(self, role: str, owner_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return {"items": [asdict(item) for item in self.watchlist_service.list_actions(owner_id)]}

    def grant_writer_dashboard(self, role: str, user_id: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return self.grant_writer_service.dashboard_payload(user_id=user_id)

    def grant_writer_upsert_source(
        self,
        role: str,
        user_id: str,
        source_id: str,
        name: str,
        url: str,
        access: str,
        active: bool = True,
    ) -> dict:
        _authorize(role, {"operator", "admin"})
        return {
            "source": self.grant_writer_service.upsert_source(
                source_id=source_id,
                user_id=user_id,
                name=name,
                url=url,
                access=access,
                active=active,
            )
        }

    def grant_writer_delete_source(self, role: str, user_id: str, source_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        self.grant_writer_service.delete_source(user_id=user_id, source_id=source_id)
        return {"ok": True}

    def grant_writer_reset_sources_to_defaults(self, role: str, user_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return self.grant_writer_service.reset_sources_to_defaults(user_id=user_id)

    def grant_writer_set_schedule(self, role: str, user_id: str, frequency: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return {"schedule": self.grant_writer_service.set_schedule(user_id=user_id, frequency=frequency)}

    def grant_writer_run_scan(self, role: str, user_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return self.grant_writer_service.run_scan(user_id=user_id)

    def grant_writer_pipeline_run(self, role: str, user_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return self.grant_writer_service.run_scan(user_id=user_id)

    def grant_writer_pipeline_details(self, role: str, user_id: str, run_id: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return self.grant_writer_service.pipeline_run_details(user_id=user_id, run_id=run_id)

    def grant_writer_discovery_debug(self, role: str, user_id: str, source_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return self.grant_writer_service.discovery_debug(user_id=user_id, source_id=source_id)

    def grant_writer_board(self, role: str, user_id: str, filters: dict | None = None, sort_by: str = "deadline") -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return self.grant_writer_service.board_list(user_id=user_id, filters=filters or {}, sort_by=sort_by)

    def grant_writer_move_status(self, role: str, user_id: str, grant_result_id: str, workflow_status: str) -> dict:
        _authorize(role, {"operator", "admin"})
        self.grant_writer_service.move_status(user_id=user_id, grant_result_id=grant_result_id, workflow_status=workflow_status)
        return {"ok": True}

    def grant_writer_mark_reviewed(self, role: str, user_id: str, grant_result_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        self.grant_writer_service.mark_reviewed(user_id=user_id, grant_result_id=grant_result_id)
        return {"ok": True}

    def grant_writer_mark_submitted(self, role: str, user_id: str, grant_result_id: str) -> dict:
        _authorize(role, {"operator", "admin"})
        self.grant_writer_service.mark_submitted(user_id=user_id, grant_result_id=grant_result_id)
        return {"ok": True}

    def grant_writer_update_tracking(
        self, role: str, user_id: str, grant_result_id: str, notes: str, outcome: str, contact_names: str, reference_numbers: str
    ) -> dict:
        _authorize(role, {"operator", "admin"})
        self.grant_writer_service.update_tracking(
            user_id=user_id,
            grant_result_id=grant_result_id,
            notes=notes,
            outcome=outcome,
            contact_names=contact_names,
            reference_numbers=reference_numbers,
        )
        return {"ok": True}

    def grant_writer_draft(self, role: str, user_id: str, grant_result_id: str, prompt: str = "") -> dict:
        _authorize(role, {"operator", "admin"})
        return self.grant_writer_service.create_or_regenerate_draft(user_id=user_id, grant_result_id=grant_result_id, prompt=prompt)

    def grant_writer_drafts(self, role: str, user_id: str, grant_result_id: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return self.grant_writer_service.list_drafts(user_id=user_id, grant_result_id=grant_result_id)

    def get_settings(self, role: str, user_id: str, email: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        profile = self.platform_service.get_or_create_profile(user_id=user_id, email=email)
        return {"profile": profile.__dict__, "profile_completeness": self.platform_service.profile_completeness(profile)}

    def update_settings(self, role: str, user_id: str, email: str, updates: dict) -> dict:
        _authorize(role, {"operator", "admin"})
        profile = self.platform_service.update_profile(user_id=user_id, email=email, updates=updates)
        return {"profile": profile.__dict__, "profile_completeness": self.platform_service.profile_completeness(profile)}

    def scheduler_run_now(self, role: str, user_id: str, vertical: str, job_type: str = "scan") -> dict:
        _authorize(role, {"operator", "admin"})
        job = self.platform_service.queue_job(user_id=user_id, vertical=vertical, job_type=job_type)
        return {"job": job.__dict__}

    def scheduler_process(self, role: str) -> dict:
        _authorize(role, {"operator", "admin"})
        return self.platform_service.run_due_jobs()

    def scheduler_jobs(self, role: str, user_id: str, vertical: str = "") -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return {"jobs": [row.__dict__ for row in self.repository.list_jobs(user_id=user_id, vertical=vertical, limit=200)]}

    def home_shell(self, role: str, user_id: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return self.platform_service.home_summary(user_id=user_id)

    def notifications(self, role: str, user_id: str, unread_only: bool = False) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        return {"items": self.platform_service.notifications(user_id=user_id, unread_only=unread_only)}

    def notification_mark_read(self, role: str, user_id: str, notification_id: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        self.platform_service.mark_notification_read(user_id=user_id, notification_id=notification_id)
        return {"ok": True}

    def global_search(self, role: str, user_id: str, query: str) -> dict:
        _authorize(role, {"viewer", "operator", "admin"})
        grants = self.grant_writer_service.search(user_id=user_id, query=query)
        jobs = self.repository.list_jobs(user_id=user_id, limit=200)
        if len(query.strip()) < 2:
            return {"results": [], "jobs": [], "summary": grants["summary"]}
        job_matches = [row.__dict__ for row in jobs if query.lower() in f"{row.vertical} {row.job_type} {row.status}".lower()]
        return {"results": grants["results"], "jobs": job_matches[:20], "summary": grants["summary"]}
