"""Audit + ops event logging: system_events and pipeline_events."""

from __future__ import annotations

import json
from typing import Any, Literal

from .db import cursor

Severity = Literal["info", "warn", "error", "critical"]


def log_system_event(
    *,
    severity: Severity,
    component: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    with cursor() as cur:
        cur.execute(
            """
            insert into system_events (severity, component, message, detail)
            values (%s, %s, %s, %s)
            """,
            (severity, component, message, json.dumps(detail or {})),
        )


def log_pipeline_event(
    *,
    content_item_id: str,
    from_status: str | None,
    to_status: str | None,
    actor: str,
    detail: dict[str, Any] | None = None,
) -> None:
    with cursor() as cur:
        cur.execute(
            """
            insert into pipeline_events
              (content_item_id, from_status, to_status, actor, detail)
            values (%s, %s, %s, %s, %s)
            """,
            (
                content_item_id,
                from_status,
                to_status,
                actor,
                json.dumps(detail or {}),
            ),
        )
