import os
import sys
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure the parent directory is on sys.path so we can import from src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import execution functions directly from your existing modules
from src.parser import parse_chat
from src.summariser import summarize_chat_messages

app = FastAPI(title="WhatsApp Chat Summarizer API")

# Enable CORS so your React frontend (e.g. running on http://localhost:5173) can communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/summarize")
async def summarize_endpoint(file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file format. Please upload a raw WhatsApp export (.txt file)."
        )

    try:
        # 1. Save uploaded stream bytes to a temporary file on disk
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # 2. Call parse_chat from parser.py using the temporary file path
        # This handles regex Android/iOS checks, line continuations, and noise filtering
        parsed_messages = parse_chat(temp_path)

        # Remove temporary file from disk immediately after reading
        os.remove(temp_path)

        if not parsed_messages:
            raise HTTPException(
                status_code=400, 
                detail="No valid chat messages found in the file."
            )

        # 3. Call summarize_chat_messages from summarizer.py
        # This handles chunking, local Ollama API calls, validation, and summary merging
        summary_result = summarize_chat_messages(parsed_messages)

        # 4. Return final structured JSON directly back to React FileUploader component
        return summary_result

    except Exception as e:
        # Ensure temporary file is cleaned up if an error occurs mid-execution
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)