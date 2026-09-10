export default function TLDRBanner({ tldr }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface px-6 py-8 sm:px-8 sm:py-10">
      <p className="text-sm text-text-muted mb-2">While you were away</p>
      <p className="font-serif text-2xl sm:text-3xl leading-snug text-text-primary">
        {tldr || "No summary text was generated for this chat."}
      </p>
    </div>
  );
}
