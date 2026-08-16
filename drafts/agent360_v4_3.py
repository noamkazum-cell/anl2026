"""Agent360V43 — frozen V4.3 behavior (rank-28 tournament regression; do not submit)."""

from __future__ import annotations

from agent360_FINAL import Agent360 as Agent360V42Active
from agent360_FINAL import Agent360Base, Agent360V2


class Agent360V43(Agent360V42Active):
    """V4.3 constants + behavior archived for post-mortem / A/B only."""

    FIRST_MIN_OPPONENT_OFFERS = 5
    SECOND_DECOY_PHASE_END = 0.32
    ACCEPT_ESCAPE_TIME = 0.88
    BAIT_REJECT_MAX_TIME = 0.78
    FIRST_STABLE_ISSUE_BLEND = 0.20
    CLOSING_CAP_LEARNER = 0.50
    CLOSING_CAP_UNKNOWN = 0.44
    CLOSING_LEARNER_UTILITY_BOOST = 0.06
    CLOSING_LEARNER_SAMPLE_CAP = 55
    ASPIRATION_SLOPE_CONCEDING = 0.40
    ASPIRATION_SLOPE_LEARNER = 0.48

    def decoy_phase_end(self) -> float:
        if self.is_first_negotiator():
            return self.FIRST_DECOY_PHASE_END
        return self.SECOND_DECOY_PHASE_END

    def transition_allowed(self) -> bool:
        if not self.is_first_negotiator():
            if self._opponent_conceding_early_exit():
                if self._opponent_offer_count >= self.CONCEDING_EARLY_EXIT_MIN_OPP_OFFERS:
                    return True
        return Agent360V2.transition_allowed(self)
