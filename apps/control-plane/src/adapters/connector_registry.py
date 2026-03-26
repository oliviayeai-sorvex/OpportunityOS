from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .providers import ProviderAdapter, StaticJsonAdapter


@dataclass
class ConnectorSpec:
    source: str
    adapter: str
    options: dict


class ConnectorRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[ConnectorSpec, Path], ProviderAdapter]] = {
            "static_json": self._build_static_json,
        }

    def _build_static_json(self, spec: ConnectorSpec, src_root: Path) -> ProviderAdapter:
        rel = spec.options.get("file_path")
        if not rel:
            raise ValueError(f"Missing file_path for connector source={spec.source}")
        return StaticJsonAdapter(source=spec.source, file_path=str(src_root / rel))

    def build_adapters(self, config_path: str, src_root: Path) -> dict[str, ProviderAdapter]:
        with Path(config_path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        adapters: dict[str, ProviderAdapter] = {}
        for row in payload:
            spec = ConnectorSpec(source=row["source"], adapter=row["adapter"], options=row.get("options", {}))
            factory = self._factories.get(spec.adapter)
            if factory is None:
                raise ValueError(f"Unknown adapter type: {spec.adapter}")
            adapters[spec.source] = factory(spec, src_root)
        return adapters
