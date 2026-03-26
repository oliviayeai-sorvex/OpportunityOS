from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from models.entities import JobRecord, NotificationItem, UserProfile
from models.repository_protocol import OpportunityRepository


class PlatformService:
    def __init__(self, repository: OpportunityRepository) -> None:
        self._repository = repository

    def _default_profile(self, user_id: str, email: str) -> UserProfile:
        return UserProfile(
            user_id=user_id,
            email=email,
            name="",
            organisation="",
            company_name="",
            abn="",
            anzsic_code="",
            business_stage="early",
            headcount=1,
            revenue=0,
            goals_json='[]',
            state_territory="NSW",
            business_objectives="",
            company_size="small",
            interest_industries='["technology"]',
            timezone="Australia/Sydney",
            notification_preferences='{"email": true, "in_app": true}',
            active_verticals='["grants"]',
            billing_plan="free",
            digest_time="07:00",
            digest_enabled_verticals='{"grants": true}',
        )

    def get_or_create_profile(self, user_id: str, email: str) -> UserProfile:
        profile = self._repository.get_user_profile(user_id)
        if profile is None:
            profile = self._default_profile(user_id, email)
            self._repository.upsert_user_profile(profile)
        return profile

    def _json_field(self, value: object, current_value: str) -> str:
        if value is None:
            return current_value
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return current_value

    def update_profile(self, user_id: str, email: str, updates: dict) -> UserProfile:
        current = self.get_or_create_profile(user_id, email)
        digest_enabled = updates.get("digest_enabled_verticals", updates.get("digest_verticals"))
        merged = UserProfile(
            user_id=user_id,
            email=email,
            name=updates.get("name", current.name),
            organisation=updates.get("organisation", current.organisation),
            company_name=updates.get("company_name", current.company_name),
            abn=updates.get("abn", current.abn),
            anzsic_code=updates.get("anzsic_code", current.anzsic_code),
            business_stage=updates.get("business_stage", current.business_stage),
            headcount=int(updates.get("headcount", current.headcount)),
            revenue=int(updates.get("revenue", current.revenue)),
            goals_json=self._json_field(
                updates.get("goals"),
                current.goals_json,
            ),
            state_territory=updates.get("state_territory", current.state_territory),
            business_objectives=updates.get("business_objectives", current.business_objectives),
            company_size=updates.get("company_size", current.company_size),
            interest_industries=self._json_field(
                updates.get("interest_industries"),
                current.interest_industries,
            ),
            timezone=updates.get("timezone", current.timezone),
            notification_preferences=self._json_field(
                updates.get("notification_preferences"),
                current.notification_preferences,
            ),
            active_verticals=self._json_field(
                updates.get("active_verticals"),
                current.active_verticals,
            ),
            billing_plan=updates.get("billing_plan", current.billing_plan),
            digest_time=updates.get("digest_time", current.digest_time),
            digest_enabled_verticals=self._json_field(
                digest_enabled,
                current.digest_enabled_verticals,
            ),
        )
        return self._repository.upsert_user_profile(merged)

    def profile_completeness(self, profile: UserProfile) -> dict:
        required = {
            "company_name": profile.company_name.strip(),
            "abn": profile.abn.strip(),
            "anzsic_code": profile.anzsic_code.strip(),
            "business_stage": profile.business_stage.strip(),
            "headcount": str(profile.headcount).strip(),
            "revenue": str(profile.revenue).strip(),
            "state_territory": profile.state_territory.strip(),
            "goals_json": profile.goals_json.strip(),
            "business_objectives": profile.business_objectives.strip(),
        }
        missing = [field for field, value in required.items() if not value]
        score = int(((len(required) - len(missing)) / len(required)) * 100)
        return {
            "score": score,
            "is_complete": not missing,
            "missing_fields": missing,
        }

    def queue_job(self, user_id: str, vertical: str, job_type: str, scheduled_at: str | None = None) -> JobRecord:
        if scheduled_at is None:
            scheduled_at = datetime.now(timezone.utc).isoformat()
        job = JobRecord(
            id=str(uuid4()),
            user_id=user_id,
            vertical=vertical,
            job_type=job_type,
            status="queued",
            scheduled_at=scheduled_at,
            started_at="",
            completed_at="",
            attempts=0,
            max_attempts=3,
            next_retry_at="",
            error_message="",
        )
        return self._repository.enqueue_job(job)

    def run_due_jobs(self) -> dict:
        now = datetime.now(timezone.utc)
        due = self._repository.list_due_jobs(now.isoformat())
        processed = 0
        for job in due:
            processed += 1
            self._repository.update_job(job.id, status="running", started_at=now.isoformat(), attempts=job.attempts + 1)
            if job.attempts >= 1 and job.job_type == "digest":
                next_retry = (now + timedelta(minutes=5 * (2 ** min(job.attempts, 5)))).isoformat()
                self._repository.update_job(
                    job.id,
                    status="failed",
                    next_retry_at=next_retry,
                    error_message="simulated transient digest provider error",
                )
                self._repository.add_notification(
                    NotificationItem(
                        id=str(uuid4()),
                        user_id=job.user_id,
                        level="warning",
                        message=f"Job failed for {job.vertical}; retry scheduled",
                        is_read=False,
                        created_at=now.isoformat(),
                    )
                )
                continue

            self._repository.update_job(job.id, status="completed", completed_at=now.isoformat(), error_message="", next_retry_at="")
            self._repository.add_notification(
                NotificationItem(
                    id=str(uuid4()),
                    user_id=job.user_id,
                    level="info",
                    message=f"Job completed for {job.vertical}",
                    is_read=False,
                    created_at=now.isoformat(),
                )
            )
        return {"processed": processed}

    def home_summary(self, user_id: str) -> dict:
        jobs = self._repository.list_jobs(user_id=user_id, limit=200)
        by_vertical: dict[str, dict] = {}
        for job in jobs:
            bucket = by_vertical.setdefault(job.vertical, {"count": 0, "last_run": "", "next_run": ""})
            bucket["count"] += 1
            if job.completed_at and (not bucket["last_run"] or job.completed_at > bucket["last_run"]):
                bucket["last_run"] = job.completed_at
            if job.status in {"queued", "failed"} and (not bucket["next_run"] or job.scheduled_at < bucket["next_run"]):
                bucket["next_run"] = job.scheduled_at
        recent = [job.__dict__ for job in jobs[:10]]
        unread = len(self._repository.list_notifications(user_id=user_id, unread_only=True, limit=500))
        return {"vertical_summary": by_vertical, "recent_activity": recent, "unread_notifications": unread}

    def notifications(self, user_id: str, unread_only: bool = False) -> list[dict]:
        return [row.__dict__ for row in self._repository.list_notifications(user_id=user_id, unread_only=unread_only, limit=200)]

    def mark_notification_read(self, user_id: str, notification_id: str) -> None:
        self._repository.mark_notification_read(user_id=user_id, notification_id=notification_id)

    def search(self, user_id: str, query: str, opportunities: list[dict], jobs: list[JobRecord]) -> dict:
        needle = query.strip().lower()
        opp_matches = [item for item in opportunities if needle in item.get("title", "").lower()]
        job_matches = [job.__dict__ for job in jobs if needle in job.vertical.lower() or needle in job.job_type.lower()]
        return {"opportunities": opp_matches[:50], "jobs": job_matches[:50]}
