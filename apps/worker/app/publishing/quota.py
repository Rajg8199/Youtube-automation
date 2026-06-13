"""YouTube Data API quota ledger. Blocks uploads that would exceed the daily unit budget."""

from __future__ import annotations

from ..config import get_settings
from ..db import cursor

# YouTube Data API unit costs.
COST_VIDEOS_INSERT = 1600
COST_THUMBNAIL_SET = 50


def units_used_today(api: str = "youtube_data") -> int:
    with cursor() as cur:
        cur.execute(
            "select coalesce(units_used, 0) as u from quota_ledger "
            "where date = current_date and api = %s",
            (api,),
        )
        row = cur.fetchone()
        return int(row["u"]) if row else 0


def can_spend(units: int, api: str = "youtube_data") -> bool:
    return units_used_today(api) + units <= get_settings().youtube_daily_quota


def record_units(units: int, api: str = "youtube_data") -> int:
    """Add units to today's ledger (upsert). Returns the new total."""
    with cursor() as cur:
        cur.execute(
            """
            insert into quota_ledger (date, api, units_used)
            values (current_date, %s, %s)
            on conflict (date, api) do update set units_used = quota_ledger.units_used + excluded.units_used
            returning units_used
            """,
            (api, units),
        )
        return int(cur.fetchone()["units_used"])


def remaining(api: str = "youtube_data") -> int:
    return max(0, get_settings().youtube_daily_quota - units_used_today(api))
