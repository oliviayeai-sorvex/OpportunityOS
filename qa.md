# Feature Status Tracker (qa.md)

## Overall Status: MVP P0 Complete ✅

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🔄 | In Progress |
| ⬜ | Not Started |
| ❌ | Blocked |

## Feature Pipeline

| Feature | Priority | -1 Scoped | 0 PM Spec | 1 UX/UI | 2 Arch+Sec | 3 Impl | 4 QA | 5 Done | Status |
|---------|----------|-----------|-----------|---------|------------|--------|------|--------|--------|
| source_ingestion_pipeline | P0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |
| opportunity_command_center | P0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |
| action_queue_watchlist | P1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |
| platform_shell_auth_scheduler_digest | P0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |
| grant_writer_dashboard | P0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |

## Completed Features

| Feature | Completed | Completion Doc |
|---------|-----------|----------------|
| source_ingestion_pipeline | 2026-03-24 | ai/context/feature_source_ingestion_pipeline_completion.md |
| opportunity_command_center | 2026-03-24 | ai/context/feature_opportunity_command_center_completion.md |
| action_queue_watchlist | 2026-03-24 | ai/context/feature_action_queue_watchlist_completion.md |
| platform_shell_auth_scheduler_digest | 2026-03-24 | ai/context/mvp_completion_report.md |
| grant_writer_dashboard | 2026-03-24 | ai/context/mvp_completion_report.md |

## Notes

- Features were seeded during Part -1 Step 3 based on `docs/mvp_scope.md`.
- P0 features are executed before P1 in `/run-agent` feature loop.
- 2026-03-24 localhost verification:
  - Backend live: `http://127.0.0.1:8000`
  - Frontend live: `http://127.0.0.1:4173`
  - End-to-end checks passed for auth signup/login/reset endpoint availability, settings read/write, grant scan schedule/source CRUD, run-now job queue + processing, home summary, notifications, and search.
- 2026-03-24 grant writer enhancement:
  - `Run now` now generates grant opportunities from configured source list and computes eligibility against profile.
  - Settings now include `company_size` and multi-select `interest_industries`.
  - Grant dashboard results now include: date, location, industry, details, URL, due date, grant amount, and eligibility reason.
- 2026-03-24 grant writer stage-1 expansion:
  - Added recommended source pack: business.gov.au, grants.gov.au, NSW/VIC/QLD/SA/WA, ATO R&D, ARENA, CSIRO, MedTech.
  - Added full business profile schema and profile completeness indicator in settings API/UI.
  - Added grant pre-filter scoring (0-100), recommended/deadline badges, and dedupe by `external_key`.
  - Added Kanban workflow columns: New, Shortlisted, In Progress, Under Review, Submitted, Closed.
  - Added draft workflow: create/regenerate draft, version history, mark reviewed/submitted, tracking notes/outcome.
  - Search now returns filtered grant matches with AI summary/comparison and empty-query guard.
- 2026-03-25 grant scan debug fix:
  - Scrape-first path was rolled back to preserve scalability and reliability of source adapters.
  - Grant pipeline now follows staged architecture: `raw -> normalized -> rule candidates -> ai assessments -> dashboard projection`.
  - Added persistent stage tables and indexes: `grant_raw_records`, `grant_normalized`, `grant_match_candidates`, `grant_ai_assessments`.
  - Added profile fields for matching quality: `revenue`, `goals_json`.
  - Added API contracts and endpoints for pipeline orchestration and debugging:
    - `POST /api/v1/grant-writer/pipeline/run`
    - `GET /api/v1/grant-writer/pipeline?run_id=<id>`
  - Added local Llama3 eligibility path for scheduler/worker testing with cloud-provider reserve option via `AI_PROVIDER`.
  - Localhost smoke validated: signup/login, profile update, pipeline run, pipeline detail retrieval, and board population.
- 2026-03-25 source delete performance/reliability:
  - Fixed grant source persistence model to isolate per-user source records with `(user_id, id)` key semantics (`grant_sources_v2`).
  - Fixed "Remove" behavior when user source list was inherited from global defaults (now materializes user set before delete).
  - Frontend source remove now uses optimistic row removal instead of full dashboard reload per click.
  - Verified via API smoke: source count decreases and deleted source does not reappear.
- 2026-03-25 generic source discovery:
  - Added generic link discovery (non site-specific parsing) to extract child grant opportunity URLs from listing pages.
  - Ingestion now runs `generic discovery -> fallback catalog` per source.
  - Verified NSW source now returns item-level links (example: `/grants-and-funding/...-round-2`) instead of only listing root URL.
- 2026-03-25 pre-AI optimization pipeline:
  - Added staged pre-AI flow in discovery: `heuristic filter -> rule engine -> cache check -> AI extraction`.
  - Added strict cleaned text cap (`GRANT_DISCOVERY_MAX_TEXT_CHARS`, default `3000`) and low-cost keyword/length rejection.
  - Added deterministic rule gate (amount/deadline + location signal) before extraction calls.
  - Added persistent `ai_cache` table and repository APIs to skip repeated extraction AI calls by content hash.
- 2026-03-25 default source curation update:
  - Removed defaults: `ATO R&D`, `State: South Australia`, `State: Western Australia`.
  - Renamed `State: Invest Victoria` -> `State: Business Victoria` and updated URL.
  - Updated URLs for GrantConnect, CSIRO, MedTech, and Queensland as requested.
  - Added startup sync to upsert current global defaults and remove deprecated default source ids.
- 2026-03-27 pipeline refactor implementation:
  - Added architecture plan artifact: `ai/architecture/grant_pipeline_refactor_plan.md`.
  - Implemented typed fetch artifacts with explicit `ok/error/fetch_method/content_type/content_length`.
  - Expanded page typing to `LISTING | DETAIL | SEARCH | LANDING | UNKNOWN` with confidence signals in debug.
  - Replaced keyword-only listing behavior with clustering + repeated-structure scoring and canonical URL handling.
  - Added per-detail fetch type re-detection instead of inheriting listing fetch mode.
  - Split extraction into deterministic pass + AI completion pass (`_deterministic_extract` + `_ai_complete_extraction`).
  - Added explicit schemas in `models/entities.py`: `ExtractedGrant`, `NormalizedGrant`.
  - Added multi-key dedupe primitives (canonical URL normalization and semantic dedupe hash before detail fetch).
  - Preserved and expanded per-stage observability fields including stage failure reason and confidence signals.
  - Fixed local auth regression (`verify_token` alias) and local CORS allowlist for `127.0.0.1:4173`.
