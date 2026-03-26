# UI Components: source_ingestion_pipeline

## Component Hierarchy
- `DashboardPage`
- `IngestionToolbar`
- `ProviderStatusChips`
- `IngestionSummaryCard`
- `OpportunityTable`

## Component Responsibilities
- `IngestionToolbar`: source multi-select, run action, loading state.
- `ProviderStatusChips`: render provider-level success/failure badge list.
- `IngestionSummaryCard`: count totals (`ingested`, `rejected`, `failed_providers`).
- `OpportunityTable`: normalized record table.

## Key Props
- `IngestionToolbar`
  - `sources: SourceType[]`
  - `isRunning: boolean`
  - `onRun(sources: SourceType[]): Promise<void>`
- `ProviderStatusChips`
  - `statuses: ProviderRunStatus[]`
- `OpportunityTable`
  - `rows: OpportunityViewModel[]`
  - `isLoading: boolean`
  - `onRetry?: () => void`
