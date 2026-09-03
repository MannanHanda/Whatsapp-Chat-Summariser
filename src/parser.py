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

SENDER_MESSAGE_PATTERN = re.compile(r'^(?P<sender>[^:]{1,40}?):\s(?P<message>.*)$')
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