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
from urllib.parse import parse_qs, unquote_plus, urlparse

logger = logging.getLogger(__name__)

# Regex for a JSON string value inside __next_f.push([1, "..."])
_PUSH_RE = re.compile(
    r'__next_f\.push\(\[1\s*,\s*"((?:[^"\\]|\\.)*)"\]\)',
    re.DOTALL,
)


def _rsc_bool(val, default: bool = False) -> bool:
    """
    Coerce an RSC value to bool.
    The RSC wire format encodes JavaScript `undefined` as the string '$undefined'.
    Treat it (and None) as the given default rather than as truthy.
    """
    if val is None or val == "$undefined":
        return default
    return bool(val)


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
            is_completed=_rsc_bool(d.get("isCompleted"), default=False),
            destination=d.get("destination", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            date=d.get("date", ""),
            is_locked=_rsc_bool(d.get("isLocked"), default=False),
            image_url=d.get("imageUrl", ""),
        )

    @property
    def activity_type(self) -> str:
        """
        Infer the activity type from the destination URL.

        Types:
          BING_QUIZ      — Copilot-based quiz (form=dsetqu, IsConversation=True)
          URL_OFFER      — Navigate-to-earn (BTEPOKey=REWARDSQUIZ_DailySet_UrlOffer)
          TRAVEL_REWARD  — Travel search reward (FORM=tgrew*)
          REFERRAL       — Referral link (rewards.bing.com/referandearn)
          UNKNOWN        — Anything else
        """
        dest = self.destination
        if not dest:
            return "UNKNOWN"
        if "referandearn" in dest:
            return "REFERRAL"
        qs = parse_qs(urlparse(dest).query)
        filters = unquote_plus(" ".join(qs.get("filters", [])))
        form = (qs.get("form") or qs.get("FORM") or [""])[0].lower()
        if "IsConversation" in filters and "True" in filters:
            return "BING_QUIZ"
        if "UrlOffer" in filters:
            return "URL_OFFER"
        if form.startswith("tgrew"):
            return "TRAVEL_REWARD"
        if form.startswith("ml2"):
            return "URL_OFFER"
        # Catch-all: any bing.com destination is a navigate-to-earn offer
        if "bing.com" in urlparse(dest).netloc:
            return "URL_OFFER"
        return "UNKNOWN"

    @property
    def quiz_key(self) -> str | None:
        """WQOskey value for BING_QUIZ items (e.g. 'Mount_Fuji_quiz_202607')."""
        if self.activity_type != "BING_QUIZ":
            return None
        qs = parse_qs(urlparse(self.destination).query)
        filters = unquote_plus(" ".join(qs.get("filters", [])))
        m = re.search(r'WQOskey:"([^"]+)"', filters)
        return m.group(1) if m else None

    @property
    def form_code(self) -> str:
        """The form= or FORM= tracking code from the destination URL."""
        qs = parse_qs(urlparse(self.destination).query)
        return (qs.get("form") or qs.get("FORM") or [""])[0]

    @property
    def url_selector_token(self) -> str:
        """
        A URL fragment unique enough to identify this item's <a> in the DOM.

        form= codes like 'tgrew4' and 'dsetqu' are shared across multiple items,
        so we prefer the q= parameter value (still URL-encoded with +, as it
        appears in href attributes).  This is always unique per activity because
        each activity has a distinct search query or quiz topic.
        """
        dest = self.destination
        m = re.search(r'[?&](?:q|Q)=([^&]+)', dest)
        if m:
            return m.group(1)  # already +-encoded, matches href attribute as-is
        return self.form_code


@dataclass
class DashboardData:
    balance: int = 0
    level: int = 1
    daily_set_items: list[DailySetItem] = field(default_factory=list)
    activities_remaining: int = 0
    activities_requirement: int = 0
    activities_progress: int = 0
    point_claim_points: int = 0  # streak bonus points ready to claim (0 = nothing claimable)

    def todays_daily_set(self) -> list[DailySetItem]:
        """Return only the daily set items whose date matches today (local date).

        The RSC payload always contains 3 days of items (today, tomorrow, day after).
        Only today's items have clickable anchors on the dashboard.
        """
        from datetime import date
        today = date.today().strftime("%m/%d/%Y")
        return [i for i in self.daily_set_items if i.date == today]


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

    # pointsclaim block: "type":"pointsclaim","model":{"pointClaim":{"points":<n>,...}}
    m = re.search(r'"type"\s*:\s*"pointsclaim".*?"points"\s*:\s*(\d+)', rsc_text, re.DOTALL)
    if m:
        data.point_claim_points = int(m.group(1))
        logger.info("RSC: point_claim_points=%d", data.point_claim_points)

    logger.info(
        "RSC: balance=%d level=%d daily_set_items=%d activities_remaining=%d/%d",
        data.balance,
        data.level,
        len(data.daily_set_items),
        data.activities_remaining,
        data.activities_requirement,
    )
    return data
