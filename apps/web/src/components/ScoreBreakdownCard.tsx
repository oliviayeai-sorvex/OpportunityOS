import React from "react";
import type { Opportunity } from "../lib/types";

type Props = {
  selected: Opportunity | null;
};

export function ScoreBreakdownCard({ selected }: Props) {
  if (!selected || !selected.score_card) {
    return <p>Select an opportunity to view score breakdown.</p>;
  }

  return (
    <section>
      <h2>Score Breakdown</h2>
      <p>{selected.title}</p>
      <p>Total Score: {selected.score_card.total}</p>
      <p>Confidence: {selected.score_card.confidence}</p>
      <ul>
        {Object.entries(selected.score_card.factors).map(([key, value]) => (
          <li key={key}>
            {key}: {value}
          </li>
        ))}
      </ul>
    </section>
  );
}
