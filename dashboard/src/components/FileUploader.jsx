import { useCallback, useRef, useState } from "react";

export default function FileUploader({ onLoad }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const intervalRef = useRef(null);

  const stopTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsLoading(false);
  };

  const handleFile = useCallback(
    async (file) => {
      setError(null);
      if (!file) return;

      // Ensure it is a text file
      if (!file.name.endsWith(".txt") && file.type !== "text/plain") {
        setError("Please upload a valid raw WhatsApp export (.txt file).");
        return;
      }

      const startedAt = performance.now();
      setIsLoading(true);
      setElapsedMs(0);
      intervalRef.current = setInterval(() => {
        setElapsedMs(performance.now() - startedAt);
      }, 50);

      const formData = new FormData();
      formData.append("file", file);

      try {
        // Sends raw .txt file to your local Python backend server
        const response = await fetch("http://localhost:8000/api/process", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        stopTimer();
        
        // Pass the generated summary back up to the main React dashboard
        onLoad(data.summary);
      } catch (err) {
        stopTimer();
        setError(
          err.message || "Failed to process chat file. Make sure your Python backend is running."
        );
      }
    },
    [onLoad]
  );

  return (
    <div className="w-full">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-14 text-center transition-colors cursor-pointer ${
          isDragging
            ? "border-amber bg-surface-alt"
            : "border-hairline bg-surface hover:border-text-muted"
        }`}
      >
        <p className="font-serif text-xl text-text-primary">
          Drop your WhatsApp exported chat (.txt) here
        </p>
        <p className="text-sm text-text-muted">
          or click to choose a file &mdash; processed locally on your device
        </p>
        <input
          type="file"
          accept=".txt,text/plain"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </label>
      {isLoading && (
        <p className="mt-3 text-sm text-text-muted">
          Parsing chat & running local Ollama model&hellip; {(elapsedMs / 1000).toFixed(2)}s
        </p>
      )}
      {error && (
        <p className="mt-3 text-sm text-coral" role="alert">
          {error}
        </p>
      )}
    </div>
  );
} 