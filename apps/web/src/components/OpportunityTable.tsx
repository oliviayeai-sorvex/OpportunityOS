import React from "react";
import type { Opportunity } from "../lib/types";

type Props = {
  rows: Opportunity[];
  isLoading: boolean;
  error?: string | null;
  onSelect: (id: string) => void;
};

export function OpportunityTable({ rows, isLoading, error, onSelect }: Props) {
  if (isLoading) {
    return <p>Loading opportunities...</p>;
  }
  if (error) {
    return <p role="alert">{error}</p>;
  }
  if (rows.length === 0) {
    return <p>No opportunities match current filters.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Domain</th>
          <th>Value</th>
          <th>Risk</th>
          <th>Score</th>
          <th>Verification</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} onClick={() => onSelect(row.id)}>
            <td>{row.title}</td>
            <td>{row.domain}</td>
            <td>{row.value_estimate.toLocaleString()}</td>
            <td>{row.risk_level}</td>
            <td>{row.score_card?.total ?? 0}</td>
            <td>{row.verification_status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
