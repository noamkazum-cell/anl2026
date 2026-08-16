"""Tests for Agent360V2."""

import pytest
from negmas.inout import Scenario
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from drafts.agent360 import Agent360Base
from drafts.agent360_v2 import (
    Agent360V2,
    Agent360V2_5,
    Agent360V2Adaptive,
    Agent360V2FirstSeat,
    Agent360V2FirstSeatMinOffers,
    Agent360V2FirstSeatRotate,
)


@pytest.fixture
def test_scenario():
    ufuns = generate_multi_issue_ufuns(
        n_issues=2,
        n_values=(3, 5),
        ufun_names=("First", "Second"),
        rational_fractions=[1.0, 1.0],
    )
    return Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns)


class TestAgent360V2:
    def test_instantiation(self):
        assert Agent360V2() is not None

    def test_pools_initialized(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert len(agent.rational_outcomes) > 0
        assert len(agent.decoy_outcomes) > 0

    def test_negotiation_completes(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V2()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_vs_boa_completes(self, test_scenario):
        from examples.boa import BOANeg

        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V2()
        opponent = BOANeg()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_v24_first_seat_min_offers_gate(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.is_first_negotiator()
        assert agent.FIRST_MIN_OPPONENT_OFFERS == 3
        agent._opponent_offer_count = 0
        assert not agent.transition_allowed()
        agent._opponent_offer_count = 3
        assert agent.transition_allowed()

    def test_second_seat_no_min_offers_gate(self, test_scenario):
        from examples.boa import BOANeg

        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2()
        mechanism.add(BOANeg(), ufun=test_scenario.ufuns[0])
        mechanism.add(agent, ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert not agent.is_first_negotiator()
        agent._opponent_offer_count = 0
        assert agent.transition_allowed()

    def test_v24_fixed_phase_boundaries(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.decoy_phase_end() == Agent360Base.DECOY_PHASE_END
        assert agent.transition_phase_end() == Agent360Base.TRANSITION_PHASE_END

    def test_maximal_mismatch_decoy_pool(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=3)
        agent = Agent360V2()
        gradient = Agent360Base()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(gradient, ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.decoy_outcomes
        assert len(agent.decoy_outcomes) <= len(agent.rational_outcomes)


class TestAgent360V2Adaptive:
    def test_seat_detection_first_and_second(self, test_scenario):
        from examples.boa import BOANeg

        for probe_first in (True, False):
            mechanism = SAOMechanism(
                outcome_space=test_scenario.outcome_space, n_steps=5
            )
            agent = Agent360V2Adaptive()
            opponent = BOANeg()
            if probe_first:
                mechanism.add(agent, ufun=test_scenario.ufuns[0])
                mechanism.add(opponent, ufun=test_scenario.ufuns[1])
            else:
                mechanism.add(opponent, ufun=test_scenario.ufuns[0])
                mechanism.add(agent, ufun=test_scenario.ufuns[1])
            mechanism.run()

            assert agent.negotiation_seat == (0 if probe_first else 1)
            assert agent.is_first_negotiator() is probe_first
            expected_cap = 0.38 if probe_first else 0.45
            assert agent.effective_closing_opponent_weight_cap() == expected_cap


class TestAgent360V2FirstSeat:
    def test_first_seat_longer_decoy_phase(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2FirstSeat()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.decoy_phase_end() == Agent360V2FirstSeat.FIRST_DECOY_PHASE_END_OVERRIDE

    def test_minoffers_only_keeps_v23_decoy_end(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2FirstSeatMinOffers()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert agent.decoy_phase_end() == Agent360Base.DECOY_PHASE_END
        assert agent.FIRST_MIN_OPPONENT_OFFERS == 3

    def test_rotate_only_no_min_offers_gate(self, test_scenario):
        agent = Agent360V2FirstSeatRotate()
        agent._opponent_offer_count = 0
        assert agent.transition_allowed()

    def test_second_seat_matches_v23_boundaries(self, test_scenario):
        from examples.boa import BOANeg

        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        opponent = BOANeg()
        agent = Agent360V2FirstSeat()
        mechanism.add(opponent, ufun=test_scenario.ufuns[0])
        mechanism.add(agent, ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.decoy_phase_end() == Agent360Base.DECOY_PHASE_END

    def test_first_seat_transition_gated_by_opponent_offers(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.is_first_negotiator()
        agent._opponent_offer_count = 0
        assert not agent.transition_allowed()
        agent._opponent_offer_count = Agent360V2.FIRST_MIN_OPPONENT_OFFERS
        assert agent.transition_allowed()

    def test_negotiation_completes(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V2FirstSeat()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout


class TestAgent360V2_5:
    def test_first_seat_softer_transition(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2_5()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.effective_transition_decoy_mix_until() == 0.85
        assert agent.transition_progress_scale() == 0.72

    def test_second_seat_default_transition(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=5)
        agent = Agent360V2_5()
        mechanism.add(Agent360V2(), ufun=test_scenario.ufuns[0])
        mechanism.add(agent, ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert agent.effective_transition_decoy_mix_until() == Agent360Base.TRANSITION_DECOY_MIX_UNTIL
        assert agent.transition_progress_scale() == 1.0

    def test_negotiation_completes(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=50)
        agent = Agent360V2_5()
        opponent = Agent360V2()
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout
