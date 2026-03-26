from __future__ import annotations

from api.router import ControlPlaneAPI


class IngestionWorker:
    def __init__(self, api: ControlPlaneAPI) -> None:
        self._api = api

    def run_once(self) -> dict:
        return self._api.run_ingestion(role="admin", sources=["stocks", "real_estate", "grants"])
