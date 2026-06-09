"""Shared opponent modeling for 2026-style sparring agents (no oracle ufun)."""

from __future__ import annotations

from typing import Any

import numpy as np
from negmas.outcomes import Outcome


class FrequencyOpponentModel:
    """Smith-style frequency model learned only from opponent bids."""

    def __init__(self, num_issues: int) -> None:
        self.num_issues = num_issues
        self.opponent_preference_counts: list[dict[Any, int]] = [
            {} for _ in range(num_issues)
        ]

    def record_opponent_offer(self, offer: Outcome) -> None:
        for issue_index, value in enumerate(offer):
            counts = self.opponent_preference_counts[issue_index]
            counts[value] = counts.get(value, 0) + 1

    def has_observations(self) -> bool:
        return any(self.opponent_preference_counts[i] for i in range(self.num_issues))

    def estimated_opponent_utility(self, offer: Outcome) -> float:
        if self.num_issues == 0:
            return 0.5

        utility_sum = 0.0
        for issue_index in range(self.num_issues):
            counts = self.opponent_preference_counts[issue_index]
            if not counts:
                utility_sum += 0.5
                continue

            value = offer[issue_index]
            count_for_value = counts.get(value, 0)
            max_count = max(counts.values())
            normalized = count_for_value / max_count if max_count else 0.5
            utility_sum += normalized

        return utility_sum / self.num_issues


def aspiration_function(t: float, mx: float, rv: float, e: float) -> float:
    """Time-based aspiration in [rv, mx] (Shochan-style)."""
    t = min(max(float(t), 0.0), 1.0)
    return (mx - rv) * (1.0 - t**e) + rv


def count_unique_utilities(utilities: list[float], tol: float = 1e-3) -> int:
    if not utilities:
        return 0
    sorted_u = sorted(utilities)
    unique = 1
    for i in range(1, len(sorted_u)):
        if abs(sorted_u[i] - sorted_u[i - 1]) > tol:
            unique += 1
    return unique


def opponent_concession_curve(
    t: np.ndarray, u0: float, rv: float, e: float
) -> np.ndarray:
    """Estimated opponent utility vs normalized time."""
    return (u0 - rv) * (1.0 - np.power(t, e)) + rv
