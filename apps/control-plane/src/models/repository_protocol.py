from __future__ import annotations

from typing import Protocol, List

from .entities import (
    ActionItem,
    FilterCriteria,
    GrantDraft,
    GrantScanResult,
    GrantSource,
    JobRecord,
    NotificationItem,
    Opportunity,
    ScoreCard,
    UserProfile,
    VerificationEvent,
)


class OpportunityRepository(Protocol):
    def upsert_opportunity(self, item: Opportunity) -> Opportunity:
        ...

    def list_opportunities(self, criteria: FilterCriteria) -> List[Opportunity]:
        ...

    def set_scorecard(self, opportunity_id: str, score_card: ScoreCard) -> None:
        ...

    def set_verification(self, event: VerificationEvent) -> None:
        ...

    def add_watchlist_item(self, user_id: str, opportunity_id: str) -> None:
        ...

    def get_watchlist(self, user_id: str) -> List[Opportunity]:
        ...

    def create_action(self, opportunity_id: str, owner_id: str, summary: str, due_date: str) -> ActionItem:
        ...

    def has_opportunity(self, opportunity_id: str) -> bool:
        ...

    def list_actions(self, owner_id: str) -> List[ActionItem]:
        ...

    def add_ingestion_run(self, trace_id: str, ingested_count: int, rejected_count: int, errors: List[dict]) -> None:
        ...

    def list_ingestion_runs(self) -> List[dict]:
        ...

    def dashboard_summary(self) -> dict:
        ...

    def list_grant_sources(self, user_id: str = "global") -> List[GrantSource]:
        ...

    def upsert_grant_source(self, source: GrantSource, user_id: str = "global") -> GrantSource:
        ...

    def delete_grant_source(self, source_id: str, user_id: str = "global") -> None:
        ...

    def list_grant_source_quality(self, user_id: str = "global") -> dict[str, dict]:
        ...

    def upsert_grant_source_quality(self, user_id: str, source_id: str, metrics: dict) -> None:
        ...

    def get_grant_source_memory(self, user_id: str, source_id: str) -> dict | None:
        ...

    def upsert_grant_source_memory(self, user_id: str, source_id: str, memory: dict) -> None:
        ...

    def get_grant_source_api_config(self, user_id: str, source_id: str) -> dict | None:
        ...

    def upsert_grant_source_api_config(self, user_id: str, source_id: str, config: dict) -> None:
        ...

    def get_grant_scan_schedule(self, user_id: str = "global") -> str:
        ...

    def set_grant_scan_schedule(self, frequency: str, user_id: str = "global") -> None:
        ...

    def add_grant_scan_results(self, results: List[GrantScanResult], user_id: str = "global") -> None:
        ...

    def replace_grant_scan_results(self, results: List[GrantScanResult], user_id: str = "global") -> None:
        ...

    def list_grant_scan_results(self, limit: int = 100, user_id: str = "global") -> List[GrantScanResult]:
        ...

    def update_grant_scan_result(self, user_id: str, result_id: str, **updates) -> None:
        ...

    def create_grant_draft(self, draft: GrantDraft) -> GrantDraft:
        ...

    def list_grant_drafts(self, user_id: str, grant_result_id: str) -> List[GrantDraft]:
        ...

    def add_grant_raw_records(self, user_id: str, run_id: str, records: List[dict]) -> None:
        ...

    def list_grant_raw_records(self, user_id: str, run_id: str) -> List[dict]:
        ...

    def upsert_grant_normalized_records(self, user_id: str, run_id: str, records: List[dict]) -> None:
        ...

    def list_grant_normalized_records(self, user_id: str, run_id: str) -> List[dict]:
        ...

    def add_grant_match_candidates(self, user_id: str, run_id: str, records: List[dict]) -> None:
        ...

    def list_grant_match_candidates(self, user_id: str, run_id: str) -> List[dict]:
        ...

    def add_grant_ai_assessments(self, user_id: str, run_id: str, records: List[dict]) -> None:
        ...

    def list_grant_ai_assessments(self, user_id: str, run_id: str) -> List[dict]:
        ...

    def add_grant_pipeline_runs(self, user_id: str, run_id: str, records: List[dict]) -> None:
        ...

    def list_grant_pipeline_runs(self, user_id: str, run_id: str) -> List[dict]:
        ...

    def get_ai_cache(self, stage: str, content_hash: str) -> dict | None:
        ...

    def set_ai_cache(self, stage: str, content_hash: str, result: dict) -> None:
        ...

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        ...

    def upsert_user_profile(self, profile: UserProfile) -> UserProfile:
        ...

    def enqueue_job(self, job: JobRecord) -> JobRecord:
        ...

    def update_job(self, job_id: str, **updates) -> None:
        ...

    def list_jobs(self, user_id: str, vertical: str = "", limit: int = 100) -> List[JobRecord]:
        ...

    def list_due_jobs(self, current_time: str) -> List[JobRecord]:
        ...

    def add_notification(self, item: NotificationItem) -> NotificationItem:
        ...

    def list_notifications(self, user_id: str, unread_only: bool = False, limit: int = 100) -> List[NotificationItem]:
        ...

    def mark_notification_read(self, user_id: str, notification_id: str) -> None:
        ...
