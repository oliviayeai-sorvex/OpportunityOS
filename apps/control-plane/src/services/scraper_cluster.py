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

SourceType = Literal["HTML", "JS", "API"]


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
        if job.source_type == "JS" and self._api_discovery.is_enabled():
            html = self._api_discovery.fetch_page_html(job.url)
            if html:
                return html
        return self._fetch_static(job.url)

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
                raw = resp.read().decode("utf-8", errors="ignore")
                import json

                return json.loads(raw)
        except (URLError, TimeoutError, OSError, ValueError):
            return None

    def _fetch_static(self, url: str) -> str:
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
                if "html" not in content_type and "xml" not in content_type:
                    return ""
                return resp.read().decode("utf-8", errors="ignore")
        except (URLError, TimeoutError, OSError, ValueError):
            return ""
