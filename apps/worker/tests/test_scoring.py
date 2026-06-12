"""Composite scoring: range, monotonicity, weighting."""

import pytest

from app.agents.scoring import DEFAULT_WEIGHTS, FactorScores, composite


def _fs(v: float) -> FactorScores:
    return FactorScores(v, v, v, v, v, v, predicted_views_score=v)


def test_all_zero_is_zero():
    assert composite(_fs(0.0)) == 0.0


def test_all_one_is_one():
    assert composite(_fs(1.0)) == 1.0


def test_in_range_and_monotonic():
    lo = composite(_fs(0.2))
    hi = composite(_fs(0.8))
    assert 0.0 <= lo < hi <= 1.0


def test_clamps_out_of_range_inputs():
    fs = FactorScores(2.0, -1.0, 0.5, 0.5, 0.5, 0.5, predicted_views_score=0.5)
    c = composite(fs)
    assert 0.0 <= c <= 1.0


def test_weights_matter():
    # Heavy monetization weight should lift a topic strong only on monetization.
    fs = FactorScores(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, predicted_views_score=0.0)
    base = composite(fs, DEFAULT_WEIGHTS)
    heavy = composite(fs, {**DEFAULT_WEIGHTS, "monetization_potential": 1.0})
    assert heavy > base


def test_zero_weights_raise():
    with pytest.raises(ValueError):
        composite(_fs(0.5), {k: 0.0 for k in DEFAULT_WEIGHTS})
