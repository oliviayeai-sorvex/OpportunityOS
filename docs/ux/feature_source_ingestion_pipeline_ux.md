# UX Design: source_ingestion_pipeline

## User Journey
1. Operator opens dashboard ingestion panel.
2. Operator selects provider domains (`stocks`, `real_estate`, `grants`) and starts ingestion.
3. UI shows per-provider progress and partial failures.
4. Operator reviews normalized opportunities and ingestion summary.

## Page Map
- Dashboard `/dashboard`
- Ingestion panel section (top)
- Recent ingestion history table

## Interaction Flow
- Trigger ingestion -> optimistic spinner -> provider status chips -> summary toast.
- Provider failure chip opens detail drawer with validation errors.

## UI States
- Loading: all selected providers show `Syncing...`.
- Empty: `No opportunities ingested yet` with CTA to start ingestion.
- Success: `N opportunities synced` and table refresh.
- Validation Error: inline message for unsupported source.
- API Error: non-blocking banner and retry action.

## ASCII Wireframes

```text
+--------------------------------------------------------------+
| OpportunityOS Dashboard                                      |
| [Ingest Now] [stocks x] [real_estate x] [grants x]          |
|--------------------------------------------------------------|
| Provider Status: [stocks: done] [real_estate: done] [grants: error] |
| Error: grants timeout (retry)                                |
+--------------------------------------------------------------+
| Recent Opportunities                                         |
| id | domain | title | value_estimate | risk | source         |
|--------------------------------------------------------------|
| ...                                                          |
+--------------------------------------------------------------+
```
