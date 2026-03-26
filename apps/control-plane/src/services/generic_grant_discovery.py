from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from models.entities import ExtractedGrant, GrantSource, NormalizedGrant
from models.repository_protocol import OpportunityRepository
from services.ai_agent_service import AIAgentService
from services.api_discovery_service import ApiDiscoveryService
from services.scraper_cluster import ScrapeJob, ScraperCluster

KEYWORDS = (
    "grant",
    "fund",
    "funding",
    "program",
    "incentive",
    "apply",
    "round",
    "support",
    "assistance",
)
KEY_SECTIONS = (
    "eligibility",
    "who can apply",
    "requirements",
    "criteria",
    "funding",
    "deadline",
    "closing date",
    "how to apply",
)

BLOCKED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".ico", ".zip")
PAGE_TYPES = ("LISTING", "DETAIL", "SEARCH", "LANDING", "UNKNOWN")
KNOWN_SITES = {
    "nsw.gov.au": "nsw_parser",
    "business.gov.au": "au_grants_parser",
    "grants.gov.au": "au_grants_parser",
}

SOURCE_CONFIGS = {
    "src-arena": {
        "name": "ARENA",
        "type": "STATIC",
        "link_pattern": "/funding",
        "pagination": {"type": "none"},
    },
    "src-csiro": {
        "name": "CSIRO SME Programs",
        "type": "STATIC",
        "link_pattern": "program",
        "pagination": {"type": "none"},
    },
    "src-grantconnect": {
        "name": "GrantConnect",
        "type": "API",
        "link_pattern": "grants",
        "pagination": {"type": "query_param", "param": "page"},
    },
    "src-nsw-grants": {
        "name": "NSW Grants",
        "type": "JS",
        "link_pattern": "grant",
        "pagination": {"type": "next_button"},
    },
    "src-business-qld": {
        "name": "QLD Grants",
        "type": "STATIC",
        "link_pattern": "grant",
        "pagination": {"type": "none"},
    },
    "src-business-vic": {
        "name": "VIC Grants",
        "type": "JS",
        "link_pattern": "grants",
        "pagination": {"type": "query_param", "param": "page"},
    },
    "src-business-gov-au": {
        "name": "business.gov.au Grants Finder",
        "type": "API",
        "link_pattern": "grants",
        "pagination": {"type": "query_param", "param": "page"},
    },
}

MONTHS_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
DATE_PATTERNS = [
    re.compile(rf"(?:closing date|deadline|close date)[^.\n:]{{0,40}}(\d{{1,2}}\s+{MONTHS_RE}[a-z]*\s+\d{{4}})", re.I),
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{1,2}/\d{1,2}/\d{4})"),
]
AMOUNT_PATTERNS = [
    re.compile(r"(AUD\s?\$?\s?\d[\d,]*(?:\.\d+)?)", re.I),
    re.compile(r"(\$\s?\d[\d,]*(?:\.\d+)?)"),
]


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href = ""
        self._text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = ""
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value.strip()
                break
        self._current_href = href
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._text_parts.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return
        text = " ".join(part for part in self._text_parts if part).strip()
        self.links.append((self._current_href, text))
        self._current_href = ""
        self._text_parts = []


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        cleaned = data.strip()
        if cleaned:
            self._chunks.append(cleaned)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


