import { useState } from "react";
import FileUploader from "./components/FileUploader";
import EstimatorTimer from "./components/EstimatorTimer";
import TLDRBanner from "./components/TLDRBanner";
import ActionItemsCard from "./components/ActionItemsCard";
import DecisionsCard from "./components/DecisionsCard";
import MentionsGrid from "./components/MentionsGrid";

export default function App() {
  const [summary, setSummary] = useState(null);

  return (
    <div className="min-h-screen px-4 py-10 sm:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <h1 className="font-serif text-3xl sm:text-4xl text-text-primary">
            Chat Digest
          </h1>
          <p className="text-text-muted mt-1">
            A quick read on what happened while you were away.
          </p>
        </header>

        {!summary ? (
          <div className="space-y-6">
            <FileUploader onLoad={setSummary} />
            <EstimatorTimer />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setSummary(null)}
                className="text-sm text-text-muted hover:text-text-primary transition-colors"
              >
                &larr; Load a different file
              </button>
            </div>

            <TLDRBanner tldr={summary.tldr} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ActionItemsCard items={summary.action_items} />
              <DecisionsCard decisions={summary.key_decisions} />
            </div>

            <MentionsGrid highlights={summary.direct_mentions_and_highlights} />
          </div>
        )}
      </div>
    </div>
  );
}
