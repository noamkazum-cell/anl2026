"""Agent360V3 — V2.4 persona + competition-style opponent modeling."""

from __future__ import annotations

import random
from collections import Counter
from typing import Literal

from negmas.outcomes import Outcome
from negmas.preferences import LambdaMultiFun
from negmas.sao import SAOState

from drafts.agent360 import FrequencyOpponentModel
from drafts.agent360_v2 import Agent360V2

OpponentMode = Literal["unknown", "mirror", "conceding", "learner", "deceptive"]


def issue_weighted_smith_estimate(
    offers: list[Outcome],
    offer: Outcome,
    *,
    num_issues: int,
) -> float:
    """
    Smith estimate with higher weight on issues the opponent actually negotiates.

    Issues they repeat one value on (noise / decoy) get low weight; issues with
    spread signal real preferences — matches how rational-filter agents behave.
    """
    if not offers or num_issues == 0:
        return 0.5

    weighted_sum = 0.0
    weight_total = 0.0
    for issue_index in range(num_issues):
        values = [o[issue_index] for o in offers]
        counts = Counter(values)
        n = len(values)
        distinct = len(counts)
        max_count = max(counts.values())
        concentration = max_count / n
        issue_weight = max(0.12, (1.0 - concentration) + 0.18 * (distinct - 1))
        value = offer[issue_index]
        score = counts.get(value, 0) / max_count if max_count else 0.5
        weighted_sum += issue_weight * score
        weight_total += issue_weight

    if weight_total < 1e-12:
        return 0.5
    return weighted_sum / weight_total


class RecencyBlendedSmith:
    """Smith frequency model with extra weight on recent opponent bids."""

    def __init__(self, full_model: FrequencyOpponentModel, window: int = 5) -> None:
        self.full_model = full_model
        self.window = window
        self._recent: list[Outcome] = []

    def record(self, offer: Outcome) -> None:
        self._recent.append(offer)
        if len(self._recent) > self.window:
            self._recent.pop(0)

    def recent_count(self) -> int:
        return len(self._recent)

    def estimated(self, offer: Outcome) -> float:
        full_u = self.full_model.estimated_opponent_utility(offer)
        n = len(self._recent)
        if n < 2:
            return full_u

        recent_model = FrequencyOpponentModel(self.full_model.num_issues)
        for recent_offer in self._recent:
            recent_model.record_opponent_offer(recent_offer)
        recent_u = recent_model.estimated_opponent_utility(offer)

        weight = min(0.68, 0.22 + 0.09 * n)
        return (1.0 - weight) * full_u + weight * recent_u


class TimedOpponentModel:
    """Opponent Smith model that up-weights bids after their likely decoy phase."""

    def __init__(
        self,
        num_issues: int,
        *,
        late_time_threshold: float = 0.40,
        late_bid_weight: int = 3,
    ) -> None:
        self.num_issues = num_issues
        self.late_time_threshold = late_time_threshold
        self.late_bid_weight = late_bid_weight
        self._timed_offers: list[tuple[float, Outcome]] = []

    def record(self, relative_time: float, offer: Outcome) -> None:
        self._timed_offers.append((relative_time, offer))

    def offer_count(self) -> int:
        return len(self._timed_offers)

    def late_count(self) -> int:
        return sum(
            1 for t, _ in self._timed_offers if t >= self.late_time_threshold
        )

    def _build_weighted_model(self) -> FrequencyOpponentModel:
        model = FrequencyOpponentModel(self.num_issues)
        for relative_time, offer in self._timed_offers:
            repeats = (
                self.late_bid_weight
                if relative_time >= self.late_time_threshold
                else 1
            )
            for _ in range(repeats):
                model.record_opponent_offer(offer)
        return model

    def late_phase_estimated(self, offer: Outcome) -> float:
        late_offers = [
            o for t, o in self._timed_offers if t >= self.late_time_threshold
        ]
        if len(late_offers) >= 2:
            model = FrequencyOpponentModel(self.num_issues)
            for late_offer in late_offers:
                model.record_opponent_offer(late_offer)
            return model.estimated_opponent_utility(offer)
        if self._timed_offers:
            return self._build_weighted_model().estimated_opponent_utility(offer)
        return 0.5

    def late_offers(self) -> list[Outcome]:
        return [o for t, o in self._timed_offers if t >= self.late_time_threshold]

    def late_issue_weighted_estimated(self, offer: Outcome) -> float:
        late = self.late_offers()
        if len(late) >= 2:
            return issue_weighted_smith_estimate(
                late, offer, num_issues=self.num_issues
            )
        return self.late_phase_estimated(offer)

    def weighted_estimated(self, offer: Outcome) -> float:
        if not self._timed_offers:
            return 0.5
        return self._build_weighted_model().estimated_opponent_utility(offer)


