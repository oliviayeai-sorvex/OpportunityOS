# Observability: opportunity_command_center

## Metrics
- `dashboard_query_requests_total{status}`
- `dashboard_query_latency_ms`
- `verification_mutations_total{status}`
- `verification_conversion_ratio`

## Tracing
- Root spans: `api.opportunities.list`, `api.verification.update`, `api.dashboard.summary`
- Child spans: `service.dashboard.filter`, `repo.opportunity.list`, `repo.verification.update`

## Logs
- Events: `opportunity_list_served`, `verification_updated`, `dashboard_summary_computed`
- Required keys: `trace_id`, `actor_id`, `filter_hash`, `result_count`.

## Alerts
- Verification mutation error rate > 2% for 10 minutes.
- Dashboard p95 latency > 500ms for 10 minutes.
