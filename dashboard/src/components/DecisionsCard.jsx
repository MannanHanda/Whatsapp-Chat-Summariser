export default function DecisionsCard({ decisions }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface p-5">
      <h2 className="font-serif text-lg mb-3">Key decisions</h2>
      {!decisions || decisions.length === 0 ? (
        <p className="text-sm text-text-muted">No decisions were finalized.</p>
      ) : (
        <ul className="space-y-3">
          {decisions.map((decision, i) => (
            <li
              key={i}
              className="border-l-2 border-sage pl-3 text-sm text-text-primary"
            >
              {decision}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
