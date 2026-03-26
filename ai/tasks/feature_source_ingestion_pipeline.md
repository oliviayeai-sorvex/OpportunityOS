# Feature: Source Ingestion Pipeline

**Priority**: P0
**Status**: Approved

## Goal
Ingest and normalize opportunities from stock, real-estate, and grant providers through pluggable adapters so new data sources can be added without rewriting service logic.

## User Stories
- As an operator, I want opportunities from multiple domains in a single normalized feed so I can compare opportunities consistently.
- As an admin, I want connector adapters to be modular so provider changes do not break the whole ingestion service.
- As a reliability engineer, I want partial-failure handling and ingestion telemetry so outages are visible and isolated.

## Acceptance Criteria
- [ ] Supports ingestion from `stocks`, `real_estate`, and `grants` providers in one run.
- [ ] Provider data is normalized into one canonical opportunity schema.
- [ ] Duplicate opportunities upsert by stable key and source.
- [ ] Per-provider ingestion failures are captured without failing the entire run.
- [ ] Ingestion route enforces RBAC (`operator` and `admin` only).

## Edge Cases & Error States
- Provider timeout should produce partial success response with error list.
- Empty provider payload should return success with `ingested_count=0`.
- Unknown provider source should return validation error.
- Invalid provider record should be rejected and counted in `rejected_count`.

## Out of Scope
- Real-time stream ingestion.
- Tenant-specific connector credentials UI.
- Provider-side schema negotiation automation.

## Dependencies
- `ai/architecture/system_architecture.md`
- `ai/security/secrets_standard.md`
- `observability.md`
