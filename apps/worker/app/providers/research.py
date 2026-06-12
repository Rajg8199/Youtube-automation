"""Research source adapters: pull raw signals from RSS feeds and Reddit listings.

Each adapter returns RawSignalInput rows with a stable `external_id` for dedupe
(unique on (source_id, external_id) in the DB).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import feedparser
import httpx


@dataclass(slots=True)
class RawSignalInput:
    external_id: str
    title: str
    url: str | None = None
    content: str | None = None
    published_at: datetime | None = None


def _stable_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:24]


class ResearchSource(Protocol):
    name: str
    type: str

    def poll(self) -> list[RawSignalInput]: ...


class RSSSource:
    """Parses an RSS/Atom feed. external_id prefers the entry guid/id, else a hash."""

    type = "rss"

    def __init__(self, name: str, url: str, user_agent: str, limit: int = 50) -> None:
        self.name = name
        self.url = url
        self._user_agent = user_agent
        self._limit = limit

    def poll(self) -> list[RawSignalInput]:
        parsed = feedparser.parse(self.url, agent=self._user_agent)
        out: list[RawSignalInput] = []
        for e in parsed.entries[: self._limit]:
            title = getattr(e, "title", "").strip()
            if not title:
                continue
            link = getattr(e, "link", None)
            guid = getattr(e, "id", None) or link or _stable_id(self.name, title)
            summary = getattr(e, "summary", None)
            out.append(
                RawSignalInput(
                    external_id=str(guid)[:200],
                    title=title,
                    url=link,
                    content=summary,
                    published_at=_entry_time(e),
                )
            )
        return out


class RedditSource:
    """Reads a subreddit `new.json` listing via the public JSON endpoint."""

    type = "reddit"

    def __init__(self, name: str, url: str, user_agent: str, limit: int = 50) -> None:
        self.name = name
        self.url = url
        self._user_agent = user_agent
        self._limit = limit

    def poll(self) -> list[RawSignalInput]:
        headers = {"User-Agent": self._user_agent}
        params = {"limit": str(self._limit)}
        with httpx.Client(timeout=20.0, headers=headers) as client:
            resp = client.get(self.url, params=params)
            resp.raise_for_status()
            data = resp.json()
        out: list[RawSignalInput] = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            title = (d.get("title") or "").strip()
            if not title:
                continue
            out.append(
                RawSignalInput(
                    external_id=str(d.get("id") or _stable_id(self.name, title)),
                    title=title,
                    url="https://www.reddit.com" + d.get("permalink", ""),
                    content=d.get("selftext") or None,
                    published_at=_epoch_to_dt(d.get("created_utc")),
                )
            )
        return out


def _entry_time(entry: Any) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _epoch_to_dt(epoch: float | None) -> datetime | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def build_source(row: dict[str, Any], user_agent: str) -> ResearchSource | None:
    """Construct an adapter from a `sources` DB row. Returns None for unsupported types."""
    stype = row["type"]
    name = row["name"]
    url = row.get("url")
    if not url:
        return None
    if stype == "rss":
        return RSSSource(name, url, user_agent)
    if stype == "reddit":
        return RedditSource(name, url, user_agent)
    return None  # api/scrape/youtube_channel/manual wired in later phases
