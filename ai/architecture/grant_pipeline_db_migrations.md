# Grant Pipeline DB Migrations

## Purpose
Introduce a scalable staged pipeline:
`raw -> normalized -> rule candidates -> ai assessments -> dashboard projection`

## User Profile Extension
`user_profiles` additions:
- `revenue INTEGER NOT NULL DEFAULT 0`
- `goals_json TEXT NOT NULL DEFAULT '[]'`

## New Tables

### `grant_raw_records`
- `id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `run_id TEXT NOT NULL`
- `source_id TEXT NOT NULL`
- `fetched_at TEXT NOT NULL`
- `payload_json TEXT NOT NULL`
- `payload_hash TEXT NOT NULL`
- `url TEXT NOT NULL`

Indexes:
- `idx_grant_raw_run(user_id, run_id, source_id)`

### `grant_normalized`
- `id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `run_id TEXT NOT NULL`
- `source_id TEXT NOT NULL`
- `dedupe_key TEXT NOT NULL`
- `grant_name TEXT NOT NULL`
- `provider TEXT NOT NULL`
- `industry_json TEXT NOT NULL`
- `location TEXT NOT NULL`
- `min_size INTEGER NOT NULL`
- `max_size INTEGER NOT NULL`
- `funding_amount INTEGER NOT NULL`
- `deadline TEXT NOT NULL`
- `eligibility_text TEXT NOT NULL`
- `description TEXT NOT NULL`
- `url TEXT NOT NULL`
- `normalized_json TEXT NOT NULL`
- `version INTEGER NOT NULL`
- `updated_at TEXT NOT NULL`

Indexes:
- `idx_grant_norm_dedupe(user_id, dedupe_key)` UNIQUE
- `idx_grant_norm_run(user_id, run_id)`

### `grant_match_candidates`
- `id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `run_id TEXT NOT NULL`
- `normalized_id TEXT NOT NULL`
- `rule_status TEXT NOT NULL`
- `rule_score INTEGER NOT NULL`
- `rule_reasons_json TEXT NOT NULL`
- `created_at TEXT NOT NULL`

Indexes:
- `idx_grant_candidate_run(user_id, run_id)`

### `grant_ai_assessments`
- `id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `run_id TEXT NOT NULL`
- `normalized_id TEXT NOT NULL`
- `eligibility TEXT NOT NULL`
- `confidence INTEGER NOT NULL`
- `key_reasons_json TEXT NOT NULL`
- `missing_requirements_json TEXT NOT NULL`
- `recommended_action TEXT NOT NULL`
- `model TEXT NOT NULL`
- `prompt_version TEXT NOT NULL`
- `created_at TEXT NOT NULL`

Indexes:
- `idx_grant_ai_run(user_id, run_id)`

## Projection Strategy
Projection continues to use `grant_scan_results` as dashboard read model.
Pipeline writes only `ELIGIBLE` and `PARTIAL` results into this projection using replacement semantics per user.

## Rollback Safety
- New tables are additive only.
- Existing `grant_scan_results` path remains backward-compatible for UI.
- If AI stage fails, rule-qualified records can be marked `PARTIAL` deterministically.
