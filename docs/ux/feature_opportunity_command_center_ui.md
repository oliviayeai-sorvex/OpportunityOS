# UI Components: opportunity_command_center

## Component Hierarchy
- `DashboardPage`
- `FilterPanel`
- `VerificationSummary`
- `OpportunityTable`
- `ScoreBreakdownCard`
- `VerifyActionControls`

## Responsibilities
- `FilterPanel`: criteria controls with validation.
- `OpportunityTable`: ranked rows and selection callbacks.
- `ScoreBreakdownCard`: selected row factor details.
- `VerifyActionControls`: verify/reject actions with reason input.
- `VerificationSummary`: domain totals and status metrics.

## Key Props
- `OpportunityTable`
  - `rows: OpportunityViewModel[]`
  - `onSelect(rowId: string): void`
- `ScoreBreakdownCard`
  - `score?: ScoreCard`
- `VerifyActionControls`
  - `opportunityId: string`
  - `onVerify(status: 'verified' | 'rejected', reason: string): Promise<void>`
