# Grant Pipeline API Contracts

Base: `/api/v1`
Auth: Bearer token required for all routes below.

## 1) Run pipeline
`POST /grant-writer/pipeline/run`

Runs all stages in order:
1. Ingest raw grant data
2. Normalize
3. Rule filter
4. AI eligibility assessment
5. Project eligible/partial grants to dashboard

### Response
```json
{
  "run_id": "uuid",
  "raw_count": 24,
  "normalized_count": 24,
  "rule_candidate_count": 12,
  "assessment_count": 12,
  "scanned_count": 8,
  "eligible_count": 6,
  "partial_count": 2,
  "scanned_at": "2026-03-25T...",
  "results": []
}
```

## 2) Read pipeline artifacts by run
`GET /grant-writer/pipeline?run_id=<uuid>`

### Response
```json
{
  "run_id": "uuid",
  "raw_records": [],
  "normalized_records": [],
  "rule_candidates": [],
  "ai_assessments": []
}
```

## 3) Backward-compatible scan trigger
`POST /grant-writer/scan`

Alias for pipeline run. Same response shape as `/grant-writer/pipeline/run`.

## 4) Dashboard feed
`GET /grant-writer/dashboard`

Returns source list + schedule + dashboard projection + board columns.
Projection contains only `ELIGIBLE` and `PARTIAL` grants.

## 5) Board read
`GET /grant-writer/board?state=&sector=&min_score=&max_score=&sort_by=deadline|amount|score`

### Response
```json
{
  "board": {
    "New": [],
    "Shortlisted": [],
    "In Progress": [],
    "Under Review": [],
    "Submitted": [],
    "Closed": []
  },
  "count": 0
}
```

## 6) Board status update
`POST /grant-writer/board/move`

### Request
```json
{
  "grant_result_id": "uuid",
  "workflow_status": "Shortlisted"
}
```

## 7) Draft workflow
- `POST /grant-writer/draft`
- `GET /grant-writer/drafts?grant_result_id=<uuid>`

## 8) Review/submit lifecycle
- `POST /grant-writer/mark-reviewed`
- `POST /grant-writer/mark-submitted`
- `POST /grant-writer/tracking`

## 9) Search
`POST /search`

### Request
```json
{ "query": "clean energy grant" }
```

### Response
```json
{
  "results": [],
  "jobs": [],
  "summary": "..."
}
```

Behavior:
- query length < 2 => empty result set with guidance
- specific query => single best match preferred
- otherwise ranked matching list

## AI provider contract
Environment:
- `AI_PROVIDER=local|cloud`
- local test default uses llama3 endpoint:
  - `LOCAL_LLM_MODEL=llama3`
  - `LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/api/generate`

Cloud mode is reserved by interface and can be enabled without API contract changes.
