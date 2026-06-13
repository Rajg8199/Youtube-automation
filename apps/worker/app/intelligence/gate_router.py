"""Gate router: advance approval gates according to the autonomy dial.

manual          -> humans approve in the dashboard (no auto-advance here).
auto_with_veto  -> auto-approve, but a human can still veto before the next stage runs.
full_auto       -> auto-approve.

This is what lets the n8n schedulers run the pipeline hands-off when gates are on auto.
"""

from __future__ import annotations

from typing import Any

from ..db import cursor
from ..events import log_pipeline_event, log_system_event
from ..state_machine import transition
from .autonomy import get_autonomy

COMPONENT = "service:gate_router"
_AUTO = ("auto_with_veto", "full_auto")


def run_gate_router(*, limit: int = 50) -> dict[str, Any]:
    modes = {g["gate"]: g["mode"] for g in get_autonomy()}
    script_auto = modes.get("script") in _AUTO
    publish_auto = modes.get("publish") in _AUTO
    scripts_approved = publishes_advanced = 0

    if script_auto:
        with cursor() as cur:
            cur.execute(
                """
                update approvals set status='approved', decided_at=now(), reviewer_note='auto'
                where gate='script' and status='pending'
                  and content_item_id in (select id from content_items where status='script_approved')
                """
            )
            scripts_approved = cur.rowcount

    if publish_auto:
        with cursor() as cur:
            cur.execute(
                "select id from content_items where status='ready_for_review' "
                "order by priority desc limit %s",
                (limit,),
            )
            ids = [r["id"] for r in cur.fetchall()]
        for cid in ids:
            transition(content_item_id=cid, to_status="approved", actor=COMPONENT,
                       detail={"gate": "publish", "mode": modes.get("publish")})
            with cursor() as cur:
                cur.execute(
                    "insert into approvals (content_item_id, gate, status, reviewer_note, decided_at) "
                    "values (%s, 'publish', 'approved', 'auto', now())",
                    (cid,),
                )
            publishes_advanced += 1

    summary = {"scripts_auto_approved": scripts_approved,
               "publishes_auto_advanced": publishes_advanced,
               "modes": modes}
    log_system_event(severity="info", component=COMPONENT, message="gate router run complete",
                     detail=summary)
    return summary
