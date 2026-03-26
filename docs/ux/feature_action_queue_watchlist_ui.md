# UI Components: action_queue_watchlist

## Component Hierarchy
- `WatchlistPanel`
- `ActionQueuePanel`
- `CreateActionForm`

## Responsibilities
- `WatchlistPanel`: render saved opportunities and add action button.
- `CreateActionForm`: capture summary/due date, submit with validation.
- `ActionQueuePanel`: list open/done actions by owner.

## Key Props
- `WatchlistPanel`
  - `items: OpportunityViewModel[]`
  - `onAdd(opportunityId: string): Promise<void>`
- `CreateActionForm`
  - `opportunityId: string`
  - `onSubmit(payload: ActionInput): Promise<void>`
- `ActionQueuePanel`
  - `actions: ActionItemViewModel[]`
