# Observability: action_queue_watchlist

## Metrics
- `watchlist_add_total{status}`
- `watchlist_size_per_user`
- `action_create_total{status}`
- `action_open_count`

## Tracing
- `api.watchlist.add` -> `service.watchlist.add` -> `repo.watchlist.upsert`
- `api.actions.create` -> `service.actions.create` -> `repo.actions.insert`

## Logs
- `watchlist_item_added`
- `action_item_created`
- `action_list_served`

## Alerts
- Action creation error rate > 2% for 15 minutes.
- Watchlist read latency p95 > 300ms for 10 minutes.
