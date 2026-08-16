"""Tests for deceptive sparring opponents."""

import pytest
from negmas.inout import Scenario
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from drafts.agent360_v2 import Agent360V2
from sparring.decoy_persona import DecoyPersona
from sparring.renting_lite import RentingLite
from sparring.shochan_lite import ShochanLite
from sparring.uoagent_lite import UOAgentLite


@pytest.fixture
def test_scenario():
    ufuns = generate_multi_issue_ufuns(
        n_issues=2,
        n_values=(4, 4),
        ufun_names=("First", "Second"),
        rational_fractions=[1.0, 1.0],
    )
    return Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns)


class TestDecoyPersona:
    def test_builds_decoys(self, test_scenario):
        persona = DecoyPersona()
        ufun = test_scenario.ufuns[0]
        rational = tuple(test_scenario.outcome_space.enumerate_or_sample())
        persona.build(ufun, rational)
        assert len(persona.decoys) >= 1

    def test_early_phase_uses_decoy(self, test_scenario):
        persona = DecoyPersona()
        ufun = test_scenario.ufuns[0]
        rational = tuple(test_scenario.outcome_space.enumerate_or_sample())
        persona.build(ufun, rational)
        honest = rational[0]
        picks = {
            persona.wrap(0.1, "a", i, lambda: honest)
            for i in range(20)
        }
        assert picks.issubset(set(persona.decoys))


class TestDeceptiveSparring:
    @pytest.mark.parametrize(
        "opponent_cls",
        [ShochanLite, UOAgentLite, RentingLite],
    )
    def test_deceptive_negotiation_completes(self, test_scenario, opponent_cls):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=30)
        agent = Agent360V2()
        opponent = opponent_cls(deceptive=True)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_honest_mode_available(self, test_scenario):
        mechanism = SAOMechanism(outcome_space=test_scenario.outcome_space, n_steps=20)
        agent = Agent360V2()
        opponent = ShochanLite(deceptive=False)
        mechanism.add(agent, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])
        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout
