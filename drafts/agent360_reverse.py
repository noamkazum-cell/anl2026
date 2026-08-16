"""Agent360Reverse — reverse-psychology decoy variant: bid true preferences early, misdirect later."""

from __future__ import annotations

import random

from negmas.outcomes import Outcome

from drafts.agent360 import Agent360Base


class Agent360Reverse(Agent360Base):
    """
    Reverse / truth-first decoy strategy.

    Early phase: bid our true top preferences (reverse-psychology hypothesis).
    Transition: introduce misdirection outcomes (wrong issue priorities), then converge.
    Closing: inherited from Agent360.
    """

    misdirection_outcomes: tuple[Outcome, ...] = ()

    def on_preferences_changed(self, changes):
        """Build truth decoy pool and a separate misdirection pool for transition."""
        super().on_preferences_changed(changes)
        self.misdirection_outcomes = self.decoy_outcomes
        self.decoy_outcomes = self._build_truth_pool()

    def _build_truth_pool(self) -> tuple[Outcome, ...]:
        """Top rational outcomes — what we actually want (shown early on purpose)."""
        if not self.rational_outcomes:
            return ()

        num_rational = len(self.rational_outcomes)
        top_k = max(3, min(30, num_rational // 10 or 3))
        return self.rational_outcomes[:top_k]

    def _build_transition_candidate_pool(
        self, relative_time: float, rng: random.Random
    ) -> list[Outcome]:
        """
        Inverse of gradient: after truth phase, mix misdirection then move to true band.

        Early transition favors misdirection_outcomes; late transition uses true aspirations.
        """
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

        if self.misdirection_outcomes and transition_progress < 0.55:
            num_misdirection_slots = max(
                1,
                int(len(true_preference_band) * (1.0 - transition_progress * 1.2)),
            )
            misdirection_slice = list(
                self.misdirection_outcomes[: max(5, num_misdirection_slots)]
            )
            return misdirection_slice + true_preference_band

        return true_preference_band
