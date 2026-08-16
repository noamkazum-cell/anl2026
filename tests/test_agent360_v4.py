"""Tests for Agent360V4."""

import pytest
from negmas.inout import Scenario
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from drafts.agent360_submit import Agent360 as Agent360V3
from agent360_FINAL import Agent360, OfferTrajectoryModel, __version__
from drafts.agent360_v2 import Agent360V2
from drafts.agent360_v4 import Agent360V4


@pytest.fixture
def test_scenario():
    ufuns = generate_multi_issue_ufuns(
        n_issues=2,
        n_values=(3, 5),
        ufun_names=("First", "Second"),
        rational_fractions=[1.0, 1.0],
    )
    return Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns)


class TestAgent360V4:
    def test_instantiation(self):
        assert Agent360V4() is not None

    def test_is_v4_submission_class(self):
        assert Agent360V4 is Agent360

    def test_relaxed_bait_constants(self):
        agent = Agent360V4()
        assert agent.BAIT_THRESHOLD > Agent360V3.BAIT_THRESHOLD
        assert agent.BAIT_DISCOUNT < Agent360V3.BAIT_DISCOUNT
        assert agent.BAIT_MIN_TRAJECTORY_SAMPLES > Agent360V3.MIN_TRAJECTORY_SAMPLES

    def test_mode_closing_caps(self):
        agent = Agent360V4()
        assert agent.CLOSING_CAP_CONCEDING > agent.CLOSING_CAP_DECEPTIVE
        assert agent.CLOSING_CAP_DECEPTIVE < Agent360V3.CLOSING_OPPONENT_WEIGHT_CAP

    def test_v46_submission_version(self):
        assert __version__ == "4.6.0"

    def test_v46_tournament_hardening(self):
        agent = Agent360V4()
        assert agent.FIRST_MIN_OPPONENT_OFFERS == 4
        assert agent.FIRST_DECOY_PHASE_END == 0.40
        assert agent.ACCEPT_CATASTROPHE_TIME == 0.95
        assert agent.ACCEPT_DEADLINE_SAFE == 0.90
        assert not hasattr(agent, "ACCEPT_STALL_TIME")
        assert agent.CLOSING_CAP_LEARNER > 0.45
        assert agent.ASPIRATION_SLOPE_CONCEDING < agent.ASPIRATION_SLOPE_DEFAULT
        assert agent.FIRST_LATE_BLEND_MAX > 0.62

    def test_conceding_early_exit_allows_transition(self):
        agent = Agent360V4()
        agent.negotiation_seat = 1
        agent._opponent_offer_count = 1
        agent.offer_trajectory_model = OfferTrajectoryModel()
        for t, u in [(0.1, 0.9), (0.2, 0.75), (0.3, 0.6)]:
            agent.offer_trajectory_model.record(t, u)
        assert agent._opponent_conceding_early_exit()
        assert agent.transition_allowed()

    def test_first_seat_conceding_early_exit_allowed(self):
        agent = Agent360V4()
        agent.negotiation_seat = 0
        agent._opponent_offer_count = 1
        agent.offer_trajectory_model = OfferTrajectoryModel()
        for t, u in [(0.1, 0.9), (0.2, 0.75), (0.3, 0.6)]:
            agent.offer_trajectory_model.record(t, u)
        assert agent._opponent_conceding_early_exit()
        assert agent.transition_allowed()

    def test_negotiation_completes_vs_boa(self, test_scenario):
        from examples.boa import BOANeg

        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V4()
        opponent = BOANeg()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_negotiation_completes_vs_conceder(self, test_scenario):
        from negmas.sao import ConcederTBNegotiator

        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V4()
        opponent = ConcederTBNegotiator()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_vs_v2_completes(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V4()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout
