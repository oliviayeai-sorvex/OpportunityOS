# Performance Review: action_queue_watchlist

## Load Assumptions
- 50 operators with average 30 watchlist items each.
- Action creation rate peaks at 200/day.

## Bottleneck Analysis
- Watchlist joins can degrade if opportunity table grows without indexes.
- Action list queries must index by `owner_id` and `status`.

## Scaling Risks
- Large watchlists returned unpaginated can bloat payloads.
- Concurrent action updates may require optimistic locking strategy.

## Query Optimization
- Add index `watchlist_items(user_id, opportunity_id)`.
- Add index `action_items(owner_id, due_date)`.
- Paginate watchlist/action list endpoints after 100 rows.
