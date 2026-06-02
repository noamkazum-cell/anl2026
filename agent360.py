"""Agent360 — bilateral ANL 2026 agent with phased concealment and frequency opponent model."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from negmas.outcomes import Outcome
from negmas.preferences import LambdaMultiFun
from negmas.sao import ResponseType, SAOCallNegotiator, SAOResponse, SAOState


class FrequencyOpponentModel:
    """
    Smith-style frequency model of the opponent's preferences.

    Each time the opponent makes an offer, we count how often they use each
    issue-value. Values they repeat often are treated as more valuable to them.
    """

    def __init__(self, num_issues: int) -> None:
        self.num_issues = num_issues
        # opponent_preference_counts[issue_index][value] = how many times seen
        self.opponent_preference_counts: list[dict[Any, int]] = [
            {} for _ in range(num_issues)
        ]

    def record_opponent_offer(self, offer: Outcome) -> None:
        """Update counts from one opponent bid."""
        for issue_index, value in enumerate(offer):
            counts_for_issue = self.opponent_preference_counts[issue_index]
            counts_for_issue[value] = counts_for_issue.get(value, 0) + 1

    def has_observations(self) -> bool:
        """True once we have seen at least one value on some issue."""
        return any(self.opponent_preference_counts[i] for i in range(self.num_issues))

    def estimated_opponent_utility(self, offer: Outcome) -> float:
        """
        Score in [0, 1]: for each issue, value frequency / max frequency on that issue,
        then average across issues. Uniform issue weights (Smith default).
        """
        if self.num_issues == 0:
            return 0.5

        utility_sum = 0.0
        for issue_index in range(self.num_issues):
            counts_for_issue = self.opponent_preference_counts[issue_index]
            if not counts_for_issue:
                utility_sum += 0.5
                continue

            value = offer[issue_index]
            count_for_value = counts_for_issue.get(value, 0)
            max_count_on_issue = max(counts_for_issue.values())
            normalized = count_for_value / max_count_on_issue if max_count_on_issue else 0.5
            utility_sum += normalized

        return utility_sum / self.num_issues


class Agent360(SAOCallNegotiator):
    """
    Phased negotiation agent for ANL 2026.

    Phases (by relative_time t in [0, 1]):
      1. Decoy   — bid outcomes that misrepresent which issues we care about.
      2. Transition — blend decoy persona with gradually lower true aspirations.
      3. Closing — use opponent model to pick bids they may accept while we still win.
    """

    # Phase boundaries (relative time)
    DECOY_PHASE_END = 0.35
    TRANSITION_PHASE_END = 0.75

    # Populated in on_preferences_changed
    rational_outcomes: tuple[Outcome, ...] = ()
    decoy_outcomes: tuple[Outcome, ...] = ()

    opponent_frequency_model: FrequencyOpponentModel | None = None
    last_counter_offer: Outcome | None = None

    def on_preferences_changed(self, changes):
        """Build outcome pools and initialize opponent utility estimate."""
        if self.ufun is None:
            return

        # All outcomes above reservation, sorted best-for-us first
        utility_and_outcome = [
            (self.ufun(outcome), outcome)
            for outcome in self.nmi.outcome_space.enumerate_or_sample()
            if self.ufun(outcome) > self.ufun.reserved_value
        ]
        self.rational_outcomes = tuple(
            outcome for _, outcome in sorted(utility_and_outcome, reverse=True)
        )
        self.decoy_outcomes = self._build_decoy_pool()
        self.last_counter_offer = None

        num_issues = len(self.rational_outcomes[0]) if self.rational_outcomes else 0
        self.opponent_frequency_model = FrequencyOpponentModel(num_issues)
        self.private_info["opponent_ufun"] = LambdaMultiFun(
            f=self.opponent_frequency_model.estimated_opponent_utility
        )

    def _build_decoy_pool(self) -> tuple[Outcome, ...]:
        """
        Outcomes that look like we care about different issues than we really do.

        1. Infer our true favorite value per issue from our top outcomes.
        2. Keep rational outcomes that disagree on many issues but stay above a utility floor.
        """
        if not self.rational_outcomes:
            return ()

        num_rational = len(self.rational_outcomes)
        top_k = max(3, min(30, num_rational // 10 or 3))
        our_best_outcomes = self.rational_outcomes[:top_k]
        num_issues = len(our_best_outcomes[0])

        # Most common value per issue among our best outcomes = our true preference signal
        true_preferred_value_per_issue: list[Any] = []
        for issue_index in range(num_issues):
            values_in_top = [o[issue_index] for o in our_best_outcomes]
            true_preferred_value_per_issue.append(
                Counter(values_in_top).most_common(1)[0][0]
            )

        reserved_utility = float(self.ufun.reserved_value)
        min_decoy_utility = max(
            reserved_utility, float(self.ufun(our_best_outcomes[-1])) * 0.55
        )

        decoy_candidates: list[Outcome] = []
        for outcome in self.rational_outcomes:
            outcome_utility = float(self.ufun(outcome))
            if outcome_utility < min_decoy_utility:
                break

            num_mismatched_issues = sum(
                1
                for issue_index in range(num_issues)
                if outcome[issue_index] != true_preferred_value_per_issue[issue_index]
            )
            min_mismatches = max(1, num_issues // 3)
            if num_mismatched_issues >= min_mismatches:
                decoy_candidates.append(outcome)

        # Fallback: mid-ranked rational outcomes if we found too few decoys
        if len(decoy_candidates) < 3:
            mid_start = min(top_k, num_rational - 1)
            mid_end = min(num_rational, mid_start + max(10, num_rational // 5))
            decoy_candidates = list(self.rational_outcomes[mid_start:mid_end])

        return tuple(decoy_candidates)

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        """Main SAO loop: accept partner offer or send a counter-offer."""
        if self.ufun is None:
            return SAOResponse(ResponseType.END_NEGOTIATION, None)

        partner_offer = state.current_offer

        if partner_offer is None:
            counter = self.concealing_bidding_strategy(state)
            self.last_counter_offer = counter
            return SAOResponse(ResponseType.REJECT_OFFER, counter)

        self.update_opponent_model(state)

        if self.acceptance_strategy(state):
            return SAOResponse(ResponseType.ACCEPT_OFFER, partner_offer)

        counter = self.concealing_bidding_strategy(state)
        self.last_counter_offer = counter
        return SAOResponse(ResponseType.REJECT_OFFER, counter)

    def acceptance_strategy(self, state: SAOState) -> bool:
        """
        Accept if the offer meets a time-decaying aspiration, beats our next bid,
        or we are near the deadline with a safe deal.
        """
        assert self.ufun
        partner_offer = state.current_offer
        if partner_offer is None:
            return False

        offer_utility_for_me = float(self.ufun(partner_offer))
        relative_time = state.relative_time
        max_utility_for_me = float(self.ufun.max())

        # Aspiration level drops as deadline approaches
        aspiration_utility = max_utility_for_me * (1.0 - 0.55 * relative_time)
        if (
            offer_utility_for_me >= aspiration_utility
            and offer_utility_for_me > float(self.ufun.reserved_value)
        ):
            return True

        # Accept if partner offer is at least as good as what we would bid next
        our_next_bid = self.concealing_bidding_strategy(state)
        if our_next_bid is not None:
            utility_of_our_next_bid = float(self.ufun(our_next_bid))
            if offer_utility_for_me >= utility_of_our_next_bid - 1e-9:
                return True

        # Last resort before timeout
        if relative_time > 0.92 and offer_utility_for_me > float(
            self.ufun.reserved_value
        ) * 1.02:
            return True

        return False

    def concealing_bidding_strategy(self, state: SAOState) -> Outcome | None:
        """Pick the next counter-offer based on negotiation phase."""
        if not self.rational_outcomes:
            return None

        relative_time = state.relative_time
        # Deterministic randomness per step (reproducible for a given negotiator id)
        rng = random.Random(hash((self.id, state.step)) & 0xFFFFFFFF)

        if relative_time < self.DECOY_PHASE_END and self.decoy_outcomes:
            return rng.choice(self.decoy_outcomes)

        if relative_time < self.TRANSITION_PHASE_END:
            candidate_pool = self._build_transition_candidate_pool(relative_time, rng)
            return rng.choice(candidate_pool)

        return self._pick_closing_bid(relative_time, rng)

    def _build_transition_candidate_pool(
        self, relative_time: float, rng: random.Random
    ) -> list[Outcome]:
        """Gradually shift from decoy bids toward our true aspiration band."""
        max_utility_for_me = float(self.ufun.max())
        transition_progress = (relative_time - self.DECOY_PHASE_END) / max(
            1e-9, self.TRANSITION_PHASE_END - self.DECOY_PHASE_END
        )
        min_utility_in_band = max_utility_for_me * (0.92 - 0.35 * transition_progress)

        true_preference_band = [
            o
            for o in self.rational_outcomes
            if float(self.ufun(o)) >= min_utility_in_band
        ]
        if not true_preference_band:
            true_preference_band = list(self.rational_outcomes[:10])

        # Early in transition, still mix some decoy outcomes
        if self.decoy_outcomes and transition_progress < 0.6:
            num_decoy_slots = max(1, int(len(true_preference_band) * (1.0 - transition_progress)))
            decoy_slice = list(self.decoy_outcomes[: max(5, num_decoy_slots)])
            return decoy_slice + true_preference_band

        return true_preference_band

    def _pick_closing_bid(self, relative_time: float, rng: random.Random) -> Outcome:
        """
        Late phase: maximize a blend of our utility and estimated opponent utility.

        Goal: offer something they think is great (bait-and-switch after decoy phase)
        while still keeping enough utility for us.
        """
        max_utility_for_me = float(self.ufun.max())
        min_closing_utility = max(
            float(self.ufun.reserved_value),
            max_utility_for_me
            * (
                0.72
                - 0.2
                * (relative_time - self.TRANSITION_PHASE_END)
                / max(1e-9, 1.0 - self.TRANSITION_PHASE_END)
            ),
        )

        closing_candidates = [
            o for o in self.rational_outcomes if float(self.ufun(o)) >= min_closing_utility
        ]
        if not closing_candidates:
            closing_candidates = list(self.rational_outcomes[:20])

        opponent_model = self.opponent_frequency_model
        if opponent_model is None or not opponent_model.has_observations():
            return rng.choice(closing_candidates[: min(15, len(closing_candidates))])

        # Weight on opponent utility grows through the closing phase
        opponent_utility_weight = min(
            0.45, 0.15 + 0.35 * (relative_time - self.TRANSITION_PHASE_END)
        )
        best_combined_score = -1.0
        best_outcomes: list[Outcome] = []

        sample = (
            closing_candidates
            if len(closing_candidates) <= 40
            else rng.sample(closing_candidates, 40)
        )
        for outcome in sample:
            my_utility = float(self.ufun(outcome))
            their_estimated_utility = opponent_model.estimated_opponent_utility(outcome)
            combined_score = (1.0 - opponent_utility_weight) * (
                my_utility / max_utility_for_me
            ) + opponent_utility_weight * their_estimated_utility

            if combined_score > best_combined_score + 1e-9:
                best_combined_score = combined_score
                best_outcomes = [outcome]
            elif abs(combined_score - best_combined_score) < 1e-9:
                best_outcomes.append(outcome)

        return rng.choice(best_outcomes)

    def update_opponent_model(self, state: SAOState) -> None:
        """Learn from the opponent's latest offer."""
        partner_offer = state.current_offer
        if partner_offer is None or self.opponent_frequency_model is None:
            return
        self.opponent_frequency_model.record_opponent_offer(partner_offer)
