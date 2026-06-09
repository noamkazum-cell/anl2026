"""Tests for Agent360V3 (Phase 1)."""

import pytest
from negmas.inout import Scenario
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from agent360_v3 import (
    Agent360V3,
    OfferTrajectoryModel,
    RecencyBlendedSmith,
    TimedOpponentModel,
    issue_weighted_smith_estimate,
)
from agent360 import FrequencyOpponentModel
from agent360_v2 import Agent360V2


class TestOfferTrajectoryModel:
    def test_concession_slope_decreasing(self):
        traj = OfferTrajectoryModel()
        for t, u in [(0.1, 0.9), (0.3, 0.7), (0.5, 0.5), (0.7, 0.3)]:
            traj.record(t, u)
        assert traj.concession_slope() < 0.0

    def test_predicted_utility_at_extends_line(self):
        traj = OfferTrajectoryModel()
        traj.record(0.2, 0.8)
        traj.record(0.4, 0.6)
        pred = traj.predicted_utility_at(0.6)
        assert 0.35 < pred < 0.45

    def test_non_monotone_detects_rises(self):
        traj = OfferTrajectoryModel()
        for t, u in [(0.1, 0.3), (0.2, 0.7), (0.3, 0.4), (0.4, 0.8)]:
            traj.record(t, u)
        assert traj.is_non_monotone()

    def test_monotone_not_flagged(self):
        traj = OfferTrajectoryModel()
        for t, u in [(0.1, 0.9), (0.3, 0.7), (0.5, 0.5)]:
            traj.record(t, u)
        assert not traj.is_non_monotone()


@pytest.fixture
def test_scenario():
    ufuns = generate_multi_issue_ufuns(
        n_issues=2,
        n_values=(3, 5),
        ufun_names=("First", "Second"),
        rational_fractions=[1.0, 1.0],
    )
    return Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns)


