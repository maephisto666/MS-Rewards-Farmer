import csv
import json
import logging
import os
import random
import tempfile
import time
from pathlib import Path
from typing import Callable

from trendspyg import download_google_trends_csv, download_google_trends_rss

MAX_AGE_SECONDS = 24 * 60 * 60
"""
how long a fetched set of trends is considered fresh
"""
RETRY_INTERVAL_SECONDS = 60 * 60
"""
minimal time between two fetch attempts, whether the previous one worked or not
"""
CSV_HOURS = 24
"""
time window of the trends requested from Google Trends
"""

Trends = dict[str, list[str]]
"""
trending keyword -> related keywords (the keyword itself is always the first one)
"""
Source = tuple[str, Callable[[str], Trends]]


def _withKeyword(keyword: str, related: list[str]) -> list[str]:
    return [keyword] + [r for r in related if r != keyword]


def fetchTrendingCsv(geo: str, hours: int = CSV_HOURS) -> Trends:
    """
    Bulk source: drives a headless Chrome to download the "Trending now" CSV.
    Returns hundreds of trends along with their related keywords.
    """
    with tempfile.TemporaryDirectory() as downloadDir:
        path = download_google_trends_csv(
            geo=geo, hours=hours, download_dir=downloadDir, output_format="csv"
        )
        if not path:
            raise RuntimeError("Google Trends CSV download returned no file")
        with open(path, encoding="utf-8-sig", newline="") as file:
            return {
                row["Trends"]: _withKeyword(
                    row["Trends"],
                    [k.strip() for k in (row.get("Trend breakdown") or "").split(",")
                     if k.strip()],
                )
                for row in csv.DictReader(file)
                if row.get("Trends")
            }


def fetchTrendingRss(geo: str) -> Trends:
    """
    Fallback source: no browser needed, but only a handful (about 10) of trends
    and no related keywords.
    """
    items = download_google_trends_rss(
        geo=geo, include_images=False, include_articles=False
    )
    return {item["trend"]: [item["trend"]] for item in items if item.get("trend")}


DEFAULT_SOURCES: list[Source] = [("CSV", fetchTrendingCsv), ("RSS", fetchTrendingRss)]


class TrendsCache:
    """
    Persistent pool of trending keywords used to feed the Bing searches.

    Google is only queried when the pool cannot cover the searches still needed
    or when it is older than `MAX_AGE_SECONDS`, and never more than once per
    `RETRY_INTERVAL_SECONDS`, so a failing source is not hammered at every run.
    Keywords that were already searched are not fed back by later fetches.
    """

    def __init__(
        self,
        path: Path,
        geo: str,
        sources: list[Source] | None = None,
        clock: Callable[[], float] = time.time,
        maxAge: float = MAX_AGE_SECONDS,
        retryInterval: float = RETRY_INTERVAL_SECONDS,
    ):
        self.path = path
        self.geo = geo
        self.sources = DEFAULT_SOURCES if sources is None else sources
        self.clock = clock
        self.maxAge = maxAge
        self.retryInterval = retryInterval
        self.fetchedAt: float | None = None
        self.attemptedAt: float | None = None
        self.trends: Trends = {}
        self.used: dict[str, float] = {}
        self._load()

    def __len__(self) -> int:
        return len(self.trends)

    def _load(self) -> None:
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            self.fetchedAt = state["fetched_at"]
            self.attemptedAt = state["attempted_at"]
            self.trends = state["trends"]
            self.used = state["used"]
        except FileNotFoundError:
            pass
        except (ValueError, KeyError, TypeError):
            logging.warning(f"[TRENDS] Ignoring unreadable cache '{self.path}'")

    def _save(self) -> None:
        tmpPath = self.path.with_name(self.path.name + ".tmp")
        tmpPath.write_text(
            json.dumps(
                {
                    "fetched_at": self.fetchedAt,
                    "attempted_at": self.attemptedAt,
                    "trends": self.trends,
                    "used": self.used,
                }
            ),
            encoding="utf-8",
        )
        os.replace(tmpPath, self.path)

    def _isStale(self) -> bool:
        return self.fetchedAt is None or self.clock() - self.fetchedAt > self.maxAge

    def needsRefresh(self, needed: int) -> bool:
        return len(self) < needed or self._isStale()

    def refresh(self, needed: int) -> None:
        """
        Fetch new trends if the pool is too small or too old. Never raises: when
        every source fails the pool is left untouched and the caller decides what
        to do with it.
        """
        if not self.needsRefresh(needed):
            return
        now = self.clock()
        if self.attemptedAt is not None and now - self.attemptedAt < self.retryInterval:
            logging.debug("[TRENDS] Last fetch attempt is too recent, not retrying yet")
            return

        self.attemptedAt = now
        self.used = {k: t for k, t in self.used.items() if now - t < self.maxAge}
        for name, fetch in self.sources:
            try:
                fetched = fetch(self.geo)
            except Exception as e:
                logging.warning(f"[TRENDS] {name} source failed: {e!r}")
                continue
            fresh = {k: v for k, v in fetched.items() if k not in self.used}
            if not fresh:
                logging.warning(f"[TRENDS] {name} source returned no new trends")
                continue
            if self._isStale():
                self.trends = {}
            self.trends.update(fresh)
            self.fetchedAt = now
            logging.info(f"[TRENDS] Loaded {len(fresh)} trends from {name}")
            break
        else:
            logging.warning(
                f"[TRENDS] No source worked, retrying in {self.retryInterval / 60:.0f} min"
            )
        self._save()

    def pick(self) -> tuple[str, list[str]] | None:
        """
        A random keyword from the pool with a copy of its related keywords, or
        None if the pool is empty.
        """
        if not self.trends:
            return None
        keyword = random.choice(list(self.trends))
        return keyword, list(self.trends[keyword])

    def markUsed(self, keyword: str) -> None:
        self.trends.pop(keyword, None)
        self.used[keyword] = self.clock()
        self._save()
