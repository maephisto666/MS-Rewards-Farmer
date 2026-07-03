"""
Parse the Next.js App Router RSC (React Server Components) wire format
embedded in the Rewards dashboard page HTML.

All dashboard data (balance, daily set items, activity counters) is
server-rendered into self.__next_f.push([1, "..."]) inline scripts, where
the payload is a JSON-string-encoded RSC text stream. This module decodes
those payloads and extracts the structured data without requiring any
JavaScript execution.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Regex for a JSON string value inside __next_f.push([1, "..."])
_PUSH_RE = re.compile(
    r'__next_f\.push\(\[1\s*,\s*"((?:[^"\\]|\\.)*)"\]\)',
    re.DOTALL,
)


@dataclass
class DailySetItem:
    offer_id: str
    points: int
    is_completed: bool
    destination: str
    title: str
    description: str
    date: str
    is_locked: bool
    image_url: str = ""

    @classmethod
    def from_rsc(cls, d: dict) -> "DailySetItem":
        return cls(
            offer_id=d.get("offerId", ""),
            points=d.get("points", 0),
            is_completed=bool(d.get("isCompleted", False)),
            destination=d.get("destination", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            date=d.get("date", ""),
            is_locked=bool(d.get("isLocked", False)),
            image_url=d.get("imageUrl", ""),
        )


@dataclass
class DashboardData:
    balance: int = 0
    level: int = 1
    daily_set_items: list[DailySetItem] = field(default_factory=list)
    activities_remaining: int = 0
    activities_requirement: int = 0
    activities_progress: int = 0


def _collect_rsc_text(html: str) -> str:
    """
    Collect all RSC payload text from the page HTML.

    Next.js streams RSC data as self.__next_f.push([1, "..."]) calls where
    the inner string is JSON-string-encoded (so `"` → `\"`). We decode each
    payload and join them for searching.
    """
    parts: list[str] = []
    inline_scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for script in inline_scripts:
        for m in _PUSH_RE.finditer(script):
            raw = m.group(1)
            try:
                # Decode the JSON string escaping: \" → ", \n → newline, etc.
                parts.append(json.loads('"' + raw + '"'))
            except json.JSONDecodeError:
                # Fallback: simple unescape of the most common escapes
                parts.append(raw.replace('\\"', '"').replace("\\n", "\n"))
    return "\n".join(parts)


def _extract_json_array(text: str, key: str) -> list:
    """
    Extract the JSON array value for the given key from arbitrary text.
    Uses a bracket counter so nested objects inside the array are handled.
    """
    m = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if not m:
        return []
    start = m.end() - 1  # position of opening '['
    depth = 0
    for i, c in enumerate(text[start:]):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : start + i + 1])
                except json.JSONDecodeError:
                    logger.debug("RSC: failed to JSON-parse %s array", key)
                    return []
    return []


def _int_field(key: str, text: str) -> int | None:
    m = re.search(rf'"{re.escape(key)}"\s*:\s*(\d+)', text)
    return int(m.group(1)) if m else None


def parse_dashboard(html: str) -> DashboardData:
    """
    Extract structured dashboard data from the Next.js RSC wire format
    embedded in the page HTML. Returns a DashboardData with best-effort
    values (zeros / empty list) for anything not found.
    """
    rsc_text = _collect_rsc_text(html)
    data = DashboardData()

    balance = _int_field("balance", rsc_text)
    if balance is not None:
        data.balance = balance
    else:
        logger.warning("RSC: 'balance' not found in RSC payload")

    level = _int_field("level", rsc_text)
    if level is not None:
        data.level = level

    remaining = _int_field("activitiesRemaining", rsc_text)
    if remaining is not None:
        data.activities_remaining = remaining

    requirement = _int_field("activitiesRequirement", rsc_text)
    if requirement is not None:
        data.activities_requirement = requirement

    progress = _int_field("activitiesProgress", rsc_text)
    if progress is not None:
        data.activities_progress = progress

    raw_items = _extract_json_array(rsc_text, "dailySetItems")
    data.daily_set_items = [
        DailySetItem.from_rsc(item)
        for item in raw_items
        if isinstance(item, dict)
    ]

    if not data.daily_set_items:
        logger.warning("RSC: dailySetItems empty or not found in RSC payload")

    logger.info(
        "RSC: balance=%d level=%d daily_set_items=%d activities_remaining=%d/%d",
        data.balance,
        data.level,
        len(data.daily_set_items),
        data.activities_remaining,
        data.activities_requirement,
    )
    return data
