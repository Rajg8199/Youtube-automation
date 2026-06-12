"""Research sweep: poll active sources and insert deduped raw_signals.

Dedupe is enforced by the unique(source_id, external_id) constraint — re-runs are
idempotent (ON CONFLICT DO NOTHING). LLM-free.
"""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..db import cursor
from ..events import log_system_event
from ..providers.research import build_source

COMPONENT = "service:research_poll"


def _active_sources(cur) -> list[dict[str, Any]]:
    cur.execute(
        "select id, name, type, url, active from sources where active = true order by name"
    )
    return cur.fetchall()


def run_research_sweep(*, per_source_limit: int = 50) -> dict[str, int]:
    settings = get_settings()
    ua = settings.http_user_agent
    sources_polled = signals_new = errors = 0

    with cursor() as cur:
        sources = _active_sources(cur)

    for src in sources:
        adapter = build_source(src, ua)
        if adapter is None:
            continue
        try:
            items = adapter.poll()
            sources_polled += 1
            with cursor() as cur:
                for item in items[:per_source_limit]:
                    cur.execute(
                        """
                        insert into raw_signals
                          (source_id, external_id, title, url, content, published_at)
                        values (%s, %s, %s, %s, %s, %s)
                        on conflict (source_id, external_id) do nothing
                        """,
                        (
                            src["id"],
                            item.external_id,
                            item.title,
                            item.url,
                            item.content,
                            item.published_at,
                        ),
                    )
                    if cur.rowcount == 1:
                        signals_new += 1
                cur.execute(
                    "update sources set last_polled_at = now() where id = %s",
                    (src["id"],),
                )
        except Exception as e:  # noqa: BLE001 - one bad feed shouldn't stop the sweep
            errors += 1
            log_system_event(
                severity="warn",
                component=COMPONENT,
                message=f"source poll failed: {src['name']}",
                detail={"source_id": str(src["id"]), "error": str(e)},
            )

    summary = {
        "sources_polled": sources_polled,
        "signals_new": signals_new,
        "errors": errors,
    }
    log_system_event(
        severity="info", component=COMPONENT, message="research sweep complete", detail=summary
    )
    return summary
