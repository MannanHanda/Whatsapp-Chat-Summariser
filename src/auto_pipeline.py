"""
Auto-pipeline: watches for new messages since the last run and triggers
summarization automatically once a threshold is crossed.

WhatsApp has no API to auto-export chats, so this assumes you periodically
drop a fresh export .txt into data/ (manually, or via a folder-watcher later).
Each run compares the export against a checkpoint of how many messages were
already processed, and only summarizes the *new* messages once there are
enough of them.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import parser as chat_parser
import summariser

STATE_PATH = "data/.pipeline_state.json"
DEFAULT_THRESHOLD = 50


def load_state(state_path: str = STATE_PATH) -> dict:
    if not os.path.exists(state_path):
        return {"last_processed_count": 0}
    with open(state_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_state(state: dict, state_path: str = STATE_PATH) -> None:
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)


def run_auto_pipeline(export_path: str, threshold: int = DEFAULT_THRESHOLD,
                       state_path: str = STATE_PATH,
                       output_dir: str = "data",
                       url: str = summariser.OLLAMA_URL) -> dict:
    """
    Parse the export, compare against the checkpoint, and summarize only if
    enough new messages have accumulated. Returns a status dict describing
    what happened (useful for a UI to display later).
    """
    all_messages = chat_parser.parse_chat(export_path)
    state = load_state(state_path)
    last_count = state.get("last_processed_count", 0)

    new_messages = all_messages[last_count:]

    if len(new_messages) < threshold:
        return {
            "triggered": False,
            "new_message_count": len(new_messages),
            "threshold": threshold,
            "messages_needed": threshold - len(new_messages),
        }

    summary = summariser.summarize_chat_messages(new_messages, url=url)

    output_path = os.path.join(output_dir, "summary_output.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    state["last_processed_count"] = len(all_messages)
    save_state(state, state_path)

    return {
        "triggered": True,
        "new_message_count": len(new_messages),
        "threshold": threshold,
        "summary_path": output_path,
        "summary": summary,
    }


def main():
    export_path = sys.argv[1] if len(sys.argv) > 1 else 'data/chat.txt'
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_THRESHOLD

    result = run_auto_pipeline(export_path, threshold=threshold)

    if result["triggered"]:
        print(f"Threshold crossed: {result['new_message_count']} new messages "
              f"(>= {result['threshold']}). Summary written -> {result['summary_path']}")
    else:
        print(f"Only {result['new_message_count']} new messages since last run "
              f"(need {result['messages_needed']} more to reach the {result['threshold']} threshold). "
              f"No summary generated.")


if __name__ == '__main__':
    main()