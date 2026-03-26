# Feature: Opportunity Command Center

**Priority**: P0
**Status**: Approved

## Goal
Provide an operator-facing command center that ranks opportunities, supports flexible filter criteria, and records verification outcomes visible on dashboard summaries.

## User Stories
- As an operator, I want ranked opportunities with score breakdowns so I can trust prioritization decisions.
- As an operator, I want to filter by domain, score, risk, and value to match my active strategy.
- As a manager, I want dashboard verification metrics to confirm pipeline quality.

## Acceptance Criteria
- [ ] Command center returns opportunities sorted by score descending.
- [ ] Filter criteria supports domain list, minimum score, minimum value, and maximum risk.
- [ ] Verification action updates opportunity status and summary counters.
- [ ] Dashboard summary returns totals (`verified`, `pending`, `rejected`) and domain breakdown.
- [ ] Viewer role can read dashboard; only operator/admin can verify.

## Edge Cases & Error States
- No opportunities should return empty state while preserving summary payload.
- Invalid filter values should fail validation with explicit error details.
- Verification for unknown opportunity id should return not-found contract.
- Role mismatch should return permission error.

## Out of Scope
- Natural-language filter query parsing.
- Portfolio simulation/forecasting.
- External BI export connectors.

## Dependencies
- `ai/architecture/system_architecture.md`
- `ai/tasks/feature_source_ingestion_pipeline.md`
