import { useEffect, useMemo, useState } from "react";
import { fetchDashboardData } from "../lib/mockApi";
import type { DashboardSummary, Opportunity } from "../lib/types";

type ActionItem = {
  id: string;
  summary: string;
  dueDate: string;
};

export function useOpportunities() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minScore, setMinScore] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);

  useEffect(() => {
    fetchDashboardData()
      .then((data) => {
        setItems(data.items);
        setSummary(data.summary);
      })
      .catch(() => setError("Failed to load opportunities"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () => items.filter((row) => (row.score_card?.total ?? 0) >= minScore),
    [items, minScore],
  );

  const selected = useMemo(
    () => filtered.find((row) => row.id === selectedId) ?? null,
    [filtered, selectedId],
  );

  const createAction = (summary: string, dueDate: string) => {
    setActions((current) => [
      ...current,
      {
        id: `${Date.now()}`,
        summary,
        dueDate,
      },
    ]);
  };

  return {
    items: filtered,
    summary,
    loading,
    error,
    minScore,
    setMinScore,
    selected,
    setSelectedId,
    actions,
    createAction,
  };
}