class GenericGrantDiscovery:
    def __init__(self, ai: AIAgentService | None = None, repository: OpportunityRepository | None = None) -> None:
        self._ai = ai or AIAgentService()
        self._repository = repository
        self._api_discovery = ApiDiscoveryService()
        self._cluster = ScraperCluster()
        self._timeout = float(os.getenv("GRANT_DISCOVERY_TIMEOUT_SEC", "6"))
        self._max_items = int(os.getenv("GRANT_DISCOVERY_MAX_ITEMS_PER_SOURCE", "2"))
        self._max_text_chars = int(os.getenv("GRANT_DISCOVERY_MAX_TEXT_CHARS", "3000"))
        self._max_pages = int(os.getenv("GRANT_DISCOVERY_MAX_LISTING_PAGES", "2"))
        self._max_links = int(os.getenv("GRANT_DISCOVERY_MAX_LISTING_LINKS", "20"))
        self._source_budget_sec = float(os.getenv("GRANT_DISCOVERY_SOURCE_BUDGET_SEC", "20"))
        self._playwright_fallback_enabled = os.getenv("GRANT_DISCOVERY_ENABLE_PLAYWRIGHT_FALLBACK", "0") == "1"

    def discover(
        self,
        source: GrantSource,
        preferences: dict,
        user_id: str = "global",
        stats: dict | None = None,
    ) -> list[dict]:
        started_at = time.perf_counter()
        discovery_debug: dict | None = None
        if stats and isinstance(stats.get("discovery_debugs"), dict):
            discovery_debug = stats["discovery_debugs"].setdefault(source.id, {})
        config = self._get_source_config(source)
        site = self.detect_site(source.url)
        if discovery_debug is not None:
            discovery_debug.update(
                {
                    "source_id": source.id,
                    "source_name": source.name,
                    "url": source.url,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "registry_status": "known" if config else "new",
                    "site": site["domain"],
                    "source_detection": site["type"],
                    "fetch_status": "pending",
                    "content_length": 0,
                    "page_type": "",
                    "links_found": 0,
                    "links_after_filter": 0,
                    "final_selected_count": 0,
                    "detail_pages_processed": 0,
                    "successful_extractions": 0,
                    "normalized_count": 0,
                    "deduplicated_count": 0,
                    "heuristic_rejected_count": 0,
                    "rule_rejected_count": 0,
                    "cache_hit_count": 0,
                    "ai_called_count": 0,
                    "failed_step": "",
                    "error_message": "",
                    "raw_preview": "",
                    "sample_output": [],
                    "detail_urls": [],
                    "extracted_links": [],
                    "filtered_links": [],
                    "selected_links": [],
                }
            )
        api_config = None
        if self._repository is not None:
            api_config = self._repository.get_grant_source_api_config(user_id=user_id, source_id=source.id)
        if not api_config and config and config.get("type") == "API":
            discovered = self._api_discovery.discover(source.url, debug=discovery_debug)
            if discovered and self._repository is not None:
                self._repository.upsert_grant_source_api_config(user_id=user_id, source_id=source.id, config=discovered)
                api_config = discovered
        source_type, source_signals = self._detect_source_type(source.url, config=config, api_config=api_config)
        if discovery_debug is not None:
            discovery_debug["source_type"] = source_type
            discovery_debug["source_signals"] = source_signals
            if config:
                discovery_debug["config"] = config
            if api_config:
                discovery_debug["api_config"] = api_config
        memory = None
        if self._repository is not None:
            memory = self._repository.get_grant_source_memory(user_id=user_id, source_id=source.id)
        links: list[tuple[str, str]] = []
        if source_type == "API" and api_config:
            if discovery_debug is not None:
                discovery_debug["fetch_status"] = "success"
                discovery_debug["page_type"] = "LISTING"
                discovery_debug["fetch_method"] = "api"
            links = self._extract_links(
                source.url,
                html="",
                site_type=site["type"],
                memory=memory,
                config=config,
                api_config=api_config,
                debug=discovery_debug,
            )
        else:
            listing_fetch = self._fetch_artifact(source.url, source_type=source_type, source_id=source.id)
            if not listing_fetch["ok"]:
                if discovery_debug is not None:
                    discovery_debug["fetch_status"] = "failed"
                    discovery_debug["failed_step"] = "FETCH_CONTENT"
                    discovery_debug["error_message"] = str(listing_fetch.get("error", "listing fetch failed"))
                    discovery_debug["fetch_method"] = str(listing_fetch.get("fetch_method", ""))
                return []
            listing_html = str(listing_fetch.get("raw_html", ""))
            if discovery_debug is not None:
                discovery_debug["fetch_status"] = "success"
                discovery_debug["fetch_method"] = str(listing_fetch.get("fetch_method", ""))
                discovery_debug["content_type"] = str(listing_fetch.get("content_type", ""))
                discovery_debug["content_length"] = int(listing_fetch.get("content_length", len(listing_html)))
                discovery_debug["raw_preview"] = listing_html[:1000]
            links = self._extract_links(
                source.url,
                listing_html,
                site_type=site["type"],
                memory=memory,
                config=config,
                api_config=api_config,
                debug=discovery_debug,
            )
        if not links:
            if discovery_debug is not None and not discovery_debug.get("error_message"):
                discovery_debug["failed_step"] = "LISTING_EXTRACTION"
                discovery_debug["error_message"] = "no candidate links found"
            return []
        if time.perf_counter() - started_at > self._source_budget_sec:
            if discovery_debug is not None:
                discovery_debug["failed_step"] = "SOURCE_TIMEOUT"
                discovery_debug["error_message"] = "source time budget exhausted after listing extraction"
            return []

        now = datetime.now(timezone.utc)
        open_date = now.date().isoformat()
        fallback_deadline = f"{now.year}-12-31"
        state = self._infer_state(source)
        states = {state} if state != "AU" else {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"}

        out: list[dict] = []
        seen_items: set[str] = set()
        selected_links = self._dedupe_link_records(links)[: self._max_items]
        if discovery_debug is not None:
            discovery_debug["final_selected_count"] = len(selected_links)
            discovery_debug["detail_pages_processed"] = len(selected_links)
            discovery_debug["detail_urls"] = [url for url, _ in selected_links]
        detail_fetch_map: dict[str, dict] = {}
        for url, _ in selected_links:
            if time.perf_counter() - started_at > self._source_budget_sec:
                if discovery_debug is not None:
                    discovery_debug["failed_step"] = "SOURCE_TIMEOUT"
                    discovery_debug["error_message"] = "source time budget exhausted during detail fetch"
                break
            detail_type, detail_signals = self._detect_source_type(url, config=None, api_config=None)
            fetch = self._fetch_artifact(url, source_type=detail_type, source_id=source.id)
            fetch["detail_type"] = detail_type
            fetch["detail_signals"] = detail_signals
            detail_fetch_map[url] = fetch
        for url, anchor_text in selected_links:
            if time.perf_counter() - started_at > self._source_budget_sec:
                if discovery_debug is not None and not discovery_debug.get("failed_step"):
                    discovery_debug["failed_step"] = "SOURCE_TIMEOUT"
                    discovery_debug["error_message"] = "source time budget exhausted during field extraction"
                break
            key = f"{url}|{anchor_text}".lower()
            if key in seen_items:
                if discovery_debug is not None:
                    discovery_debug["deduplicated_count"] = int(discovery_debug.get("deduplicated_count", 0)) + 1
                continue
            seen_items.add(key)
            detail_fetch = detail_fetch_map.get(url, {})
            if not detail_fetch.get("ok"):
                if discovery_debug is not None and not discovery_debug.get("failed_step"):
                    discovery_debug["failed_step"] = "DETAIL_FETCH"
                    discovery_debug["error_message"] = str(detail_fetch.get("error", "detail fetch failed"))
                continue
            raw_item = self._build_raw_item(
                url=url,
                anchor_text=anchor_text,
                raw_html=str(detail_fetch.get("raw_html", "")),
                source=source,
            )
            if stats is not None:
                stats["scraped_count"] = int(stats.get("scraped_count", 0)) + 1
            if not self.heuristic_filter(raw_item):
                if stats is not None:
                    stats["heuristic_rejected_count"] = int(stats.get("heuristic_rejected_count", 0)) + 1
                if discovery_debug is not None:
                    discovery_debug["heuristic_rejected_count"] = int(discovery_debug.get("heuristic_rejected_count", 0)) + 1
                continue
            if not self.rule_engine(raw_item, user_profile={"location": preferences.get("state_territory", state)}):
                if stats is not None:
                    stats["rule_rejected_count"] = int(stats.get("rule_rejected_count", 0)) + 1
                if discovery_debug is not None:
                    discovery_debug["rule_rejected_count"] = int(discovery_debug.get("rule_rejected_count", 0)) + 1
                continue
            cache_before = int(stats.get("cache_hit_count", 0)) if stats is not None else 0
            ai_before = int(stats.get("ai_called_count", 0)) if stats is not None else 0
            extracted = self.process_item(raw_item=raw_item, provider=source.name, fallback_location=state, user_id=user_id, stats=stats)
            if discovery_debug is not None:
                if stats is not None:
                    discovery_debug["cache_hit_count"] = int(discovery_debug.get("cache_hit_count", 0)) + max(
                        0, int(stats.get("cache_hit_count", 0)) - cache_before
                    )
                    discovery_debug["ai_called_count"] = int(discovery_debug.get("ai_called_count", 0)) + max(
                        0, int(stats.get("ai_called_count", 0)) - ai_before
                    )
            if not self._is_valid_structured(extracted):
                continue
            extracted_grant = self._build_extracted_grant(
                extracted=extracted,
                raw_item=raw_item,
                source=source,
                fetch_method=str(detail_fetch.get("fetch_method", "")),
            )
            normalized = self._normalize_discovery(extracted_grant, source)
            if discovery_debug is not None:
                discovery_debug["successful_extractions"] = int(discovery_debug.get("successful_extractions", 0)) + 1
                discovery_debug["normalized_count"] = int(discovery_debug.get("normalized_count", 0)) + 1
            out.append(
                {
                    "title": normalized.title,
                    "funder": normalized.provider or source.name,
                    "program": "Discovered opportunity",
                    "max_amount": normalized.amount_display or "TBD",
                    "eligibility_criteria": normalized.eligibility_summary or "See source page for full criteria.",
                    "open_date": open_date,
                    "close_date": normalized.deadline_iso or fallback_deadline,
                    "application_url": normalized.detail_url,
                    "target_sectors": normalized.criteria_industries or normalized.industry or preferences["industries"],
                    "location": normalized.location_display or (f"{state}, Australia" if state != "AU" else "National, Australia"),
                    "industry": (normalized.industry or preferences["industries"] or ["technology"])[0],
                    "details": self._details_text(asdict(normalized), source_url=source.url),
                    "criteria_industries": normalized.criteria_industries,
                    "criteria_locations": normalized.criteria_locations,
                    "criteria_business_size": normalized.criteria_business_size,
                    "criteria_must_have": normalized.criteria_must_have,
                    "criteria_not_allowed": normalized.criteria_not_allowed,
                    "relevant_text": normalized.relevant_text,
                    "company_sizes": {"micro", "small", "medium", "large"},
                    "states": states,
                    "stages": {"pre-revenue", "early", "growth", "established"},
                    "text_content": raw_item["text_content"],
                    "scrape_timestamp": raw_item["timestamp"],
                    "discovery_extracted": asdict(extracted_grant),
                    "discovery_normalized": asdict(normalized),
                }
            )
        if discovery_debug is not None:
            discovery_debug["sample_output"] = [row.get("discovery_normalized", {}) for row in out[:2]]
            if not out and not discovery_debug.get("failed_step"):
                discovery_debug["failed_step"] = "FIELD_EXTRACTION"
                discovery_debug["error_message"] = "no valid structured grant items extracted"
        if self._repository is not None:
            self._store_memory(user_id=user_id, source_id=source.id, links=links, results=out, debug=discovery_debug)
        return out

    def detect_site(self, url: str) -> dict:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        parser = KNOWN_SITES.get(domain)
        return {
            "domain": domain,
            "type": "KNOWN" if parser else "UNKNOWN",
            "parser": parser or "generic_extractor",
        }

    def extract_candidate_links(self, base_url: str, html: str) -> list[tuple[str, str]]:
        return self._extract_links(base_url=base_url, html=html, site_type="UNKNOWN", memory=None, config=None, api_config=None, debug=None)

    def discovery_debug(self, source: GrantSource, preferences: dict, user_id: str) -> dict:
        listing_html = self._fetch(source.url)
        if not listing_html:
            return {"error": "listing fetch failed"}
        site = self.detect_site(source.url)
        memory = None
        if self._repository is not None:
            memory = self._repository.get_grant_source_memory(user_id=user_id, source_id=source.id)
        api_config = None
        if self._repository is not None:
            api_config = self._repository.get_grant_source_api_config(user_id=user_id, source_id=source.id)
        config = self._get_source_config(source)
        debug: dict = {}
        links = self._extract_links(
            base_url=source.url,
            html=listing_html,
            site_type=site["type"],
            memory=memory,
            config=config,
            api_config=api_config,
            debug=debug,
        )
        return {
            "source_id": source.id,
            "source_url": source.url,
            "listing_detected": debug.get("listing_detected", False),
            "extracted_links": debug.get("extracted_links", []),
            "filtered_links": debug.get("filtered_links", []),
            "selected_links": [url for url, _ in links],
            "top_patterns": debug.get("top_patterns", []),
            "pagination_chain": debug.get("pagination_chain", []),
            "config": debug.get("config", {}),
            "api_config": debug.get("api_config", {}),
        }

    def _extract_links(
        self,
        base_url: str,
        html: str,
        site_type: str,
        memory: dict | None,
        config: dict | None,
        api_config: dict | None,
        debug: dict | None,
    ) -> list[tuple[str, str]]:
        if config and config.get("type") == "API" and api_config:
            api_urls, api_items = self._extract_items_from_api(api_config, debug=debug)
            if api_items:
                selected = self._build_records_from_api_items(api_items, base_url=base_url)
                if debug is not None:
                    debug["page_type"] = "LISTING"
                    debug["links_found"] = len(api_items)
                    debug["links_after_filter"] = len(selected)
                    debug["selected_links"] = [url for url, _ in selected][:100]
                return selected
            if api_urls:
                if debug is not None:
                    debug["page_type"] = "LISTING"
                    debug["links_found"] = len(api_urls)
                    debug["links_after_filter"] = len(api_urls)
                    debug["selected_links"] = [url for url, _ in api_urls][:100]
                return api_urls[: self._max_links]
        parser = _LinkParser()
        parser.feed(html)
        base = urlparse(base_url)
        all_links = self._normalise_links(base_url=base_url, links=parser.links)
        if debug is not None:
            debug["extracted_links"] = [url for url, _ in all_links][:100]
            debug["links_found"] = len(all_links)
            debug.setdefault("filtered_links", [])
            debug.setdefault("selected_links", [])
            if config:
                debug["config"] = config
            if api_config:
                debug["api_config"] = api_config
        page_type, page_signals = self._detect_page_type(html=html, links=all_links)
        listing_detected = page_type in {"LISTING", "SEARCH"}
        if debug is not None:
            debug["listing_detected"] = listing_detected
            debug["page_type"] = page_type
            debug["page_signals"] = page_signals

        pages = [(base_url, html)]
        pagination_chain: list[str] = []
        if listing_detected:
            pages = self._expand_pagination(base_url, html, memory=memory, config=config, chain=pagination_chain)
        if debug is not None:
            debug["pagination_chain"] = pagination_chain

        merged_links: list[tuple[str, str]] = []
        for page_url, page_html in pages:
            parser = _LinkParser()
            parser.feed(page_html)
            merged_links.extend(self._normalise_links(base_url=page_url, links=parser.links))

        deduped_merged = self._dedupe_link_records(merged_links)
        filtered = self._filter_candidate_links(deduped_merged, memory=memory, config=config)
        if not filtered:
            ai_links = self._ai_fallback_links(base_url=base_url, html=html)
            filtered = [(self._canonical_url(url), "") for url in ai_links]

        if debug is not None:
            debug["filtered_links"] = [url for url, _ in filtered][:100]
            debug["links_after_filter"] = len(filtered)

        top_patterns = self._cluster_patterns(filtered)
        if debug is not None:
            debug["top_patterns"] = top_patterns[:3]

        scored: list[tuple[int, str, str]] = []
        seen: set[str] = set()
        for url, text in filtered:
            if url in seen:
                continue
            seen.add(url)
            parsed = urlparse(url)
            score = self._score_link(base, parsed, text, site_type=site_type, top_patterns=top_patterns)
            if score <= 0:
                continue
            scored.append((score, url, text))
        scored.sort(key=lambda row: row[0], reverse=True)
        selected = [(url, text) for _, url, text in scored[: self._max_links]]
        if debug is not None:
            debug["selected_links"] = [url for url, _ in selected][:100]
            debug["final_selected_count"] = len(selected)
        return selected

    def _fetch(self, url: str) -> str:
        req = Request(
            url,
            headers={
                "User-Agent": "OpportunityOS-GrantDiscovery/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
            method="GET",
        )
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                content_type = (resp.headers.get("Content-Type", "") or "").lower()
                if "html" not in content_type and "xml" not in content_type:
                    return ""
                return resp.read().decode("utf-8", errors="ignore")
        except (URLError, TimeoutError, OSError, ValueError):
            return ""

    def _fetch_artifact(self, url: str, source_type: str, source_id: str) -> dict:
        artifact = {
            "ok": False,
            "url": url,
            "fetch_method": source_type.lower(),
            "content_type": "",
            "content_length": 0,
            "raw_html": "",
            "raw_json": None,
            "error": "",
        }
        try:
            if source_type == "API":
                data = self._cluster.fetch_json(url)
                if data is None:
                    artifact["error"] = "api fetch failed"
                    return artifact
                raw = json.dumps(data)
                artifact.update(
                    {
                        "ok": True,
                        "fetch_method": "api",
                        "content_type": "application/json",
                        "content_length": len(raw),
                        "raw_json": data,
                    }
                )
                return artifact
            html = self._cluster.fetch_html(ScrapeJob(url=url, source_type=source_type, source_id=source_id))
            if not html and self._playwright_fallback_enabled and self._api_discovery.is_enabled():
                html = self._api_discovery.fetch_page_html(url) or ""
                if html:
                    artifact["fetch_method"] = "playwright-dom"
            if not html:
                artifact["error"] = "html fetch failed"
                return artifact
            artifact.update(
                {
                    "ok": True,
                    "content_type": "text/html",
                    "content_length": len(html),
                    "raw_html": html,
                }
            )
            return artifact
        except Exception as exc:
            artifact["error"] = str(exc)
            return artifact

    def _fetch_probe(self, url: str) -> tuple[str, int]:
        req = Request(
            url,
            headers={
                "User-Agent": "OpportunityOS-GrantDiscovery/1.0",
                "Accept": "*/*",
            },
            method="GET",
        )
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                content_type = (resp.headers.get("Content-Type", "") or "").lower()
                raw = resp.read(2048)
                return content_type, len(raw)
        except (URLError, TimeoutError, OSError, ValueError):
            return "", 0

    def _score_link(self, base, parsed, text: str, site_type: str, top_patterns: list[str]) -> int:
        score = 0
        if parsed.netloc == base.netloc:
            score += 40
        path = parsed.path.strip("/")
        if not path:
            return -100
        depth = len([part for part in path.split("/") if part])
        if depth >= 2:
            score += 20
        elif depth == 1:
            score += 5
        lower_blob = f"{path} {text}".lower()
        kw_hits = sum(1 for k in KEYWORDS if k in lower_blob)
        score += kw_hits * 10
        pattern = self._link_pattern(parsed.path)
        if pattern and pattern in top_patterns:
            score += 15
        if pattern and any(token in pattern.lower() for token in KEYWORDS):
            score += 15
        if site_type == "KNOWN":
            score += 10
        if any(token in lower_blob for token in ("news", "media", "contact", "privacy", "terms", "about")):
            score -= 30
        return score

    def _normalise_links(self, base_url: str, links: list[tuple[str, str]]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for href, text in links:
            href = href.strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.path.lower().endswith(BLOCKED_EXTENSIONS):
                continue
            if full in seen:
                continue
            seen.add(full)
            out.append((full, text))
        return out

    def _detect_page_type(self, html: str, links: list[tuple[str, str]]) -> tuple[str, dict]:
        low = html.lower()
        keyword_hits = sum(1 for url, text in links if self._is_candidate_link(url) or self._is_candidate_text(text))
        top_patterns = self._cluster_patterns(links)
        listing_score = min(100, (len(links) * 2) + (keyword_hits * 6) + (25 if top_patterns else 0))
        detail_score = 0
        if "<h1" in low:
            detail_score += 20
        if "deadline" in low or "closing date" in low:
            detail_score += 20
        if "eligibility" in low or "who can apply" in low:
            detail_score += 20
        if any(token in low for token in ("apply now", "application form", "submit application")):
            detail_score += 15
        if len(links) <= 6:
            detail_score += 20
        search_score = 20 if any(token in low for token in ("search results", "filter", "sort by")) else 0
        if len(links) > 24 or (keyword_hits >= 5 and top_patterns):
            page_type = "LISTING"
        elif detail_score >= 45:
            page_type = "DETAIL"
        elif search_score >= 20:
            page_type = "SEARCH"
        elif len(links) >= 8:
            heuristic = keyword_hits >= 4
            page_type = "LISTING" if self._ai.classify_listing_page(cleaned_html=html, fallback=heuristic) else "LANDING"
        else:
            page_type = "LANDING" if len(links) > 0 else "UNKNOWN"
        return page_type, {
            "listing_score": listing_score,
            "detail_score": detail_score,
            "search_score": search_score,
            "keyword_hits": keyword_hits,
            "top_patterns": top_patterns[:3],
        }

    def _filter_candidate_links(self, links: list[tuple[str, str]], memory: dict | None, config: dict | None) -> list[tuple[str, str]]:
        filtered = []
        config_pattern = str(config.get("link_pattern", "")).lower() if config else ""
        for url, text in links:
            if config_pattern and config_pattern not in url.lower() and config_pattern not in text.lower():
                continue
            if not self._is_candidate_link(url) and not self._is_candidate_text(text) and not config_pattern:
                path = urlparse(url).path.lower()
                pattern = self._link_pattern(path)
                if len([part for part in path.strip("/").split("/") if part]) < 2 and not pattern:
                    continue
            filtered.append((url, text))
        if not filtered:
            filtered = links
        if memory and memory.get("link_pattern"):
            pattern = str(memory.get("link_pattern", "")).strip()
            if pattern:
                filtered = [(url, text) for url, text in filtered if pattern in url]
        return filtered

    def _cluster_patterns(self, links: list[tuple[str, str]]) -> list[str]:
        patterns = [self._link_pattern(urlparse(url).path) for url, _ in links]
        counts = Counter([p for p in patterns if p])
        return [pattern for pattern, _ in counts.most_common(3)]

    def _link_pattern(self, path: str) -> str:
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) < 2:
            return ""
        return "/" + "/".join(parts[:-1])

    def _expand_pagination(self, base_url: str, html: str, memory: dict | None, config: dict | None, chain: list[str]) -> list[tuple[str, str]]:
        pages = [(base_url, html)]
        current_url = base_url
        current_html = html
        pattern = str(memory.get("pagination_pattern", "")) if memory else ""
        if config and config.get("pagination", {}).get("type") == "query_param":
            param = config.get("pagination", {}).get("param", "page")
            for page in range(2, self._max_pages + 1):
                next_url = f"{base_url}?{param}={page}"
                chain.append(next_url)
                next_html = self._fetch(next_url)
                if not next_html:
                    break
                pages.append((next_url, next_html))
            return pages
        for _ in range(self._max_pages - 1):
            next_url = self._find_next_page(current_url, current_html, pattern)
            if not next_url or next_url in chain:
                break
            chain.append(next_url)
            next_html = self._fetch(next_url)
            if not next_html:
                break
            pages.append((next_url, next_html))
            current_url = next_url
            current_html = next_html
        return pages

    def _find_next_page(self, base_url: str, html: str, pattern: str) -> str | None:
        parser = _LinkParser()
        parser.feed(html)
        for href, text in parser.links:
            candidate = urljoin(base_url, href)
            if pattern and pattern in candidate:
                return candidate
            if "next" in text.lower() or "older" in text.lower() or "more" in text.lower():
                return candidate
            if "page=" in candidate or "p=" in candidate:
                return candidate
        return None

    def _extract_items_from_api(self, api_config: dict, debug: dict | None) -> tuple[list[tuple[str, str]], list[dict]]:
        endpoint = str(api_config.get("endpoint", "")).strip()
        if not endpoint:
            return [], []
        if debug is not None:
            debug["api_endpoint"] = endpoint
        data = self._fetch_api_json(endpoint)
        if data is None:
            if debug is not None:
                debug["error"] = "api fetch failed"
            return [], []
        items = self._api_discovery.extract_items_from_json(data)
        if not items:
            urls = self._api_discovery.extract_links_from_json(data)
            return [(url, "") for url in urls], []
        urls: list[str] = []
        for item in items:
            for key in ["url", "link", "href", "application_url", "apply_url", "grant_url"]:
                raw = item.get(key)
                if isinstance(raw, str) and raw.startswith("http"):
                    urls.append(raw)
        return [(url, "") for url in urls], items

    def _fetch_api_json(self, url: str) -> object | None:
        return self._cluster.fetch_json(url)

    def _source_type_from_config(self, config: dict | None) -> str:
        if not config:
            return "UNKNOWN"
        raw = str(config.get("type", "HTML")).upper()
        if raw in {"API", "JS"}:
            return raw
        if raw in {"STATIC", "HTML"}:
            return "STATIC"
        return "UNKNOWN"

    def _detect_source_type(self, url: str, config: dict | None = None, api_config: dict | None = None) -> tuple[str, dict]:
        config_type = self._source_type_from_config(config)
        signals: dict = {"config_type": config_type}
        if api_config:
            signals["api_config_present"] = True
            return "API", signals
        if config_type in {"API", "JS", "STATIC"}:
            signals["reason"] = "source config"
            return config_type, signals
        content_type, size = self._fetch_probe(url)
        signals["content_type"] = content_type
        signals["probe_size"] = size
        if "application/json" in content_type:
            signals["reason"] = "json content-type"
            return "API", signals
        shell = self._fetch(url)[:2000].lower()
        script_signals = sum(1 for token in ("__next_data__", "data-reactroot", "webpack", "vite", "apollo", "hydration") if token in shell)
        signals["script_signals"] = script_signals
        if size < 1000 or script_signals >= 2:
            signals["reason"] = "js-shell heuristics"
            return "JS", signals
        if size > 0:
            signals["reason"] = "html response"
            return "STATIC", signals
        signals["reason"] = "unknown"
        return "UNKNOWN", signals

    def _normalize_discovery(self, extracted: ExtractedGrant, source: GrantSource) -> NormalizedGrant:
        return NormalizedGrant(
            title=extracted.title,
            source=source.name,
            source_url=extracted.source_url,
            detail_url=extracted.detail_url,
            provider=extracted.provider,
            provider_raw=extracted.provider_raw,
            deadline=extracted.deadline_raw,
            deadline_iso=extracted.deadline_iso,
            amount=extracted.amount_raw,
            amount_display=extracted.amount_display,
            raw_text=extracted.raw_text,
            eligibility_summary=extracted.eligibility_summary,
            industry=list(extracted.industry),
            location_display=extracted.location_display,
            criteria_industries=list(extracted.criteria_industries),
            criteria_locations=list(extracted.criteria_locations),
            criteria_business_size=extracted.criteria_business_size,
            criteria_must_have=list(extracted.criteria_must_have),
            criteria_not_allowed=list(extracted.criteria_not_allowed),
            relevant_text=extracted.relevant_text,
            field_confidence=dict(extracted.field_confidence),
            evidence=dict(extracted.evidence),
        )

    def _build_records_from_api_items(self, items: list[dict], base_url: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for item in items[: self._max_links]:
            title = ""
            for key in ["title", "name", "programName", "grant_name"]:
                raw = item.get(key)
                if isinstance(raw, str) and raw.strip():
                    title = raw.strip()
                    break
            url = ""
            for key in ["url", "link", "href", "application_url", "apply_url", "grant_url"]:
                raw = item.get(key)
                if isinstance(raw, str) and raw.strip():
                    url = self._canonical_url(urljoin(base_url, raw.strip()))
                    break
            if not url:
                continue
            out.append((url, title))
        return out

    def _get_source_config(self, source: GrantSource) -> dict | None:
        config = SOURCE_CONFIGS.get(source.id)
        if config:
            return dict(config)
        for entry in SOURCE_CONFIGS.values():
            if entry.get("name", "").lower() in source.name.lower():
                return dict(entry)
        return None

    def _ai_fallback_links(self, base_url: str, html: str) -> list[str]:
        urls = self._ai.extract_links_from_html(cleaned_html=html)
        out: list[str] = []
        for url in urls:
            full = urljoin(base_url, url)
            if self._is_candidate_link(full):
                out.append(full)
        return out

    def _is_candidate_link(self, url: str) -> bool:
        low = url.lower()
        return any(key in low for key in KEYWORDS)

    def _is_candidate_text(self, text: str) -> bool:
        low = text.lower()
        return any(key in low for key in KEYWORDS)

    def _store_memory(self, user_id: str, source_id: str, links: list[tuple[str, str]], results: list[dict], debug: dict | None) -> None:
        if self._repository is None:
            return
        if not links:
            return
        success_rate = len(results) / max(1, len(links))
        patterns = []
        if debug and debug.get("top_patterns"):
            patterns = debug["top_patterns"]
        else:
            patterns = self._cluster_patterns(links)
        pagination_pattern = ""
        if debug and debug.get("pagination_chain"):
            first = debug["pagination_chain"][0] if debug["pagination_chain"] else ""
            if "page=" in first:
                pagination_pattern = "page="
            elif "p=" in first:
                pagination_pattern = "p="
        memory = {
            "link_pattern": patterns[0] if patterns else "",
            "pagination_pattern": pagination_pattern,
            "last_success_rate": round(success_rate, 3),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._repository.upsert_grant_source_memory(user_id=user_id, source_id=source_id, memory=memory)

    def _build_raw_item(self, url: str, anchor_text: str, raw_html: str, source: GrantSource) -> dict:
        return {
            "url": self._canonical_url(url),
            "title": self._title_from_link(anchor_text, url),
            "raw_html": raw_html,
            "text_content": self._clean_html_to_text(raw_html),
            "source": urlparse(source.url).netloc.lower().removeprefix("www."),
            "timestamp": datetime.now(timezone.utc).date().isoformat(),
        }

    def heuristic_filter(self, item: dict) -> bool:
        text = str(item.get("text_content", "")).lower()
        if len(text) < 200:
            return False
        return any(k in text for k in KEYWORDS)

    def extract_basic_fields(self, text: str) -> dict:
        amount = self._first_match(text, AMOUNT_PATTERNS)
        has_deadline = bool(self._first_match(text, DATE_PATTERNS) or re.search(r"(deadline|closing date|close date)", text, flags=re.I))
        return {
            "amount_found": bool(amount),
            "has_deadline": has_deadline,
        }

    def rule_engine(self, item: dict, user_profile: dict) -> bool:
        text = str(item.get("text_content", ""))
        fields = self.extract_basic_fields(text)
        if not (fields["amount_found"] or fields["has_deadline"]):
            return False
        location = str(user_profile.get("location", "")).strip().lower()
        low = text.lower()
        if location and location not in low and "australia" not in low:
            return False
        return True

    def process_item(self, raw_item: dict, provider: str, fallback_location: str, user_id: str, stats: dict | None = None) -> dict:
        cleaned_text = str(raw_item.get("text_content", ""))[: self._max_text_chars]
        focused_text = self.extract_relevant_sections(cleaned_text) or cleaned_text
        heuristic, heuristic_criteria = self._deterministic_extract(
            focused_text=focused_text,
            raw_item=raw_item,
            provider=provider,
            fallback_location=fallback_location,
        )
        if not cleaned_text:
            combined = dict(heuristic)
            combined.update(heuristic_criteria)
            combined["relevant_text"] = focused_text[:1200]
            return combined
        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
        stage = "grant_extract_v2"
        if self._repository is not None:
            cached = self._repository.get_ai_cache(stage=stage, content_hash=content_hash)
            if cached:
                if stats is not None:
                    stats["cache_hit_count"] = int(stats.get("cache_hit_count", 0)) + 1
                return self._merge_structured(cached, heuristic, heuristic_criteria, focused_text)
        if stats is not None:
            stats["ai_called_count"] = int(stats.get("ai_called_count", 0)) + 1
        merged = self._ai_complete_extraction(
            focused_text=focused_text,
            deterministic_fields=heuristic,
            deterministic_criteria=heuristic_criteria,
        )
        if self._repository is not None:
            self._repository.set_ai_cache(stage=stage, content_hash=content_hash, result=merged)
        return merged

    def _deterministic_extract(self, focused_text: str, raw_item: dict, provider: str, fallback_location: str) -> tuple[dict, dict]:
        heuristic = self._heuristic_extract(
            focused_text,
            anchor_text=str(raw_item.get("title", "")),
            url=str(raw_item.get("url", "")),
            provider=provider,
            fallback_location=fallback_location,
        )
        heuristic_criteria = self._heuristic_extract_criteria(
            focused_text,
            fallback_location=fallback_location,
            fallback_industry=heuristic.get("industry", []),
        )
        return heuristic, heuristic_criteria

    def _ai_complete_extraction(self, focused_text: str, deterministic_fields: dict, deterministic_criteria: dict) -> dict:
        ai = self._ai.extract_grant_fields(cleaned_text=focused_text, fallback=deterministic_fields)
        criteria = self._ai.extract_eligibility_criteria(cleaned_text=focused_text, fallback=deterministic_criteria)
        return self._merge_structured(ai, deterministic_fields, criteria, focused_text)

    def extract_relevant_sections(self, text: str) -> str:
        if not text:
            return ""
        snippets: list[str] = []
        seen: set[str] = set()
        lower = text.lower()
        for key in KEY_SECTIONS:
            start = 0
            while True:
                idx = lower.find(key, start)
                if idx < 0:
                    break
                left = max(0, idx - 180)
                right = min(len(text), idx + 320)
                snippet = re.sub(r"\s+", " ", text[left:right]).strip()
                start = idx + len(key)
                if len(snippet) < 50:
                    continue
                if snippet in seen:
                    continue
                seen.add(snippet)
                snippets.append(snippet)
        if snippets:
            return "\n".join(snippets)[: self._max_text_chars]
        return text[: min(len(text), 1200)]

    def _clean_html_to_text(self, html: str) -> str:
        if not html:
            return ""
        parser = _TextParser()
        parser.feed(html)
        text = parser.text()
        return text[: self._max_text_chars]

    def _heuristic_extract(self, text: str, anchor_text: str, url: str, provider: str, fallback_location: str) -> dict:
        amount = self._first_match(text, AMOUNT_PATTERNS)
        deadline = self._first_match(text, DATE_PATTERNS)
        title = anchor_text.strip() if anchor_text.strip() else self._title_from_link("", url)
        summary = ""
        if text:
            summary = text[:260]
        location = f"{fallback_location}, Australia" if fallback_location != "AU" else "National, Australia"
        industry = self._infer_industry(text)
        return {
            "title": title,
            "provider": provider,
            "amount": amount or None,
            "deadline": deadline or None,
            "eligibility_summary": summary or "See source page for eligibility criteria.",
            "industry": industry,
            "location": location,
            "key_requirements": [],
        }

    def _merge_structured(self, ai: dict, heuristic: dict, criteria: dict, relevant_text: str) -> dict:
        merged = dict(heuristic)
        merged.update({k: v for k, v in ai.items() if v not in (None, "", [])})
        if not isinstance(merged.get("industry"), list):
            merged["industry"] = heuristic.get("industry", [])
        if not isinstance(merged.get("key_requirements"), list):
            merged["key_requirements"] = []
        merged["criteria_industries"] = self._pick_list(criteria.get("industries"), [])
        merged["criteria_locations"] = self._normalise_locations(self._pick_list(criteria.get("locations"), []))
        merged["criteria_business_size"] = str(criteria.get("business_size") or "")
        merged["criteria_must_have"] = self._pick_list(criteria.get("must_have"), [])
        merged["criteria_not_allowed"] = self._pick_list(criteria.get("not_allowed"), [])
        merged["relevant_text"] = relevant_text[:1200]
        merged["field_confidence"] = {
            "title": 0.9 if merged.get("title") else 0.0,
            "deadline": 0.8 if merged.get("deadline") else 0.0,
            "amount": 0.8 if merged.get("amount") else 0.0,
            "location": 0.7 if merged.get("location") else 0.0,
        }
        merged["evidence"] = {
            "relevant_text": relevant_text[:400],
            "requirements": merged.get("key_requirements", [])[:3],
        }
        return merged

    def _build_extracted_grant(self, extracted: dict, raw_item: dict, source: GrantSource, fetch_method: str) -> ExtractedGrant:
        deadline_raw = str(extracted.get("deadline") or "")
        amount_raw = str(extracted.get("amount") or "")
        return ExtractedGrant(
            title=str(extracted.get("title") or ""),
            source_url=source.url,
            detail_url=str(raw_item.get("url") or ""),
            provider=str(extracted.get("provider") or source.name),
            provider_raw=str(extracted.get("provider") or source.name),
            deadline_raw=deadline_raw,
            deadline_iso=self._normalise_deadline(deadline_raw) or "",
            amount_raw=amount_raw,
            amount_display=amount_raw,
            eligibility_summary=str(extracted.get("eligibility_summary") or ""),
            industry=self._pick_list(extracted.get("industry"), []),
            location_display=str(extracted.get("location") or ""),
            criteria_industries=self._pick_list(extracted.get("criteria_industries"), []),
            criteria_locations=self._pick_list(extracted.get("criteria_locations"), []),
            criteria_business_size=str(extracted.get("criteria_business_size") or ""),
            criteria_must_have=self._pick_list(extracted.get("criteria_must_have"), []),
            criteria_not_allowed=self._pick_list(extracted.get("criteria_not_allowed"), []),
            relevant_text=str(extracted.get("relevant_text") or ""),
            raw_text=str(raw_item.get("text_content") or ""),
            field_confidence={k: float(v) for k, v in dict(extracted.get("field_confidence", {})).items() if isinstance(v, (float, int))},
            evidence=dict(extracted.get("evidence", {})) if isinstance(extracted.get("evidence"), dict) else {},
            fetch_method=fetch_method,
            content_hash=hashlib.sha256(str(raw_item.get("text_content", "")).encode("utf-8")).hexdigest(),
        )

    def _is_valid_structured(self, item: dict) -> bool:
        title = str(item.get("title", "")).strip()
        if not title:
            return False
        # Validation layer: keep low-confidence results when one of amount/deadline exists.
        amount_raw = item.get("amount")
        deadline_raw = item.get("deadline")
        amount = "" if amount_raw is None else str(amount_raw).strip()
        deadline = "" if deadline_raw is None else str(deadline_raw).strip()
        return bool(amount or deadline)

    def _details_text(self, extracted: dict, source_url: str) -> str:
        reqs = extracted.get("key_requirements") or []
        req_summary = ", ".join(str(r) for r in reqs[:3]) if reqs else ""
        base = extracted.get("eligibility_summary") or f"Discovered from {source_url}"
        if req_summary:
            return f"{base} Requirements: {req_summary}"[:400]
        return str(base)[:400]

    def _first_match(self, text: str, patterns: list[re.Pattern[str]]) -> str | None:
        if not text:
            return None
        for pattern in patterns:
            m = pattern.search(text)
            if not m:
                continue
            value = m.group(1).strip()
            if pattern in DATE_PATTERNS:
                norm = self._normalise_deadline(value)
                return norm or value
            return value
        return None

    def _normalise_deadline(self, raw: str) -> str | None:
        raw = raw.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass
        m = re.match(rf"(\d{{1,2}})\s+((?:{MONTHS_RE})[a-z]*)\s+(\d{{4}})", raw, flags=re.I)
        if not m:
            return None
        day = int(m.group(1))
        month_text = m.group(2).lower()[:3]
        year = int(m.group(3))
        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        month = months.get(month_text)
        if not month:
            return None
        try:
            return datetime(year, month, day).date().isoformat()
        except ValueError:
            return None

    def _title_from_link(self, text: str, url: str) -> str:
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        if len(cleaned) >= 6:
            return cleaned[:180]
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        if not slug:
            return "Discovered Grant Opportunity"
        human = re.sub(r"[-_]+", " ", slug).strip().title()
        return human[:180] if human else "Discovered Grant Opportunity"

    def _canonical_url(self, url: str) -> str:
        parsed = urlparse(url)
        cleaned_query = []
        if parsed.query:
            for item in parsed.query.split("&"):
                if not item:
                    continue
                key = item.split("=", 1)[0].lower()
                if key.startswith("utm_") or key in {"fbclid", "gclid", "mc_cid", "mc_eid"}:
                    continue
                cleaned_query.append(item)
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        canonical = parsed._replace(netloc=parsed.netloc.lower(), path=path, query="&".join(cleaned_query), fragment="")
        return canonical.geturl()

    def _dedupe_link_records(self, links: list[tuple[str, str]]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for url, text in links:
            canonical = self._canonical_url(url)
            semantic_key = hashlib.sha256(f"{canonical}|{str(text).strip().lower()}".encode("utf-8")).hexdigest()
            if semantic_key in seen:
                continue
            seen.add(semantic_key)
            out.append((canonical, text))
        return out

    def _infer_state(self, source: GrantSource) -> str:
        blob = f"{source.id} {source.name} {source.url}".upper()
        for code in ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]:
            if code in blob:
                return code
        return "AU"

    def _infer_industry(self, text: str) -> list[str]:
        blob = (text or "").lower()
        out = []
        mapping = {
            "clean_energy": ["clean energy", "renewable"],
            "advanced_manufacturing": ["manufacturing", "industry"],
            "healthcare": ["health", "medical", "medtech"],
            "technology": ["technology", "digital", "software", "innovation"],
            "agriculture": ["agriculture", "farming", "agribusiness"],
            "professional_services": ["services", "consulting"],
            "retail": ["retail"],
        }
        for key, tokens in mapping.items():
            if any(token in blob for token in tokens):
                out.append(key)
        return out

    def _heuristic_extract_criteria(self, text: str, fallback_location: str, fallback_industry: list[str]) -> dict:
        blob = (text or "").lower()
        return {
            "industries": fallback_industry or [],
            "locations": self._infer_locations(blob, fallback_location),
            "business_size": self._extract_business_size(blob),
            "must_have": self._extract_list_by_phrases(text, ("must", "required", "eligible", "who can apply")),
            "not_allowed": self._extract_list_by_phrases(text, ("not eligible", "ineligible", "must not", "non-profit only", "for-profit only")),
        }

    def _infer_locations(self, text: str, fallback_location: str) -> list[str]:
        codes = []
        for code in ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]:
            if code.lower() in text:
                codes.append(code)
        if "national" in text or "australia wide" in text or "australia-wide" in text:
            codes.append("AU")
        if not codes:
            codes = [fallback_location]
        return codes

    def _extract_business_size(self, text: str) -> str:
        patterns = [
            re.compile(r"(less than\s+\d+\s+employees)", re.I),
            re.compile(r"(fewer than\s+\d+\s+employees)", re.I),
            re.compile(r"(up to\s+\d+\s+employees)", re.I),
            re.compile(r"(between\s+\d+\s+and\s+\d+\s+employees)", re.I),
            re.compile(r"((?:small|medium|large)\s+business(?:es)?)", re.I),
        ]
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
        return ""

    def _extract_list_by_phrases(self, text: str, phrases: tuple[str, ...]) -> list[str]:
        low = text.lower()
        found: list[str] = []
        for phrase in phrases:
            start = 0
            while True:
                idx = low.find(phrase, start)
                if idx < 0:
                    break
                snippet = re.sub(r"\s+", " ", text[max(0, idx - 80): min(len(text), idx + 160)]).strip()
                start = idx + len(phrase)
                if snippet and snippet not in found:
                    found.append(snippet[:220])
        return found[:5]

    def _pick_list(self, candidate: object, fallback: list[str]) -> list[str]:
        if isinstance(candidate, list):
            items = [str(item).strip() for item in candidate if str(item).strip()]
            if items:
                return items
        return fallback

    def _normalise_locations(self, raw_locations: list[str]) -> list[str]:
        out: list[str] = []
        for item in raw_locations:
            upper = str(item).upper().strip()
            if not upper:
                continue
            if "NATIONAL" in upper or "AUSTRALIA" in upper:
                upper = "AU"
            for code in ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT", "AU"]:
                if code in upper and code not in out:
                    out.append(code)
                    break
        return out
