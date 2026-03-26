from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import json
from typing import Dict, List
from uuid import uuid4

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

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

DEFAULT_GRANT_SOURCES = [
    GrantSource(id="src-business-gov-au", name="business.gov.au Grants Finder", url="https://business.gov.au/grants-and-programs", access="Public, scrapeable"),
    GrantSource(id="src-grantconnect", name="GrantConnect (Federal)", url="https://www.grants.gov.au/Go/List", access="Public API available"),
    GrantSource(id="src-nsw-grants", name="NSW Government Grants", url="https://www.nsw.gov.au/grants-and-funding", access="Public"),
    GrantSource(id="src-arena", name="ARENA (clean energy)", url="https://arena.gov.au/funding", access="Public"),
    GrantSource(id="src-business-vic", name="State: Business Victoria", url="https://business.vic.gov.au/grants-and-programs?filter=%7B%22status%22%3A%5B%22opening+soon%22%2C%22open%22%2C%22ongoing%22%5D%7D", access="Public"),
    GrantSource(id="src-business-qld", name="State: Business Queensland", url="https://www.business.qld.gov.au/running-business/support-services/financial/grants/schedule", access="Public"),
    GrantSource(id="src-csiro", name="CSIRO", url="https://www.csiro.au/en/work-with-us/funding-programs/SME/SME-Connect-programs", access="Public"),
    GrantSource(id="src-medtech-grants", name="MedTech Grants", url="https://help.grants.gov.au/getting-started-with-grantconnect/information-made-easy/current-opportunities/", access="Curated programs"),
]


