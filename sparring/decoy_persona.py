"""Decoy persona helper for deceptive sparring opponents (2024-style concealment)."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, Callable

from negmas.outcomes import Outcome


class DecoyPersona:
    """
    Early-phase decoy bids + occasional transition bait offers.

    Mimics top 2024 agents that mislead Smith/frequency learners before conceding.
    """

    DECOY_PHASE_END = 0.38
    BAIT_UNTIL = 0.62
    BAIT_PROB = 0.24

    def __init__(self) -> None:
        self._decoys: tuple[Outcome, ...] = ()
        self._rational: tuple[Outcome, ...] = ()

    def build(self, ufun, rational_outcomes: tuple[Outcome, ...]) -> None:
        """Build maximal-mismatch decoy pool from rational outcomes."""
        self._rational = rational_outcomes
        if not rational_outcomes:
            self._decoys = ()
            return

        num_rational = len(rational_outcomes)
        top_k = max(3, min(30, num_rational // 10 or 3))
        best = rational_outcomes[:top_k]
        num_issues = len(best[0])

        true_preferred: list[Any] = []
        for issue_index in range(num_issues):
            values = [o[issue_index] for o in best]
            true_preferred.append(Counter(values).most_common(1)[0][0])

        rv = float(ufun.reserved_value)
        min_u = max(rv, float(ufun(best[-1])) * 0.55)

        scored: list[tuple[int, Outcome]] = []
        for outcome in rational_outcomes:
            ou = float(ufun(outcome))
            if ou < min_u:
                break
            mismatches = sum(
                1
                for i in range(num_issues)
                if outcome[i] != true_preferred[i]
            )
            if mismatches >= max(1, num_issues // 2):
                scored.append((mismatches, outcome))

        if not scored:
            mid = rational_outcomes[top_k : top_k + max(5, num_rational // 8)]
            self._decoys = tuple(mid) if mid else rational_outcomes[-3:]
            return

        max_m = max(s for s, _ in scored)
        pool = [o for s, o in scored if s >= max_m - 1]
        self._decoys = tuple(pool[: max(3, len(pool))])

    @property
    def decoys(self) -> tuple[Outcome, ...]:
        return self._decoys

    def wrap(
        self,
        relative_time: float,
        negotiator_id: str,
        step: int,
        honest: Callable[[], Outcome | None],
    ) -> Outcome | None:
        """Return decoy, bait, or honest bid."""
        base = honest()
        if base is None or not self._decoys:
            return base

        rng = random.Random(hash((negotiator_id, step)) & 0xFFFFFFFF)

        if relative_time < self.DECOY_PHASE_END:
            return rng.choice(self._decoys)

        if relative_time < self.BAIT_UNTIL and rng.random() < self.BAIT_PROB:
            return rng.choice(self._decoys)

        return base
