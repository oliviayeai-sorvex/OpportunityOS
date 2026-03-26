# Architecture: action_queue_watchlist

## Request Flow
1. `POST /api/v1/watchlists/add` saves opportunity id for operator.
2. `GET /api/v1/watchlists` lists user watchlist opportunities.
3. `POST /api/v1/actions` creates follow-up action item.
4. `GET /api/v1/actions` lists actions by owner id.

## Service Boundaries
- API: role and payload validation.
- Watchlist service: idempotent add/list behavior.
- Repository: persistence for watchlist links and action items.

## API Endpoints
- `POST /api/v1/watchlists/add`
- `GET /api/v1/watchlists`
- `POST /api/v1/actions`
- `GET /api/v1/actions`

## Data Model Notes
- `watchlist_items(user_id, opportunity_id)` unique pair.
- `action_items(id, opportunity_id, owner_id, summary, due_date, status)`.

## Migration Plan
1. Create watchlist join table with unique index.
2. Create action_items table with owner and due_date indexes.

## Test Plan Outline
- Unit: idempotent watchlist add and due-date validation.
- Integration: create/list watchlist and action flow.
- E2E: ingest -> select -> watchlist add -> action creation -> action list.
