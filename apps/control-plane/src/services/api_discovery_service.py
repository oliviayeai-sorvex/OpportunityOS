from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

KEYWORDS = ("grant", "fund", "program", "opportunity")


class ApiDiscoveryService:
    def __init__(self) -> None:
        self._enabled = os.getenv("API_DISCOVERY_ENABLED", "1") == "1"
        self._timeout = float(os.getenv("API_DISCOVERY_TIMEOUT_SEC", "20"))
        self._playwright_available = self._check_playwright()

    def _check_playwright(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore  # noqa: F401
        except Exception:
            return False
        return True

    def is_enabled(self) -> bool:
        return self._enabled and self._playwright_available

    def discover(self, url: str, debug: dict | None = None) -> dict | None:
        if not self.is_enabled():
            return None
        candidates = self._capture_api_candidates(url, debug=debug)
        if debug is not None:
            debug["api_candidates"] = [row["url"] for row in candidates][:30]
        filtered = [c for c in candidates if self._is_relevant_url(c["url"])]
        if debug is not None:
            debug["api_filtered"] = [row["url"] for row in filtered][:30]
        for cand in filtered:
            analysis = self._analyze_api(cand["url"])
            if analysis and analysis.get("is_valid"):
                return {
                    "endpoint": cand["url"],
                    "method": "GET",
                    "params": {},
                    "pagination": self._detect_pagination(cand["url"]),
                    "confidence": 0.85,
                    "last_verified": datetime.now(timezone.utc).isoformat(),
                }
        return None

    def _capture_api_candidates(self, url: str, debug: dict | None = None) -> list[dict]:
        if not self.is_enabled():
            return []
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
            candidates: list[dict] = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                def handle_response(response) -> None:
                    try:
                        content_type = response.headers.get("content-type", "")
                        if "application/json" in content_type:
                            candidates.append({"url": response.url, "status": response.status})
                    except Exception:
                        pass

                page.on("response", handle_response)
                nav_timeout_ms = int(max(3000, self._timeout * 1000))
                page.goto(url, timeout=nav_timeout_ms)
                page.wait_for_timeout(min(3000, nav_timeout_ms // 2))
                browser.close()
        except Exception as exc:
            if debug is not None:
                debug["api_discovery_error"] = str(exc)
            return []
        return candidates

    def fetch_page_html(self, url: str) -> str | None:
        if not self.is_enabled():
            return None
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                nav_timeout_ms = int(max(3000, self._timeout * 1000))
                page.goto(url, timeout=nav_timeout_ms)
                page.wait_for_timeout(min(3000, nav_timeout_ms // 2))
                html = page.content()
                browser.close()
            return html
        except Exception:
            return None

    def _is_relevant_url(self, url: str) -> bool:
        low = url.lower()
        return any(key in low for key in KEYWORDS)

    def _analyze_api(self, api_url: str) -> dict | None:
        try:
            req = Request(api_url, headers={"User-Agent": "OpportunityOS-ApiDiscovery/1.0"}, method="GET")
            with urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            return {
                "url": api_url,
                "sample": data,
                "is_valid": self._validate_structure(data),
            }
        except (URLError, TimeoutError, ValueError, OSError):
            return None

    def _validate_structure(self, data: object) -> bool:
        if isinstance(data, dict):
            keys = str(data).lower()
            return any(k in keys for k in ("grant", "title", "deadline"))
        if isinstance(data, list) and data:
            sample = str(data[0]).lower()
            return "title" in sample or "name" in sample
        return False

    def _detect_pagination(self, url: str) -> dict:
        if "page=" in url:
            return {"type": "query_param", "param": "page"}
        return {"type": "none"}

    def extract_links_from_json(self, data: object) -> list[str]:
        if data is None:
            return []
        blob = json.dumps(data)
        return list({url for url in re.findall(r"https?://[^\s\"']+", blob)})

    def extract_items_from_json(self, data: object) -> list[dict]:
        if data is None:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in ["items", "data", "results", "grants", "records"]:
                if key in data and isinstance(data[key], list):
                    return [item for item in data[key] if isinstance(item, dict)]
        return []
