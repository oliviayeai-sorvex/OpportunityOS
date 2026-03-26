# Architecture: source_ingestion_pipeline

## Request Flow
1. API `POST /api/v1/ingestion/run` validates payload and role.
2. Ingestion service resolves adapter registry for requested sources.
3. Each adapter fetches provider records and normalizes to canonical model.
4. Repository upserts opportunities by `(external_id, source)`.
5. Response returns totals and per-provider errors.

## Service Boundaries
- API: auth + input validation only.
- Services: orchestration, dedupe/upsert, partial-failure handling.
- Adapters: provider fetch + schema normalization only.
- Models: canonical domain entities and repository contracts.
- Workers: scheduled ingestion trigger path shares service API.

## API Endpoints
- `POST /api/v1/ingestion/run`
  - Request: `{ sources: string[], trace_id?: string }`
  - Response: `{ ingested_count, rejected_count, provider_results[] }`
- `GET /api/v1/ingestion/history`
  - Response: last ingestion summaries.

## Data Model / Schema Notes
- `opportunities`
  - `id` (uuid), `external_id` (text), `source` (text), `domain` (text), `title` (text), `value_estimate` (numeric), `risk_level` (text), `captured_at` (timestamp), `updated_at` (timestamp)
  - Unique index: `(external_id, source)`
- `ingestion_runs`
  - `id`, `trace_id`, `started_at`, `finished_at`, `ingested_count`, `rejected_count`, `error_json`

## Migration Plan
1. Create `opportunities` and `ingestion_runs` tables.
2. Add unique key on provider identity tuple.
3. Add index on `(domain, captured_at)` for downstream queries.

## Test Plan Outline
- Unit: adapter normalization, dedupe logic, partial-failure aggregation.
- Integration: API -> service -> adapter -> repository happy path and partial failure path.
- E2E: gateway/router/provider/logging/policy trace continuity and response contract checks.
