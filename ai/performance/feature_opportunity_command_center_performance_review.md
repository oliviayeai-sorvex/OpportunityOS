# Performance Review: opportunity_command_center

## Load Assumptions
- 25 concurrent dashboard users.
- Query burst during morning triage windows.
- Verification write rate lower than read rate (~1:8).

## Bottleneck Analysis
- Filtering + sorting can become expensive if done in memory at high scale.
- Summary recomputation on each request may cause avoidable CPU overhead.
- Score breakdown endpoint should avoid full-table scans.

## Scaling Risks
- Without pagination, response payload grows linearly.
- Lack of cache for summary metrics can increase DB pressure.
- Verification updates need optimistic locking if multi-operator collisions rise.

## Query Optimization
- Add composite index `(verification_status, domain, score_total DESC)`.
- Introduce cursor pagination on opportunities endpoint.
- Cache summary payload for short TTL and invalidate on verify/reject mutation.
