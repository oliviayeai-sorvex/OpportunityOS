# UX Design: opportunity_command_center

## User Journey
1. Operator opens command center dashboard.
2. Operator adjusts filter controls (domain, min score, max risk, min value).
3. Ranked list updates with score explanation and verification badges.
4. Operator verifies/rejects opportunity and observes summary counter update.

## Page Map
- `/dashboard` command center main view
- Verification detail side panel

## Interaction Flow
- Filter change triggers debounced query refresh.
- Selecting row expands score breakdown panel.
- Verify action submits mutation and updates table + summary widgets.

## UI States
- Loading: table skeleton + disabled verify buttons.
- Empty: no rows match filters with quick-reset CTA.
- Success: ranked table and metrics cards.
- Validation Error: inline validation under filters.
- API Error: sticky alert with retry.

## ASCII Wireframes

```text
+-------------------------------------------------------------+
| Command Center                                              |
| Filters: [domain] [min score] [max risk] [min value]       |
+----------------------+--------------------------------------+
| Ranked Opportunities | Score Breakdown                      |
| #1 re-441 92.3       | Value: 1.0                           |
| #2 stk-001 79.2      | Risk: 0.75                           |
| #3 gr-778 69.0       | Bonus: 0.15                          |
+----------------------+--------------------------------------+
| Verification Summary: verified 12 | pending 8 | rejected 3 |
+-------------------------------------------------------------+
```
