"""Agent360V2 — Full decoy pool + gradient transition; no opponent-type routing."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from negmas.outcomes import Outcome

from drafts.agent360 import Agent360Base


class Agent360V2(Agent360Base):
    """
    V2.4 submission agent: maximal-mismatch decoy pool + first-seat min-offer gate.

    Same phase boundaries as Agent360 (0.35 / 0.75). When opening (seat 0), stay in
    decoy until the opponent has made at least ``FIRST_MIN_OPPONENT_OFFERS`` bids —
    reduces curve-fit leaks (e.g. RentingLite) without opponent-type routing.
    Second seat matches prior V2.3 behavior.
    """

    FIRST_MIN_OPPONENT_OFFERS = 3

    def transition_allowed(self) -> bool:
        if not self.is_first_negotiator() or self.FIRST_MIN_OPPONENT_OFFERS <= 0:
            return True
        return self._opponent_offer_count >= self.FIRST_MIN_OPPONENT_OFFERS

    def _true_preferred_value_per_issue(self) -> list[Any]:
        if not self.rational_outcomes:
            return []

        num_rational = len(self.rational_outcomes)
        top_k = max(3, min(30, num_rational // 10 or 3))
        our_best_outcomes = self.rational_outcomes[:top_k]
        num_issues = len(our_best_outcomes[0])

        true_preferred: list[Any] = []
        for issue_index in range(num_issues):
            values_in_top = [o[issue_index] for o in our_best_outcomes]
            true_preferred.append(Counter(values_in_top).most_common(1)[0][0])
        return true_preferred

    def _build_decoy_pool(self) -> tuple[Outcome, ...]:
        """Maximal mismatch decoys for decoy and transition phases."""
        if not self.rational_outcomes:
            return ()

        true_preferred_value_per_issue = self._true_preferred_value_per_issue()
        if not true_preferred_value_per_issue:
            return super()._build_decoy_pool()

        num_issues = len(true_preferred_value_per_issue)
        num_rational = len(self.rational_outcomes)
        top_k = max(3, min(30, num_rational // 10 or 3))
        our_best_outcomes = self.rational_outcomes[:top_k]

        reserved_utility = float(self.ufun.reserved_value)
        min_decoy_utility = max(
            reserved_utility, float(self.ufun(our_best_outcomes[-1])) * 0.55
        )

        scored_candidates: list[tuple[int, Outcome]] = []
        for outcome in self.rational_outcomes:
            outcome_utility = float(self.ufun(outcome))
            if outcome_utility < min_decoy_utility:
                break

            num_mismatched_issues = sum(
                1
                for issue_index in range(num_issues)
                if outcome[issue_index] != true_preferred_value_per_issue[issue_index]
            )
            if num_mismatched_issues >= max(1, num_issues // 2):
                scored_candidates.append((num_mismatched_issues, outcome))

        if not scored_candidates:
            return super()._build_decoy_pool()

        max_mismatches = max(score for score, _ in scored_candidates)
        decoy_candidates = [
            outcome
            for score, outcome in scored_candidates
            if score == max_mismatches
        ]
        if len(decoy_candidates) < 3:
            near_max = [
                outcome
                for score, outcome in scored_candidates
                if score >= max_mismatches - 1
            ]
            decoy_candidates = near_max or decoy_candidates

        return tuple(decoy_candidates)


class Agent360V2_5(Agent360V2):
    """V2.5 pre-V3 trial: soft first-seat transition + anti-curve decoy picks."""

    FIRST_TRANSITION_DECOY_MIX_UNTIL = 0.85
    FIRST_TRANSITION_PROGRESS_SCALE = 0.72

    def effective_transition_decoy_mix_until(self) -> float:
        if self.is_first_negotiator():
            return self.FIRST_TRANSITION_DECOY_MIX_UNTIL
        return super().effective_transition_decoy_mix_until()

    def transition_progress_scale(self) -> float:
        if self.is_first_negotiator():
            return self.FIRST_TRANSITION_PROGRESS_SCALE
        return 1.0

    def _pick_decoy_bid(self, rng: random.Random) -> Outcome:
        if not self.is_first_negotiator() or not self.decoy_outcomes:
            return super()._pick_decoy_bid(rng)

        pool = list(self.decoy_outcomes)
        if not self._recent_own_bids:
            return rng.choice(pool)

        last_utility = float(self.ufun(self._recent_own_bids[-1]))
        best_gap = -1.0
        tied: list[Outcome] = []
        for outcome in pool:
            gap = abs(float(self.ufun(outcome)) - last_utility)
            if gap > best_gap + 1e-9:
                best_gap = gap
                tied = [outcome]
            elif abs(gap - best_gap) < 1e-9:
                tied.append(outcome)
        return rng.choice(tied)


class Agent360V2ClosingA(Agent360V2):
    """V2.6a: closing-only — prioritize our utility in closing bids."""

    CLOSING_OPPONENT_WEIGHT_CAP = 0.38


class Agent360V2FirstSeatBase(Agent360V2):
    """Composable first-seat hooks for ablations (seat 0 only)."""

    FIRST_DECOY_PHASE_END_OVERRIDE: float | None = None
    FIRST_MIN_OPPONENT_OFFERS = 0
    FIRST_DECOY_NO_REPEAT_WINDOW = 0

    def decoy_phase_end(self) -> float:
        if (
            self.is_first_negotiator()
            and self.FIRST_DECOY_PHASE_END_OVERRIDE is not None
        ):
            return self.FIRST_DECOY_PHASE_END_OVERRIDE
        return super().decoy_phase_end()

    def _pick_decoy_bid(self, rng: random.Random) -> Outcome:
        if (
            not self.is_first_negotiator()
            or not self.decoy_outcomes
            or self.FIRST_DECOY_NO_REPEAT_WINDOW <= 0
        ):
            return super()._pick_decoy_bid(rng)

        pool = list(self.decoy_outcomes)
        recent = set(
            self._recent_own_bids[-self.FIRST_DECOY_NO_REPEAT_WINDOW :]
        )
        candidates = [outcome for outcome in pool if outcome not in recent]
        if candidates:
            return rng.choice(candidates)
        return rng.choice(pool)


class Agent360V2FirstSeatMinOffers(Agent360V2):
    """Alias — same as ``Agent360V2`` (V2.4) after min-offer promotion."""


class Agent360V2FirstSeatMinOffersAblate(Agent360V2FirstSeatBase):
    FIRST_MIN_OPPONENT_OFFERS = 3


class Agent360V2FirstSeatRotate(Agent360V2FirstSeatBase):
    FIRST_DECOY_NO_REPEAT_WINDOW = 5


class Agent360V2FirstSeatLongDecoy(Agent360V2FirstSeatBase):
    FIRST_DECOY_PHASE_END_OVERRIDE = 0.42


class Agent360V2FirstSeatLongDecoy38(Agent360V2FirstSeatBase):
    FIRST_DECOY_PHASE_END_OVERRIDE = 0.38


class Agent360V2FirstSeatMinOffersLong38(Agent360V2FirstSeatBase):
    FIRST_DECOY_PHASE_END_OVERRIDE = 0.38
    FIRST_MIN_OPPONENT_OFFERS = 3


class Agent360V2FirstSeat(Agent360V2FirstSeatBase):
    FIRST_DECOY_PHASE_END_OVERRIDE = 0.42
    FIRST_MIN_OPPONENT_OFFERS = 3
    FIRST_DECOY_NO_REPEAT_WINDOW = 5
    FIRST_DECOY_PHASE_END = 0.42


class Agent360V2Adaptive(Agent360V2):
    FIRST_CLOSING_OPPONENT_WEIGHT_CAP = 0.38
    SECOND_CLOSING_OPPONENT_WEIGHT_CAP = 0.45

    def effective_closing_opponent_weight_cap(self) -> float:
        if self.n_negotiators <= 2:
            if self.is_first_negotiator():
                return self.FIRST_CLOSING_OPPONENT_WEIGHT_CAP
            return self.SECOND_CLOSING_OPPONENT_WEIGHT_CAP

        last_seat = max(1, self.n_negotiators - 1)
        seat_fraction = self.negotiation_seat / last_seat
        return (
            self.FIRST_CLOSING_OPPONENT_WEIGHT_CAP * (1.0 - seat_fraction)
            + self.SECOND_CLOSING_OPPONENT_WEIGHT_CAP * seat_fraction
        )
