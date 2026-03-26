# Security Review: action_queue_watchlist

## Threats
- Unauthorized access to another operator watchlist.
- Action summary injection and unbounded payload size.
- Sensitive operational comments leakage.

## Controls
- Owner-scoped list queries and role checks.
- Summary length limits and trimming.
- Due-date format validation.
- Structured logging excludes free-form summaries by default.

## Secrets Checklist
- [x] No secrets stored in action/watchlist entities.
- [x] API responses contain no credentials or provider tokens.
- [x] Env-only secret access remains unchanged.
