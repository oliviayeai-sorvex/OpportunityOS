# Architecture: opportunity_command_center

## Request Flow
1. `GET /api/v1/opportunities` receives filter criteria.
2. API validates role and filter types.
3. Dashboard service queries repository with criteria.
4. Repository returns score-sorted opportunities.
5. `POST /api/v1/verification` updates verification state and emits event.
6. `GET /api/v1/dashboard/summary` returns verification counters.

## Service Boundaries
- API: schema validation + RBAC.
- Services: ranking/filter orchestration and verification command handling.
- Models: filter criteria policy and verification event model.

## API Endpoints
- `GET /api/v1/opportunities?domains=&min_score=&max_risk=&min_value_estimate=`
- `POST /api/v1/verification`
- `GET /api/v1/dashboard/summary`

## Data Model Notes
- Reuses `opportunities` table.
- Adds `verification_status` index for summary aggregation.
- Optional `verification_events` append-only log table for auditability.

## Migration Plan
1. Add `verification_status` default `pending`.
2. Add status index and optional `verified_at` timestamp.

## Test Plan Outline
- Unit: filtering combinations, score ordering.
- Integration: verify endpoint updates status and summary counts.
- E2E: dashboard read + verify mutation + summary update path.
