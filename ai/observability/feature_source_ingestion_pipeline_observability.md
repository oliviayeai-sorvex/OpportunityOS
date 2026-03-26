# Observability: source_ingestion_pipeline

## Metrics
- `ingestion_requests_total{source,status}`
- `ingestion_latency_ms{source}` p50/p95/p99
- `ingestion_rejected_records_total{source}`
- `ingestion_provider_failures_total{source,error_type}`

## Tracing
- Root span: `api.ingestion.run`
- Child spans: `service.ingestion.execute`, `adapter.<source>.fetch`, `repo.opportunity.upsert`
- Propagate `trace_id` across API/service/adapter boundaries.

## Structured Logs
- Required keys: `timestamp`, `level`, `trace_id`, `event_name`, `source`, `ingested_count`, `rejected_count`.
- Forbidden: API keys, provider raw auth headers, PII fields.

## Alerts
- >5% provider failures for 5 minutes.
- p95 ingestion latency > 2000ms for 10 minutes.
- rejected records spike > 3x baseline over 15 minutes.
