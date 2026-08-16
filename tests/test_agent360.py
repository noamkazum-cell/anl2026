"""Tests for the V1 gradient agent (Agent360Base)."""

import pytest
from negmas.inout import Scenario
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from drafts.agent360 import Agent360Base


@pytest.fixture
def test_scenario():
    """Create a simple test scenario with two issues."""
    ufuns = generate_multi_issue_ufuns(
        n_issues=2,
        n_values=(3, 5),
        ufun_names=("First", "Second"),
        rational_fractions=[1.0, 1.0],
    )
    return Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns)


class TestAgent360Base:
    """Tests for Agent360Base (V1 gradient decoy baseline)."""

    def test_instantiation(self):
        """Test that Agent360Base can be instantiated."""
        negotiator = Agent360Base()
        assert negotiator is not None

    def test_has_required_methods(self):
        """Test that Agent360Base exposes the SAOCallNegotiator strategy hooks."""
        negotiator = Agent360Base()
        assert callable(negotiator.acceptance_strategy)
        assert callable(negotiator.concealing_bidding_strategy)
        assert callable(negotiator.update_opponent_model)

    def test_opponent_model_initialized(self, test_scenario):
        """Test that opponent_ufun is set after preferences are attached."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=5,
        )
        negotiator = Agent360Base()
        opponent = Agent360Base()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()

        assert negotiator.private_info.get("opponent_ufun") is not None
        assert len(negotiator.rational_outcomes) > 0

    def test_negotiation_completes(self, test_scenario):
        """Test that Agent360Base can complete a negotiation."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = Agent360Base()
        negotiator2 = Agent360Base()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_makes_offers(self, test_scenario):
        """Test that Agent360Base makes valid offers."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=10,
        )
        negotiator = Agent360Base()
        opponent = Agent360Base()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        mechanism.run()

        assert len(mechanism.history) > 0

    def test_negotiation_with_different_opponents(self, test_scenario):
        """Test that Agent360Base can negotiate with different types of opponents."""
        from examples.simple import SimpleNegotiator
        from examples.map import MAPNeg

        mechanism1 = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = Agent360Base()
        opponent1 = SimpleNegotiator()

        mechanism1.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism1.add(opponent1, ufun=test_scenario.ufuns[1])

        mechanism1.run()
        assert mechanism1.state.agreement is not None or mechanism1.state.timedout

        mechanism2 = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator2 = Agent360Base()
        opponent2 = MAPNeg()

        mechanism2.add(negotiator2, ufun=test_scenario.ufuns[0])
        mechanism2.add(opponent2, ufun=test_scenario.ufuns[1])

        mechanism2.run()
        assert mechanism2.state.agreement is not None or mechanism2.state.timedout

    def test_negotiation_on_multiple_scenarios(self, test_scenario):
        """Test that Agent360Base works on scenarios with different numbers of issues."""
        ufuns1 = generate_multi_issue_ufuns(
            n_issues=1,
            n_values=(3, 5),
            ufun_names=("First", "Second"),
            rational_fractions=[1.0, 1.0],
        )
        scenario1 = Scenario(outcome_space=ufuns1[0].outcome_space, ufuns=ufuns1)

        mechanism1 = SAOMechanism(
            outcome_space=scenario1.outcome_space,
            n_steps=50,
        )
        negotiator1a = Agent360Base()
        negotiator1b = Agent360Base()

        mechanism1.add(negotiator1a, ufun=scenario1.ufuns[0])
        mechanism1.add(negotiator1b, ufun=scenario1.ufuns[1])

        mechanism1.run()
        assert mechanism1.state.agreement is not None or mechanism1.state.timedout

        ufuns4 = generate_multi_issue_ufuns(
            n_issues=4,
            n_values=(3, 5),
            ufun_names=("First", "Second"),
            rational_fractions=[1.0, 1.0],
        )
        scenario4 = Scenario(outcome_space=ufuns4[0].outcome_space, ufuns=ufuns4)

        mechanism4 = SAOMechanism(
            outcome_space=scenario4.outcome_space,
            n_steps=50,
        )
        negotiator4a = Agent360Base()
        negotiator4b = Agent360Base()

        mechanism4.add(negotiator4a, ufun=scenario4.ufuns[0])
        mechanism4.add(negotiator4b, ufun=scenario4.ufuns[1])

        mechanism4.run()
        assert mechanism4.state.agreement is not None or mechanism4.state.timedout

    def test_agreement_is_valid(self, test_scenario):
        """Test that agreements reached by Agent360Base are valid outcomes."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = Agent360Base()
        negotiator2 = Agent360Base()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()

        if mechanism.state.agreement is not None:
            assert mechanism.state.agreement in test_scenario.outcome_space.enumerate()
