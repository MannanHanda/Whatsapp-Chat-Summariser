"""
Phase 2: Local AI Summarization Engine.

Sends the clean formatted_chat.json produced by Phase 1 to a local Ollama
model and produces a structured JSON summary (summary_output.json).
"""

import json
import os
import requests

# --- Configuration ------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"

# Swap models without editing code: OLLAMA_MODEL=qwen2.5:1.5b python src/summarizer.py ...
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

CHUNK_SIZE = 50  # messages per chunk sent to the model


def load_messages(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_messages_compact(chunk: list) -> str:
    """
    Render a chunk as flat "[MM-DD HH:MM] Sender: message" lines instead of
    JSON, cutting prompt token overhead significantly (no repeated key
    names, braces, or quoting per message).

    The year is dropped (redundant within a single export) and seconds are
    dropped (not meaningful for summarization), but month-day is kept since
    a chunk can span multiple days. Embedded newlines in a message (from
    Phase 1's multiline consolidation) are flattened to a single space,
    since this format uses one line per message -- an embedded newline
    would look like a second message to the model.
    """
    lines = []
    for msg in chunk:
        ts = msg.get('timestamp') or ''
        short_ts = ts[5:16].replace('T', ' ') if len(ts) >= 16 else ts  # "MM-DD HH:MM"
        sender = msg.get('sender', 'Unknown')
        text = (msg.get('message') or '').replace('\n', ' ')
        lines.append(f"[{short_ts}] {sender}: {text}")
    return "\n".join(lines)


# --- Chunking -------------------------------------------------------------

def chunk_messages(messages: list, chunk_size: int = CHUNK_SIZE) -> list:
    """
    Split messages into fixed-size batches so each request fits comfortably
    within the model's context window.

    A count-based chunk is used rather than a time-window chunk because it
    gives a predictable, bounded prompt size regardless of how bursty the
    conversation is (a chatty 10-minute window could otherwise blow past
    the context limit while a quiet 3-day window would waste a whole
    request on a handful of messages).
    """
    return [messages[i:i + chunk_size] for i in range(0, len(messages), chunk_size)]


# --- Output schema and system prompt ---------------------------------------

# The exact shape every chunk summary (and the final merged summary) must match.
TARGET_SCHEMA_EXAMPLE = {
    "tldr": "High-level summary of what happened while you were away.",
    "action_items": [
        {"assignee": "Name or Unassigned", "task": "Specific action item mentioned"}
    ],
    "key_decisions": ["Decision 1 made by the group"],
    "direct_mentions_and_highlights": ["Important messages or specific callouts"],
}

SYSTEM_PROMPT = f"""You are a precise chat log summarizer. You will be given a
batch of WhatsApp messages, one per line, in this format:
[MM-DD HH:MM] Sender: message text

Your job is to extract SIGNAL, not to narrate the conversation:
- Ignore small talk, greetings, filler, and reactions ("How are you?",
  "lol", "brb", "haha", single-emoji replies, "ok", "sounds good" with no
  new information).
- Focus strictly on: Who said/did something, What it was, When it happened
  (if relevant), Where (if a location/link is mentioned), and any Next
  Steps or open questions.
- Attribute every action item and decision to a specific sender's name
  whenever the message makes that clear. Only use "Unassigned" when no
  sender can reasonably be inferred.
- If nothing in this batch qualifies for a given field, return an empty
  list for it (not a placeholder or made-up entry).
- Do not invent information that is not present in the messages.

You MUST respond with ONLY valid JSON matching exactly this structure, with
no prose, no markdown code fences, and no commentary before or after it:

{json.dumps(TARGET_SCHEMA_EXAMPLE, indent=2)}
"""

REQUIRED_KEYS = {"tldr", "action_items", "key_decisions", "direct_mentions_and_highlights"}


def validate_summary(obj) -> bool:
    """Check the model's output has the required shape (not full type-checking,
    just enough to catch a model that ignored instructions or returned partial JSON)."""
    if not isinstance(obj, dict):
        return False
    if not REQUIRED_KEYS.issubset(obj.keys()):
        return False
    if not isinstance(obj["tldr"], str):
        return False
    if not isinstance(obj["action_items"], list):
        return False
    if not isinstance(obj["key_decisions"], list):
        return False
    if not isinstance(obj["direct_mentions_and_highlights"], list):
        return False
    return True


def _strip_code_fences(text: str) -> str:
    """Some local models still wrap JSON in ```json ... ``` even in JSON mode."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def call_ollama(system_prompt: str, user_content: str,
                 model: str = MODEL_NAME, url: str = OLLAMA_URL,
                 timeout: int = 120) -> str:
    payload = {
        "model": model,
        "format": "json",       # forces Ollama's JSON-constrained decoding
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "options": {"temperature": 0.2},  # low temperature: consistent structure over creativity
    }
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


def summarize_chunk(chunk: list, model: str = MODEL_NAME, url: str = OLLAMA_URL,
                     max_retries: int = 2) -> dict:
    """Send one chunk of messages to the model and return a validated summary dict.
    Retries once with a stricter reminder if the first response fails validation."""
    user_content = (
        "Summarize the following batch of chat messages according to your "
        "instructions. Messages:\n\n" + format_messages_compact(chunk)
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = call_ollama(SYSTEM_PROMPT, user_content, model=model, url=url)
            cleaned = _strip_code_fences(raw)
            parsed = json.loads(cleaned)
            if validate_summary(parsed):
                return parsed
            last_error = f"response failed schema validation: {cleaned[:200]}"
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_error = str(e)

        # Tighten the ask for the retry
        user_content = (
            "Your previous response was not valid JSON matching the required "
            "schema. Respond with ONLY the JSON object, nothing else.\n\n"
            + user_content
        )

    # All retries exhausted -> return an empty-but-valid schema rather than crashing
    print(f"Warning: chunk summarization failed after retries ({last_error})")
    return {
        "tldr": "",
        "action_items": [],
        "key_decisions": [],
        "direct_mentions_and_highlights": [],
    }


# --- Merging multiple chunk summaries ---------------------------------------

MERGE_SYSTEM_PROMPT = f"""You are merging several partial chat summaries (each
covering a different time segment of the same conversation) into one master
summary. You will be given a JSON array of summary objects.

- Combine and de-duplicate action items, decisions, and highlights that refer
  to the same thing (e.g. two chunks mentioning the same task) into a single
  entry rather than repeating it.
- Write a single cohesive "tldr" covering the whole conversation, not a list
  of the individual chunk tldrs.
- Preserve assignee attribution exactly as given in the source summaries.
- Do not invent new information beyond what appears in the provided summaries.

Respond with ONLY valid JSON matching exactly this structure, no prose, no
markdown fences:

{json.dumps(TARGET_SCHEMA_EXAMPLE, indent=2)}
"""


def merge_summaries(chunk_summaries: list, model: str = MODEL_NAME,
                     url: str = OLLAMA_URL, max_retries: int = 2) -> dict:
    """Run a lightweight final pass merging N chunk summaries into one master summary."""
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    user_content = "Merge these partial summaries:\n\n" + json.dumps(
        chunk_summaries, ensure_ascii=False
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = call_ollama(MERGE_SYSTEM_PROMPT, user_content, model=model, url=url)
            cleaned = _strip_code_fences(raw)
            parsed = json.loads(cleaned)
            if validate_summary(parsed):
                return parsed
            last_error = f"response failed schema validation: {cleaned[:200]}"
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_error = str(e)

        user_content = (
            "Your previous response was not valid JSON matching the required "
            "schema. Respond with ONLY the JSON object, nothing else.\n\n"
            + user_content
        )

    # Fallback: naive concatenation if the merge pass itself keeps failing --
    # better than losing all the work already done per-chunk.
    print(f"Warning: merge pass failed after retries ({last_error}); falling back to concatenation")
    return {
        "tldr": " ".join(s["tldr"] for s in chunk_summaries if s["tldr"]),
        "action_items": [item for s in chunk_summaries for item in s["action_items"]],
        "key_decisions": [d for s in chunk_summaries for d in s["key_decisions"]],
        "direct_mentions_and_highlights": [
            h for s in chunk_summaries for h in s["direct_mentions_and_highlights"]
        ],
    }


# --- Orchestration ------------------------------------------------------------

def summarize_chat_messages(messages: list, model: str = MODEL_NAME, url: str = OLLAMA_URL,
                             chunk_size: int = CHUNK_SIZE) -> dict:
    """Chunk-then-merge summarization over an in-memory list of messages
    (rather than a file path) -- used when only a slice of messages needs
    summarizing, e.g. just the new ones since a checkpoint."""
    chunks = chunk_messages(messages, chunk_size)
    print(f"{len(messages)} messages -> {len(chunks)} chunk(s) of up to {chunk_size}")

    chunk_summaries = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Summarizing chunk {i}/{len(chunks)} ({len(chunk)} messages)...")
        chunk_summaries.append(summarize_chunk(chunk, model=model, url=url))

    if len(chunk_summaries) > 1:
        print("Merging chunk summaries into master summary...")
    return merge_summaries(chunk_summaries, model=model, url=url)


def summarize_chat(input_path: str, output_path: str = "data/summary_output.json",
                    model: str = MODEL_NAME, url: str = OLLAMA_URL,
                    chunk_size: int = CHUNK_SIZE) -> dict:
    messages = load_messages(input_path)
    master_summary = summarize_chat_messages(messages, model=model, url=url, chunk_size=chunk_size)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(master_summary, f, ensure_ascii=False, indent=2)

    print(f"Summary written -> {output_path}")
    return master_summary


def main():
    import sys
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'data/formatted_chat.json'
    summarize_chat(input_path)


if __name__ == '__main__':
    main()