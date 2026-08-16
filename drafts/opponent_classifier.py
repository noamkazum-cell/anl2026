"""Detect time-based conceders for optional truth-first routing (V2.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from negmas.outcomes import Outcome


class OpponentType(str, Enum):
    """Legacy labels for persona_schedules.py (V2.0 adaptive weights)."""

    UNKNOWN = "unknown"
    PREFERENCE_LEARNER = "preference_learner"
    TIME_BASED = "time_based"
    INVERTED_MODEL = "inverted_model"
    PHASED = "phased"


class BiddingMode(str, Enum):
    """In-house persona routing for Agent360V2."""

    DECOY_FIRST = "decoy_first"
    TRUTH_FIRST = "truth_first"


def _pearson_correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(ys) < 2 or len(xs) != len(ys):
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x < 1e-12 or den_y < 1e-12:
        return 0.0
    return num / (den_x * den_y)


@dataclass
class OpponentRouter:
    """
    Default decoy-first; switch to truth-first only for clear time-based conceders.

    Learners (high value repetition, flat utility over time) never trigger truth-first.
    """

    MIN_OBSERVATIONS: int = 2
    CONCEDER_TIME_CORR: float = 0.28
    CONCEDER_MAX_CONCENTRATION: float = 0.76
    LEARNER_CONCENTRATION: float = 0.80
    LEARNER_MAX_TIME_CORR: float = 0.22

    num_issues: int = 0
    opponent_offers: list[Outcome] = field(default_factory=list)
    opponent_times: list[float] = field(default_factory=list)
    my_utilities_on_their_offers: list[float] = field(default_factory=list)

    def reset(self, num_issues: int = 0) -> None:
        self.num_issues = num_issues
        self.opponent_offers = []
        self.opponent_times = []
        self.my_utilities_on_their_offers = []

    def update(
        self,
        opponent_offer: Outcome,
        relative_time: float,
        my_utility_on_offer: float,
    ) -> BiddingMode:
        self.opponent_offers.append(opponent_offer)
        self.opponent_times.append(relative_time)
        self.my_utilities_on_their_offers.append(my_utility_on_offer)
        return self.current_mode()

    def current_mode(self) -> BiddingMode:
        if len(self.opponent_offers) < self.MIN_OBSERVATIONS:
            return BiddingMode.DECOY_FIRST
        if self._is_learner():
            return BiddingMode.DECOY_FIRST
        if self._is_conceder():
            return BiddingMode.TRUTH_FIRST
        return BiddingMode.DECOY_FIRST

    def _is_conceder(self) -> bool:
        time_corr = _pearson_correlation(
            self.opponent_times, self.my_utilities_on_their_offers
        )
        concentration = self._frequency_concentration()
        return (
            time_corr >= self.CONCEDER_TIME_CORR
            and concentration < self.CONCEDER_MAX_CONCENTRATION
        )

    def _is_learner(self) -> bool:
        if len(self.opponent_offers) < self.MIN_OBSERVATIONS:
            return False
        concentration = self._frequency_concentration()
        time_corr = abs(
            _pearson_correlation(self.opponent_times, self.my_utilities_on_their_offers)
        )
        return (
            concentration >= self.LEARNER_CONCENTRATION
            and time_corr < self.LEARNER_MAX_TIME_CORR
        )

    def _frequency_concentration(self) -> float:
        if not self.opponent_offers or self.num_issues == 0:
            return 0.0
        per_issue: list[float] = []
        for issue_index in range(self.num_issues):
            counts: dict[Any, int] = {}
            for offer in self.opponent_offers:
                value = offer[issue_index]
                counts[value] = counts.get(value, 0) + 1
            if counts:
                per_issue.append(max(counts.values()) / len(self.opponent_offers))
        return sum(per_issue) / len(per_issue) if per_issue else 0.0
