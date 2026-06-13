"""Autonomy dial validation (the unknown gate/mode branch raises before any DB access)."""

import pytest

from app.intelligence import autonomy


def test_gates_and_modes():
    assert autonomy.GATES == ("topic_selection", "script", "publish")
    assert autonomy.MODES == ("manual", "auto_with_veto", "full_auto")


def test_unknown_gate_rejected():
    with pytest.raises(ValueError):
        autonomy.set_autonomy("nope", "manual")


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        autonomy.set_autonomy("script", "turbo")
