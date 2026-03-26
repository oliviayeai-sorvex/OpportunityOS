from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from models.entities import GrantDraft, GrantScanResult, GrantSource
from models.repository_protocol import OpportunityRepository
from services.ai_agent_service import AIAgentService
from services.generic_grant_discovery import GenericGrantDiscovery

CATALOG_BY_SOURCE = {
    "src-business-gov-au": [
        {
            "title": "business.gov.au Grants and Programs Listing",
            "funder": "Australian Government",
            "program": "business.gov.au",
            "max_amount": "Variable",
            "eligibility_criteria": "See listing page for current program-specific criteria",
            "open_date": "2026-03-01",
            "close_date": "2026-06-30",
            "application_url": "https://business.gov.au/grants-and-programs",
            "target_sectors": ["technology", "professional_services", "retail"],
            "location": "National, Australia",
            "industry": "technology",
            "details": "Official grants listing index for Australian businesses.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
    "src-grantconnect": [
        {
            "title": "GrantConnect Discover and Apply Listing",
            "funder": "Australian Government",
            "program": "GrantConnect",
            "max_amount": "Variable",
            "eligibility_criteria": "See listing page for each grant's criteria and deadlines",
            "open_date": "2026-02-01",
            "close_date": "2026-05-20",
            "application_url": "https://www.grants.gov.au/Go/List",
            "target_sectors": ["advanced_manufacturing", "agriculture", "technology"],
            "location": "National, Australia",
            "industry": "advanced_manufacturing",
            "details": "Federal grants discovery and application portal.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
    "src-arena": [
        {
            "title": "Clean Energy Innovation Program",
            "funder": "ARENA",
            "program": "Clean Energy Funding Program",
            "max_amount": "AUD 1,000,000",
            "eligibility_criteria": "Clean energy pilot or deployment with measurable outcomes",
            "open_date": "2026-03-10",
            "close_date": "2026-08-15",
            "application_url": "https://arena.gov.au/funding",
            "target_sectors": ["clean_energy", "infrastructure", "advanced_manufacturing"],
            "location": "National, Australia",
            "industry": "clean_energy",
            "details": "Funding for pilot and commercial clean energy deployments.",
            "company_sizes": {"medium", "large"},
            "states": {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"},
            "stages": {"growth", "established"},
        }
    ],
    "src-medtech-grants": [
        {
            "title": "MedTech and Health Funding Listing",
            "funder": "Australian Government",
            "program": "Health and Medical Funding",
            "max_amount": "Variable",
            "eligibility_criteria": "See linked health funding pages for grant-specific eligibility",
            "open_date": "2026-03-15",
            "close_date": "2026-07-30",
            "application_url": "https://help.grants.gov.au/getting-started-with-grantconnect/information-made-easy/current-opportunities/",
            "target_sectors": ["healthcare", "technology"],
            "location": "National, Australia",
            "industry": "healthcare",
            "details": "Australian Government health grants and funding listing pages.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
    "src-nsw-grants": [
        {
            "title": "NSW Grants and Funding Listing",
            "funder": "NSW Government",
            "program": "NSW Grants",
            "max_amount": "Variable",
            "eligibility_criteria": "See NSW listing pages for grant-specific criteria",
            "open_date": "2026-01-01",
            "close_date": "2026-12-31",
            "application_url": "https://www.nsw.gov.au/grants-and-funding",
            "target_sectors": ["technology", "professional_services", "advanced_manufacturing"],
            "location": "NSW, Australia",
            "industry": "technology",
            "details": "Official NSW grants and funding listing.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"NSW"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
    "src-business-vic": [
        {
            "title": "Business Victoria Grants Listing",
            "funder": "State: Business Victoria",
            "program": "Business Victoria",
            "max_amount": "Variable",
            "eligibility_criteria": "See Business Victoria program pages for eligibility",
            "open_date": "2026-01-01",
            "close_date": "2026-12-31",
            "application_url": "https://business.vic.gov.au/grants-and-programs?filter=%7B%22status%22%3A%5B%22opening+soon%22%2C%22open%22%2C%22ongoing%22%5D%7D",
            "target_sectors": ["advanced_manufacturing", "technology", "healthcare"],
            "location": "VIC, Australia",
            "industry": "advanced_manufacturing",
            "details": "Business Victoria grants and support listing.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"VIC"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
    "src-business-qld": [
        {
            "title": "Business Queensland Grants and Support Listing",
            "funder": "Queensland Government",
            "program": "Business Queensland",
            "max_amount": "Variable",
            "eligibility_criteria": "See Queensland grant pages for grant-specific criteria",
            "open_date": "2026-01-01",
            "close_date": "2026-12-31",
            "application_url": "https://www.business.qld.gov.au/running-business/support-services/financial/grants/schedule",
            "target_sectors": ["agriculture", "technology", "professional_services"],
            "location": "QLD, Australia",
            "industry": "agriculture",
            "details": "Queensland business support and grant listing pages.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"QLD"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
    "src-csiro": [
        {
            "title": "CSIRO Funding and Collaboration Listing",
            "funder": "CSIRO",
            "program": "CSIRO Funding",
            "max_amount": "Variable",
            "eligibility_criteria": "See CSIRO funding pages for challenge and sector criteria",
            "open_date": "2026-01-01",
            "close_date": "2026-12-31",
            "application_url": "https://www.csiro.au/en/work-with-us/funding-programs/SME/SME-Connect-programs",
            "target_sectors": ["technology", "advanced_manufacturing", "clean_energy"],
            "location": "National, Australia",
            "industry": "technology",
            "details": "CSIRO funding opportunities and collaboration programs.",
            "company_sizes": {"micro", "small", "medium", "large"},
            "states": {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"},
            "stages": {"pre-revenue", "early", "growth", "established"},
        }
    ],
}

LOCATION_LABEL_BY_CODE = {
    "NSW": "NSW, Australia",
    "VIC": "VIC, Australia",
    "QLD": "QLD, Australia",
    "SA": "SA, Australia",
    "WA": "WA, Australia",
    "TAS": "TAS, Australia",
    "ACT": "ACT, Australia",
    "NT": "NT, Australia",
    "AU": "National, Australia",
}

DEFAULT_BOARD_COLUMNS = ["New", "Shortlisted", "In Progress", "Under Review", "Submitted", "Closed"]
MANAGED_DEFAULT_SOURCE_IDS = {
    "src-business-gov-au",
    "src-grantconnect",
    "src-nsw-grants",
    "src-ato-rd",
    "src-arena",
    "src-invest-vic",
    "src-business-vic",
    "src-business-qld",
    "src-sa-gov",
    "src-wa-gov",
    "src-csiro",
    "src-medtech-grants",
}


class GrantWriterService:
    def __init__(self, repository: OpportunityRepository) -> None:
        self._repository = repository
        self._ai = AIAgentService()
        self._discoverer = GenericGrantDiscovery(ai=self._ai, repository=repository)

    def _safe_json_list(self, raw: str, fallback: list[str]) -> list[str]:
        try:
            parsed = json.loads(raw or "[]")
            if isinstance(parsed, list):
                out = [str(item).strip().lower() for item in parsed if str(item).strip()]
                if out:
                    return out
        except json.JSONDecodeError:
            pass
        return fallback

    def _profile_preferences(self, user_id: str) -> dict:
        profile = self._repository.get_user_profile(user_id)
        if profile is None:
            return {
                "industries": ["technology"],
                "company_size": "small",
                "state_territory": "NSW",
                "business_stage": "early",
                "objectives": "",
            }
        return {
            "industries": self._safe_json_list(profile.interest_industries, ["technology"]),
            "company_size": (profile.company_size or "small").strip().lower(),
            "state_territory": (profile.state_territory or "NSW").strip().upper(),
            "business_stage": (profile.business_stage or "early").strip().lower(),
            "objectives": profile.business_objectives or "",
            "profile": profile,
        }

    def _score_grant(self, grant: dict, preferences: dict) -> tuple[int, str]:
        score = 0
        industries = set(preferences["industries"])
        industry_match = bool(set(grant["target_sectors"]).intersection(industries))
        size_match = preferences["company_size"] in grant["company_sizes"]
        state_match = preferences["state_territory"] in grant["states"]
        stage_match = preferences["business_stage"] in grant["stages"]

        if industry_match:
            score += 40
        if size_match:
            score += 20
        if state_match:
            score += 20
        if stage_match:
            score += 20

        reasons = []
        if industry_match:
            reasons.append("industry aligned")
        if size_match:
            reasons.append("company size aligned")
        if state_match:
            reasons.append("state aligned")
        if stage_match:
            reasons.append("business stage aligned")
        if not reasons:
            reasons.append("limited criteria alignment")
        return score, ", ".join(reasons)

    def _deadline_soon(self, close_date: str) -> bool:
        try:
            close = datetime.fromisoformat(close_date)
            days = (close - datetime.now()).days
            return days <= 14
        except ValueError:
            return False

    def _manual_check_needed(self, source: GrantSource) -> bool:
        access = source.access.lower()
        return "login" in access or "paywall" in access

    def dashboard_payload(self, user_id: str) -> dict:
        rows = [result.__dict__ for result in self._repository.list_grant_scan_results(limit=300, user_id=user_id)]
        board = {name: [] for name in DEFAULT_BOARD_COLUMNS}
        for row in rows:
            status = row.get("workflow_status", "New")
            board.setdefault(status, [])
            board[status].append(row)
        return {
            "sources": [source.__dict__ for source in self._repository.list_grant_sources(user_id=user_id)],
            "recommended_sources": [source.__dict__ for source in self._repository.list_grant_sources(user_id="global")],
            "schedule": self._repository.get_grant_scan_schedule(user_id=user_id),
            "scan_results": rows,
            "board": board,
        }

    def discovery_debug(self, user_id: str, source_id: str) -> dict:
        source = next((row for row in self._repository.list_grant_sources(user_id=user_id) if row.id == source_id), None)
        if source is None:
            source = next((row for row in self._repository.list_grant_sources(user_id="global") if row.id == source_id), None)
        if source is None:
            raise KeyError("source not found")
        preferences = self._profile_preferences(user_id)
        return self._discoverer.discovery_debug(source=source, preferences=preferences, user_id=user_id)

    def upsert_source(self, user_id: str, source_id: str, name: str, url: str, access: str, active: bool = True) -> dict:
        source = GrantSource(id=source_id, name=name.strip(), url=url.strip(), access=access.strip(), active=active)
        saved = self._repository.upsert_grant_source(source, user_id=user_id)
        return saved.__dict__

    def delete_source(self, user_id: str, source_id: str) -> None:
        self._repository.delete_grant_source(source_id, user_id=user_id)

    def reset_sources_to_defaults(self, user_id: str) -> dict:
        defaults = self._repository.list_grant_sources(user_id="global")
        default_ids = {row.id for row in defaults}
        for src in defaults:
            self._repository.upsert_grant_source(src, user_id=user_id)
        current = self._repository.list_grant_sources(user_id=user_id)
        for src in current:
            if src.id in MANAGED_DEFAULT_SOURCE_IDS and src.id not in default_ids:
                self._repository.delete_grant_source(src.id, user_id=user_id)
        return {"sources": [row.__dict__ for row in self._repository.list_grant_sources(user_id=user_id)]}

    def set_schedule(self, user_id: str, frequency: str) -> str:
        if frequency not in {"daily", "weekly"}:
            raise ValueError("frequency must be daily or weekly")
        self._repository.set_grant_scan_schedule(frequency, user_id=user_id)
        return frequency

    def _amount_to_int(self, raw: str) -> int:
        digits = "".join(ch for ch in raw if ch.isdigit())
        return int(digits) if digits else 0

    def _parse_business_size_range(self, raw: str) -> tuple[int, int]:
        text = str(raw or "").lower().strip()
        if not text:
            return 0, 2000
        patterns = [
            (r"between\s+(\d+)\s+and\s+(\d+)\s+employees", lambda a, b: (int(a), int(b))),
            (r"less than\s+(\d+)\s+employees", lambda a: (0, max(0, int(a) - 1))),
            (r"fewer than\s+(\d+)\s+employees", lambda a: (0, max(0, int(a) - 1))),
            (r"up to\s+(\d+)\s+employees", lambda a: (0, int(a))),
            (r"at least\s+(\d+)\s+employees", lambda a: (int(a), 2000)),
        ]
        for pattern, builder in patterns:
            match = re.search(pattern, text)
            if match:
                return builder(*match.groups())
        return 0, 2000

    def _normalise_location(self, location: str) -> str:
        loc = location.upper()
        for code in ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]:
            if code in loc:
                return code
        return "AU"

    def _normalise_location_list(self, locations: list[str]) -> list[str]:
        codes = []
        for location in locations:
            code = self._normalise_location(str(location))
            if code not in codes:
                codes.append(code)
        return codes or ["AU"]

    def _location_label(self, code: str) -> str:
        return LOCATION_LABEL_BY_CODE.get(code.upper(), "National, Australia")

    def _pipeline_run_record(self, source: GrantSource, debug: dict) -> dict:
        return {
            "source_id": source.id,
            "source_name": source.name,
            "url": source.url,
            "timestamp": debug.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "registry_status": debug.get("registry_status", "known"),
            "site": debug.get("site", ""),
            "source_type": debug.get("source_type", ""),
            "fetch_status": debug.get("fetch_status", ""),
            "content_length": int(debug.get("content_length", 0) or 0),
            "page_type": debug.get("page_type", ""),
            "links_found": int(debug.get("links_found", 0) or 0),
            "links_after_filter": int(debug.get("links_after_filter", 0) or 0),
            "final_selected_count": int(debug.get("final_selected_count", 0) or 0),
            "detail_pages_processed": int(debug.get("detail_pages_processed", 0) or 0),
            "successful_extractions": int(debug.get("successful_extractions", 0) or 0),
            "normalized_count": int(debug.get("normalized_count", 0) or 0),
            "deduplicated_count": int(debug.get("deduplicated_count", 0) or 0),
            "heuristic_rejected_count": int(debug.get("heuristic_rejected_count", 0) or 0),
            "rule_rejected_count": int(debug.get("rule_rejected_count", 0) or 0),
            "cache_hit_count": int(debug.get("cache_hit_count", 0) or 0),
            "ai_called_count": int(debug.get("ai_called_count", 0) or 0),
            "failed_step": debug.get("failed_step", ""),
            "error_message": debug.get("error_message") or debug.get("error", ""),
            "raw_preview": debug.get("raw_preview", ""),
            "sample_output": debug.get("sample_output", []),
            "extracted_links": debug.get("extracted_links", []),
            "filtered_links": debug.get("filtered_links", []),
            "selected_links": debug.get("selected_links", []),
            "detail_urls": debug.get("detail_urls", []),
            "top_patterns": debug.get("top_patterns", []),
            "pagination_chain": debug.get("pagination_chain", []),
            "config": debug.get("config", {}),
            "api_config": debug.get("api_config", {}),
        }

    def _ingest_raw_records(self, user_id: str, run_id: str, preferences: dict, debug_stats: dict | None = None) -> list[dict]:
        now_iso = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        pipeline_runs: list[dict] = []
        for source in self._repository.list_grant_sources(user_id=user_id):
            if not source.active:
                continue
            # Generic discovery first: capture child opportunity URLs from listing pages without site-specific rules.
            if debug_stats is not None:
                debug_stats.setdefault("discovery_debugs", {})[source.id] = {}
            grants = self._discoverer.discover(
                source=source,
                preferences=preferences,
                user_id=user_id,
                stats=debug_stats,
            )
            debug_entry = debug_stats.get("discovery_debugs", {}).get(source.id, {}) if debug_stats else {}
            if not grants:
                grants = CATALOG_BY_SOURCE.get(source.id, [])
                if grants and debug_entry is not None:
                    debug_entry["fallback_used"] = "catalog"
            if not grants:
                grants = [
                    {
                        "title": "General Growth Grant",
                        "funder": source.name,
                        "program": "Open Program",
                        "max_amount": "AUD 40,000",
                        "eligibility_criteria": "Business operating in Australia",
                        "open_date": now_iso[:10],
                        "close_date": "2026-12-31",
                        "application_url": source.url,
                        "target_sectors": preferences["industries"],
                        "location": f"{preferences['state_territory']}, Australia",
                        "industry": preferences["industries"][0],
                        "details": "General grant supporting business growth initiatives.",
                        "company_sizes": {"micro", "small", "medium", "large"},
                        "states": {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"},
                        "stages": {"pre-revenue", "early", "growth", "established"},
                    }
                ]
                if debug_entry is not None:
                    debug_entry["fallback_used"] = "generic-default"
            pipeline_runs.append(self._pipeline_run_record(source=source, debug=debug_entry))
            for grant in grants:
                payload = {
                    "grant_name": grant["title"],
                    "provider": grant["funder"],
                    "amount": grant["max_amount"],
                    "deadline": grant["close_date"],
                    "eligibility_text": grant["eligibility_criteria"],
                    "description": grant["details"],
                    "url": grant["application_url"],
                    "source_program": grant["program"],
                    "target_sectors": grant["target_sectors"],
                    "location": grant["location"],
                    "criteria_industries": grant.get("criteria_industries", []),
                    "criteria_locations": grant.get("criteria_locations", []),
                    "criteria_business_size": grant.get("criteria_business_size", ""),
                    "criteria_must_have": grant.get("criteria_must_have", []),
                    "criteria_not_allowed": grant.get("criteria_not_allowed", []),
                    "relevant_text": grant.get("relevant_text", ""),
                    "source_id": source.id,
                    "text_content": grant.get("text_content", ""),
                    "scrape_timestamp": grant.get("scrape_timestamp", now_iso[:10]),
                }
                payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
                records.append(
                    {
                        "source_id": source.id,
                        "fetched_at": now_iso,
                        "payload": payload,
                        "payload_hash": payload_hash,
                        "url": source.url,
                    }
                )
        self._repository.add_grant_raw_records(user_id=user_id, run_id=run_id, records=records)
        self._repository.add_grant_pipeline_runs(user_id=user_id, run_id=run_id, records=pipeline_runs)
        return records

    def _normalize_records(self, user_id: str, run_id: str, raw_records: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for row in raw_records:
            payload = row["payload"]
            sectors = payload.get("target_sectors", [])
            industry = [str(item).strip().lower() for item in sectors if str(item).strip()]
            norm = {
                "normalized_id": str(uuid4()),
                "source_id": row["source_id"],
                "dedupe_key": hashlib.sha256(
                    f"{payload.get('provider','')}|{payload.get('grant_name','')}|{payload.get('deadline','')}|{payload.get('url','')}".encode("utf-8")
                ).hexdigest(),
                "grant_name": str(payload.get("grant_name", "")),
                "provider": str(payload.get("provider", "")),
                "industry": industry or ["general_business"],
                "location": self._normalise_location(str(payload.get("location", ""))),
                "criteria_industries": [str(item).strip().lower() for item in payload.get("criteria_industries", []) if str(item).strip()],
                "criteria_locations": self._normalise_location_list(payload.get("criteria_locations", [])),
                "criteria_business_size": str(payload.get("criteria_business_size", "")),
                "criteria_must_have": [str(item).strip() for item in payload.get("criteria_must_have", []) if str(item).strip()],
                "criteria_not_allowed": [str(item).strip() for item in payload.get("criteria_not_allowed", []) if str(item).strip()],
                "relevant_text": str(payload.get("relevant_text", "")),
                "min_size": self._parse_business_size_range(str(payload.get("criteria_business_size", "")))[0],
                "max_size": self._parse_business_size_range(str(payload.get("criteria_business_size", "")))[1],
                "funding_amount": self._amount_to_int(str(payload.get("amount", "0"))),
                "deadline": str(payload.get("deadline", "")),
                "eligibility_text": str(payload.get("eligibility_text", "")),
                "description": str(payload.get("description", "")),
                "url": str(payload.get("url", "")),
                "version": 1,
                "updated_at": now_iso,
            }
            normalized.append(norm)
        self._repository.upsert_grant_normalized_records(user_id=user_id, run_id=run_id, records=normalized)
        return normalized

    def _apply_rules(self, user_id: str, run_id: str, normalized: list[dict], profile: dict) -> list[dict]:
        now_date = datetime.now(timezone.utc).date().isoformat()
        p_industry = set(profile["industries"])
        p_state = profile["state_territory"].upper()
        p_headcount = int(profile.get("headcount", 0))
        candidates: list[dict] = []
        for row in normalized:
            reasons = []
            score = 0
            fail_reasons = []

            if row["deadline"] < now_date:
                fail_reasons.append("deadline passed")
            else:
                score += 20
                reasons.append("deadline active")

            allowed_locations = set(row.get("criteria_locations") or [row["location"]])
            if allowed_locations and p_state not in allowed_locations and "AU" not in allowed_locations:
                fail_reasons.append("location mismatch")
            else:
                score += 30
                reasons.append("location match")

            allowed_industries = set(row.get("criteria_industries") or row["industry"])
            if allowed_industries and not allowed_industries.intersection(p_industry):
                fail_reasons.append("industry mismatch")
            else:
                score += 25
                reasons.append("industry match")

            if row["min_size"] <= p_headcount <= row["max_size"]:
                score += 15
                reasons.append("size match")
            elif row.get("criteria_business_size"):
                fail_reasons.append("size mismatch")

            negative_blob = " ".join(row.get("criteria_not_allowed", [])).lower()
            if negative_blob:
                if "outside nsw" in negative_blob and p_state == "NSW":
                    fail_reasons.append("explicitly excludes NSW businesses")
                if "outside victoria" in negative_blob and p_state == "VIC":
                    fail_reasons.append("explicitly excludes Victorian businesses")

            rule_status = "pass" if not fail_reasons and score >= 55 else "fail"
            candidates.append(
                {
                    "normalized_id": row["normalized_id"],
                    "rule_status": rule_status,
                    "rule_score": score,
                    "rule_reasons": fail_reasons or reasons,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        self._repository.add_grant_match_candidates(user_id=user_id, run_id=run_id, records=candidates)
        return candidates

    def _ai_assess(self, user_id: str, run_id: str, normalized: list[dict], candidates: list[dict], profile: dict) -> list[dict]:
        normalized_by_id = {row["normalized_id"]: row for row in normalized}
        assessments: list[dict] = []
        for cand in candidates:
            if cand["rule_status"] != "pass":
                continue
            row = normalized_by_id[cand["normalized_id"]]
            business_profile = {
                "business_name": profile.get("company_name", ""),
                "industry": profile.get("industries", []),
                "location": profile.get("state_territory", ""),
                "employee_count": int(profile.get("headcount", 0)),
                "revenue": int(profile.get("revenue", 0)),
                "goals": profile.get("goals", []),
            }
            ai = self._ai.assess_eligibility(
                business_profile=business_profile,
                grant_structured_data=row,
                eligibility_text=row.get("relevant_text") or row["eligibility_text"],
            )
            assessments.append(
                {
                    "normalized_id": row["normalized_id"],
                    "eligibility": ai["eligibility"],
                    "confidence": ai["confidence"],
                    "key_reasons": ai["key_reasons"],
                    "missing_requirements": ai["missing_requirements"],
                    "recommended_action": ai["recommended_action"],
                    "rule_score": cand["rule_score"],
                    "model": "llama3-local" if ai else "deterministic",
                    "prompt_version": "eligibility-v2",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        self._repository.add_grant_ai_assessments(user_id=user_id, run_id=run_id, records=assessments)
        return assessments

    def _project_dashboard(self, user_id: str, normalized: list[dict], assessments: list[dict]) -> list[GrantScanResult]:
        normalized_by_id = {row["normalized_id"]: row for row in normalized}
        results: list[GrantScanResult] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for assessment in assessments:
            if assessment["eligibility"] not in {"ELIGIBLE", "PARTIAL"}:
                continue
            row = normalized_by_id[assessment["normalized_id"]]
            score = min(100, round((int(assessment.get("rule_score", 0)) * 0.45) + (int(assessment["confidence"]) * 0.55)))
            results.append(
                GrantScanResult(
                    id=str(uuid4()),
                    source_id=row["source_id"],
                    source_name=row["provider"],
                    title=row["grant_name"],
                    published_at=now_iso[:10],
                    location=self._location_label(row["location"]),
                    industry=", ".join(row["industry"]),
                    details=row["description"],
                    funder=row["provider"],
                    program="Grant Program",
                    max_amount=f"AUD {row['funding_amount']:,}" if row["funding_amount"] else "TBD",
                    eligibility_criteria=row["eligibility_text"],
                    open_date=now_iso[:10],
                    close_date=row["deadline"],
                    application_url=row["url"],
                    target_sectors=json.dumps(row["industry"]),
                    url=row["url"],
                    due_date=row["deadline"],
                    grant_amount=f"AUD {row['funding_amount']:,}" if row["funding_amount"] else "TBD",
                    match_score=score,
                    eligible=assessment["eligibility"] == "ELIGIBLE",
                    eligibility_reason=", ".join(assessment["key_reasons"]),
                    recommended=score >= 75,
                    deadline_soon=self._deadline_soon(row["deadline"]),
                    manual_check_needed=False,
                    workflow_status="New",
                    status=assessment["eligibility"].lower(),
                    notes="; ".join(assessment["missing_requirements"]) if assessment["missing_requirements"] else "",
                    scanned_at=now_iso,
                )
            )
        self._repository.replace_grant_scan_results(results=results, user_id=user_id)
        return results

    def run_scan(self, user_id: str) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid4())
        debug_stats = {
            "scraped_count": 0,
            "heuristic_rejected_count": 0,
            "rule_rejected_count": 0,
            "cache_hit_count": 0,
            "ai_called_count": 0,
            "discovery_debugs": {},
        }
        preferences = self._profile_preferences(user_id)
        profile = preferences.get("profile")
        profile_payload = {
            "company_name": getattr(profile, "company_name", ""),
            "state_territory": preferences["state_territory"],
            "headcount": getattr(profile, "headcount", 0),
            "revenue": getattr(profile, "revenue", 0),
            "goals": self._safe_json_list(getattr(profile, "goals_json", "[]"), []),
            "industries": preferences["industries"],
        }
        raw = self._ingest_raw_records(user_id=user_id, run_id=run_id, preferences=preferences, debug_stats=debug_stats)
        normalized = self._normalize_records(user_id=user_id, run_id=run_id, raw_records=raw)
        candidates = self._apply_rules(user_id=user_id, run_id=run_id, normalized=normalized, profile=profile_payload)
        assessments = self._ai_assess(user_id=user_id, run_id=run_id, normalized=normalized, candidates=candidates, profile=profile_payload)
        results = self._project_dashboard(user_id=user_id, normalized=normalized, assessments=assessments)
        rule_fail_reasons: dict[str, int] = {}
        for cand in candidates:
            if cand["rule_status"] != "fail":
                continue
            for reason in cand.get("rule_reasons", []):
                rule_fail_reasons[reason] = rule_fail_reasons.get(reason, 0) + 1
        ai_eligible = len([a for a in assessments if a.get("eligibility") == "ELIGIBLE"])
        ai_partial = len([a for a in assessments if a.get("eligibility") == "PARTIAL"])
        ai_rejected = len([a for a in assessments if a.get("eligibility") == "NOT_ELIGIBLE"])
        return {
            "run_id": run_id,
            "scraped_count": int(debug_stats["scraped_count"]),
            "heuristic_rejected_count": int(debug_stats["heuristic_rejected_count"]),
            "rule_rejected_count": int(debug_stats["rule_rejected_count"]),
            "cache_hit_count": int(debug_stats["cache_hit_count"]),
            "ai_called_count": int(debug_stats["ai_called_count"]),
            "projected_count": len(results),
            "raw_count": len(raw),
            "normalized_count": len(normalized),
            "rule_candidate_count": len([r for r in candidates if r["rule_status"] == "pass"]),
            "assessment_count": len(assessments),
            "ai_eligible_count": ai_eligible,
            "ai_partial_count": ai_partial,
            "ai_rejected_count": ai_rejected,
            "rule_fail_reasons": rule_fail_reasons,
            "pipeline_runs": self._repository.list_grant_pipeline_runs(user_id=user_id, run_id=run_id),
            "discovery_debugs": debug_stats.get("discovery_debugs", {}),
            "scanned_count": len(results),
            "eligible_count": len([row for row in results if row.eligible]),
            "partial_count": len([row for row in results if row.status == "partial"]),
            "scanned_at": now_iso,
            "results": [row.__dict__ for row in results],
        }

    def board_list(self, user_id: str, filters: dict | None = None, sort_by: str = "deadline") -> dict:
        filters = filters or {}
        rows = self._repository.list_grant_scan_results(limit=500, user_id=user_id)
        items: list[GrantScanResult] = []
        for row in rows:
            if filters.get("state") and filters["state"].upper() not in row.location.upper():
                continue
            if filters.get("sector") and filters["sector"].lower() not in row.industry.lower():
                continue
            if filters.get("min_score") and row.match_score < int(filters["min_score"]):
                continue
            if filters.get("max_score") and row.match_score > int(filters["max_score"]):
                continue
            items.append(row)

        if sort_by == "amount":
            items.sort(key=lambda r: r.grant_amount, reverse=True)
        elif sort_by == "score":
            items.sort(key=lambda r: r.match_score, reverse=True)
        else:
            items.sort(key=lambda r: r.due_date)

        board = {name: [] for name in DEFAULT_BOARD_COLUMNS}
        for row in items:
            board.setdefault(row.workflow_status, [])
            board[row.workflow_status].append(row.__dict__)
        return {"board": board, "count": len(items)}

    def move_status(self, user_id: str, grant_result_id: str, workflow_status: str) -> None:
        if workflow_status not in DEFAULT_BOARD_COLUMNS:
            raise ValueError("invalid workflow status")
        self._repository.update_grant_scan_result(user_id=user_id, result_id=grant_result_id, workflow_status=workflow_status)

    def mark_reviewed(self, user_id: str, grant_result_id: str) -> None:
        self._repository.update_grant_scan_result(user_id=user_id, result_id=grant_result_id, workflow_status="Under Review")

    def mark_submitted(self, user_id: str, grant_result_id: str) -> None:
        self._repository.update_grant_scan_result(
            user_id=user_id,
            result_id=grant_result_id,
            workflow_status="Submitted",
            submission_date=datetime.now(timezone.utc).date().isoformat(),
        )

    def update_tracking(self, user_id: str, grant_result_id: str, notes: str, outcome: str, contact_names: str, reference_numbers: str) -> None:
        self._repository.update_grant_scan_result(
            user_id=user_id,
            result_id=grant_result_id,
            notes=notes,
            outcome=outcome,
            contact_names=contact_names,
            reference_numbers=reference_numbers,
        )

    def _build_draft(self, grant: GrantScanResult, business_profile: str, prompt: str = "") -> str:
        base = f"""Executive Summary
This proposal targets {grant.program} by {grant.funder} with requested support up to {grant.max_amount}.

Project Description
The project aligns with {grant.industry} priorities and addresses the stated business objectives.

Budget Justification
Funding will be allocated to capability build, delivery, and measurable outcomes.

Outcomes
Expected outcomes include revenue uplift, jobs impact, and measurable program KPIs.
"""
        if prompt.strip():
            base += f"\nAdditional direction:\n{prompt.strip()}\n"
        llm_prompt = (
            "You are a grant writing assistant. Improve the following draft for clarity and persuasion. "
            f"Business profile: {business_profile}\nGrant: {grant.title}\nDraft:\n{base}"
        )
        return self._ai.summarize_and_compare(prompt=llm_prompt, fallback=base)

    def create_or_regenerate_draft(self, user_id: str, grant_result_id: str, prompt: str = "") -> dict:
        rows = self._repository.list_grant_scan_results(limit=500, user_id=user_id)
        grant = next((row for row in rows if row.id == grant_result_id), None)
        if grant is None:
            raise KeyError("grant not found")
        profile = self._repository.get_user_profile(user_id)
        profile_text = json.dumps(profile.__dict__) if profile else "{}"
        versions = self._repository.list_grant_drafts(user_id=user_id, grant_result_id=grant_result_id)
        next_version = (versions[0].version + 1) if versions else 1
        content = self._build_draft(grant=grant, business_profile=profile_text, prompt=prompt)
        draft = GrantDraft(
            id=str(uuid4()),
            grant_result_id=grant_result_id,
            user_id=user_id,
            version=next_version,
            content=content,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repository.create_grant_draft(draft)
        self._repository.update_grant_scan_result(user_id=user_id, result_id=grant_result_id, workflow_status="In Progress")
        return {"draft": draft.__dict__}

    def list_drafts(self, user_id: str, grant_result_id: str) -> dict:
        drafts = self._repository.list_grant_drafts(user_id=user_id, grant_result_id=grant_result_id)
        return {"drafts": [row.__dict__ for row in drafts]}

    def pipeline_run_details(self, user_id: str, run_id: str) -> dict:
        raw = self._repository.list_grant_raw_records(user_id=user_id, run_id=run_id)
        normalized = self._repository.list_grant_normalized_records(user_id=user_id, run_id=run_id)
        candidates = self._repository.list_grant_match_candidates(user_id=user_id, run_id=run_id)
        assessments = self._repository.list_grant_ai_assessments(user_id=user_id, run_id=run_id)
        pipeline_runs = self._repository.list_grant_pipeline_runs(user_id=user_id, run_id=run_id)
        return {
            "run_id": run_id,
            "pipeline_runs": pipeline_runs,
            "raw_records": raw,
            "normalized_records": normalized,
            "rule_candidates": candidates,
            "ai_assessments": assessments,
        }

    def search(self, user_id: str, query: str) -> dict:
        needle = query.strip().lower()
        if len(needle) < 2:
            return {"results": [], "summary": "Type at least 2 characters to search grants."}
        rows = self._repository.list_grant_scan_results(limit=500, user_id=user_id)
        matched = []
        for row in rows:
            blob = " ".join(
                [
                    row.title,
                    row.funder,
                    row.program,
                    row.eligibility_criteria,
                    row.industry,
                    row.location,
                    row.details,
                ]
            ).lower()
            if needle in blob:
                matched.append(row)
        matched.sort(key=lambda row: (needle in row.title.lower(), row.match_score, row.due_date), reverse=True)
        if len(needle) >= 8 and matched and needle in matched[0].title.lower():
            matched = matched[:1]
        else:
            matched = matched[:25]
        summary_input = [
            {
                "title": row.title,
                "score": row.match_score,
                "deadline": row.due_date,
                "industry": row.industry,
                "criteria": row.eligibility_criteria,
                "recommended": row.recommended,
            }
            for row in matched[:8]
        ]
        fallback = (
            f"Found {len(matched)} matching grants. Top results are ranked by criteria fit and deadline proximity."
            if matched
            else "No matching grants found. Try a broader keyword (industry, funder, or program)."
        )
        prompt = (
            "Summarise the search results and compare their criteria in concise bullet points for a grant writer user. "
            f"Query: {query}\nResults: {json.dumps(summary_input)}"
        )
        summary = self._ai.summarize_and_compare(prompt=prompt, fallback=fallback)
        return {"results": [row.__dict__ for row in matched], "summary": summary}