class InMemoryOpportunityRepository:
    def __init__(self) -> None:
        self._opportunities: Dict[tuple[str, str], Opportunity] = {}
        self._verifications: List[VerificationEvent] = []
        self._watchlists: Dict[str, List[str]] = defaultdict(list)
        self._actions: Dict[str, ActionItem] = {}
        self._ingestion_runs: List[dict] = []
        self._grant_sources_by_user: Dict[str, Dict[str, GrantSource]] = {
            "global": {source.id: source for source in DEFAULT_GRANT_SOURCES}
        }
        self._grant_scan_schedule_by_user: Dict[str, str] = {"global": "daily"}
        self._grant_scan_results_by_user: Dict[str, List[GrantScanResult]] = {"global": []}
        self._grant_source_quality_by_user: Dict[str, Dict[str, dict]] = {"global": {}}
        self._grant_source_memory_by_user: Dict[str, Dict[str, dict]] = {"global": {}}
        self._grant_source_api_config_by_user: Dict[str, Dict[str, dict]] = {"global": {}}
        self._profiles: Dict[str, UserProfile] = {}
        self._jobs: Dict[str, JobRecord] = {}
        self._notifications: Dict[str, NotificationItem] = {}
        self._grant_drafts: Dict[str, GrantDraft] = {}
        self._grant_raw_records: Dict[tuple[str, str], List[dict]] = {}
        self._grant_normalized_records: Dict[tuple[str, str], List[dict]] = {}
        self._grant_match_candidates: Dict[tuple[str, str], List[dict]] = {}
        self._grant_ai_assessments: Dict[tuple[str, str], List[dict]] = {}
        self._grant_pipeline_runs: Dict[tuple[str, str], List[dict]] = {}
        self._ai_cache: Dict[tuple[str, str], dict] = {}

    def upsert_opportunity(self, item: Opportunity) -> Opportunity:
        key = (item.external_id, item.source)
        if key in self._opportunities:
            existing = self._opportunities[key]
            item.id = existing.id
        else:
            item.id = str(uuid4())
        self._opportunities[key] = item
        return item

    def list_opportunities(self, criteria: FilterCriteria) -> List[Opportunity]:
        rows = list(self._opportunities.values())
        if criteria.domains:
            rows = [row for row in rows if row.domain in criteria.domains]
        rows = [row for row in rows if row.value_estimate >= criteria.min_value_estimate]
        if criteria.max_risk is not None:
            rows = [
                row
                for row in rows
                if RISK_ORDER[row.risk_level] <= RISK_ORDER[criteria.max_risk]
            ]
        rows = [row for row in rows if (row.score_card.total if row.score_card else 0) >= criteria.min_score]
        sorted_rows = sorted(rows, key=lambda row: row.score_card.total if row.score_card else 0, reverse=True)
        start = max(criteria.offset, 0)
        end = start + max(criteria.limit, 1)
        return sorted_rows[start:end]

    def set_scorecard(self, opportunity_id: str, score_card: ScoreCard) -> None:
        for row in self._opportunities.values():
            if row.id == opportunity_id:
                row.score_card = score_card
                return
        raise KeyError(f"Unknown opportunity id: {opportunity_id}")

    def set_verification(self, event: VerificationEvent) -> None:
        for row in self._opportunities.values():
            if row.id == event.opportunity_id:
                row.verification_status = event.status
                self._verifications.append(event)
                return
        raise KeyError(f"Unknown opportunity id: {event.opportunity_id}")

    def add_watchlist_item(self, user_id: str, opportunity_id: str) -> None:
        if not self.has_opportunity(opportunity_id):
            raise KeyError(f"Unknown opportunity id: {opportunity_id}")
        if opportunity_id not in self._watchlists[user_id]:
            self._watchlists[user_id].append(opportunity_id)

    def get_watchlist(self, user_id: str) -> List[Opportunity]:
        wanted = set(self._watchlists[user_id])
        return [row for row in self._opportunities.values() if row.id in wanted]

    def create_action(self, opportunity_id: str, owner_id: str, summary: str, due_date: str) -> ActionItem:
        if not self.has_opportunity(opportunity_id):
            raise KeyError(f"Unknown opportunity id: {opportunity_id}")
        action = ActionItem(
            id=str(uuid4()),
            opportunity_id=opportunity_id,
            owner_id=owner_id,
            summary=summary,
            due_date=due_date,
        )
        self._actions[action.id] = action
        return action

    def has_opportunity(self, opportunity_id: str) -> bool:
        return any(row.id == opportunity_id for row in self._opportunities.values())

    def list_actions(self, owner_id: str) -> List[ActionItem]:
        return [item for item in self._actions.values() if item.owner_id == owner_id]

    def add_ingestion_run(self, trace_id: str, ingested_count: int, rejected_count: int, errors: List[dict]) -> None:
        self._ingestion_runs.append(
            {
                "trace_id": trace_id,
                "ingested_count": ingested_count,
                "rejected_count": rejected_count,
                "errors": errors,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def list_ingestion_runs(self) -> List[dict]:
        return list(reversed(self._ingestion_runs[-20:]))

    def dashboard_summary(self) -> dict:
        total = len(self._opportunities)
        verified = sum(1 for row in self._opportunities.values() if row.verification_status == "verified")
        rejected = sum(1 for row in self._opportunities.values() if row.verification_status == "rejected")
        pending = total - verified - rejected
        by_domain: Dict[str, int] = defaultdict(int)
        for row in self._opportunities.values():
            by_domain[row.domain] += 1
        return {
            "total": total,
            "verified": verified,
            "rejected": rejected,
            "pending": pending,
            "by_domain": dict(by_domain),
        }

    def snapshot(self) -> dict:
        return {
            "opportunities": [asdict(row) for row in self._opportunities.values()],
            "ingestion_runs": self.list_ingestion_runs(),
        }

    def list_grant_sources(self, user_id: str = "global") -> List[GrantSource]:
        rows = self._grant_sources_by_user.get(user_id)
        if rows is None:
            rows = {source.id: source for source in DEFAULT_GRANT_SOURCES}
            self._grant_sources_by_user[user_id] = rows
        return list(rows.values())

    def upsert_grant_source(self, source: GrantSource, user_id: str = "global") -> GrantSource:
        self.list_grant_sources(user_id=user_id)
        self._grant_sources_by_user[user_id][source.id] = source
        return source

    def delete_grant_source(self, source_id: str, user_id: str = "global") -> None:
        self.list_grant_sources(user_id=user_id)
        if source_id in self._grant_sources_by_user[user_id]:
            del self._grant_sources_by_user[user_id][source_id]

    def list_grant_source_quality(self, user_id: str = "global") -> dict[str, dict]:
        return dict(self._grant_source_quality_by_user.get(user_id, {}))

    def upsert_grant_source_quality(self, user_id: str, source_id: str, metrics: dict) -> None:
        self._grant_source_quality_by_user.setdefault(user_id, {})[source_id] = json.loads(json.dumps(metrics))

    def get_grant_source_memory(self, user_id: str, source_id: str) -> dict | None:
        return self._grant_source_memory_by_user.get(user_id, {}).get(source_id)

    def upsert_grant_source_memory(self, user_id: str, source_id: str, memory: dict) -> None:
        self._grant_source_memory_by_user.setdefault(user_id, {})[source_id] = json.loads(json.dumps(memory))

    def get_grant_source_api_config(self, user_id: str, source_id: str) -> dict | None:
        return self._grant_source_api_config_by_user.get(user_id, {}).get(source_id)

    def upsert_grant_source_api_config(self, user_id: str, source_id: str, config: dict) -> None:
        self._grant_source_api_config_by_user.setdefault(user_id, {})[source_id] = json.loads(json.dumps(config))

    def get_grant_scan_schedule(self, user_id: str = "global") -> str:
        return self._grant_scan_schedule_by_user.get(user_id, "daily")

    def set_grant_scan_schedule(self, frequency: str, user_id: str = "global") -> None:
        self._grant_scan_schedule_by_user[user_id] = frequency

    def add_grant_scan_results(self, results: List[GrantScanResult], user_id: str = "global") -> None:
        rows = self._grant_scan_results_by_user.setdefault(user_id, [])
        existing = {f"{item.source_id}|{item.title}|{item.due_date}": item for item in rows}
        for item in results:
            key = f"{item.source_id}|{item.title}|{item.due_date}"
            if key in existing:
                existing_item = existing[key]
                existing_item.scanned_at = item.scanned_at
                existing_item.match_score = item.match_score
                existing_item.eligible = item.eligible
                existing_item.eligibility_reason = item.eligibility_reason
                existing_item.recommended = item.recommended
                existing_item.deadline_soon = item.deadline_soon
            else:
                rows.append(item)
        self._grant_scan_results_by_user[user_id] = rows[-500:]

    def replace_grant_scan_results(self, results: List[GrantScanResult], user_id: str = "global") -> None:
        self._grant_scan_results_by_user[user_id] = list(results)[-500:]

    def list_grant_scan_results(self, limit: int = 100, user_id: str = "global") -> List[GrantScanResult]:
        rows = self._grant_scan_results_by_user.setdefault(user_id, [])
        return list(reversed(rows[-limit:]))

    def update_grant_scan_result(self, user_id: str, result_id: str, **updates) -> None:
        rows = self._grant_scan_results_by_user.setdefault(user_id, [])
        for row in rows:
            if row.id == result_id:
                for key, value in updates.items():
                    if hasattr(row, key):
                        setattr(row, key, value)
                return

    def create_grant_draft(self, draft: GrantDraft) -> GrantDraft:
        self._grant_drafts[draft.id] = draft
        return draft

    def list_grant_drafts(self, user_id: str, grant_result_id: str) -> List[GrantDraft]:
        rows = [d for d in self._grant_drafts.values() if d.user_id == user_id and d.grant_result_id == grant_result_id]
        rows.sort(key=lambda row: row.version, reverse=True)
        return rows

    def add_grant_raw_records(self, user_id: str, run_id: str, records: List[dict]) -> None:
        self._grant_raw_records[(user_id, run_id)] = list(records)

    def list_grant_raw_records(self, user_id: str, run_id: str) -> List[dict]:
        return list(self._grant_raw_records.get((user_id, run_id), []))

    def upsert_grant_normalized_records(self, user_id: str, run_id: str, records: List[dict]) -> None:
        self._grant_normalized_records[(user_id, run_id)] = list(records)

    def list_grant_normalized_records(self, user_id: str, run_id: str) -> List[dict]:
        return list(self._grant_normalized_records.get((user_id, run_id), []))

    def add_grant_match_candidates(self, user_id: str, run_id: str, records: List[dict]) -> None:
        self._grant_match_candidates[(user_id, run_id)] = list(records)

    def list_grant_match_candidates(self, user_id: str, run_id: str) -> List[dict]:
        return list(self._grant_match_candidates.get((user_id, run_id), []))

    def add_grant_ai_assessments(self, user_id: str, run_id: str, records: List[dict]) -> None:
        self._grant_ai_assessments[(user_id, run_id)] = list(records)

    def list_grant_ai_assessments(self, user_id: str, run_id: str) -> List[dict]:
        return list(self._grant_ai_assessments.get((user_id, run_id), []))

    def add_grant_pipeline_runs(self, user_id: str, run_id: str, records: List[dict]) -> None:
        self._grant_pipeline_runs[(user_id, run_id)] = json.loads(json.dumps(records))

    def list_grant_pipeline_runs(self, user_id: str, run_id: str) -> List[dict]:
        return json.loads(json.dumps(self._grant_pipeline_runs.get((user_id, run_id), [])))

    def get_ai_cache(self, stage: str, content_hash: str) -> dict | None:
        value = self._ai_cache.get((stage, content_hash))
        return json.loads(json.dumps(value)) if value is not None else None

    def set_ai_cache(self, stage: str, content_hash: str, result: dict) -> None:
        self._ai_cache[(stage, content_hash)] = json.loads(json.dumps(result))

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)

    def upsert_user_profile(self, profile: UserProfile) -> UserProfile:
        self._profiles[profile.user_id] = profile
        return profile

    def enqueue_job(self, job: JobRecord) -> JobRecord:
        self._jobs[job.id] = job
        return job

    def update_job(self, job_id: str, **updates) -> None:
        current = self._jobs.get(job_id)
        if not current:
            return
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)

    def list_jobs(self, user_id: str, vertical: str = "", limit: int = 100) -> List[JobRecord]:
        rows = [job for job in self._jobs.values() if job.user_id == user_id]
        if vertical:
            rows = [job for job in rows if job.vertical == vertical]
        rows.sort(key=lambda row: row.scheduled_at, reverse=True)
        return rows[:limit]

    def list_due_jobs(self, current_time: str) -> List[JobRecord]:
        rows = []
        for job in self._jobs.values():
            if job.status == "queued" and job.scheduled_at <= current_time:
                rows.append(job)
            if job.status == "failed" and job.next_retry_at and job.next_retry_at <= current_time and job.attempts < job.max_attempts:
                rows.append(job)
        return rows

    def add_notification(self, item: NotificationItem) -> NotificationItem:
        self._notifications[item.id] = item
        return item

    def list_notifications(self, user_id: str, unread_only: bool = False, limit: int = 100) -> List[NotificationItem]:
        rows = [row for row in self._notifications.values() if row.user_id == user_id]
        if unread_only:
            rows = [row for row in rows if not row.is_read]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows[:limit]

    def mark_notification_read(self, user_id: str, notification_id: str) -> None:
        row = self._notifications.get(notification_id)
        if row and row.user_id == user_id:
            row.is_read = True