class OfferTrajectoryModel:
    """Track opponent (time, Smith-estimated utility) pairs from their offers."""

    def __init__(self) -> None:
        self._samples: list[tuple[float, float]] = []

    def record(self, relative_time: float, estimated_utility: float) -> None:
        self._samples.append(
            (relative_time, max(0.0, min(1.0, estimated_utility)))
        )

    def sample_count(self) -> int:
        return len(self._samples)

    def has_observations(self) -> bool:
        return bool(self._samples)

    def last_sample(self) -> tuple[float, float] | None:
        if not self._samples:
            return None
        return self._samples[-1]

    def concession_slope(self) -> float:
        n = len(self._samples)
        if n < 2:
            return 0.0

        times = [t for t, _ in self._samples]
        utils = [u for _, u in self._samples]
        mean_t = sum(times) / n
        mean_u = sum(utils) / n
        var_t = sum((t - mean_t) ** 2 for t in times)
        if var_t < 1e-12:
            return 0.0
        cov = sum((t - mean_t) * (u - mean_u) for t, u in self._samples)
        return cov / var_t

    def predicted_utility_at(self, relative_time: float) -> float:
        if not self._samples:
            return 0.5
        if len(self._samples) == 1:
            return self._samples[0][1]

        last_t, last_u = self._samples[-1]
        predicted = last_u + self.concession_slope() * (relative_time - last_t)
        return max(0.0, min(1.0, predicted))

    def is_non_monotone(self, tolerance: float = 0.05) -> bool:
        if len(self._samples) < 3:
            return False
        utils = [u for _, u in self._samples]
        rises = sum(
            1 for i in range(1, len(utils)) if utils[i] > utils[i - 1] + tolerance
        )
        return rises >= 2

    def inconsistency_vs_trajectory(
        self, estimated_utility: float, relative_time: float
    ) -> float:
        return abs(estimated_utility - self.predicted_utility_at(relative_time))


