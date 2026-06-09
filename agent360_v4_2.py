"""Agent360V42 — frozen V4.2 behavior for A/B eval against V4.3 submission."""

from __future__ import annotations

from agent360_submit_v4 import Agent360 as Agent360V43
from agent360_submit_v4 import Agent360Base, Agent360V2


class Agent360V42(Agent360V43):
    """V4.2 constants + seat/decoy/acceptance behavior (pre-V4.3)."""

    FIRST_MIN_OPPONENT_OFFERS = 4
    CLOSING_CAP_LEARNER = 0.48
    CLOSING_CAP_UNKNOWN = 0.40
    CLOSING_LEARNER_UTILITY_BOOST = 0.04
    CLOSING_LEARNER_SAMPLE_CAP = 40
    ASPIRATION_SLOPE_CONCEDING = 0.42
    ASPIRATION_SLOPE_LEARNER = 0.52
    FIRST_STABLE_ISSUE_BLEND = 0.14
    ACCEPT_ESCAPE_TIME = 2.0
    BAIT_REJECT_MAX_TIME = 2.0

    def decoy_phase_end(self) -> float:
        if self.is_first_negotiator():
            return self.FIRST_DECOY_PHASE_END
        return Agent360Base.decoy_phase_end(self)

    def transition_allowed(self) -> bool:
        if self._opponent_conceding_early_exit():
            if self._opponent_offer_count >= self.CONCEDING_EARLY_EXIT_MIN_OPP_OFFERS:
                return True
        return Agent360V2.transition_allowed(self)
