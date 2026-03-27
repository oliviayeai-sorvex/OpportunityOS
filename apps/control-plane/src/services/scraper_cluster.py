from __future__ import annotations

from dataclasses import dataclass
import os
from queue import Queue
from threading import Event, Lock, Semaphore, Thread
from typing import Dict, Literal
from uuid import uuid4
from urllib.error import URLError
from urllib.request import Request, urlopen

from services.api_discovery_service import ApiDiscoveryService

SourceType = Literal["HTML", "STATIC", "JS", "API", "UNKNOWN"]


@dataclass
class ScrapeJob:
    url: str
    source_type: SourceType
    source_id: str = "global"


class ScraperCluster:
    def __init__(self) -> None:
        self._api_discovery = ApiDiscoveryService()
        self._queue_enabled = os.getenv("SCRAPER_QUEUE_ENABLED", "0") == "1"
        self._max_workers = int(os.getenv("SCRAPER_QUEUE_WORKERS", "6"))
        self._per_source = int(os.getenv("SCRAPER_QUEUE_PER_SOURCE", "2"))

    def fetch_html(self, job: ScrapeJob) -> str:
        meta = self.fetch_html_with_meta(job)
        return str(meta.get("html", "")) if meta.get("ok") else ""

    def fetch_html_with_meta(self, job: ScrapeJob) -> dict:
        out = {
            "ok": False,
            "html": "",
            "error": "",
            "fetch_method": "static",
            "content_type": "",
            "content_length": 0,
        }
        if job.source_type == "JS" and self._api_discovery.is_enabled():
            out["fetch_method"] = "playwright"
            html = self._api_discovery.fetch_page_html(job.url) or ""
            if html:
                out.update(
                    {
                        "ok": True,
                        "html": html,
                        "content_type": "text/html",
                        "content_length": len(html),
                    }
                )
                return out
            out["error"] = "playwright returned empty html"
            return out
        static = self._fetch_static_with_meta(job.url)
        out.update(static)
        return out

    def fetch_html_jobs(self, jobs: list[ScrapeJob]) -> Dict[str, str]:
        if not self._queue_enabled or not jobs:
            return {job.url: self.fetch_html(job) for job in jobs}
        queue: Queue[tuple[str, ScrapeJob]] = Queue()
        results: Dict[str, str] = {}
        events: Dict[str, Event] = {}
        semaphores: Dict[str, Semaphore] = {}
        lock = Lock()
        for job in jobs:
            job_id = str(uuid4())
            events[job_id] = Event()
            queue.put((job_id, job))

        def worker() -> None:
            while True:
                item = queue.get()
                if item is None:
                    queue.task_done()
                    break
                job_id, job = item
                sem = semaphores.setdefault(job.source_id, Semaphore(self._per_source))
                sem.acquire()
                try:
                    html = self.fetch_html(job)
                    with lock:
                        results[job.url] = html
                finally:
                    sem.release()
                    events[job_id].set()
                    queue.task_done()

        workers = [Thread(target=worker, daemon=True) for _ in range(self._max_workers)]
        for w in workers:
            w.start()
        for job_id in list(events.keys()):
            events[job_id].wait(timeout=30)
        for _ in workers:
            queue.put(None)
        queue.join()
        return results

    def fetch_json(self, url: str) -> object | None:
        meta = self.fetch_json_with_meta(url)
        return meta.get("data") if meta.get("ok") else None

    def fetch_json_with_meta(self, url: str) -> dict:
        out = {
            "ok": False,
            "data": None,
            "error": "",
            "fetch_method": "api",
            "content_type": "",
            "content_length": 0,
        }
        req = Request(
            url,
            headers={
                "User-Agent": "OpportunityOS-ScraperCluster/1.0",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(req, timeout=20) as resp:
                out["content_type"] = (resp.headers.get("Content-Type", "") or "").lower()
                raw = resp.read().decode("utf-8", errors="ignore")
                out["content_length"] = len(raw)
                import json

                parsed = json.loads(raw)
                out["ok"] = True
                out["data"] = parsed
                return out
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            out["error"] = str(exc)
            return out

    def _fetch_static(self, url: str) -> str:
        meta = self._fetch_static_with_meta(url)
        return str(meta.get("html", "")) if meta.get("ok") else ""

    def _fetch_static_with_meta(self, url: str) -> dict:
        out = {
            "ok": False,
            "html": "",
            "error": "",
            "fetch_method": "static",
            "content_type": "",
            "content_length": 0,
        }
        req = Request(
            url,
            headers={
                "User-Agent": "OpportunityOS-ScraperCluster/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
            method="GET",
        )
        try:
            with urlopen(req, timeout=10) as resp:
                content_type = (resp.headers.get("Content-Type", "") or "").lower()
                out["content_type"] = content_type
                if "html" not in content_type and "xml" not in content_type:
                    out["error"] = f"unexpected content-type: {content_type or 'unknown'}"
                    return out
                html = resp.read().decode("utf-8", errors="ignore")
                out["ok"] = True
                out["html"] = html
                out["content_length"] = len(html)
                return out
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            out["error"] = str(exc)
            return out
