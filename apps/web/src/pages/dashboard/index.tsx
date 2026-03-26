import React from "react";
import { ActionQueuePanel } from "../../components/ActionQueuePanel";
import { FilterPanel } from "../../components/FilterPanel";
import { OpportunityTable } from "../../components/OpportunityTable";
import { ScoreBreakdownCard } from "../../components/ScoreBreakdownCard";
import { VerificationSummary } from "../../components/VerificationSummary";
import { useOpportunities } from "../../hooks/useOpportunities";

export default function DashboardPage() {
  const {
    items,
    summary,
    loading,
    error,
    minScore,
    setMinScore,
    selected,
    setSelectedId,
    actions,
    createAction,
  } = useOpportunities();

  return (
    <main>
      <h1>OpportunityOS Command Center</h1>
      <FilterPanel minScore={minScore} onMinScoreChange={setMinScore} />
      <VerificationSummary summary={summary} />
      <OpportunityTable rows={items} isLoading={loading} error={error} onSelect={setSelectedId} />
      <ScoreBreakdownCard selected={selected} />
      <ActionQueuePanel actions={actions} onCreateAction={createAction} />
    </main>
  );
}
