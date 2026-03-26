import React from "react";

type Props = {
  minScore: number;
  onMinScoreChange: (value: number) => void;
};

export function FilterPanel({ minScore, onMinScoreChange }: Props) {
  return (
    <section>
      <label htmlFor="minScore">Minimum Score</label>
      <input
        id="minScore"
        type="range"
        min={0}
        max={100}
        value={minScore}
        onChange={(event) => onMinScoreChange(Number(event.target.value))}
      />
      <span>{minScore}</span>
    </section>
  );
}
