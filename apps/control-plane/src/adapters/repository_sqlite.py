from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import List
from uuid import uuid4

from models.entities import (
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

DEFAULT_GRANT_SOURCES = [
    ("src-business-gov-au", "business.gov.au Grants Finder", "https://business.gov.au/grants-and-programs", "Public, scrapeable", 1),
    ("src-grantconnect", "GrantConnect (Federal)", "https://www.grants.gov.au/Go/List", "Public API available", 1),
    ("src-nsw-grants", "NSW Government Grants", "https://www.nsw.gov.au/grants-and-funding", "Public", 1),
    ("src-arena", "ARENA (clean energy)", "https://arena.gov.au/funding", "Public", 1),
    ("src-business-vic", "State: Business Victoria", "https://business.vic.gov.au/grants-and-programs?filter=%7B%22status%22%3A%5B%22opening+soon%22%2C%22open%22%2C%22ongoing%22%5D%7D", "Public", 1),
    ("src-business-qld", "State: Business Queensland", "https://www.business.qld.gov.au/running-business/support-services/financial/grants/schedule", "Public", 1),
    ("src-csiro", "CSIRO", "https://www.csiro.au/en/work-with-us/funding-programs/SME/SME-Connect-programs", "Public", 1),
    ("src-medtech-grants", "MedTech Grants", "https://help.grants.gov.au/getting-started-with-grantconnect/information-made-easy/current-opportunities/", "Curated programs", 1),
]


class SQLiteOpportunityRepository:
    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    id TEXT PRIMARY KEY,
                    external_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    title TEXT NOT NULL,
                    value_estimate REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    score_total REAL,
                    score_confidence REAL,
                    score_factors TEXT,
                    verification_status TEXT NOT NULL DEFAULT 'pending',
                    UNIQUE(external_id, source)
                );

                CREATE TABLE IF NOT EXISTS verification_events (
                    id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS watchlist_items (
                    user_id TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL,
                    PRIMARY KEY(user_id, opportunity_id)
                );

                CREATE TABLE IF NOT EXISTS action_items (
                    id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    ingested_count INTEGER NOT NULL,
                    rejected_count INTEGER NOT NULL,
                    errors_json TEXT NOT NULL,
                    finished_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_sources (
                    user_id TEXT NOT NULL DEFAULT 'global',
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    access TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                
                CREATE TABLE IF NOT EXISTS grant_sources_v2 (
                    user_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    access TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, id)
                );

                CREATE TABLE IF NOT EXISTS grant_source_quality (
                    user_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    heuristic_score INTEGER NOT NULL DEFAULT 0,
                    conversion_rate REAL NOT NULL DEFAULT 0,
                    items_extracted INTEGER NOT NULL DEFAULT 0,
                    passed_heuristic INTEGER NOT NULL DEFAULT 0,
                    passed_rules INTEGER NOT NULL DEFAULT 0,
                    passed_ai INTEGER NOT NULL DEFAULT 0,
                    quality_score INTEGER NOT NULL DEFAULT 0,
                    quality_label TEXT NOT NULL DEFAULT 'Unrated',
                    ai_enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, source_id)
                );

                CREATE TABLE IF NOT EXISTS grant_source_memory (
                    user_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    link_pattern TEXT NOT NULL DEFAULT '',
                    pagination_pattern TEXT NOT NULL DEFAULT '',
                    last_success_rate REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, source_id)
                );

                CREATE TABLE IF NOT EXISTS grant_source_api_config (
                    user_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL DEFAULT 'GET',
                    params_json TEXT NOT NULL DEFAULT '{}',
                    pagination_json TEXT NOT NULL DEFAULT '{}',
                    confidence REAL NOT NULL DEFAULT 0,
                    last_verified TEXT NOT NULL,
                    PRIMARY KEY (user_id, source_id)
                );

                CREATE TABLE IF NOT EXISTS grant_scan_config (
                    user_id TEXT PRIMARY KEY,
                    frequency TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_scan_results (
                    user_id TEXT NOT NULL DEFAULT 'global',
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    industry TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '',
                    funder TEXT NOT NULL DEFAULT '',
                    program TEXT NOT NULL DEFAULT '',
                    max_amount TEXT NOT NULL DEFAULT '',
                    eligibility_criteria TEXT NOT NULL DEFAULT '',
                    open_date TEXT NOT NULL DEFAULT '',
                    close_date TEXT NOT NULL DEFAULT '',
                    application_url TEXT NOT NULL DEFAULT '',
                    target_sectors TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL,
                    due_date TEXT NOT NULL DEFAULT '',
                    grant_amount TEXT NOT NULL DEFAULT '',
                    match_score INTEGER NOT NULL DEFAULT 0,
                    eligible INTEGER NOT NULL DEFAULT 0,
                    eligibility_reason TEXT NOT NULL DEFAULT '',
                    recommended INTEGER NOT NULL DEFAULT 0,
                    deadline_soon INTEGER NOT NULL DEFAULT 0,
                    manual_check_needed INTEGER NOT NULL DEFAULT 0,
                    workflow_status TEXT NOT NULL DEFAULT 'New',
                    contact_names TEXT NOT NULL DEFAULT '',
                    reference_numbers TEXT NOT NULL DEFAULT '',
                    submission_date TEXT NOT NULL DEFAULT '',
                    outcome TEXT NOT NULL DEFAULT 'Pending',
                    external_key TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    scanned_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    organisation TEXT NOT NULL,
                    company_name TEXT NOT NULL DEFAULT '',
                    abn TEXT NOT NULL DEFAULT '',
                    anzsic_code TEXT NOT NULL DEFAULT '',
                    business_stage TEXT NOT NULL DEFAULT 'early',
                    headcount INTEGER NOT NULL DEFAULT 1,
                    revenue INTEGER NOT NULL DEFAULT 0,
                    goals_json TEXT NOT NULL DEFAULT '[]',
                    state_territory TEXT NOT NULL DEFAULT 'NSW',
                    business_objectives TEXT NOT NULL DEFAULT '',
                    company_size TEXT NOT NULL DEFAULT 'small',
                    interest_industries TEXT NOT NULL DEFAULT '["technology"]',
                    timezone TEXT NOT NULL,
                    notification_preferences TEXT NOT NULL,
                    active_verticals TEXT NOT NULL,
                    billing_plan TEXT NOT NULL,
                    digest_time TEXT NOT NULL,
                    digest_enabled_verticals TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    vertical TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    next_retry_at TEXT NOT NULL,
                    error_message TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_drafts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    grant_result_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_raw_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    url TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_normalized (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    grant_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    industry_json TEXT NOT NULL,
                    location TEXT NOT NULL,
                    min_size INTEGER NOT NULL,
                    max_size INTEGER NOT NULL,
                    funding_amount INTEGER NOT NULL,
                    deadline TEXT NOT NULL,
                    eligibility_text TEXT NOT NULL,
                    description TEXT NOT NULL,
                    url TEXT NOT NULL,
                    normalized_json TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_match_candidates (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    normalized_id TEXT NOT NULL,
                    rule_status TEXT NOT NULL,
                    rule_score INTEGER NOT NULL,
                    rule_reasons_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_ai_assessments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    normalized_id TEXT NOT NULL,
                    eligibility TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    key_reasons_json TEXT NOT NULL,
                    missing_requirements_json TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grant_pipeline_runs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    registry_status TEXT NOT NULL DEFAULT '',
                    site TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT '',
                    fetch_status TEXT NOT NULL DEFAULT '',
                    content_length INTEGER NOT NULL DEFAULT 0,
                    page_type TEXT NOT NULL DEFAULT '',
                    links_found INTEGER NOT NULL DEFAULT 0,
                    links_after_filter INTEGER NOT NULL DEFAULT 0,
                    final_selected_count INTEGER NOT NULL DEFAULT 0,
                    detail_pages_processed INTEGER NOT NULL DEFAULT 0,
                    successful_extractions INTEGER NOT NULL DEFAULT 0,
                    normalized_count INTEGER NOT NULL DEFAULT 0,
                    deduplicated_count INTEGER NOT NULL DEFAULT 0,
                    heuristic_rejected_count INTEGER NOT NULL DEFAULT 0,
                    rule_rejected_count INTEGER NOT NULL DEFAULT 0,
                    cache_hit_count INTEGER NOT NULL DEFAULT 0,
                    ai_called_count INTEGER NOT NULL DEFAULT 0,
                    failed_step TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    raw_preview TEXT NOT NULL DEFAULT '',
                    sample_output_json TEXT NOT NULL DEFAULT '[]',
                    extracted_links_json TEXT NOT NULL DEFAULT '[]',
                    filtered_links_json TEXT NOT NULL DEFAULT '[]',
                    selected_links_json TEXT NOT NULL DEFAULT '[]',
                    detail_urls_json TEXT NOT NULL DEFAULT '[]',
                    top_patterns_json TEXT NOT NULL DEFAULT '[]',
                    pagination_chain_json TEXT NOT NULL DEFAULT '[]',
                    config_json TEXT NOT NULL DEFAULT '{}',
                    api_config_json TEXT NOT NULL DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS ai_cache (
                    stage TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(stage, content_hash)
                );

                CREATE INDEX IF NOT EXISTS idx_opportunities_filter ON opportunities(domain, risk_level, value_estimate, score_total);
                CREATE INDEX IF NOT EXISTS idx_actions_owner ON action_items(owner_id, due_date);
                CREATE INDEX IF NOT EXISTS idx_grant_scan_results_time ON grant_scan_results(scanned_at);
                CREATE INDEX IF NOT EXISTS idx_jobs_user_vertical ON jobs(user_id, vertical, scheduled_at);
                CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_grant_raw_run ON grant_raw_records(user_id, run_id, source_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_grant_norm_dedupe ON grant_normalized(user_id, dedupe_key);
                CREATE INDEX IF NOT EXISTS idx_grant_norm_run ON grant_normalized(user_id, run_id);
                CREATE INDEX IF NOT EXISTS idx_grant_candidate_run ON grant_match_candidates(user_id, run_id);
                CREATE INDEX IF NOT EXISTS idx_grant_ai_run ON grant_ai_assessments(user_id, run_id);
                CREATE INDEX IF NOT EXISTS idx_grant_pipeline_run ON grant_pipeline_runs(user_id, run_id, source_id);
                CREATE INDEX IF NOT EXISTS idx_grant_sources_v2_user ON grant_sources_v2(user_id, active, name);
                CREATE INDEX IF NOT EXISTS idx_grant_source_quality_user ON grant_source_quality(user_id, quality_score DESC);
                CREATE INDEX IF NOT EXISTS idx_grant_source_memory_user ON grant_source_memory(user_id, source_id);
                CREATE INDEX IF NOT EXISTS idx_grant_source_api_user ON grant_source_api_config(user_id, source_id);
                CREATE INDEX IF NOT EXISTS idx_ai_cache_created ON ai_cache(created_at);
                """
            )
            # Backward-compatible migration for local DBs created before per-user grant tables.
            grant_source_cols = [row["name"] for row in self._conn.execute("PRAGMA table_info(grant_sources)").fetchall()]
            if "user_id" not in grant_source_cols:
                self._conn.execute("ALTER TABLE grant_sources ADD COLUMN user_id TEXT NOT NULL DEFAULT 'global'")

            grant_scan_result_cols = [row["name"] for row in self._conn.execute("PRAGMA table_info(grant_scan_results)").fetchall()]
            if "user_id" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN user_id TEXT NOT NULL DEFAULT 'global'")
            if "title" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN title TEXT NOT NULL DEFAULT ''")
            if "published_at" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN published_at TEXT NOT NULL DEFAULT ''")
            if "location" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN location TEXT NOT NULL DEFAULT ''")
            if "industry" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN industry TEXT NOT NULL DEFAULT ''")
            if "details" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN details TEXT NOT NULL DEFAULT ''")
            if "funder" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN funder TEXT NOT NULL DEFAULT ''")
            if "program" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN program TEXT NOT NULL DEFAULT ''")
            if "max_amount" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN max_amount TEXT NOT NULL DEFAULT ''")
            if "eligibility_criteria" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN eligibility_criteria TEXT NOT NULL DEFAULT ''")
            if "open_date" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN open_date TEXT NOT NULL DEFAULT ''")
            if "close_date" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN close_date TEXT NOT NULL DEFAULT ''")
            if "application_url" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN application_url TEXT NOT NULL DEFAULT ''")
            if "target_sectors" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN target_sectors TEXT NOT NULL DEFAULT ''")
            if "due_date" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN due_date TEXT NOT NULL DEFAULT ''")
            if "grant_amount" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN grant_amount TEXT NOT NULL DEFAULT ''")
            if "match_score" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN match_score INTEGER NOT NULL DEFAULT 0")
            if "eligible" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN eligible INTEGER NOT NULL DEFAULT 0")
            if "eligibility_reason" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN eligibility_reason TEXT NOT NULL DEFAULT ''")
            if "recommended" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN recommended INTEGER NOT NULL DEFAULT 0")
            if "deadline_soon" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN deadline_soon INTEGER NOT NULL DEFAULT 0")
            if "manual_check_needed" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN manual_check_needed INTEGER NOT NULL DEFAULT 0")
            if "workflow_status" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN workflow_status TEXT NOT NULL DEFAULT 'New'")
            if "contact_names" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN contact_names TEXT NOT NULL DEFAULT ''")
            if "reference_numbers" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN reference_numbers TEXT NOT NULL DEFAULT ''")
            if "submission_date" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN submission_date TEXT NOT NULL DEFAULT ''")
            if "outcome" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN outcome TEXT NOT NULL DEFAULT 'Pending'")
            if "external_key" not in grant_scan_result_cols:
                self._conn.execute("ALTER TABLE grant_scan_results ADD COLUMN external_key TEXT NOT NULL DEFAULT ''")

            grant_scan_cfg_cols = [row["name"] for row in self._conn.execute("PRAGMA table_info(grant_scan_config)").fetchall()]
            if grant_scan_cfg_cols and "user_id" not in grant_scan_cfg_cols:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS grant_scan_config_v2 (
                        user_id TEXT PRIMARY KEY,
                        frequency TEXT NOT NULL
                    )
                    """
                )
                row = self._conn.execute("SELECT frequency FROM grant_scan_config LIMIT 1").fetchone()
                freq = row["frequency"] if row else "daily"
                self._conn.execute(
                    "INSERT OR IGNORE INTO grant_scan_config_v2(user_id, frequency) VALUES('global', ?)",
                    (freq,),
                )
                self._conn.execute("DROP TABLE grant_scan_config")
                self._conn.execute("ALTER TABLE grant_scan_config_v2 RENAME TO grant_scan_config")

            user_profile_cols = [row["name"] for row in self._conn.execute("PRAGMA table_info(user_profiles)").fetchall()]
            if user_profile_cols:
                if "company_name" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN company_name TEXT NOT NULL DEFAULT ''")
                if "abn" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN abn TEXT NOT NULL DEFAULT ''")
                if "anzsic_code" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN anzsic_code TEXT NOT NULL DEFAULT ''")
                if "business_stage" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN business_stage TEXT NOT NULL DEFAULT 'early'")
                if "headcount" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN headcount INTEGER NOT NULL DEFAULT 1")
                if "revenue" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN revenue INTEGER NOT NULL DEFAULT 0")
                if "goals_json" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN goals_json TEXT NOT NULL DEFAULT '[]'")
                if "state_territory" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN state_territory TEXT NOT NULL DEFAULT 'NSW'")
                if "business_objectives" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN business_objectives TEXT NOT NULL DEFAULT ''")
                if "company_size" not in user_profile_cols:
                    self._conn.execute("ALTER TABLE user_profiles ADD COLUMN company_size TEXT NOT NULL DEFAULT 'small'")
                if "interest_industries" not in user_profile_cols:
                    self._conn.execute(
                        "ALTER TABLE user_profiles ADD COLUMN interest_industries TEXT NOT NULL DEFAULT '[\"technology\"]'"
                    )

            self._conn.execute(
                """
                UPDATE grant_scan_results
                SET external_key = source_id || '|' || title || '|' || due_date
                WHERE COALESCE(external_key, '') = ''
                """
            )
            self._conn.execute(
                """
                DELETE FROM grant_scan_results
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM grant_scan_results
                    GROUP BY user_id, external_key
                )
                """
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_grant_scan_unique ON grant_scan_results(user_id, external_key)"
            )

            desired_global_ids = {row[0] for row in DEFAULT_GRANT_SOURCES}
            for row in DEFAULT_GRANT_SOURCES:
                self._conn.execute(
                    """
                    INSERT INTO grant_sources(user_id, id, name, url, access, active) VALUES('global',?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        user_id=excluded.user_id,
                        name=excluded.name,
                        url=excluded.url,
                        access=excluded.access,
                        active=excluded.active
                    """,
                    row[0:4] + (row[4],),
                )
                self._conn.execute(
                    """
                    INSERT INTO grant_sources_v2(user_id, id, name, url, access, active) VALUES('global',?,?,?,?,?)
                    ON CONFLICT(user_id, id) DO UPDATE SET
                        name=excluded.name,
                        url=excluded.url,
                        access=excluded.access,
                        active=excluded.active
                    """,
                    row[0:4] + (row[4],),
                )
            # Remove deprecated defaults from global source set.
            placeholders = ",".join("?" for _ in desired_global_ids)
            self._conn.execute(
                f"DELETE FROM grant_sources_v2 WHERE user_id='global' AND id NOT IN ({placeholders})",
                tuple(desired_global_ids),
            )
            # One-time migration from legacy grant_sources to v2 keyed by (user_id, id).
            legacy_count = self._conn.execute("SELECT COUNT(*) AS c FROM grant_sources").fetchone()["c"]
            v2_count = self._conn.execute("SELECT COUNT(*) AS c FROM grant_sources_v2").fetchone()["c"]
            if legacy_count > 0 and v2_count == 0:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO grant_sources_v2(user_id, id, name, url, access, active)
                    SELECT user_id, id, name, url, access, active
                    FROM grant_sources
                    """
                )
            self._conn.execute(
                "INSERT OR IGNORE INTO grant_scan_config(user_id, frequency) VALUES('global', 'daily')"
            )

    def _row_to_opp(self, row: sqlite3.Row) -> Opportunity:
        factors = {}
        if row["score_factors"]:
            factors = json.loads(row["score_factors"])
        score = None
        if row["score_total"] is not None:
            score = ScoreCard(total=row["score_total"], confidence=row["score_confidence"], factors=factors)

        return Opportunity(
            id=row["id"],
            external_id=row["external_id"],
            source=row["source"],
            domain=row["domain"],
            title=row["title"],
            value_estimate=row["value_estimate"],
            risk_level=row["risk_level"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            score_card=score,
            verification_status=row["verification_status"],
        )

    def upsert_opportunity(self, item: Opportunity) -> Opportunity:
        with self._lock, self._conn:
            existing = self._conn.execute(
                "SELECT id FROM opportunities WHERE external_id=? AND source=?",
                (item.external_id, item.source),
            ).fetchone()
            item.id = existing["id"] if existing else str(uuid4())
            self._conn.execute(
                """
                INSERT INTO opportunities(id, external_id, source, domain, title, value_estimate, risk_level, captured_at, verification_status)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(external_id, source) DO UPDATE SET
                    domain=excluded.domain,
                    title=excluded.title,
                    value_estimate=excluded.value_estimate,
                    risk_level=excluded.risk_level,
                    captured_at=excluded.captured_at
                """,
                (
                    item.id,
                    item.external_id,
                    item.source,
                    item.domain,
                    item.title,
                    item.value_estimate,
                    item.risk_level,
                    item.captured_at.isoformat(),
                    item.verification_status,
                ),
            )
        return item

    def list_opportunities(self, criteria: FilterCriteria) -> List[Opportunity]:
        clauses = ["value_estimate >= ?", "COALESCE(score_total, 0) >= ?"]
        params: list = [criteria.min_value_estimate, criteria.min_score]

        if criteria.domains:
            placeholders = ",".join(["?"] * len(criteria.domains))
            clauses.append(f"domain IN ({placeholders})")
            params.extend(criteria.domains)
        if criteria.max_risk:
            order = {"low": 0, "medium": 1, "high": 2}
            clauses.append("CASE risk_level WHEN 'low' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END <= ?")
            params.append(order[criteria.max_risk])

        params.extend([criteria.limit, criteria.offset])
        query = f"""
            SELECT * FROM opportunities
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(score_total, 0) DESC
            LIMIT ? OFFSET ?
        """
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_opp(row) for row in rows]

    def set_scorecard(self, opportunity_id: str, score_card: ScoreCard) -> None:
        with self._lock, self._conn:
            updated = self._conn.execute(
                "UPDATE opportunities SET score_total=?, score_confidence=?, score_factors=? WHERE id=?",
                (score_card.total, score_card.confidence, json.dumps(score_card.factors), opportunity_id),
            )
            if updated.rowcount == 0:
                raise KeyError(f"Unknown opportunity id: {opportunity_id}")

    def set_verification(self, event: VerificationEvent) -> None:
        with self._lock, self._conn:
            updated = self._conn.execute(
                "UPDATE opportunities SET verification_status=? WHERE id=?",
                (event.status, event.opportunity_id),
            )
            if updated.rowcount == 0:
                raise KeyError(f"Unknown opportunity id: {event.opportunity_id}")
            self._conn.execute(
                "INSERT INTO verification_events(id, opportunity_id, actor_id, status, reason, created_at) VALUES(?,?,?,?,?,?)",
                (str(uuid4()), event.opportunity_id, event.actor_id, event.status, event.reason, event.created_at.isoformat()),
            )

    def add_watchlist_item(self, user_id: str, opportunity_id: str) -> None:
        if not self.has_opportunity(opportunity_id):
            raise KeyError(f"Unknown opportunity id: {opportunity_id}")
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO watchlist_items(user_id, opportunity_id) VALUES(?,?)",
                (user_id, opportunity_id),
            )

    def get_watchlist(self, user_id: str) -> List[Opportunity]:
        rows = self._conn.execute(
            """
            SELECT o.* FROM opportunities o
            JOIN watchlist_items w ON w.opportunity_id = o.id
            WHERE w.user_id=?
            ORDER BY COALESCE(o.score_total, 0) DESC
            """,
            (user_id,),
        ).fetchall()
        return [self._row_to_opp(row) for row in rows]

    def create_action(self, opportunity_id: str, owner_id: str, summary: str, due_date: str) -> ActionItem:
        if not self.has_opportunity(opportunity_id):
            raise KeyError(f"Unknown opportunity id: {opportunity_id}")
        action = ActionItem(
            id=str(uuid4()),
            opportunity_id=opportunity_id,
            owner_id=owner_id,
            summary=summary,
            due_date=due_date,
            status="open",
        )
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO action_items(id, opportunity_id, owner_id, summary, due_date, status) VALUES(?,?,?,?,?,?)",
                (action.id, action.opportunity_id, action.owner_id, action.summary, action.due_date, action.status),
            )
        return action

    def has_opportunity(self, opportunity_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
        return row is not None

    def list_actions(self, owner_id: str) -> List[ActionItem]:
        rows = self._conn.execute(
            "SELECT * FROM action_items WHERE owner_id=? ORDER BY due_date ASC",
            (owner_id,),
        ).fetchall()
        return [
            ActionItem(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                owner_id=row["owner_id"],
                summary=row["summary"],
                due_date=row["due_date"],
                status=row["status"],
            )
            for row in rows
        ]

    def add_ingestion_run(self, trace_id: str, ingested_count: int, rejected_count: int, errors: List[dict]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO ingestion_runs(trace_id, ingested_count, rejected_count, errors_json, finished_at) VALUES(?,?,?,?,?)",
                (
                    trace_id,
                    ingested_count,
                    rejected_count,
                    json.dumps(errors),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_ingestion_runs(self) -> List[dict]:
        rows = self._conn.execute(
            "SELECT trace_id, ingested_count, rejected_count, errors_json, finished_at FROM ingestion_runs ORDER BY id DESC LIMIT 20"
        ).fetchall()
        return [
            {
                "trace_id": row["trace_id"],
                "ingested_count": row["ingested_count"],
                "rejected_count": row["rejected_count"],
                "errors": json.loads(row["errors_json"]),
                "finished_at": row["finished_at"],
            }
            for row in rows
        ]

    def dashboard_summary(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) AS c FROM opportunities").fetchone()["c"]
        verified = self._conn.execute("SELECT COUNT(*) AS c FROM opportunities WHERE verification_status='verified'").fetchone()["c"]
        rejected = self._conn.execute("SELECT COUNT(*) AS c FROM opportunities WHERE verification_status='rejected'").fetchone()["c"]
        pending = total - verified - rejected

        rows = self._conn.execute(
            "SELECT domain, COUNT(*) AS c FROM opportunities GROUP BY domain"
        ).fetchall()
        by_domain = {row["domain"]: row["c"] for row in rows}

        return {
            "total": total,
            "verified": verified,
            "rejected": rejected,
            "pending": pending,
            "by_domain": by_domain,
        }

    def list_grant_sources(self, user_id: str = "global") -> List[GrantSource]:
        rows = self._conn.execute(
            "SELECT id, name, url, access, active FROM grant_sources_v2 WHERE user_id=? ORDER BY name ASC",
            (user_id,),
        ).fetchall()
        if not rows and user_id != "global":
            rows = self._conn.execute(
                "SELECT id, name, url, access, active FROM grant_sources_v2 WHERE user_id='global' ORDER BY name ASC"
            ).fetchall()
        return [
            GrantSource(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                access=row["access"],
                active=bool(row["active"]),
            )
            for row in rows
        ]

    def upsert_grant_source(self, source: GrantSource, user_id: str = "global") -> GrantSource:
        with self._lock, self._conn:
            if user_id != "global":
                has_user_rows = self._conn.execute(
                    "SELECT 1 FROM grant_sources_v2 WHERE user_id=? LIMIT 1",
                    (user_id,),
                ).fetchone()
                if has_user_rows is None:
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO grant_sources_v2(user_id, id, name, url, access, active)
                        SELECT ?, id, name, url, access, active
                        FROM grant_sources_v2
                        WHERE user_id='global'
                        """,
                        (user_id,),
                    )
            self._conn.execute(
                """
                INSERT INTO grant_sources_v2(user_id, id, name, url, access, active) VALUES(?,?,?,?,?,?)
                ON CONFLICT(user_id, id) DO UPDATE SET
                    name=excluded.name,
                    url=excluded.url,
                    access=excluded.access,
                    active=excluded.active
                """,
                (user_id, source.id, source.name, source.url, source.access, 1 if source.active else 0),
            )
        return source

    def delete_grant_source(self, source_id: str, user_id: str = "global") -> None:
        with self._lock, self._conn:
            # If user has no custom source rows yet, materialize inherited global defaults first,
            # then remove the requested source from the user's own set.
            if user_id != "global":
                has_user_rows = self._conn.execute(
                    "SELECT 1 FROM grant_sources_v2 WHERE user_id=? LIMIT 1",
                    (user_id,),
                ).fetchone()
                if has_user_rows is None:
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO grant_sources_v2(user_id, id, name, url, access, active)
                        SELECT ?, id, name, url, access, active
                        FROM grant_sources_v2
                        WHERE user_id='global'
                        """,
                        (user_id,),
                    )
            self._conn.execute("DELETE FROM grant_sources_v2 WHERE id=? AND user_id=?", (source_id, user_id))

    def list_grant_source_quality(self, user_id: str = "global") -> dict[str, dict]:
        rows = self._conn.execute(
            """
            SELECT source_id, heuristic_score, conversion_rate, items_extracted, passed_heuristic, passed_rules,
                   passed_ai, quality_score, quality_label, ai_enabled, updated_at
            FROM grant_source_quality
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchall()
        return {
            row["source_id"]: {
                "heuristic_score": int(row["heuristic_score"]),
                "conversion_rate": float(row["conversion_rate"]),
                "items_extracted": int(row["items_extracted"]),
                "passed_heuristic": int(row["passed_heuristic"]),
                "passed_rules": int(row["passed_rules"]),
                "passed_ai": int(row["passed_ai"]),
                "quality_score": int(row["quality_score"]),
                "quality_label": row["quality_label"],
                "ai_enabled": bool(row["ai_enabled"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        }

    def upsert_grant_source_quality(self, user_id: str, source_id: str, metrics: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO grant_source_quality(
                    user_id, source_id, heuristic_score, conversion_rate, items_extracted, passed_heuristic,
                    passed_rules, passed_ai, quality_score, quality_label, ai_enabled, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id, source_id) DO UPDATE SET
                    heuristic_score=excluded.heuristic_score,
                    conversion_rate=excluded.conversion_rate,
                    items_extracted=excluded.items_extracted,
                    passed_heuristic=excluded.passed_heuristic,
                    passed_rules=excluded.passed_rules,
                    passed_ai=excluded.passed_ai,
                    quality_score=excluded.quality_score,
                    quality_label=excluded.quality_label,
                    ai_enabled=excluded.ai_enabled,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    source_id,
                    int(metrics.get("heuristic_score", 0)),
                    float(metrics.get("conversion_rate", 0.0)),
                    int(metrics.get("items_extracted", 0)),
                    int(metrics.get("passed_heuristic", 0)),
                    int(metrics.get("passed_rules", 0)),
                    int(metrics.get("passed_ai", 0)),
                    int(metrics.get("quality_score", 0)),
                    str(metrics.get("quality_label", "Unrated")),
                    1 if metrics.get("ai_enabled", True) else 0,
                    str(metrics.get("updated_at", datetime.now(timezone.utc).isoformat())),
                ),
            )

    def get_grant_source_memory(self, user_id: str, source_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT link_pattern, pagination_pattern, last_success_rate, updated_at
            FROM grant_source_memory
            WHERE user_id=? AND source_id=?
            """,
            (user_id, source_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "link_pattern": row["link_pattern"],
            "pagination_pattern": row["pagination_pattern"],
            "last_success_rate": float(row["last_success_rate"]),
            "updated_at": row["updated_at"],
        }

    def upsert_grant_source_memory(self, user_id: str, source_id: str, memory: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO grant_source_memory(user_id, source_id, link_pattern, pagination_pattern, last_success_rate, updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(user_id, source_id) DO UPDATE SET
                    link_pattern=excluded.link_pattern,
                    pagination_pattern=excluded.pagination_pattern,
                    last_success_rate=excluded.last_success_rate,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    source_id,
                    str(memory.get("link_pattern", "")),
                    str(memory.get("pagination_pattern", "")),
                    float(memory.get("last_success_rate", 0.0)),
                    str(memory.get("updated_at", datetime.now(timezone.utc).isoformat())),
                ),
            )

    def get_grant_source_api_config(self, user_id: str, source_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT endpoint, method, params_json, pagination_json, confidence, last_verified
            FROM grant_source_api_config
            WHERE user_id=? AND source_id=?
            """,
            (user_id, source_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "endpoint": row["endpoint"],
            "method": row["method"],
            "params": json.loads(row["params_json"]),
            "pagination": json.loads(row["pagination_json"]),
            "confidence": float(row["confidence"]),
            "last_verified": row["last_verified"],
        }

    def upsert_grant_source_api_config(self, user_id: str, source_id: str, config: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO grant_source_api_config(user_id, source_id, endpoint, method, params_json, pagination_json, confidence, last_verified)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id, source_id) DO UPDATE SET
                    endpoint=excluded.endpoint,
                    method=excluded.method,
                    params_json=excluded.params_json,
                    pagination_json=excluded.pagination_json,
                    confidence=excluded.confidence,
                    last_verified=excluded.last_verified
                """,
                (
                    user_id,
                    source_id,
                    str(config.get("endpoint", "")),
                    str(config.get("method", "GET")),
                    json.dumps(config.get("params", {})),
                    json.dumps(config.get("pagination", {})),
                    float(config.get("confidence", 0.0)),
                    str(config.get("last_verified", datetime.now(timezone.utc).isoformat())),
                ),
            )

    def get_grant_scan_schedule(self, user_id: str = "global") -> str:
        row = self._conn.execute("SELECT frequency FROM grant_scan_config WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            return "daily"
        return row["frequency"]

    def set_grant_scan_schedule(self, frequency: str, user_id: str = "global") -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO grant_scan_config(user_id, frequency) VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET frequency=excluded.frequency
                """,
                (user_id, frequency),
            )

    def add_grant_scan_results(self, results: List[GrantScanResult], user_id: str = "global") -> None:
        with self._lock, self._conn:
            for row in results:
                self._conn.execute(
                    """
                    INSERT INTO grant_scan_results(
                        user_id, id, source_id, source_name, title, published_at, location, industry, details, funder, program, max_amount,
                        eligibility_criteria, open_date, close_date, application_url, target_sectors, url, due_date, grant_amount, match_score,
                        eligible, eligibility_reason, recommended, deadline_soon, manual_check_needed, workflow_status, notes, contact_names,
                        reference_numbers, submission_date, outcome, external_key, status, scanned_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(user_id, external_key) DO UPDATE SET
                        scanned_at=excluded.scanned_at,
                        due_date=excluded.due_date,
                        close_date=excluded.close_date,
                        match_score=excluded.match_score,
                        eligible=excluded.eligible,
                        eligibility_reason=excluded.eligibility_reason,
                        recommended=excluded.recommended,
                        deadline_soon=excluded.deadline_soon,
                        manual_check_needed=excluded.manual_check_needed,
                        notes=excluded.notes
                    """,
                    (
                        user_id,
                        row.id,
                        row.source_id,
                        row.source_name,
                        row.title,
                        row.published_at,
                        row.location,
                        row.industry,
                        row.details,
                        row.funder,
                        row.program,
                        row.max_amount,
                        row.eligibility_criteria,
                        row.open_date,
                        row.close_date,
                        row.application_url,
                        row.target_sectors,
                        row.url,
                        row.due_date,
                        row.grant_amount,
                        row.match_score,
                        1 if row.eligible else 0,
                        row.eligibility_reason,
                        1 if row.recommended else 0,
                        1 if row.deadline_soon else 0,
                        1 if row.manual_check_needed else 0,
                        row.workflow_status,
                        row.notes,
                        row.contact_names,
                        row.reference_numbers,
                        row.submission_date,
                        row.outcome,
                        f"{row.source_id}|{row.title}|{row.due_date}",
                        row.status,
                        row.scanned_at,
                    ),
                )

    def replace_grant_scan_results(self, results: List[GrantScanResult], user_id: str = "global") -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM grant_scan_results WHERE user_id=?", (user_id,))
            for row in results:
                self._conn.execute(
                    """
                    INSERT INTO grant_scan_results(
                        user_id, id, source_id, source_name, title, published_at, location, industry, details, funder, program, max_amount,
                        eligibility_criteria, open_date, close_date, application_url, target_sectors, url, due_date, grant_amount, match_score,
                        eligible, eligibility_reason, recommended, deadline_soon, manual_check_needed, workflow_status, notes, contact_names,
                        reference_numbers, submission_date, outcome, external_key, status, scanned_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        user_id,
                        row.id,
                        row.source_id,
                        row.source_name,
                        row.title,
                        row.published_at,
                        row.location,
                        row.industry,
                        row.details,
                        row.funder,
                        row.program,
                        row.max_amount,
                        row.eligibility_criteria,
                        row.open_date,
                        row.close_date,
                        row.application_url,
                        row.target_sectors,
                        row.url,
                        row.due_date,
                        row.grant_amount,
                        row.match_score,
                        1 if row.eligible else 0,
                        row.eligibility_reason,
                        1 if row.recommended else 0,
                        1 if row.deadline_soon else 0,
                        1 if row.manual_check_needed else 0,
                        row.workflow_status,
                        row.notes,
                        row.contact_names,
                        row.reference_numbers,
                        row.submission_date,
                        row.outcome,
                        f"{row.source_id}|{row.title}|{row.due_date}",
                        row.status,
                        row.scanned_at,
                    ),
                )

    def list_grant_scan_results(self, limit: int = 100, user_id: str = "global") -> List[GrantScanResult]:
        rows = self._conn.execute(
            """
            SELECT id, source_id, source_name, title, published_at, location, industry, details, funder, program, max_amount,
                   eligibility_criteria, open_date, close_date, application_url, target_sectors, url, due_date, grant_amount,
                   match_score, eligible, eligibility_reason, recommended, deadline_soon, manual_check_needed, workflow_status,
                   notes, contact_names, reference_numbers, submission_date, outcome, status, scanned_at
            FROM grant_scan_results WHERE user_id=? ORDER BY scanned_at DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [
            GrantScanResult(
                id=row["id"],
                source_id=row["source_id"],
                source_name=row["source_name"],
                title=row["title"],
                published_at=row["published_at"],
                location=row["location"],
                industry=row["industry"],
                details=row["details"],
                funder=row["funder"],
                program=row["program"],
                max_amount=row["max_amount"],
                eligibility_criteria=row["eligibility_criteria"],
                open_date=row["open_date"],
                close_date=row["close_date"],
                application_url=row["application_url"],
                target_sectors=row["target_sectors"],
                url=row["url"],
                due_date=row["due_date"],
                grant_amount=row["grant_amount"],
                match_score=int(row["match_score"]),
                eligible=bool(row["eligible"]),
                eligibility_reason=row["eligibility_reason"],
                recommended=bool(row["recommended"]),
                deadline_soon=bool(row["deadline_soon"]),
                manual_check_needed=bool(row["manual_check_needed"]),
                workflow_status=row["workflow_status"],
                contact_names=row["contact_names"],
                reference_numbers=row["reference_numbers"],
                submission_date=row["submission_date"],
                outcome=row["outcome"],
                status=row["status"],
                notes=row["notes"],
                scanned_at=row["scanned_at"],
            )
            for row in rows
        ]

    def add_grant_raw_records(self, user_id: str, run_id: str, records: List[dict]) -> None:
        with self._lock, self._conn:
            for row in records:
                self._conn.execute(
                    """
                    INSERT INTO grant_raw_records(id, user_id, run_id, source_id, fetched_at, payload_json, payload_hash, url)
                    VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid4()),
                        user_id,
                        run_id,
                        str(row.get("source_id", "")),
                        str(row.get("fetched_at", "")),
                        json.dumps(row.get("payload", {})),
                        str(row.get("payload_hash", "")),
                        str(row.get("url", "")),
                    ),
                )

    def list_grant_raw_records(self, user_id: str, run_id: str) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT source_id, fetched_at, payload_json, payload_hash, url
            FROM grant_raw_records
            WHERE user_id=? AND run_id=?
            ORDER BY fetched_at ASC
            """,
            (user_id, run_id),
        ).fetchall()
        return [
            {
                "source_id": row["source_id"],
                "fetched_at": row["fetched_at"],
                "payload": json.loads(row["payload_json"]),
                "payload_hash": row["payload_hash"],
                "url": row["url"],
            }
            for row in rows
        ]

    def upsert_grant_normalized_records(self, user_id: str, run_id: str, records: List[dict]) -> None:
        with self._lock, self._conn:
            for row in records:
                normalized_json = json.dumps(row)
                self._conn.execute(
                    """
                    INSERT INTO grant_normalized(
                        id, user_id, run_id, source_id, dedupe_key, grant_name, provider, industry_json, location, min_size, max_size,
                        funding_amount, deadline, eligibility_text, description, url, normalized_json, version, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(user_id, dedupe_key) DO UPDATE SET
                        run_id=excluded.run_id,
                        source_id=excluded.source_id,
                        grant_name=excluded.grant_name,
                        provider=excluded.provider,
                        industry_json=excluded.industry_json,
                        location=excluded.location,
                        min_size=excluded.min_size,
                        max_size=excluded.max_size,
                        funding_amount=excluded.funding_amount,
                        deadline=excluded.deadline,
                        eligibility_text=excluded.eligibility_text,
                        description=excluded.description,
                        url=excluded.url,
                        normalized_json=excluded.normalized_json,
                        version=excluded.version,
                        updated_at=excluded.updated_at
                    """,
                    (
                        str(row.get("normalized_id", uuid4())),
                        user_id,
                        run_id,
                        str(row.get("source_id", "")),
                        str(row.get("dedupe_key", "")),
                        str(row.get("grant_name", "")),
                        str(row.get("provider", "")),
                        json.dumps(row.get("industry", [])),
                        str(row.get("location", "")),
                        int(row.get("min_size", 0)),
                        int(row.get("max_size", 0)),
                        int(row.get("funding_amount", 0)),
                        str(row.get("deadline", "")),
                        str(row.get("eligibility_text", "")),
                        str(row.get("description", "")),
                        str(row.get("url", "")),
                        normalized_json,
                        int(row.get("version", 1)),
                        str(row.get("updated_at", datetime.now(timezone.utc).isoformat())),
                    ),
                )

    def list_grant_normalized_records(self, user_id: str, run_id: str) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT id, source_id, dedupe_key, grant_name, provider, industry_json, location, min_size, max_size, funding_amount, deadline,
                   eligibility_text, description, url, normalized_json, version, updated_at
            FROM grant_normalized
            WHERE user_id=? AND run_id=?
            ORDER BY updated_at DESC
            """,
            (user_id, run_id),
        ).fetchall()
        out: List[dict] = []
        for row in rows:
            payload = json.loads(row["normalized_json"]) if row["normalized_json"] else {}
            payload.update(
                {
                    "normalized_id": row["id"],
                    "source_id": row["source_id"],
                    "dedupe_key": row["dedupe_key"],
                    "grant_name": row["grant_name"],
                    "provider": row["provider"],
                    "industry": json.loads(row["industry_json"]),
                    "location": row["location"],
                    "min_size": row["min_size"],
                    "max_size": row["max_size"],
                    "funding_amount": row["funding_amount"],
                    "deadline": row["deadline"],
                    "eligibility_text": row["eligibility_text"],
                    "description": row["description"],
                    "url": row["url"],
                    "version": row["version"],
                    "updated_at": row["updated_at"],
                }
            )
            out.append(payload)
        return out

    def add_grant_match_candidates(self, user_id: str, run_id: str, records: List[dict]) -> None:
        with self._lock, self._conn:
            for row in records:
                self._conn.execute(
                    """
                    INSERT INTO grant_match_candidates(id, user_id, run_id, normalized_id, rule_status, rule_score, rule_reasons_json, created_at)
                    VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid4()),
                        user_id,
                        run_id,
                        str(row.get("normalized_id", "")),
                        str(row.get("rule_status", "")),
                        int(row.get("rule_score", 0)),
                        json.dumps(row.get("rule_reasons", [])),
                        str(row.get("created_at", datetime.now(timezone.utc).isoformat())),
                    ),
                )

    def list_grant_match_candidates(self, user_id: str, run_id: str) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT normalized_id, rule_status, rule_score, rule_reasons_json, created_at
            FROM grant_match_candidates
            WHERE user_id=? AND run_id=?
            ORDER BY created_at DESC
            """,
            (user_id, run_id),
        ).fetchall()
        return [
            {
                "normalized_id": row["normalized_id"],
                "rule_status": row["rule_status"],
                "rule_score": row["rule_score"],
                "rule_reasons": json.loads(row["rule_reasons_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def add_grant_ai_assessments(self, user_id: str, run_id: str, records: List[dict]) -> None:
        with self._lock, self._conn:
            for row in records:
                self._conn.execute(
                    """
                    INSERT INTO grant_ai_assessments(
                        id, user_id, run_id, normalized_id, eligibility, confidence, key_reasons_json, missing_requirements_json,
                        recommended_action, model, prompt_version, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid4()),
                        user_id,
                        run_id,
                        str(row.get("normalized_id", "")),
                        str(row.get("eligibility", "PARTIAL")),
                        int(row.get("confidence", 0)),
                        json.dumps(row.get("key_reasons", [])),
                        json.dumps(row.get("missing_requirements", [])),
                        str(row.get("recommended_action", "REVIEW")),
                        str(row.get("model", "")),
                        str(row.get("prompt_version", "v1")),
                        str(row.get("created_at", datetime.now(timezone.utc).isoformat())),
                    ),
                )

    def list_grant_ai_assessments(self, user_id: str, run_id: str) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT normalized_id, eligibility, confidence, key_reasons_json, missing_requirements_json, recommended_action, model, prompt_version, created_at
            FROM grant_ai_assessments
            WHERE user_id=? AND run_id=?
            ORDER BY created_at DESC
            """,
            (user_id, run_id),
        ).fetchall()
        return [
            {
                "normalized_id": row["normalized_id"],
                "eligibility": row["eligibility"],
                "confidence": row["confidence"],
                "key_reasons": json.loads(row["key_reasons_json"]),
                "missing_requirements": json.loads(row["missing_requirements_json"]),
                "recommended_action": row["recommended_action"],
                "model": row["model"],
                "prompt_version": row["prompt_version"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def add_grant_pipeline_runs(self, user_id: str, run_id: str, records: List[dict]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM grant_pipeline_runs WHERE user_id=? AND run_id=?",
                (user_id, run_id),
            )
            for row in records:
                self._conn.execute(
                    """
                    INSERT INTO grant_pipeline_runs(
                        id, user_id, run_id, source_id, source_name, url, timestamp, registry_status, site, source_type,
                        fetch_status, content_length, page_type, links_found, links_after_filter, final_selected_count,
                        detail_pages_processed, successful_extractions, normalized_count, deduplicated_count,
                        heuristic_rejected_count, rule_rejected_count, cache_hit_count, ai_called_count,
                        failed_step, error_message, raw_preview, sample_output_json, extracted_links_json,
                        filtered_links_json, selected_links_json, detail_urls_json, top_patterns_json,
                        pagination_chain_json, config_json, api_config_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid4()),
                        user_id,
                        run_id,
                        str(row.get("source_id", "")),
                        str(row.get("source_name", "")),
                        str(row.get("url", "")),
                        str(row.get("timestamp", datetime.now(timezone.utc).isoformat())),
                        str(row.get("registry_status", "")),
                        str(row.get("site", "")),
                        str(row.get("source_type", "")),
                        str(row.get("fetch_status", "")),
                        int(row.get("content_length", 0) or 0),
                        str(row.get("page_type", "")),
                        int(row.get("links_found", 0) or 0),
                        int(row.get("links_after_filter", 0) or 0),
                        int(row.get("final_selected_count", 0) or 0),
                        int(row.get("detail_pages_processed", 0) or 0),
                        int(row.get("successful_extractions", 0) or 0),
                        int(row.get("normalized_count", 0) or 0),
                        int(row.get("deduplicated_count", 0) or 0),
                        int(row.get("heuristic_rejected_count", 0) or 0),
                        int(row.get("rule_rejected_count", 0) or 0),
                        int(row.get("cache_hit_count", 0) or 0),
                        int(row.get("ai_called_count", 0) or 0),
                        str(row.get("failed_step", "")),
                        str(row.get("error_message", "")),
                        str(row.get("raw_preview", "")),
                        json.dumps(row.get("sample_output", [])),
                        json.dumps(row.get("extracted_links", [])),
                        json.dumps(row.get("filtered_links", [])),
                        json.dumps(row.get("selected_links", [])),
                        json.dumps(row.get("detail_urls", [])),
                        json.dumps(row.get("top_patterns", [])),
                        json.dumps(row.get("pagination_chain", [])),
                        json.dumps(row.get("config", {})),
                        json.dumps(row.get("api_config", {})),
                    ),
                )

    def list_grant_pipeline_runs(self, user_id: str, run_id: str) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT source_id, source_name, url, timestamp, registry_status, site, source_type, fetch_status, content_length,
                   page_type, links_found, links_after_filter, final_selected_count, detail_pages_processed,
                   successful_extractions, normalized_count, deduplicated_count, heuristic_rejected_count,
                   rule_rejected_count, cache_hit_count, ai_called_count, failed_step, error_message, raw_preview,
                   sample_output_json, extracted_links_json, filtered_links_json, selected_links_json,
                   detail_urls_json, top_patterns_json, pagination_chain_json, config_json, api_config_json
            FROM grant_pipeline_runs
            WHERE user_id=? AND run_id=?
            ORDER BY source_name ASC, timestamp ASC
            """,
            (user_id, run_id),
        ).fetchall()
        return [
            {
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "url": row["url"],
                "timestamp": row["timestamp"],
                "registry_status": row["registry_status"],
                "site": row["site"],
                "source_type": row["source_type"],
                "fetch_status": row["fetch_status"],
                "content_length": row["content_length"],
                "page_type": row["page_type"],
                "links_found": row["links_found"],
                "links_after_filter": row["links_after_filter"],
                "final_selected_count": row["final_selected_count"],
                "detail_pages_processed": row["detail_pages_processed"],
                "successful_extractions": row["successful_extractions"],
                "normalized_count": row["normalized_count"],
                "deduplicated_count": row["deduplicated_count"],
                "heuristic_rejected_count": row["heuristic_rejected_count"],
                "rule_rejected_count": row["rule_rejected_count"],
                "cache_hit_count": row["cache_hit_count"],
                "ai_called_count": row["ai_called_count"],
                "failed_step": row["failed_step"],
                "error_message": row["error_message"],
                "raw_preview": row["raw_preview"],
                "sample_output": json.loads(row["sample_output_json"]),
                "extracted_links": json.loads(row["extracted_links_json"]),
                "filtered_links": json.loads(row["filtered_links_json"]),
                "selected_links": json.loads(row["selected_links_json"]),
                "detail_urls": json.loads(row["detail_urls_json"]),
                "top_patterns": json.loads(row["top_patterns_json"]),
                "pagination_chain": json.loads(row["pagination_chain_json"]),
                "config": json.loads(row["config_json"]),
                "api_config": json.loads(row["api_config_json"]),
            }
            for row in rows
        ]

    def get_ai_cache(self, stage: str, content_hash: str) -> dict | None:
        row = self._conn.execute(
            "SELECT result_json FROM ai_cache WHERE stage=? AND content_hash=?",
            (stage, content_hash),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["result_json"])

    def set_ai_cache(self, stage: str, content_hash: str, result: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO ai_cache(stage, content_hash, result_json, created_at)
                VALUES(?,?,?,?)
                ON CONFLICT(stage, content_hash) DO UPDATE SET
                    result_json=excluded.result_json,
                    created_at=excluded.created_at
                """,
                (stage, content_hash, json.dumps(result), datetime.now(timezone.utc).isoformat()),
            )

    def update_grant_scan_result(self, user_id: str, result_id: str, **updates) -> None:
        if not updates:
            return
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key}=?")
            if isinstance(value, bool):
                values.append(1 if value else 0)
            else:
                values.append(value)
        values.extend([result_id, user_id])
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE grant_scan_results SET {', '.join(fields)} WHERE id=? AND user_id=?",
                values,
            )

    def create_grant_draft(self, draft: GrantDraft) -> GrantDraft:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO grant_drafts(id, user_id, grant_result_id, version, content, created_at) VALUES(?,?,?,?,?,?)",
                (draft.id, draft.user_id, draft.grant_result_id, draft.version, draft.content, draft.created_at),
            )
        return draft

    def list_grant_drafts(self, user_id: str, grant_result_id: str) -> List[GrantDraft]:
        rows = self._conn.execute(
            "SELECT id, user_id, grant_result_id, version, content, created_at FROM grant_drafts WHERE user_id=? AND grant_result_id=? ORDER BY version DESC",
            (user_id, grant_result_id),
        ).fetchall()
        return [
            GrantDraft(
                id=row["id"],
                user_id=row["user_id"],
                grant_result_id=row["grant_result_id"],
                version=row["version"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        row = self._conn.execute(
            """
            SELECT user_id, email, name, organisation, company_name, abn, anzsic_code, business_stage, headcount, revenue, goals_json, state_territory, business_objectives,
                   company_size, interest_industries, timezone, notification_preferences, active_verticals, billing_plan, digest_time, digest_enabled_verticals
            FROM user_profiles WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return UserProfile(
            user_id=row["user_id"],
            email=row["email"],
            name=row["name"],
            organisation=row["organisation"],
            company_name=row["company_name"],
            abn=row["abn"],
            anzsic_code=row["anzsic_code"],
            business_stage=row["business_stage"],
            headcount=int(row["headcount"]),
            revenue=int(row["revenue"]),
            goals_json=row["goals_json"],
            state_territory=row["state_territory"],
            business_objectives=row["business_objectives"],
            company_size=row["company_size"] if "company_size" in row.keys() else "small",
            interest_industries=row["interest_industries"] if "interest_industries" in row.keys() else '["technology"]',
            timezone=row["timezone"],
            notification_preferences=row["notification_preferences"],
            active_verticals=row["active_verticals"],
            billing_plan=row["billing_plan"],
            digest_time=row["digest_time"],
            digest_enabled_verticals=row["digest_enabled_verticals"],
        )

    def upsert_user_profile(self, profile: UserProfile) -> UserProfile:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO user_profiles(user_id, email, name, organisation, company_name, abn, anzsic_code, business_stage, headcount, revenue, goals_json, state_territory, business_objectives, company_size, interest_industries, timezone, notification_preferences, active_verticals, billing_plan, digest_time, digest_enabled_verticals)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                    email=excluded.email,
                    name=excluded.name,
                    organisation=excluded.organisation,
                    company_name=excluded.company_name,
                    abn=excluded.abn,
                    anzsic_code=excluded.anzsic_code,
                    business_stage=excluded.business_stage,
                    headcount=excluded.headcount,
                    revenue=excluded.revenue,
                    goals_json=excluded.goals_json,
                    state_territory=excluded.state_territory,
                    business_objectives=excluded.business_objectives,
                    company_size=excluded.company_size,
                    interest_industries=excluded.interest_industries,
                    timezone=excluded.timezone,
                    notification_preferences=excluded.notification_preferences,
                    active_verticals=excluded.active_verticals,
                    billing_plan=excluded.billing_plan,
                    digest_time=excluded.digest_time,
                    digest_enabled_verticals=excluded.digest_enabled_verticals
                """,
                (
                    profile.user_id,
                    profile.email,
                    profile.name,
                    profile.organisation,
                    profile.company_name,
                    profile.abn,
                    profile.anzsic_code,
                    profile.business_stage,
                    profile.headcount,
                    profile.revenue,
                    profile.goals_json,
                    profile.state_territory,
                    profile.business_objectives,
                    profile.company_size,
                    profile.interest_industries,
                    profile.timezone,
                    profile.notification_preferences,
                    profile.active_verticals,
                    profile.billing_plan,
                    profile.digest_time,
                    profile.digest_enabled_verticals,
                ),
            )
        return profile

    def enqueue_job(self, job: JobRecord) -> JobRecord:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO jobs(id, user_id, vertical, job_type, status, scheduled_at, started_at, completed_at, attempts, max_attempts, next_retry_at, error_message)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    job.id,
                    job.user_id,
                    job.vertical,
                    job.job_type,
                    job.status,
                    job.scheduled_at,
                    job.started_at,
                    job.completed_at,
                    job.attempts,
                    job.max_attempts,
                    job.next_retry_at,
                    job.error_message,
                ),
            )
        return job

    def update_job(self, job_id: str, **updates) -> None:
        if not updates:
            return
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key}=?")
            values.append(value)
        values.append(job_id)
        with self._lock, self._conn:
            self._conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id=?", values)

    def list_jobs(self, user_id: str, vertical: str = "", limit: int = 100) -> List[JobRecord]:
        if vertical:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE user_id=? AND vertical=? ORDER BY scheduled_at DESC LIMIT ?",
                (user_id, vertical, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE user_id=? ORDER BY scheduled_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [
            JobRecord(
                id=row["id"],
                user_id=row["user_id"],
                vertical=row["vertical"],
                job_type=row["job_type"],
                status=row["status"],
                scheduled_at=row["scheduled_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                attempts=row["attempts"],
                max_attempts=row["max_attempts"],
                next_retry_at=row["next_retry_at"],
                error_message=row["error_message"],
            )
            for row in rows
        ]

    def list_due_jobs(self, current_time: str) -> List[JobRecord]:
        rows = self._conn.execute(
            """
            SELECT * FROM jobs
            WHERE
                (status='queued' AND scheduled_at <= ?)
                OR (status='failed' AND next_retry_at != '' AND next_retry_at <= ? AND attempts < max_attempts)
            ORDER BY scheduled_at ASC
            """,
            (current_time, current_time),
        ).fetchall()
        return [
            JobRecord(
                id=row["id"],
                user_id=row["user_id"],
                vertical=row["vertical"],
                job_type=row["job_type"],
                status=row["status"],
                scheduled_at=row["scheduled_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                attempts=row["attempts"],
                max_attempts=row["max_attempts"],
                next_retry_at=row["next_retry_at"],
                error_message=row["error_message"],
            )
            for row in rows
        ]

    def add_notification(self, item: NotificationItem) -> NotificationItem:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO notifications(id, user_id, level, message, is_read, created_at) VALUES(?,?,?,?,?,?)",
                (item.id, item.user_id, item.level, item.message, 1 if item.is_read else 0, item.created_at),
            )
        return item

    def list_notifications(self, user_id: str, unread_only: bool = False, limit: int = 100) -> List[NotificationItem]:
        if unread_only:
            rows = self._conn.execute(
                "SELECT * FROM notifications WHERE user_id=? AND is_read=0 ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [
            NotificationItem(
                id=row["id"],
                user_id=row["user_id"],
                level=row["level"],
                message=row["message"],
                is_read=bool(row["is_read"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def mark_notification_read(self, user_id: str, notification_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
                (notification_id, user_id),
            )
