# Feature: Action Queue Watchlist

**Priority**: P1
**Status**: Approved

## Goal
Allow operators to save opportunities to watchlists and manage action queue follow-ups with due dates and ownership.

## User Stories
- As an operator, I want to save opportunities to my watchlist for later review.
- As an operator, I want to create follow-up action items tied to opportunities.
- As a manager, I want to review open actions to ensure execution throughput.

## Acceptance Criteria
- [ ] Operator can add opportunity to watchlist and list saved items.
- [ ] Operator can create action item with summary and due date.
- [ ] Action list can be queried by owner.
- [ ] Watchlist and actions are RBAC-protected (`operator`/`admin`).

## Edge Cases & Error States
- Duplicate watchlist add should be idempotent.
- Missing due date should fail validation.
- Unknown opportunity id should fail action creation.

## Out of Scope
- Calendar integration.
- SLA reminders and notifications.
- Team-shared watchlists.

## Dependencies
- `ai/tasks/feature_opportunity_command_center.md`
