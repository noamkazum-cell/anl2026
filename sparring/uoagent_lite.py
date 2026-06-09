"""UOAgent-inspired sparring agent: rational filtering + learned partner RV."""

from __future__ import annotations

import numpy as np
from negmas.outcomes import Outcome
from negmas.preferences import LambdaMultiFun
from negmas.sao import ResponseType, SAOCallNegotiator, SAOResponse, SAOState

from sparring.common import FrequencyOpponentModel
from sparring.decoy_persona import DecoyPersona

__all__ = ["UOAgentLite"]


class UOAgentLite(SAOCallNegotiator):
    """
    Bilateral 2026 sparring partner inspired by UOAgent (ANL 2024).

    Filters rational outcomes aggressively, tracks partner reserved value from
    the frequency opponent model, and uses a steep time-based acceptance curve.

    With ``deceptive=True`` (default), adds decoy/bait bids before the rational filter.
    """

    def __init__(self, *args, deceptive: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.deceptive = deceptive
        self.rational_outcomes: tuple[Outcome, ...] = ()
        self.partner_reserved_value = 1.0
        self.under = 1.0
        self.step = 0
        self._freq: FrequencyOpponentModel | None = None
        self._decoy = DecoyPersona()

    @staticmethod
    def _nearest_index(values: list[float], target: float) -> int:
        return int(np.abs(np.asarray(values) - target).argmin())

    def on_preferences_changed(self, changes) -> None:
        if self.ufun is None:
            return

        rv = float(self.ufun.reserved_value)
        outcomes = self.nmi.outcome_space.enumerate_or_sample()
        if rv <= 0.4:
            rational = [
                o
                for o in outcomes
                if float(self.ufun(o)) >= rv + 0.40
            ]
        else:
            rational = [
                o for o in outcomes if float(self.ufun(o)) >= rv and float(self.ufun(o)) >= 0.80
            ]
        if not rational:
            rational = [o for o in outcomes if float(self.ufun(o)) >= rv]

        utility_and_outcome = sorted(
            ((float(self.ufun(o)), o) for o in rational),
            reverse=True,
        )
        self.rational_outcomes = tuple(o for _, o in utility_and_outcome)
        self.under = rv if rv > 0.85 else 0.85
        self.partner_reserved_value = 1.0
        self.step = 0
        if self.deceptive:
            self._decoy.build(self.ufun, self.rational_outcomes)

        num_issues = len(self.rational_outcomes[0]) if self.rational_outcomes else 0
        self._freq = FrequencyOpponentModel(num_issues)
        self.private_info["opponent_ufun"] = LambdaMultiFun(
            f=self._freq.estimated_opponent_utility
        )

    def _est_opp(self, outcome: Outcome) -> float:
        assert self._freq is not None
        return self._freq.estimated_opponent_utility(outcome)

    def _update_partner_rv(self, offer: Outcome) -> None:
        est = self._est_opp(offer)
        if est < self.partner_reserved_value and est >= 0.01:
            self.partner_reserved_value = est
        if self._freq is not None:
            self._freq.record_opponent_offer(offer)

    def _accept(self, state: SAOState, offer: Outcome) -> bool:
        assert self.ufun is not None
        rv = float(self.ufun.reserved_value)
        t = state.relative_time

        if self.nmi.n_steps is not None and self.nmi.n_steps - self.step <= 1:
            return float(self.ufun(offer)) > rv

        threshold = 1.0 - (1.0 - rv) * (t**50)
        return float(self.ufun(offer)) > threshold

    def _bid(self, state: SAOState) -> Outcome | None:
        if not self.rational_outcomes or self.ufun is None or self._freq is None:
            return None

        n_steps = self.nmi.n_steps or 100
        t = state.relative_time

        def honest() -> Outcome | None:
            if t > 0.975 or (
                self.nmi.n_steps is not None and self.nmi.n_steps - self.step <= 1
            ):
                ranked = sorted(
                    self.rational_outcomes,
                    key=lambda o: self._est_opp(o),
                    reverse=True,
                )
                opp_utils = [self._est_opp(o) for o in ranked]
                hi = self._nearest_index(opp_utils, self.partner_reserved_value + 0.02)
                lo = self._nearest_index(opp_utils, self.partner_reserved_value)
                lo, hi = min(lo, hi), max(lo, hi)
                window = ranked[lo : hi + 1]
                return max(
                    window,
                    key=lambda o: (
                        self._est_opp(o) + float(self.ufun(o)),
                        float(self.ufun(o)),
                    ),
                )

            value = 1.0 - (1.0 - self.under) * ((self.step / n_steps) ** 5)
            my_utils = [float(self.ufun(o)) for o in self.rational_outcomes]
            hi = self._nearest_index(my_utils, value + 0.02)
            lo = self._nearest_index(my_utils, value - 0.02)
            lo, hi = min(lo, hi), max(lo, hi)
            window = self.rational_outcomes[lo : hi + 1]
            return max(
                window,
                key=lambda o: (
                    self._est_opp(o) + float(self.ufun(o)),
                    float(self.ufun(o)),
                ),
            )

        if self.deceptive:
            return self._decoy.wrap(t, str(self.id), self.step, honest)
        return honest()

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        if self.ufun is None:
            return SAOResponse(ResponseType.END_NEGOTIATION, None)

        offer = state.current_offer
        if offer is not None:
            self._update_partner_rv(offer)
            if self._accept(state, offer):
                self.step += 1
                return SAOResponse(ResponseType.ACCEPT_OFFER, offer)

        self.step += 1
        return SAOResponse(ResponseType.REJECT_OFFER, self._bid(state))
