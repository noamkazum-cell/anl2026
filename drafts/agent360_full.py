"""Agent360Full — full-flip decoy variant: strong opposite persona, abrupt shift to true preferences."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from negmas.outcomes import Outcome

from drafts.agent360 import Agent360Base


class Agent360Full(Agent360Base):
    """
    Full-flip decoy strategy.

    Early phase: bid outcomes that mismatch true preferences on as many issues as possible.
    Transition: jump straight to the true aspiration band (no gradual decoy blending).
    Closing: inherited from Agent360.
    """

    def _true_preferred_value_per_issue(self) -> list[Any]:
        """Infer favorite value per issue from our top rational outcomes."""
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
        """
        Maximal mismatch decoys: rational outcomes that disagree on the most issues.

        Prefer outcomes that mismatch every issue when possible; still above a utility floor.
        """
        if not self.rational_outcomes:
            return ()

        true_preferred_value_per_issue = self._true_preferred_value_per_issue()
        if not true_preferred_value_per_issue:
            return ()

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

    def _build_transition_candidate_pool(
        self, relative_time: float, rng: random.Random
    ) -> list[Outcome]:
        """Abrupt shift: true aspiration band only, no decoy mixing."""
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

        return true_preference_band
