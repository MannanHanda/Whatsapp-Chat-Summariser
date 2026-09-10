import { useState } from "react";

function AssigneeBadge({ assignee }) {
  const isUnassigned = !assignee || assignee.toLowerCase() === "unassigned";
  return (
    <span
      className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
        isUnassigned
          ? "bg-coral/15 text-coral"
          : "bg-sage/15 text-sage"
      }`}
    >
      {isUnassigned ? "Unassigned" : assignee}
    </span>
  );
}

export default function ActionItemsCard({ items }) {
  // Keyed by index so checking a box doesn't depend on task text staying unique.
  const [checked, setChecked] = useState({});

  const toggle = (index) => {
    setChecked((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  if (!items || items.length === 0) {
    return (
      <div className="rounded-lg border border-hairline bg-surface p-5">
        <h2 className="font-serif text-lg mb-1">Action items</h2>
        <p className="text-sm text-text-muted">Nothing came up that needs doing.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-hairline bg-surface overflow-hidden">
      <h2 className="font-serif text-lg px-5 pt-5 pb-3">Action items</h2>
      <ul>
        {items.map((item, i) => (
          <li
            key={i}
            className="flex items-start gap-3 border-t border-hairline px-5 py-3"
          >
            <input
              type="checkbox"
              checked={!!checked[i]}
              onChange={() => toggle(i)}
              className="mt-1 h-4 w-4 shrink-0 accent-sage cursor-pointer"
              aria-label={`Mark "${item.task}" as done`}
            />
            <span
              className={`flex-1 text-sm ${
                checked[i] ? "line-through text-text-muted" : "text-text-primary"
              }`}
            >
              {item.task}
            </span>
            <AssigneeBadge assignee={item.assignee} />
          </li>
        ))}
      </ul>
    </div>
  );
}
