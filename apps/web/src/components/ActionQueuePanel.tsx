import React from "react";

type ActionItem = {
  id: string;
  summary: string;
  dueDate: string;
};

type Props = {
  actions: ActionItem[];
  onCreateAction: (summary: string, dueDate: string) => void;
};

export function ActionQueuePanel({ actions, onCreateAction }: Props) {
  const [summary, setSummary] = React.useState("");
  const [dueDate, setDueDate] = React.useState("");

  const onSubmit = () => {
    if (summary.trim().length < 4 || !dueDate) {
      return;
    }
    onCreateAction(summary.trim(), dueDate);
    setSummary("");
    setDueDate("");
  };

  return (
    <section>
      <h2>Action Queue</h2>
      <p>Track follow-up tasks for selected opportunities.</p>
      <div>
        <input
          placeholder="Action summary"
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
        />
        <input
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.target.value)}
        />
        <button onClick={onSubmit}>Create Action</button>
      </div>
      <ul>
        {actions.map((action) => (
          <li key={action.id}>
            {action.summary} (due {action.dueDate})
          </li>
        ))}
      </ul>
    </section>
  );
}
