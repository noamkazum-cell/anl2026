"""Persona schedule weights for Agent360 version 2."""

from __future__ import annotations

from drafts.opponent_classifier import OpponentType


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _lerp(start: float, end: float, progress: float) -> float:
    progress = _clamp(progress, 0.0, 1.0)
    return start + (end - start) * progress


def _normalize_weights(
    decoy: float, truth: float, closing: float
) -> tuple[float, float, float]:
    total = decoy + truth + closing
    if total <= 1e-12:
        return 0.0, 1.0, 0.0
    return decoy / total, truth / total, closing / total


def _schedule_decoy_first(relative_time: float) -> tuple[float, float, float]:
    if relative_time < 0.25:
        return _normalize_weights(0.85, 0.15, 0.0)
    if relative_time < 0.55:
        progress = (relative_time - 0.25) / 0.30
        decoy = _lerp(0.85, 0.20, progress)
        truth = _lerp(0.15, 0.65, progress)
        return _normalize_weights(decoy, truth, 0.0)
    if relative_time < 0.75:
        return _normalize_weights(0.10, 0.70, 0.20)
    return _normalize_weights(0.0, 0.30, 0.70)


def _schedule_truth_first(relative_time: float) -> tuple[float, float, float]:
    if relative_time < 0.20:
        return _normalize_weights(0.05, 0.95, 0.0)
    if relative_time < 0.80:
        return _normalize_weights(0.0, 0.85, 0.15)
    return _normalize_weights(0.0, 0.25, 0.75)


def _schedule_inverted_exploit(relative_time: float) -> tuple[float, float, float]:
    if relative_time < 0.30:
        return _normalize_weights(0.10, 0.90, 0.0)
    if relative_time < 0.75:
        return _normalize_weights(0.20, 0.50, 0.30)
    return _normalize_weights(0.0, 0.20, 0.80)


def mixing_weights(
    opponent_type: OpponentType, relative_time: float
) -> tuple[float, float, float]:
    """
    Return (decoy_weight, truth_weight, closing_weight) for the current moment.

    Unknown, preference learner, and phased opponents use decoy-first schedule.
    """
    if opponent_type is OpponentType.TIME_BASED:
        return _schedule_truth_first(relative_time)
    if opponent_type is OpponentType.INVERTED_MODEL:
        return _schedule_inverted_exploit(relative_time)
    return _schedule_decoy_first(relative_time)
