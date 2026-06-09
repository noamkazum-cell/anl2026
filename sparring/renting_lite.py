"""AgentRenting-inspired sparring agent: curve-fit partner RV + frequency model."""

from __future__ import annotations

import numpy as np
from negmas.outcomes import Outcome
from negmas.preferences import LambdaMultiFun
from negmas.sao import ResponseType, SAOCallNegotiator, SAOResponse, SAOState
from scipy.optimize import curve_fit

from sparring.common import (
    FrequencyOpponentModel,
    aspiration_function,
    count_unique_utilities,
    opponent_concession_curve,
)
from sparring.decoy_persona import DecoyPersona

__all__ = ["RentingLite"]


class RentingLite(SAOCallNegotiator):
    """
    Bilateral 2026 sparring partner inspired by AgentRenting2024.

    Tracks opponent offer times and estimated utilities, fits a concession curve
    when enough unique points exist, and uses the learned floor in acceptance.

    With ``deceptive=True`` (default), adds decoy/bait bids that poison curve-fit
    unless the opponent models trajectory inconsistency (V3).
    """

    def __init__(
        self,
        *args,
        e: float = 3.0,
        min_unique_utilities: int = 8,
        deceptive: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.e = e
        self.min_unique_utilities = min_unique_utilities
        self.deceptive = deceptive
        self._rational: tuple[Outcome, ...] = ()
        self._freq: FrequencyOpponentModel | None = None
        self._decoy = DecoyPersona()
        self.opponent_times: list[float] = []
        self.opponent_est_utils: list[float] = []
        self.partner_reserved_value = 0.0

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
        self.opponent_times.clear()
        self.opponent_est_utils.clear()
        self.partner_reserved_value = 0.0

    def _record_opponent(self, state: SAOState, offer: Outcome) -> None:
        assert self._freq is not None
        self._freq.record_opponent_offer(offer)
        self.opponent_times.append(state.relative_time)
        self.opponent_est_utils.append(self._freq.estimated_opponent_utility(offer))
        self._fit_partner_rv()

    def _fit_partner_rv(self) -> None:
        if count_unique_utilities(self.opponent_est_utils) < self.min_unique_utilities:
            return

        times = np.asarray(self.opponent_times, dtype=float)
        utils = np.asarray(self.opponent_est_utils, dtype=float)
        u0 = float(utils[0])

        def _curve(t: np.ndarray, rv: float, e: float) -> np.ndarray:
            return opponent_concession_curve(t, u0, rv, e)

        try:
            popt, _ = curve_fit(
                _curve,
                times,
                utils,
                p0=(max(0.0, float(utils.min()) - 0.05), self.e),
                bounds=([0.0, 0.5], [1.0, 25.0]),
                maxfev=4000,
            )
            self.partner_reserved_value = max(0.0, float(popt[0]))
        except Exception:
            self.partner_reserved_value = max(0.0, float(min(utils)))

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

    def _accept(self, state: SAOState, offer: Outcome) -> bool:
        assert self.ufun is not None
        my_u = float(self.ufun(offer))
        rv = float(self.ufun.reserved_value)
        t = state.relative_time

        if my_u >= self._aspiration(t):
            return True
        if t > 0.95 and my_u >= rv:
            return True
        if (
            self.partner_reserved_value > 0.0
            and self._freq is not None
            and self._freq.estimated_opponent_utility(offer) >= self.partner_reserved_value - 0.05
            and my_u >= rv + 0.05
            and t > 0.85
        ):
            return True
        return False

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        if self.ufun is None:
            return SAOResponse(ResponseType.END_NEGOTIATION, None)

        offer = state.current_offer
        t = state.relative_time

        if offer is not None:
            self._record_opponent(state, offer)
            if self._accept(state, offer):
                return SAOResponse(ResponseType.ACCEPT_OFFER, offer)

        return SAOResponse(ResponseType.REJECT_OFFER, self._pick_offer(t, state.step))
