export default function MentionsGrid({ highlights }) {
  if (!highlights || highlights.length === 0) return null;

  return (
    <div>
      <h2 className="font-serif text-lg mb-3">Worth a second look</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {highlights.map((highlight, i) => (
          <div
            key={i}
            className="rounded-lg border border-hairline bg-surface-alt p-4 text-sm text-text-primary"
          >
            {highlight}
          </div>
        ))}
      </div>
    </div>
  );
}
