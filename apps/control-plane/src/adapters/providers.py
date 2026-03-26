from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from models.entities import Opportunity


class ProviderAdapter(Protocol):
    source: str

    def fetch_raw(self) -> list[dict]:
        ...


@dataclass
class StaticJsonAdapter:
    source: str
    file_path: str

    def fetch_raw(self) -> list[dict]:
        path = Path(self.file_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError(f"Connector file must contain a list: {path}")
        return payload


def normalize_record(source: str, raw: dict) -> Opportunity:
    required = ["external_id", "domain", "title", "value_estimate", "risk_level"]
    for key in required:
        if key not in raw:
            raise ValueError(f"Missing field: {key}")
    return Opportunity(
        external_id=str(raw["external_id"]),
        source=source,
        domain=str(raw["domain"]),
        title=str(raw["title"]).strip(),
        value_estimate=float(raw["value_estimate"]),
        risk_level=str(raw["risk_level"]),
        captured_at=datetime.now(timezone.utc),
    )
