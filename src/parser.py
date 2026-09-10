import re
import json
from datetime import datetime

# Android: 12/08/2026, 14:20 - Alice: message
ANDROID_PATTERN = re.compile(
    r'^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s'
    r'(?P<time>\d{1,2}:\d{2}(?:\s?[APap][Mm])?)\s-\s'
    r'(?P<rest>.*)$'
)

# iOS: [12/08/2026, 14:20:15] Alice: message
IOS_PATTERN = re.compile(
    r'^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s'
    r'(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)\]\s'
    r'(?P<rest>.*)$'
)

SENDER_MESSAGE_PATTERN = re.compile(r'^(?P<sender>[^:]+):\s(?P<message>.*)$', re.DOTALL)
NOISE_SUBSTRINGS = [
    "Messages and calls are end-to-end encrypted",
    "<Media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "GIF omitted",
    "document omitted",
    "This message was deleted",
    "You deleted this message",
    "Missed voice call",
    "Missed video call",
]

def is_noise(text: str) -> bool:
    return any(marker in text for marker in NOISE_SUBSTRINGS)

DATE_FORMATS = ["%d/%m/%Y", "%d/%m/%y"]
TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]

def normalize_timestamp(date_str: str, time_str: str) -> str | None:
    dt_date = None
    for fmt in DATE_FORMATS:
        try:
            dt_date = datetime.strptime(date_str, fmt).date()
            break
        except ValueError:
            continue
    if dt_date is None:
        return None

    # iPhone exports insert a narrow no-break space (U+202F) before AM/PM
    # instead of a normal space — invisible in most editors, breaks strptime.
    time_clean = time_str.replace('\u202f', ' ').strip()

    dt_time = None
    for fmt in TIME_FORMATS:
        try:
            dt_time = datetime.strptime(time_clean, fmt).time()
            break
        except ValueError:
            continue
    if dt_time is None:
        return None

    return datetime.combine(dt_date, dt_time).strftime("%Y-%m-%d %H:%M:%S")

def parse_line(line: str):
    for pattern in (ANDROID_PATTERN, IOS_PATTERN):
        m = pattern.match(line)
        if m:
            return m.group('date'), m.group('time'), m.group('rest')
    return None


def parse_chat(filepath: str) -> list[dict]:
    messages = []
    current = None  # in-progress message dict, or None

    with open(filepath, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            if not line.strip():
                continue

            parsed = parse_line(line)

            if parsed is None:
                # No timestamp prefix -> continuation of the previous message
                if current is not None:
                    current['message'] += '\n' + line
                continue

            # A new timestamped entry starts -> flush whatever we were building
            if current is not None:
                messages.append(current)
                current = None

            date_str, time_str, rest = parsed
            sender_match = SENDER_MESSAGE_PATTERN.match(rest)

            if sender_match is None:
                continue  # system/group event, drop it

            sender = sender_match.group('sender').strip()
            message = sender_match.group('message').strip()

            if is_noise(message):
                continue

            current = {
                'timestamp': normalize_timestamp(date_str, time_str),
                'sender': sender,
                'message': message,
            }

    if current is not None:
        messages.append(current)

    return messages

def main():
    import sys
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'data/chat.txt'
    output_path = 'data/formatted_chat.json'

    messages = parse_chat(input_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(messages)} messages -> {output_path}")


if __name__ == '__main__':
    main()