class TestAgent360V3:
    def test_instantiation(self):
        assert Agent360V3() is not None

    def test_trajectory_initialized(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        agent = Agent360V3()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert agent.offer_trajectory_model is not None
        assert agent.private_info.get("opponent_ufun") is not None

    def test_records_opponent_offers(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=30)
        agent = Agent360V3()
        opponent = Agent360V2()
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.run()
        assert agent.offer_trajectory_model.has_observations()

    def test_pre_closing_no_bait_adjustment(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        agent = Agent360V3()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        if agent.rational_outcomes and agent.opponent_frequency_model:
            offer = agent.rational_outcomes[0]
            agent._eval_relative_time = 0.1
            agent.offer_trajectory_model = OfferTrajectoryModel()
            agent.offer_trajectory_model.record(0.05, 0.5)
            published = agent._published_opponent_utility(offer)
            assert agent.estimated_opponent_utility(offer) == pytest.approx(published)

    def test_negotiation_completes(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V3()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_inherits_v24_min_offers(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V3()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert agent.FIRST_MIN_OPPONENT_OFFERS == 3
        agent._opponent_offer_count = 0
        assert not agent.transition_allowed()

    def test_bluff_score_zero_without_samples(self):
        agent = Agent360V3()
        agent.offer_trajectory_model = OfferTrajectoryModel()
        assert agent.current_bluff_score() == 0.0

    def test_bluff_discounts_high_smith_vs_trajectory(self, test_scenario):
        agent = Agent360V3()
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        traj = agent.offer_trajectory_model
        assert traj is not None
        traj = OfferTrajectoryModel()
        agent.offer_trajectory_model = traj
        for t, u in [(0.1, 0.3), (0.2, 0.7), (0.3, 0.4), (0.4, 0.85), (0.5, 0.35)]:
            traj.record(t, u)
        agent._eval_relative_time = 0.8
        agent.negotiation_seat = 1
        agent._opponent_offer_history = [
            (0.05, agent.rational_outcomes[0]),
            (0.10, agent.rational_outcomes[min(1, len(agent.rational_outcomes) - 1)]),
            (0.15, agent.rational_outcomes[0]),
            (0.20, agent.rational_outcomes[min(1, len(agent.rational_outcomes) - 1)]),
        ]

        if agent.rational_outcomes:
            offer = agent.rational_outcomes[0]
            base = agent._published_opponent_utility(offer)
            adjusted = agent.estimated_opponent_utility(offer)
            if base > traj.predicted_utility_at(0.8) + agent.BAIT_THRESHOLD:
                assert adjusted < base

    def test_bluff_inactive_before_closing(self, test_scenario):
        agent = Agent360V3()
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        traj = agent.offer_trajectory_model
        assert traj is not None
        for t, u in [(0.1, 0.3), (0.2, 0.7), (0.3, 0.4), (0.4, 0.85)]:
            traj.record(t, u)
        agent._eval_relative_time = 0.5
        if agent.rational_outcomes:
            published = agent._published_opponent_utility(agent.rational_outcomes[0])
            assert agent.estimated_opponent_utility(
                agent.rational_outcomes[0]
            ) == pytest.approx(published)

    def test_early_decoy_suppresses_structural_bluff(self, test_scenario):
        agent = Agent360V3()
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        if not agent.rational_outcomes:
            pytest.skip("no rational outcomes")

        decoy_a = agent.rational_outcomes[0]
        decoy_b = agent.rational_outcomes[min(1, len(agent.rational_outcomes) - 1)]
        agent._opponent_offer_history = [
            (0.05, decoy_a),
            (0.10, decoy_b),
            (0.15, decoy_a),
            (0.20, decoy_b),
            (0.25, decoy_a),
        ]
        traj = agent.offer_trajectory_model
        assert traj is not None
        for t, u in [(0.05, 0.8), (0.15, 0.4), (0.25, 0.85), (0.35, 0.35)]:
            traj.record(t, u)
        assert agent._opponent_early_decoy_persona()
        assert agent._opponent_shows_concealment_tactics()
        assert agent._opponent_mode() == "deceptive"

    def test_honest_concession_zero_bluff(self):
        agent = Agent360V3()
        traj = OfferTrajectoryModel()
        for t, u in [(0.1, 0.9), (0.3, 0.7), (0.5, 0.5), (0.7, 0.3)]:
            traj.record(t, u)
        agent.offer_trajectory_model = traj
        assert agent.current_bluff_score() == 0.0

    def test_mirror_detection_zeros_bluff(self, test_scenario):
        agent = Agent360V3()
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()
        if len(agent.rational_outcomes) >= 4:
            bids = agent.rational_outcomes[:4]
            agent._recent_own_bids = list(bids)
            agent._opponent_recent_offers = list(bids)
            traj = agent.offer_trajectory_model
            assert traj is not None
            for t, u in [(0.1, 0.3), (0.2, 0.7), (0.3, 0.4), (0.4, 0.85)]:
                traj.record(t, u)
            assert agent.current_bluff_score() == 0.0

    def test_opponent_ufun_uses_published_blend(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=20)
        agent = Agent360V3()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()
        opp_ufun = agent.private_info.get("opponent_ufun")
        assert opp_ufun is not None
        if agent.rational_outcomes:
            offer = agent.rational_outcomes[0]
            assert float(opp_ufun(offer)) == pytest.approx(
                agent._published_opponent_utility(offer)
            )

    def test_recency_blend_weights_recent_offers(self):
        model = FrequencyOpponentModel(2)
        model.record_opponent_offer((0, 0))
        model.record_opponent_offer((0, 0))
        model.record_opponent_offer((1, 1))
        blended = RecencyBlendedSmith(model, window=3)
        for offer in [(0, 0), (1, 1), (1, 1)]:
            blended.record(offer)
        full_score = model.estimated_opponent_utility((1, 1))
        recent_score = blended.estimated((1, 1))
        assert recent_score >= full_score

    def test_conceding_mode_detected(self):
        agent = Agent360V3()
        traj = OfferTrajectoryModel()
        for t, u in [(0.1, 0.9), (0.3, 0.7), (0.5, 0.5), (0.7, 0.3)]:
            traj.record(t, u)
        agent.offer_trajectory_model = traj
        assert agent._opponent_mode() == "conceding"

    def test_timed_model_weights_late_offers(self):
        timed = TimedOpponentModel(2, late_time_threshold=0.4, late_bid_weight=3)
        timed.record(0.1, (0, 0))
        timed.record(0.2, (0, 0))
        timed.record(0.5, (1, 1))
        timed.record(0.6, (1, 1))
        assert timed.late_count() == 2
        assert timed.late_phase_estimated((1, 1)) == pytest.approx(1.0)

    def test_issue_weighted_prefers_negotiated_issue(self):
        offers = [(0, 9), (1, 9), (2, 9), (3, 9), (4, 9)]
        score_match = issue_weighted_smith_estimate(offers, (4, 9), num_issues=2)
        score_miss = issue_weighted_smith_estimate(offers, (9, 9), num_issues=2)
        assert score_match > score_miss

    def test_smith_learner_not_classified_deceptive(self):
        agent = Agent360V3()
        agent._opponent_recent_offers = [(0, 0), (0, 0), (0, 0), (0, 0), (0, 0)]
        agent._opponent_offer_history = [
            (0.45 + 0.03 * i, o) for i, o in enumerate(agent._opponent_recent_offers)
        ]
        traj = OfferTrajectoryModel()
        for t, u in [(0.5, 0.6), (0.6, 0.58), (0.7, 0.55), (0.8, 0.52)]:
            traj.record(t, u)
        agent.offer_trajectory_model = traj
        assert agent._opponent_smith_learner_profile()
        assert agent._opponent_mode() == "learner"
        timed = TimedOpponentModel(2, late_time_threshold=0.4, late_bid_weight=3)
        timed.record(0.1, (0, 0))
        timed.record(0.2, (0, 0))
        timed.record(0.5, (1, 1))
        timed.record(0.6, (1, 1))
        assert timed.late_count() == 2
        assert timed.late_phase_estimated((1, 1)) == pytest.approx(1.0)

    def test_first_seat_decoy_rotation(self, test_scenario):
        agent = Agent360V3()
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()
        if len(agent.decoy_outcomes) >= 2:
            rng = __import__("random").Random(0)
            first = agent._pick_decoy_bid(rng)
            agent._record_own_bid(first)
            second = agent._pick_decoy_bid(rng)
            assert second != first or len(agent.decoy_outcomes) == 1

    def test_acceptance_vetoes_bait_before_deadline(self, monkeypatch, test_scenario):
        agent = Agent360V3()
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=10)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()
        if not agent.rational_outcomes:
            pytest.skip("no rational outcomes")

        traj = OfferTrajectoryModel()
        for t, u in [(0.1, 0.3), (0.2, 0.7), (0.3, 0.4), (0.4, 0.35)]:
            traj.record(t, u)
        agent.offer_trajectory_model = traj
        agent._opponent_offer_history = [
            (0.05, agent.rational_outcomes[0]),
            (0.10, agent.rational_outcomes[min(1, len(agent.rational_outcomes) - 1)]),
            (0.15, agent.rational_outcomes[0]),
        ]

        from negmas.sao import SAOState

        bait_offer = agent.rational_outcomes[0]
        state = SAOState(relative_time=0.8, step=50, current_offer=bait_offer)
        monkeypatch.setattr(Agent360V2, "acceptance_strategy", lambda self, s: True)
        monkeypatch.setattr(agent, "_partner_offer_looks_like_bait", lambda s: True)
        assert not agent.acceptance_strategy(state)
        state_late = SAOState(relative_time=0.95, step=90, current_offer=bait_offer)
        assert agent.acceptance_strategy(state_late)
