"""State-machine parity with packages/shared/src/state-machine.ts (pure, no DB)."""

import pytest

from app.state_machine import (
    CONTENT_STATUSES,
    assert_transition,
    can_transition,
    is_terminal,
)


def test_has_19_statuses():
    assert len(CONTENT_STATUSES) == 19


def test_happy_path_end_to_end():
    path = [
        "idea", "researched", "scripting", "script_qa", "script_approved",
        "voiceover", "assembly", "thumbnail", "metadata", "ready_for_review",
        "approved", "scheduled", "publishing", "published", "analyzing", "archived",
    ]
    for a, b in zip(path, path[1:]):
        assert can_transition(a, b), f"{a} -> {b} should be legal"


def test_qa_revise_loop():
    assert can_transition("script_qa", "qa_failed")
    assert can_transition("qa_failed", "scripting")


def test_illegal_jumps():
    assert not can_transition("idea", "published")
    assert not can_transition("idea", "idea")
    with pytest.raises(ValueError):
        assert_transition("idea", "published")


def test_failure_only_from_processing_states():
    assert can_transition("publishing", "failed")
    assert not can_transition("idea", "failed")


def test_terminals():
    assert is_terminal("archived")
    assert is_terminal("rejected")
    assert not is_terminal("idea")
