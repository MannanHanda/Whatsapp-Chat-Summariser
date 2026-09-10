import { useMemo, useState } from "react";

// Rough per-request timings derived from qwen2.5:3b / llama3.1:8b benchmarking
// against chunk_size=50 (see Phase 2 discussion). These are estimates, not
// live measurements -- this dashboard never calls Ollama directly, since a
// static page can't reach a local process without a backend bridge and
// Ollama's default CORS settings block it anyway.
const PROFILES = {
  cpu: { perChunkSeconds: 25, mergeSeconds: 20, label: "CPU only" },
  gpu: { perChunkSeconds: 6, mergeSeconds: 5, label: "GPU-accelerated" },
};

function estimateSeconds(messageCount, chunkSize, profileKey) {
  const chunks = Math.max(1, Math.ceil(messageCount / chunkSize));
  const profile = PROFILES[profileKey];
  const chunkTime = chunks * profile.perChunkSeconds;
  const mergeTime = chunks > 1 ? profile.mergeSeconds : 0;
  return chunkTime + mergeTime;
}

function formatDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.round(totalSeconds % 60);
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

export default function EstimatorTimer() {
  const [messageCount, setMessageCount] = useState(500);
  const [chunkSize, setChunkSize] = useState(50);
  const [profile, setProfile] = useState("cpu");

  const seconds = useMemo(
    () => estimateSeconds(messageCount, chunkSize, profile),
    [messageCount, chunkSize, profile]
  );
  const chunks = Math.max(1, Math.ceil(messageCount / chunkSize));

  return (
    <div className="rounded-lg border border-hairline bg-surface p-5">
      <h2 className="font-serif text-lg mb-1">Estimate a summarization run</h2>
      <p className="text-sm text-text-muted mb-4">
        A rough guide before you run src/summarizer.py &mdash; not a live
        measurement.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <label className="text-sm">
          <span className="block text-text-muted mb-1">Messages</span>
          <input
            type="number"
            min={1}
            value={messageCount}
            onChange={(e) => setMessageCount(Number(e.target.value) || 0)}
            className="w-full rounded border border-hairline bg-surface-alt px-3 py-2 text-text-primary"
          />
        </label>
        <label className="text-sm">
          <span className="block text-text-muted mb-1">Chunk size</span>
          <input
            type="number"
            min={1}
            value={chunkSize}
            onChange={(e) => setChunkSize(Number(e.target.value) || 1)}
            className="w-full rounded border border-hairline bg-surface-alt px-3 py-2 text-text-primary"
          />
        </label>
        <label className="text-sm">
          <span className="block text-text-muted mb-1">Hardware</span>
          <select
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            className="w-full rounded border border-hairline bg-surface-alt px-3 py-2 text-text-primary"
          >
            <option value="cpu">CPU only</option>
            <option value="gpu">GPU-accelerated</option>
          </select>
        </label>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="font-serif text-3xl text-amber">
          {formatDuration(seconds)}
        </span>
        <span className="text-sm text-text-muted">
          estimated &middot; {chunks} chunk{chunks !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  );
}
