"""Shochan-inspired sparring agent: time aspiration + frequency opponent model."""

from __future__ import annotations

from negmas.outcomes import Outcome
from negmas.preferences import LambdaMultiFun
from negmas.sao import ResponseType, SAOCallNegotiator, SAOResponse, SAOState

from sparring.common import FrequencyOpponentModel, aspiration_function
from sparring.decoy_persona import DecoyPersona

__all__ = ["ShochanLite"]


class ShochanLite(SAOCallNegotiator):
    """
    Bilateral 2026 sparring partner inspired by Shochan (ANL 2024).

    Uses a Boulware-style aspiration curve for offering/acceptance and a
    frequency model of the opponent (no oracle ``opponent_ufun``).

    With ``deceptive=True`` (default), adds an early decoy phase and occasional
    transition bait offers to stress-test bluff-aware agents.
    """

    def __init__(self, *args, e: float = 4.0, deceptive: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.e = e
        self.deceptive = deceptive
        self._rational: tuple[Outcome, ...] = ()
        self._freq: FrequencyOpponentModel | None = None
        self._decoy = DecoyPersona()

    def on_preferences_changed(self, changes) -> None:
        if self.ufun is None:
            return

        rv = float(self.ufun.reserved_value)
        utility_and_outcome = [
            (float(self.ufun(outcome)), outcome)
            for outcome in self.nmi.outcome_space.enumerate_or_sample()
            if float(self.ufun(outcome)) > rv
        ]
        self._rational = tuple(
            outcome for _, outcome in sorted(utility_and_outcome, reverse=True)
        )
        if self.deceptive:
            self._decoy.build(self.ufun, self._rational)

        num_issues = len(self._rational[0]) if self._rational else 0
        self._freq = FrequencyOpponentModel(num_issues)
        self.private_info["opponent_ufun"] = LambdaMultiFun(
            f=self._freq.estimated_opponent_utility
        )

    def _record_opponent(self, offer: Outcome) -> None:
        if self._freq is not None:
            self._freq.record_opponent_offer(offer)

    def _aspiration(self, relative_time: float) -> float:
        rv = float(self.ufun.reserved_value)
        return aspiration_function(relative_time, 1.0, rv, self.e)

    def _pick_offer(self, relative_time: float, step: int = 0) -> Outcome | None:
        if not self._rational:
            return None

        def honest() -> Outcome | None:
            target = self._aspiration(relative_time)
            best = self._rational[0]
            best_gap = abs(float(self.ufun(best)) - target)
            for outcome in self._rational:
                gap = abs(float(self.ufun(outcome)) - target)
                if gap < best_gap:
                    best, best_gap = outcome, gap
            return best

        if self.deceptive:
            return self._decoy.wrap(relative_time, str(self.id), step, honest)
        return honest()

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        if self.ufun is None:
            return SAOResponse(ResponseType.END_NEGOTIATION, None)

        offer = state.current_offer
        t = state.relative_time
        rv = float(self.ufun.reserved_value)

        if offer is not None:
            self._record_opponent(offer)
            my_u = float(self.ufun(offer))
            if my_u >= self._aspiration(t) or (t > 0.97 and my_u >= rv):
                return SAOResponse(ResponseType.ACCEPT_OFFER, offer)

        return SAOResponse(ResponseType.REJECT_OFFER, self._pick_offer(t, state.step))
