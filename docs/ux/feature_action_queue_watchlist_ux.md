# UX Design: action_queue_watchlist

## User Journey
1. Operator selects opportunity row from command center.
2. Operator clicks `Add to Watchlist`.
3. Operator creates action with due date and owner.
4. Operator monitors action queue status list.

## Page Map
- Dashboard watchlist panel
- Action queue panel and create-action form modal

## Interaction Flow
- Add to watchlist is idempotent and confirms via toast.
- Create action validates summary + due date before submit.
- Action list updates immediately after creation.

## UI States
- Loading: action queue skeleton.
- Empty: no watchlist items and no open actions.
- Success: list of watchlist opportunities and actions.
- Validation Error: required fields highlighted.
- API Error: inline retry banner.

## ASCII Wireframes

```text
+--------------------------------------------------------------+
| Watchlist                                                     |
| [Add selected]                                               |
| - re-441 Distressed multifamily                              |
| - stk-001 Undervalued semiconductor basket                   |
+--------------------------------------------------------------+
| Action Queue                                                 |
| [summary.............] [due date] [Create Action]            |
| - Open: call broker (due 2026-03-30)                         |
+--------------------------------------------------------------+
```
