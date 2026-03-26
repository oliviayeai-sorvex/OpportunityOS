from __future__ import annotations

from typing import Iterable

from adapters.providers import ProviderAdapter, normalize_record
from models.repository_protocol import OpportunityRepository
from .scoring_service import ScoringService


class IngestionService:
    def __init__(
        self,
        repository: OpportunityRepository,
        adapters: dict[str, ProviderAdapter],
        scoring_service: ScoringService,
    ) -> None:
        self._repository = repository
        self._adapters = adapters
        self._scoring_service = scoring_service

    def run(self, sources: Iterable[str], trace_id: str) -> dict:
        provider_results: list[dict] = []
        ingested_count = 0
        rejected_count = 0

        for source in sources:
            adapter = self._adapters.get(source)
            if adapter is None:
                provider_results.append({"source": source, "status": "error", "error": "unsupported_source"})
                continue

            accepted = 0
            rejected = 0
            try:
                for raw in adapter.fetch_raw():
                    try:
                        normalized = normalize_record(source, raw)
                    except ValueError as exc:
                        rejected += 1
                        provider_results.append(
                            {
                                "source": source,
                                "status": "rejected",
                                "error": str(exc),
                            }
                        )
                        continue
                    saved = self._repository.upsert_opportunity(normalized)
                    self._repository.set_scorecard(saved.id, self._scoring_service.score(saved))
                    accepted += 1

                provider_results.append({"source": source, "status": "ok", "ingested": accepted, "rejected": rejected})
                ingested_count += accepted
                rejected_count += rejected
            except Exception as exc:  # pragma: no cover
                provider_results.append({"source": source, "status": "error", "error": str(exc)})

        errors = [row for row in provider_results if row["status"] in {"error", "rejected"}]
        self._repository.add_ingestion_run(trace_id, ingested_count, rejected_count, errors)

        return {
            "trace_id": trace_id,
            "ingested_count": ingested_count,
            "rejected_count": rejected_count,
            "provider_results": provider_results,
        }
