# Grant Pipeline Refactor Plan

## Goal
Stabilize the Grant Writer discovery pipeline from `URL -> raw JSON -> normalized grant -> dashboard` by making each stage explicit, typed, observable, and independently debuggable.

## Target Flow
1. Source Detection
2. Fetch Content
3. Page Type Detection
4. Listing Extraction
5. Detail Fetch
6. Field Extraction
7. Normalisation
8. Deduplication

## Current Problems
- Source type detection is too brittle.
- Fetch failures collapse into empty strings instead of typed errors.
- Listing/detail classification is too naive.
- Listing extraction is too keyword-only and misses many valid links.
- Detail pages inherit listing fetch mode incorrectly.
- Extraction mixes heuristics and AI without field-level contracts.
- Normalization is too close to downstream business rules.
- Deduplication is too weak and too late.

## Refactor Plan

### 1. Typed Source Detection
- Add `UNKNOWN` classification.
- Store detection signals and confidence in debug output.
- Prefer config/registry, then probe content, then Playwright/API hints.

### 2. Typed Fetch Artifacts
- Introduce structured fetch artifacts:
  - `status`
  - `http_status`
  - `content_type`
  - `fetch_method`
  - `content_length`
  - `raw_html`
  - `raw_json`
  - `error`
- Never silently collapse failures to empty strings.

### 3. Page Type Scoring
- Replace boolean listing check with:
  - `LISTING`
  - `DETAIL`
  - `SEARCH`
  - `LANDING`
  - `UNKNOWN`
- Use repeated path patterns, filter/search UI, heading density, and dominant detail signals.

### 4. Listing Extraction
- Keep all extracted links.
- Cluster by repeated path prefixes.
- Score links using:
  - same-domain
  - repeated path pattern
  - path depth
  - grant-like anchor/url text
- Preserve three buckets in debug:
  - extracted
  - candidate
  - selected

### 5. Detail Fetch
- Re-detect fetch type per detail URL.
- Store per-source detail fetch counts and detail URLs in debug.
- Do not assume detail pages share the listing page fetch mode.

### 6. Field Extraction
- Split into:
  - deterministic extraction
  - AI completion/fallback
- Keep evidence snippets and field-level confidence in extracted payloads.

### 7. Normalisation
- Explicit schemas:
  - `ExtractedGrant`
  - `NormalizedGrant`
- Normalize after extraction, not directly from raw heuristics.

### 8. Deduplication
- Deduplicate on:
  - canonical URL hash
  - content hash
  - semantic/title-provider-deadline hash
- Apply dedupe both before detail fetch and after normalization.

## Repo Changes
- `apps/control-plane/src/services/generic_grant_discovery.py`
  - typed fetch artifacts
  - page type scoring
  - improved listing extraction
  - per-detail fetch reclassification
  - stronger extraction + normalization contracts
  - stronger dedupe
- `apps/control-plane/src/services/grant_writer_service.py`
  - persist and expose pipeline runs
  - keep normalized outputs stable for dashboard projection
- `apps/control-plane/src/adapters/repository_sqlite.py`
  - persist pipeline run artifacts
- `apps/web/index.html`
  - render pipeline summary and drill-down cards

## Success Criteria
- Each source run explains exactly where it failed.
- Listing pages yield measurable link funnels.
- Detail pages are fetched with the correct strategy more often.
- Extracted raw JSON is stable and inspectable before normalization.
- Duplicate grants are reduced across repeated runs and mirrored URLs.
