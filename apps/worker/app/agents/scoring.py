"""Composite topic-scoring weights + calculation (pure, testable).

Weights live here in Phase 1; the Growth Strategist (Phase 5) proposes updated weights
monthly. The six factors each range 0..1; composite is their weighted average, also 0..1.
"""

from __future__ import annotations

from dataclasses import dataclass

# Default weights (sum need not be 1; we normalize). Tuned later by Strategy agent.
DEFAULT_WEIGHTS: dict[str, float] = {
    "trend_velocity": 0.20,
    "search_demand": 0.20,
    "competition_gap": 0.15,
    "channel_fit": 0.15,
    "monetization_potential": 0.20,
    "freshness": 0.10,
}

FACTORS = tuple(DEFAULT_WEIGHTS.keys())


@dataclass(slots=True)
class FactorScores:
    trend_velocity: float
    search_demand: float
    competition_gap: float
    channel_fit: float
    monetization_potential: float
    freshness: float
    predicted_views_score: float = 0.5  # learning-loop output; neutral until Phase 5

    def as_dict(self) -> dict[str, float]:
        return {
            "trend_velocity": self.trend_velocity,
            "search_demand": self.search_demand,
            "competition_gap": self.competition_gap,
            "channel_fit": self.channel_fit,
            "monetization_potential": self.monetization_potential,
            "freshness": self.freshness,
            "predicted_views_score": self.predicted_views_score,
        }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def composite(
    scores: FactorScores, weights: dict[str, float] | None = None
) -> float:
    """Weighted average of the six factors, blended 85/15 with predicted_views_score."""
    w = weights or DEFAULT_WEIGHTS
    total_w = sum(w[f] for f in FACTORS)
    if total_w <= 0:
        raise ValueError("weights sum to zero")
    base = sum(_clamp01(getattr(scores, f)) * w[f] for f in FACTORS) / total_w
    blended = 0.85 * base + 0.15 * _clamp01(scores.predicted_views_score)
    return round(_clamp01(blended), 4)
