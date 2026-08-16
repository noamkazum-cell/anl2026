#!/usr/bin/env python3
"""Benchmark submission agent vs in-house sparring opponents (+ optional learners).

Usage:
  uv run python scripts/eval_sparring.py
  uv run python scripts/eval_sparring.py --agent v2 --repeats 3
  uv run python scripts/eval_sparring.py --include-learners --output results/sparring.csv
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import typer
from rich.console import Console
from rich.table import Table

from drafts.agent360 import Agent360Base
from drafts.agent360_submit import Agent360
from drafts.agent360_full import Agent360Full
from drafts.agent360_reverse import Agent360Reverse
from drafts.agent360_v4 import Agent360V4
from drafts.agent360_v4_2 import Agent360V42
from drafts.agent360_v2 import (
    Agent360V2,
    Agent360V2_5,
    Agent360V2Adaptive,
    Agent360V2FirstSeat,
    Agent360V2FirstSeatLongDecoy,
    Agent360V2FirstSeatLongDecoy38,
    Agent360V2FirstSeatMinOffersAblate,
    Agent360V2FirstSeatMinOffersLong38,
    Agent360V2FirstSeatRotate,
)
from compare_decoy_agents import AgentSpec, run_panel_match
from evaluate_noamneg import FULL_OPPONENTS, OpponentSpec, list_scenario_names
from sparring import SPARRING_OPPONENTS, sparring_opponent_kwargs

app = typer.Typer(help="Benchmark agents vs sparring pool")
console = Console()

LEARNER_PATHS = {
    "examples.boa.BOANeg",
    "examples.map.MAPNeg",
    "negmas.sao.MiCRONegotiator",
}

AGENTS: dict[str, AgentSpec] = {
    "gradient": AgentSpec(Agent360Base, "gradient", "Agent360Base (V1 gradient)"),
    "v2": AgentSpec(Agent360V2, "v2", "Agent360V2 (V2.4)"),
    "v3": AgentSpec(Agent360, "v3", "Agent360 (submission)"),
    "v4": AgentSpec(Agent360V4, "v4.5", "Agent360 V4.5 (submission)"),
    "v4.2": AgentSpec(Agent360V42, "v4.2", "Agent360 V4.2"),
    "v2.5": AgentSpec(Agent360V2_5, "v2.5", "Agent360V2_5 (pre-V3 trial)"),
    "v2.firstseat": AgentSpec(
        Agent360V2FirstSeat, "v2.firstseat", "Agent360V2FirstSeat (full combo)"
    ),
    "v2.fs.minoffers": AgentSpec(
        Agent360V2FirstSeatMinOffersAblate,
        "v2.fs.minoffers",
        "FirstSeat: min offers (ablate)",
    ),
    "v2.fs.rotate": AgentSpec(
        Agent360V2FirstSeatRotate, "v2.fs.rotate", "FirstSeat: decoy rotate"
    ),
    "v2.fs.longdecoy": AgentSpec(
        Agent360V2FirstSeatLongDecoy, "v2.fs.longdecoy", "FirstSeat: decoy 0.42"
    ),
    "v2.fs.longdecoy38": AgentSpec(
        Agent360V2FirstSeatLongDecoy38, "v2.fs.longdecoy38", "FirstSeat: decoy 0.38"
    ),
    "v2.fs.min38": AgentSpec(
        Agent360V2FirstSeatMinOffersLong38, "v2.fs.min38", "FirstSeat: min+0.38"
    ),
    "v2.adaptive": AgentSpec(Agent360V2Adaptive, "v2.adaptive", "Agent360V2Adaptive"),
    "full": AgentSpec(Agent360Full, "full", "Agent360Full"),
    "reverse": AgentSpec(Agent360Reverse, "reverse", "Agent360Reverse"),
}


@dataclass(frozen=True)
class PanelOpponent:
    spec: OpponentSpec
    group: str


def _sparring_specs() -> list[PanelOpponent]:
    return [
        PanelOpponent(
            OpponentSpec(
                class_path=path,
                strategy_label=label,
                family=family,
            ),
            "sparring",
        )
        for path, label, family in SPARRING_OPPONENTS
    ]


def _learner_specs() -> list[PanelOpponent]:
    return [
        PanelOpponent(o, "learner")
        for o in FULL_OPPONENTS
        if o.class_path in LEARNER_PATHS
    ]


@app.command()
def main(
    agent: str = typer.Option(
        "v3",
        "--agent",
        "-a",
        help=f"Agent under test: {', '.join(AGENTS)}",
    ),
    scenario: list[str] | None = typer.Option(
        None, "--scenario", "-s", help="Scenario name(s); default all"
    ),
    repeats: int = typer.Option(2, "--repeats", "-r"),
    steps: int = typer.Option(100, "--steps"),
    include_learners: bool = typer.Option(
        False,
        "--include-learners",
        help="Also run BOA / MAP / MiCRO (slower, fuller picture)",
    ),
    panel: str = typer.Option(
        "deceptive",
        "--panel",
        "-p",
        help="Sparring lite opponents: deceptive (decoy+bait, default) or honest",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write CSV here"),
):
    """Run agent vs sparring pool; print mean Score / Advantage / Concealing."""
    if agent not in AGENTS:
        console.print(f"[red]Unknown agent[/red] {agent!r}; choose from {list(AGENTS)}")
        raise typer.Exit(1)
    if panel not in ("deceptive", "honest"):
        console.print(f"[red]Unknown panel[/red] {panel!r}; use deceptive or honest")
        raise typer.Exit(1)

    deceptive = panel == "deceptive"

    agent_spec = AGENTS[agent]
    opponents = _sparring_specs()
    if include_learners:
        opponents = opponents + _learner_specs()

    scenario_names = scenario if scenario else list_scenario_names()
    totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
    group_totals: dict[str, dict[str, float]] = {}
    group_counts: dict[str, int] = {}
    rows: list[dict] = []
    n = 0

    total_configs = (
        len(scenario_names) * len(opponents) * 2 * repeats
    )
    console.print(
        f"Sparring panel ({panel}): {len(opponents)} opponents x {len(scenario_names)} scenarios "
        f"x 2 roles x {repeats} repeats ({total_configs} runs)"
    )

    for scenario_name in scenario_names:
        for panel_opp in opponents:
            opp = panel_opp.spec
            for agent_first in (True, False):
                role = "first" if agent_first else "second"
                run_totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
                ok = 0
                for _ in range(repeats):
                    try:
                        result = run_panel_match(
                            scenario_name,
                            agent_spec,
                            opp,
                            n_steps=steps,
                            agent_goes_first=agent_first,
                            opponent_kwargs=sparring_opponent_kwargs(
                                opp.class_path, deceptive=deceptive
                            ),
                        )
                    except Exception as exc:
                        console.print(
                            f"[red]Failed[/red] {scenario_name} vs "
                            f"{opp.class_path.split('.')[-1]} ({role}): {exc}"
                        )
                        result = None
                    if result:
                        for k in run_totals:
                            run_totals[k] += result[k]
                        ok += 1

                if ok == 0:
                    continue

                mean = {k: run_totals[k] / ok for k in run_totals}
                row = {
                    "agent_mode": agent_spec.mode,
                    "panel": panel,
                    "group": panel_opp.group,
                    "scenario": scenario_name,
                    "opponent": opp.class_path.split(".")[-1],
                    "opponent_class": opp.class_path,
                    "family": opp.family,
                    "agent_first": role,
                    "runs": ok,
                    "advantage": mean["Advantage"],
                    "concealing": mean["Concealing"],
                    "score": mean["Score"],
                }
                rows.append(row)
                for k in totals:
                    totals[k] += mean[k]
                g = panel_opp.group
                bucket = group_totals.setdefault(g, {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0})
                for k in bucket:
                    bucket[k] += mean[k]
                group_counts[g] = group_counts.get(g, 0) + 1
                n += 1

    if n == 0:
        console.print("[yellow]No successful runs[/yellow]")
        raise typer.Exit(1)

    table = Table(title=f"Sparring panel — {agent_spec.label} (n={n} configs)")
    table.add_column("group")
    table.add_column("scenario")
    table.add_column("opponent")
    table.add_column("role")
    table.add_column("advantage")
    table.add_column("concealing")
    table.add_column("score")
    for row in sorted(rows, key=lambda r: -r["score"]):
        table.add_row(
            row["group"],
            row["scenario"],
            row["opponent"],
            row["agent_first"],
            f"{row['advantage']:.3f}",
            f"{row['concealing']:.3f}",
            f"{row['score']:.3f}",
        )
    console.print(table)

    console.print(
        f"\n[bold]Overall mean[/bold]  advantage={totals['Advantage']/n:.3f}  "
        f"concealing={totals['Concealing']/n:.3f}  "
        f"score={totals['Score']/n:.3f}"
    )
    for g in sorted(group_totals):
        c = group_counts[g]
        gt = group_totals[g]
        console.print(
            f"  [bold]{g}[/bold] (n={c})  advantage={gt['Advantage']/c:.3f}  "
            f"concealing={gt['Concealing']/c:.3f}  score={gt['Score']/c:.3f}"
        )

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(rows[0].keys())
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        console.print(f"\nWrote [green]{output}[/green]")


if __name__ == "__main__":
    app()
