"""
Backend for the dashboard: accepts a raw WhatsApp .txt export, runs it
through the existing Phase 1 parser and Phase 2 summarizer, and returns
the structured summary JSON.
This exists because a browser can't read a local file with Python, and
can't reach a local Ollama instance directly for anything beyond a raw
fetch (no ability to run the chunking/retry/merge logic client-side).
So the flow is: browser uploads .txt -> this server parses + summarizes
it using the same src/parser.py and src/summarizer.py from Phases 1-2 ->
server returns the summary JSON -> browser renders it. Nothing leaves
your machine; this server only listens on localhost.
"""

import json
import os
import sys
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Reuse the existing Phase 1 / Phase 2 modules directly rather than
# reimplementing parsing or summarization logic here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.parser import parse_chat  # noqa: E402
from src.summarizer import summarize_chat_messages  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


app = FastAPI(title="WhatsApp Chat Summarizer")

# CORS: only the dashboard's pinned dev server port (5174) is allowed to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.post("/api/process")
async def process_export(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a .txt WhatsApp export.")

    contents = await file.read()

    # parse_chat() expects a filepath, so the upload is written to a temp
    # file rather than reworking the parser to accept raw text in memory.
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        messages = parse_chat(tmp_path)
    finally:
        os.remove(tmp_path)

    if not messages:
        raise HTTPException(
            status_code=422,
            detail="No messages could be parsed from that file. Is it a genuine WhatsApp export?",
        )

    # Persist the parsed messages to disk, mirroring what running
    # src/parser.py directly would produce -- so data/formatted_chat.json
    # stays in sync with whatever was last processed, whether that
    # happened via the CLI or via a dashboard upload.
    os.makedirs(DATA_DIR, exist_ok=True)
    formatted_path = os.path.join(DATA_DIR, "formatted_chat.json")
    with open(formatted_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    try:
        summary = summarize_chat_messages(messages)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Couldn't reach Ollama or summarization failed: {e}",
        )

    # Same reasoning as above: keep data/summary_output.json in sync too.
    summary_path = os.path.join(DATA_DIR, "summary_output.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        "message_count": len(messages),
        "summary": summary,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)