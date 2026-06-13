"""content_items status state machine (Python mirror of packages/shared/src/state-machine.ts).

Single source of truth for legal transitions in the worker. Kept in parity with the TS
version by tests on both sides (ADR-0006).
"""

from __future__ import annotations

from typing import Any

from .db import cursor
from .events import log_pipeline_event

CONTENT_STATUSES: tuple[str, ...] = (
    "idea",
    "researched",
    "scripting",
    "script_qa",
    "qa_failed",
    "script_approved",
    "voiceover",
    "assembly",
    "thumbnail",
    "metadata",
    "ready_for_review",
    "approved",
    "scheduled",
    "publishing",
    "published",
    "analyzing",
    "archived",
    "rejected",
    "failed",
)

TERMINAL_STATUSES: frozenset[str] = frozenset({"archived", "rejected"})

_TRANSITIONS: dict[str, list[str]] = {
    "idea": ["researched", "rejected"],
    "researched": ["scripting", "rejected"],
    "scripting": ["script_qa", "failed"],
    "script_qa": ["script_approved", "qa_failed"],
    "qa_failed": ["scripting", "rejected"],
    # script_approved may also bounce back to qa_failed (human requests changes) or be rejected.
    "script_approved": ["voiceover", "qa_failed", "rejected"],
    "voiceover": ["assembly", "failed"],
    "assembly": ["thumbnail", "failed"],
    "thumbnail": ["metadata", "failed"],
    "metadata": ["ready_for_review"],
    "ready_for_review": ["approved", "rejected"],
    "approved": ["scheduled"],
    "scheduled": ["publishing", "rejected"],
    "publishing": ["published", "failed"],
    "published": ["analyzing"],
    "analyzing": ["archived"],
    "archived": [],
    "rejected": [],
    "failed": ["scripting", "archived"],
}

# Processing states that may fail mid-flight even without an explicit edge.
_FAILABLE: frozenset[str] = frozenset(
    {
        "researched",
        "scripting",
        "script_qa",
        "script_approved",
        "voiceover",
        "assembly",
        "thumbnail",
        "metadata",
        "scheduled",
        "publishing",
    }
)


def can_transition(from_status: str, to_status: str) -> bool:
    if from_status == to_status:
        return False
    if to_status == "failed" and from_status in _FAILABLE:
        return True
    return to_status in _TRANSITIONS.get(from_status, [])


def assert_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise ValueError(f"illegal content_item transition: {from_status} -> {to_status}")


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


def transition(
    *,
    content_item_id: str,
    to_status: str,
    actor: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """Validate + apply a status change and record a pipeline_event, in one transaction."""
    with cursor() as cur:
        cur.execute(
            "select status from content_items where id = %s for update", (content_item_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"content_item not found: {content_item_id}")
        from_status = row["status"]
        assert_transition(from_status, to_status)
        cur.execute(
            "update content_items set status = %s, updated_at = now() where id = %s",
            (to_status, content_item_id),
        )
    log_pipeline_event(
        content_item_id=content_item_id,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        detail=detail,
    )
