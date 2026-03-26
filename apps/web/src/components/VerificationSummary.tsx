import React from "react";
import type { DashboardSummary } from "../lib/types";

type Props = {
  summary: DashboardSummary | null;
};

export function VerificationSummary({ summary }: Props) {
  if (!summary) return null;

  return (
    <section>
      <h2>Verification Dashboard</h2>
      <p>Total: {summary.total}</p>
      <p>Verified: {summary.verified}</p>
      <p>Pending: {summary.pending}</p>
      <p>Rejected: {summary.rejected}</p>
    </section>
  );
}
