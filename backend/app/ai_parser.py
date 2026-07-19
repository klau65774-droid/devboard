"""Rule-based fallback parser for the AI task assistant.

Pure functions with no side effects: extract a due date and a clean title
from a short natural-language sentence (Chinese or English). The reference
"current time" is passed in explicitly so tests are deterministic.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

# Chinese weekday names -> Python weekday index (Monday=0).
_CN_WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
_CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
_EN_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# Filler words stripped from the leftover text to form the title.
_FILLER_PATTERN = re.compile(
    r"(记得|提醒(我)?|我要|我想|我需要|需要|必须|赶紧|别忘了|把|要|在|前|之前|"
    r"please|remember to|remind me to|don't forget to|by|before)",
    re.IGNORECASE,
)


@dataclass
class ParsedTask:
    title: str
    description: str
    due_date: datetime | None


def _at(day: datetime, hour: int = 0) -> datetime:
    """Return ``day`` at a fixed hour (default: start of day)."""
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


def _next_weekday(now: datetime, target: int, next_week: bool) -> datetime:
    """Next occurrence of weekday ``target``; ``next_week`` forces next week."""
    days_ahead = (target - now.weekday()) % 7
    if next_week:
        # Days until next Monday, then offset into that week.
        days_ahead = (7 - now.weekday()) % 7 or 7
        days_ahead += target
    elif days_ahead == 0:
        days_ahead = 7
    return _at(now + timedelta(days=days_ahead))


def _extract_due_date(text: str, now: datetime) -> tuple[datetime | None, str]:
    """Find the first date expression; return (due_date, text without it)."""
    # Each rule: (pattern, handler(match) -> datetime). First match wins.
    rules: list[tuple[re.Pattern[str], object]] = [
        (re.compile(r"大后天(晚上|晚)?"),
         lambda m: _at(now + timedelta(days=3), 18 if m.group(1) else 0)),
        (re.compile(r"后天(晚上|晚)?"),
         lambda m: _at(now + timedelta(days=2), 18 if m.group(1) else 0)),
        (re.compile(r"明晚|明天(晚上|晚)"),
         lambda m: _at(now + timedelta(days=1), 18)),
        (re.compile(r"明天(下午)?"),
         lambda m: _at(now + timedelta(days=1), 14 if m.group(1) else 0)),
        (re.compile(r"今晚|今天(晚上|晚)"),
         lambda m: _at(now, 18)),
        (re.compile(r"今天(下午)?"),
         lambda m: _at(now, 14 if m.group(1) else 0)),
        (re.compile(r"下?下个?(周|星期)([一二三四五六日天])"),
         lambda m: _next_weekday(now, _CN_WEEKDAYS[m.group(2)], True)),
        (re.compile(r"(周|星期)([一二三四五六日天])"),
         lambda m: _next_weekday(now, _CN_WEEKDAYS[m.group(2)], False)),
        (re.compile(r"([0-9]+|[一二两三四五六七八九十])天后"),
         lambda m: _at(now + timedelta(
             days=int(m.group(1)) if m.group(1).isdigit()
             else _CN_DIGITS[m.group(1)]))),
        (re.compile(r"\bday after tomorrow\b", re.IGNORECASE),
         lambda m: _at(now + timedelta(days=2))),
        (re.compile(r"\btomorrow\b", re.IGNORECASE),
         lambda m: _at(now + timedelta(days=1))),
        (re.compile(r"\btoday\b", re.IGNORECASE),
         lambda m: _at(now)),
        (re.compile(r"\bin (\d+) days?\b", re.IGNORECASE),
         lambda m: _at(now + timedelta(days=int(m.group(1))))),
        (re.compile(
            r"\b(?:next\s+)?(monday|tuesday|wednesday|thursday|friday|"
            r"saturday|sunday)\b", re.IGNORECASE),
         lambda m: _next_weekday(
             now, _EN_WEEKDAYS[m.group(1).lower()],
             bool(re.match(r"(?i)next", m.group(0))))),
    ]
    for pattern, handler in rules:
        match = pattern.search(text)
        if match:
            due = handler(match)  # type: ignore[operator]
            remainder = (text[: match.start()] + " " + text[match.end():])
            return due, remainder
    return None, text


def _clean_title(text: str) -> str:
    """Strip filler words and stray punctuation from the leftover text."""
    text = _FILLER_PATTERN.sub(" ", text)
    text = re.sub(r"[\s，。,.!！?？;；:：、~～]+", " ", text)
    return text.strip()


def parse_task(text: str, now: datetime) -> ParsedTask:
    """Parse a natural-language sentence into title/description/due_date.

    ``now`` is the reference time used to resolve relative dates.
    """
    original = text.strip()
    due_date, remainder = _extract_due_date(original, now)
    title = _clean_title(remainder) or original
    return ParsedTask(title=title, description=original, due_date=due_date)
