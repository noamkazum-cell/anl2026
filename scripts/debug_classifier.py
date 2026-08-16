#!/usr/bin/env python3
"""Post-hoc offer-stream stats (analysis only — V2 does not route on these)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import typer
from negmas.helpers import get_class, instantiate
from negmas.inout import Scenario
from negmas.sao import SAOMechanism
from rich.console import Console
from rich.table import Table

from drafts.agent360_v2 import Agent360V2
from main import SCENARIOS_DIR, calc_scores
from drafts.opponent_classifier import OpponentRouter, _pearson_correlation

app = typer.Typer()
console = Console()

OPPONENTS = [
    "examples.boa.BOANeg",
    "examples.map.MAPNeg",
    "negmas.sao.MiCRONegotiator",
    "negmas.sao.ConcederTBNegotiator",
    "negmas.sao.LinearTBNegotiator",
    "negmas.sao.BoulwareTBNegotiator",
]


class _TelemetryAgent(Agent360V2):
    """Records offer-stream stats during negotiation (not used for bidding)."""

    telemetry: OpponentRouter | None = None

    def on_preferences_changed(self, changes):
        super().on_preferences_changed(changes)
        num_issues = len(self.rational_outcomes[0]) if self.rational_outcomes else 0
        self.telemetry = OpponentRouter()
        self.telemetry.reset(num_issues)

    def update_opponent_model(self, state):
        super().update_opponent_model(state)
        partner_offer = state.current_offer
        if (
            partner_offer is None
            or self.telemetry is None
            or self.ufun is None
        ):
            return
        self.telemetry.update(
            partner_offer, state.relative_time, float(self.ufun(partner_offer))
        )


@app.command()
def main(
    scenario: str = typer.Option("Camera", "--scenario", "-s"),
    steps: int = typer.Option(100, "--steps"),
):
    scenario_obj = Scenario.load(SCENARIOS_DIR / scenario, ignore_discount=True)
    if scenario_obj is None:
        raise typer.Exit(1)

    table = Table(title=f"Post-hoc offer stats — {scenario}")
    table.add_column("opponent")
    table.add_column("score")
    table.add_column("conceal")
    table.add_column("offers")
    table.add_column("time_corr")
    table.add_column("concentration")
    table.add_column("if_we_routed")

    for class_path in OPPONENTS:
        mechanism = SAOMechanism(
            outcome_space=scenario_obj.outcome_space, n_steps=steps
        )
        agent = _TelemetryAgent()
        opponent = instantiate(get_class(class_path))
        mechanism.add(agent, ufun=scenario_obj.ufuns[0])
        mechanism.add(opponent, ufun=scenario_obj.ufuns[1])
        mechanism.run()

        tel = agent.telemetry
        tc = _pearson_correlation(
            tel.opponent_times if tel else [],
            tel.my_utilities_on_their_offers if tel else [],
        )
        conc = tel._frequency_concentration() if tel else 0.0
        would = tel.current_mode().value if tel else "—"

        row = calc_scores(mechanism).get(agent.id, {})
        table.add_row(
            class_path.split(".")[-1],
            f"{row.get('Score', 0.0):.3f}",
            f"{row.get('Concealing', 0.0):.3f}",
            str(len(tel.opponent_offers) if tel else 0),
            f"{tc:.3f}",
            f"{conc:.3f}",
            would,
        )

    console.print(table)
    console.print(
        "\n[dim]Agent360V2 uses a fixed persona; if_we_routed is diagnostic only.[/dim]"
    )


if __name__ == "__main__":
    app()
