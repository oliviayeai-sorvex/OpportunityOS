from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal

RiskLevel = Literal["low", "medium", "high"]
VerificationStatus = Literal["pending", "verified", "rejected"]
ScanFrequency = Literal["daily", "weekly"]


@dataclass
class ScoreCard:
    total: float
    factors: Dict[str, float]
    confidence: float


@dataclass
class Opportunity:
    external_id: str
    source: str
    domain: str
    title: str
    value_estimate: float
    risk_level: RiskLevel
    captured_at: datetime
    id: str = ""
    score_card: ScoreCard | None = None
    verification_status: VerificationStatus = "pending"


@dataclass
class VerificationEvent:
    opportunity_id: str
    actor_id: str
    status: VerificationStatus
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ActionItem:
    id: str
    opportunity_id: str
    owner_id: str
    summary: str
    due_date: str
    status: Literal["open", "done"] = "open"


@dataclass
class FilterCriteria:
    domains: List[str] = field(default_factory=list)
    min_score: float = 0.0
    max_risk: RiskLevel | None = None
    min_value_estimate: float = 0.0
    limit: int = 100
    offset: int = 0


@dataclass
class GrantSource:
    id: str
    name: str
    url: str
    access: str
    active: bool = True
    quality_score: int = 0
    heuristic_score: int = 0
    conversion_rate: float = 0.0
    quality_label: str = "Unrated"
    ai_enabled: bool = True


@dataclass
class GrantScanResult:
    id: str
    source_id: str
    source_name: str
    title: str
    published_at: str = ""
    location: str = ""
    industry: str = ""
    details: str = ""
    funder: str = ""
    program: str = ""
    max_amount: str = ""
    eligibility_criteria: str = ""
    open_date: str = ""
    close_date: str = ""
    application_url: str = ""
    target_sectors: str = ""
    url: str = ""
    due_date: str = ""
    grant_amount: str = ""
    match_score: int = 0
    eligible: bool = False
    eligibility_reason: str = ""
    recommended: bool = False
    deadline_soon: bool = False
    manual_check_needed: bool = False
    workflow_status: str = "New"
    notes: str = ""
    contact_names: str = ""
    reference_numbers: str = ""
    submission_date: str = ""
    outcome: str = "Pending"
    status: str = "new"
    scanned_at: str = ""


@dataclass
class UserProfile:
    user_id: str
    email: str
    name: str
    organisation: str
    company_name: str
    abn: str
    anzsic_code: str
    business_stage: str
    headcount: int
    revenue: int
    goals_json: str
    state_territory: str
    business_objectives: str
    company_size: str
    interest_industries: str
    timezone: str
    notification_preferences: str
    active_verticals: str
    billing_plan: str
    digest_time: str
    digest_enabled_verticals: str


@dataclass
class JobRecord:
    id: str
    user_id: str
    vertical: str
    job_type: str
    status: str
    scheduled_at: str
    started_at: str
    completed_at: str
    attempts: int
    max_attempts: int
    next_retry_at: str
    error_message: str


@dataclass
class NotificationItem:
    id: str
    user_id: str
    level: str
    message: str
    is_read: bool
    created_at: str


@dataclass
class GrantDraft:
    id: str
    grant_result_id: str
    user_id: str
    version: int
    content: str
    created_at: str


@dataclass
class ExtractedGrant:
    title: str
    source_url: str
    detail_url: str
    provider: str
    provider_raw: str
    deadline_raw: str
    deadline_iso: str
    amount_raw: str
    amount_display: str
    eligibility_summary: str
    industry: List[str]
    location_display: str
    criteria_industries: List[str]
    criteria_locations: List[str]
    criteria_business_size: str
    criteria_must_have: List[str]
    criteria_not_allowed: List[str]
    relevant_text: str
    raw_text: str
    field_confidence: Dict[str, float]
    evidence: Dict[str, str | List[str]]
    fetch_method: str
    content_hash: str


@dataclass
class NormalizedGrant:
    title: str
    source: str
    source_url: str
    detail_url: str
    provider: str
    provider_raw: str
    deadline: str
    deadline_iso: str
    amount: str
    amount_display: str
    raw_text: str
    eligibility_summary: str
    industry: List[str]
    location_display: str
    criteria_industries: List[str]
    criteria_locations: List[str]
    criteria_business_size: str
    criteria_must_have: List[str]
    criteria_not_allowed: List[str]
    relevant_text: str
    field_confidence: Dict[str, float]
    evidence: Dict[str, str | List[str]]