class Agent360V3(Agent360V2):
    """
    V3 submission agent: V2.4 concealment + anti-competitor opponent modeling.

    Assumes rivals use the same three tactics we do:

    1. **Decoy** — early bids misrepresent issue priorities (down-weight t < 0.4).
    2. **Bait** — transition spikes that look good on Smith but not trajectory.
    3. **Smith learning** — frequency model of us (we keep decoy rotation + min offers).

    Modeling uses late/recency/issue-weighted Smith; bait guards fire only when
    concealment-style signals appear, not on plain BOA/MAP learners.
    """

    MIN_TRAJECTORY_SAMPLES = 3
    HONEST_CONCESSION_SLOPE = -0.04

    BAIT_THRESHOLD = 0.10
    BAIT_DISCOUNT = 0.45
    ACCEPT_BAIT_THRESHOLD = 0.08
    ACCEPT_DEADLINE_SAFE = 0.92
    INCONSISTENCY_BLEND_THRESHOLD = 0.18
    INCONSISTENCY_BLEND = 0.38

    EARLY_DECOY_FLIP_RATE = 0.25
    EARLY_DECOY_MIN_OFFERS = 3
    EARLY_SMITH_SPREAD = 0.12
    MIRROR_MATCH_WINDOW = 4
    MIRROR_MATCH_MIN = 3

    RECENCY_WINDOW = 5
    STABLE_ISSUE_WINDOW = 4
    STABLE_ISSUE_BLEND = 0.14
    CONCEDING_SLOPE_THRESHOLD = -0.025

    LATE_TIME_THRESHOLD = 0.40
    LATE_BID_WEIGHT = 3
    LATE_BLEND_MAX = 0.55
    FIRST_LATE_BLEND_MAX = 0.62
    ISSUE_WEIGHT_BLEND_MAX = 0.28

    LEARNER_CONCENTRATION = 0.78
    LEARNER_MIN_OFFERS = 4

    FIRST_DECOY_NO_REPEAT_WINDOW = 5

    offer_trajectory_model: OfferTrajectoryModel | None = None
    _recency_blended: RecencyBlendedSmith | None = None
    _timed_opponent: TimedOpponentModel | None = None
    _eval_relative_time: float = 0.0
    _opponent_recent_offers: list[Outcome] | None = None
    _opponent_offer_history: list[tuple[float, Outcome]] | None = None

    def on_preferences_changed(self, changes) -> None:
        super().on_preferences_changed(changes)
        if getattr(self, "_recent_own_bids", None) is None:
            self._recent_own_bids = []
        self.offer_trajectory_model = OfferTrajectoryModel()
        self._opponent_recent_offers = []
        self._opponent_offer_history = []
        if self.opponent_frequency_model is not None:
            num_issues = self.opponent_frequency_model.num_issues
            self._recency_blended = RecencyBlendedSmith(
                self.opponent_frequency_model, window=self.RECENCY_WINDOW
            )
            self._timed_opponent = TimedOpponentModel(
                num_issues,
                late_time_threshold=self.LATE_TIME_THRESHOLD,
                late_bid_weight=self.LATE_BID_WEIGHT,
            )
            self.private_info["opponent_ufun"] = LambdaMultiFun(
                f=self._published_opponent_utility
            )

    def _pick_decoy_bid(self, rng: random.Random) -> Outcome:
        """Rotate decoy outcomes when opening to break opponent curve-fit."""
        own_bids = getattr(self, "_recent_own_bids", None) or []
        if (
            not self.is_first_negotiator()
            or not self.decoy_outcomes
            or self.FIRST_DECOY_NO_REPEAT_WINDOW <= 0
            or not own_bids
        ):
            return super()._pick_decoy_bid(rng)

        pool = list(self.decoy_outcomes)
        recent = set(own_bids[-self.FIRST_DECOY_NO_REPEAT_WINDOW :])
        candidates = [outcome for outcome in pool if outcome not in recent]
        if candidates:
            return rng.choice(candidates)
        return rng.choice(pool)

    def _closing_bluff_active(self, relative_time: float | None = None) -> bool:
        t = self._eval_relative_time if relative_time is None else relative_time
        if t < self.transition_phase_end():
            return False
        traj = self.offer_trajectory_model
        return traj is not None and traj.sample_count() >= self.MIN_TRAJECTORY_SAMPLES

    def update_opponent_model(self, state: SAOState) -> None:
        super().update_opponent_model(state)
        partner_offer = state.current_offer
        if (
            partner_offer is None
            or self.offer_trajectory_model is None
            or self.opponent_frequency_model is None
        ):
            return
        if self._recency_blended is not None:
            self._recency_blended.record(partner_offer)
        if self._timed_opponent is not None:
            self._timed_opponent.record(state.relative_time, partner_offer)
        smith_u = self.opponent_frequency_model.estimated_opponent_utility(
            partner_offer
        )
        self.offer_trajectory_model.record(state.relative_time, smith_u)
        if self._opponent_recent_offers is not None:
            self._opponent_recent_offers.append(partner_offer)
            if len(self._opponent_recent_offers) > self.MIRROR_MATCH_WINDOW:
                self._opponent_recent_offers.pop(0)
        if self._opponent_offer_history is not None:
            self._opponent_offer_history.append((state.relative_time, partner_offer))

    def _opponent_mirrors_us(self) -> bool:
        own_bids = getattr(self, "_recent_own_bids", None) or []
        opp_offers = self._opponent_recent_offers or []
        if not own_bids or not opp_offers:
            return False
        window = min(
            self.MIRROR_MATCH_WINDOW,
            len(own_bids),
            len(opp_offers),
        )
        if window < self.MIRROR_MATCH_MIN:
            return False
        own = own_bids[-window:]
        opp = opp_offers[-window:]
        matches = sum(1 for a, b in zip(own, opp) if a == b)
        return matches >= self.MIRROR_MATCH_MIN

    def _early_offers(self) -> list[Outcome]:
        history = self._opponent_offer_history
        if not history:
            return []
        return [o for t, o in history if t < self.LATE_TIME_THRESHOLD]

    def _early_issue_flip_rate(self) -> float:
        early = self._early_offers()
        if len(early) < 2:
            return 0.0
        flips = sum(1 for i in range(1, len(early)) if early[i] != early[i - 1])
        return flips / (len(early) - 1)

    def _early_smith_util_spread(self) -> float:
        early = self._early_offers()
        if len(early) < 3 or self.opponent_frequency_model is None:
            return 0.0
        utils = [
            self.opponent_frequency_model.estimated_opponent_utility(o) for o in early
        ]
        return max(utils) - min(utils)

    def _opponent_early_decoy_persona(self) -> bool:
        early = self._early_offers()
        if len(early) < self.EARLY_DECOY_MIN_OFFERS:
            return False
        if len(set(early)) == 1:
            return True
        if self._early_issue_flip_rate() >= self.EARLY_DECOY_FLIP_RATE:
            return True
        return self._early_smith_util_spread() >= self.EARLY_SMITH_SPREAD

    def _opponent_offer_concentration(self, offers: list[Outcome]) -> float:
        if not offers:
            return 0.0
        num_issues = len(offers[0])
        per_issue: list[float] = []
        for issue_index in range(num_issues):
            counts = Counter(o[issue_index] for o in offers)
            per_issue.append(max(counts.values()) / len(offers))
        return sum(per_issue) / num_issues

    def _opponent_late_bait_switch(self) -> bool:
        history = self._opponent_offer_history or []
        late = [o for t, o in history if t >= self.LATE_TIME_THRESHOLD]
        if len(late) < 4:
            return False
        mid = len(late) // 2
        first, second = late[:mid], late[mid:]
        num_issues = len(late[0])
        flips = 0
        for issue_index in range(num_issues):
            pref_first = Counter(o[issue_index] for o in first).most_common(1)[0][0]
            pref_second = Counter(o[issue_index] for o in second).most_common(1)[0][0]
            if pref_first != pref_second:
                flips += 1
        return flips >= max(1, num_issues // 2)

    def _opponent_shows_concealment_tactics(self) -> bool:
        traj = self.offer_trajectory_model
        if self._opponent_early_decoy_persona():
            return True
        if traj is not None and traj.is_non_monotone():
            return True
        return self._opponent_late_bait_switch()

    def _opponent_smith_learner_profile(self) -> bool:
        recent = self._opponent_recent_offers or []
        if len(recent) < self.LEARNER_MIN_OFFERS:
            return False
        if self._opponent_shows_concealment_tactics():
            return False
        concentration = self._opponent_offer_concentration(recent)
        traj = self.offer_trajectory_model
        if traj is not None and traj.is_non_monotone():
            return False
        return concentration >= self.LEARNER_CONCENTRATION

    def _opponent_mode(self) -> OpponentMode:
        if self._opponent_mirrors_us():
            return "mirror"
        traj = self.offer_trajectory_model
        if traj is None or traj.sample_count() < 2:
            return "unknown"
        if self._opponent_smith_learner_profile():
            return "learner"
        if self._opponent_shows_concealment_tactics():
            return "deceptive"
        if (
            traj.sample_count() >= self.MIN_TRAJECTORY_SAMPLES
            and traj.concession_slope() <= self.CONCEDING_SLOPE_THRESHOLD
        ):
            return "conceding"
        return "learner"

    def _stable_issue_match_score(self, offer: Outcome) -> float:
        recent = self._opponent_recent_offers or []
        if len(recent) < 3 or not offer:
            return 0.5
        window = recent[-self.STABLE_ISSUE_WINDOW :]
        num_issues = len(offer)
        matches = 0
        for issue_index in range(num_issues):
            values = [o[issue_index] for o in window]
            preferred = Counter(values).most_common(1)[0][0]
            if offer[issue_index] == preferred:
                matches += 1
        return matches / num_issues

    def _blended_opponent_utility(self, offer: Outcome) -> float:
        if self.opponent_frequency_model is None:
            return 0.5
        if self._opponent_mirrors_us():
            return self.opponent_frequency_model.estimated_opponent_utility(offer)

        full_u = self.opponent_frequency_model.estimated_opponent_utility(offer)
        blended = full_u

        timed = self._timed_opponent
        if timed is not None and timed.late_count() >= 2:
            late_u = timed.late_phase_estimated(offer)
            late_weight = min(
                self.FIRST_LATE_BLEND_MAX if self.is_first_negotiator() else self.LATE_BLEND_MAX,
                0.22 + 0.08 * timed.late_count(),
            )
            blended = (1.0 - late_weight) * blended + late_weight * late_u

        if timed is not None and len(timed.late_offers()) >= 3:
            issue_u = timed.late_issue_weighted_estimated(offer)
            issue_weight = min(
                self.ISSUE_WEIGHT_BLEND_MAX,
                0.10 + 0.04 * len(timed.late_offers()),
            )
            blended = (1.0 - issue_weight) * blended + issue_weight * issue_u

        if not self.is_first_negotiator() and self._recency_blended is not None:
            if self._recency_blended.recent_count() >= 2:
                recency_u = self._recency_blended.estimated(offer)
                recency_weight = min(
                    0.55, 0.18 + 0.08 * self._recency_blended.recent_count()
                )
                blended = (1.0 - recency_weight) * blended + recency_weight * recency_u

            mode = self._opponent_mode()
            if mode in ("learner", "conceding", "unknown") and (
                self._recency_blended.recent_count() >= 3
            ):
                stable = self._stable_issue_match_score(offer)
                blended = (
                    (1.0 - self.STABLE_ISSUE_BLEND) * blended
                    + self.STABLE_ISSUE_BLEND * stable
                )

        return max(0.0, min(1.0, blended))

    def _published_opponent_utility(self, offer: Outcome) -> float:
        return self._blended_opponent_utility(offer)

    def effective_closing_opponent_weight_cap(self) -> float:
        cap = super().effective_closing_opponent_weight_cap()
        mode = self._opponent_mode()
        if mode == "conceding":
            return min(0.52, cap * 1.12)
        if mode == "deceptive":
            return max(0.28, cap * 0.88)
        return cap

    def acceptance_strategy(self, state: SAOState) -> bool:
        self._eval_relative_time = state.relative_time
        if not super().acceptance_strategy(state):
            return False
        if state.relative_time > self.ACCEPT_DEADLINE_SAFE:
            return True
        if self._partner_offer_looks_like_bait(state):
            return False
        return True

    def _partner_offer_looks_like_bait(self, state: SAOState) -> bool:
        partner_offer = state.current_offer
        if partner_offer is None or self.opponent_frequency_model is None:
            return False
        if self._opponent_mirrors_us():
            return False
        if self._opponent_mode() != "deceptive":
            return False
        if not self._opponent_shows_concealment_tactics():
            return False
        if self._opponent_smith_learner_profile():
            return False
        traj = self.offer_trajectory_model
        if traj is None or traj.sample_count() < self.MIN_TRAJECTORY_SAMPLES:
            return False
        if traj.concession_slope() < self.HONEST_CONCESSION_SLOPE:
            return False

        smith_u = self.opponent_frequency_model.estimated_opponent_utility(
            partner_offer
        )
        predicted = traj.predicted_utility_at(state.relative_time)
        return smith_u > predicted + self.ACCEPT_BAIT_THRESHOLD

    def concealing_bidding_strategy(self, state: SAOState) -> Outcome | None:
        self._eval_relative_time = state.relative_time
        return super().concealing_bidding_strategy(state)

    def current_bluff_score(self) -> float:
        if self._opponent_mirrors_us():
            return 0.0
        traj = self.offer_trajectory_model
        if traj is None or traj.sample_count() < self.MIN_TRAJECTORY_SAMPLES:
            return 0.0
        slope = traj.concession_slope()
        if slope < self.HONEST_CONCESSION_SLOPE:
            return 0.0
        last = traj.last_sample()
        if last is None:
            return 0.0
        last_t, last_u = last
        return min(1.0, traj.inconsistency_vs_trajectory(last_u, last_t) * 1.75)

    def _should_apply_bait_discount(self) -> bool:
        if self._opponent_mirrors_us():
            return False
        if not self._closing_bluff_active():
            return False
        if self._opponent_mode() != "deceptive":
            return False
        if not self._opponent_shows_concealment_tactics():
            return False
        return not self._opponent_smith_learner_profile()

    def _offer_looks_like_bait(self, smith_u: float, relative_time: float) -> bool:
        traj = self.offer_trajectory_model
        if traj is None or not self._closing_bluff_active(relative_time):
            return False
        if traj.concession_slope() < self.HONEST_CONCESSION_SLOPE:
            return False
        predicted = traj.predicted_utility_at(relative_time)
        return smith_u > predicted + self.BAIT_THRESHOLD

    def estimated_opponent_utility(self, offer: Outcome) -> float:
        base_u = self._blended_opponent_utility(offer)
        if not self._should_apply_bait_discount():
            return base_u

        traj = self.offer_trajectory_model
        assert traj is not None

        relative_time = self._eval_relative_time
        predicted = traj.predicted_utility_at(relative_time)
        if not self._offer_looks_like_bait(base_u, relative_time):
            return base_u

        adjusted = base_u
        excess = base_u - predicted - self.BAIT_THRESHOLD
        adjusted = predicted + self.BAIT_THRESHOLD + excess * (1.0 - self.BAIT_DISCOUNT)

        inconsistency = abs(base_u - predicted)
        if inconsistency > self.INCONSISTENCY_BLEND_THRESHOLD:
            adjusted = (
                (1.0 - self.INCONSISTENCY_BLEND) * adjusted
                + self.INCONSISTENCY_BLEND * predicted
            )

        return max(0.0, min(1.0, adjusted))

# Standalone dev copy — submission uses agent360_submit.py (zipped as agent360.py).
