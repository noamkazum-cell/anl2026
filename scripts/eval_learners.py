#!/usr/bin/env python3
"""Fast learner-only benchmark (BOA, MAP, MiCRO) for closing/decoy ablations.

Usage:
  uv run python scripts/eval_learners.py
  uv run python scripts/eval_learners.py --repeats 3 --scenario Car
  uv run python scripts/eval_learners.py --agent v2
"""

from __future__ import annotations

import sys
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
from drafts.agent360_v2 import Agent360V2, Agent360V2Adaptive, Agent360V2ClosingA
from drafts.agent360_v4 import Agent360V4
from drafts.agent360_v4_2 import Agent360V42
from compare_decoy_agents import AgentSpec, run_panel_match
from evaluate_noamneg import FULL_OPPONENTS, list_scenario_names

app = typer.Typer(help="Benchmark agents vs BOA/MAP/MiCRO only")
console = Console()

LEARNER_PATHS = {
    "examples.boa.BOANeg",
    "examples.map.MAPNeg",
    "negmas.sao.MiCRONegotiator",
}

AGENTS: dict[str, AgentSpec] = {
    "gradient": AgentSpec(Agent360Base, "gradient", "Agent360Base"),
    "v2": AgentSpec(Agent360V2, "v2", "Agent360V2"),
    "submission": AgentSpec(Agent360, "submission", "Agent360 (submission)"),
    "v4": AgentSpec(Agent360V4, "v4.5", "Agent360 V4.5 (submission)"),
    "v4.2": AgentSpec(Agent360V42, "v4.2", "Agent360 V4.2"),
    "v2.6a": AgentSpec(Agent360V2ClosingA, "v2.6a", "Agent360V2ClosingA"),
    "v2.adaptive": AgentSpec(Agent360V2Adaptive, "v2.adaptive", "Agent360V2Adaptive"),
    "full": AgentSpec(Agent360Full, "full", "Agent360Full"),
}

LEARNER_OPPONENTS = [o for o in FULL_OPPONENTS if o.class_path in LEARNER_PATHS]


@app.command()
def main(
    agent: str = typer.Option(
        "v2",
        "--agent",
        "-a",
        help=f"Agent to test: {', '.join(AGENTS)}",
    ),
    scenario: list[str] | None = typer.Option(
        None, "--scenario", "-s", help="Scenario name(s); default all"
    ),
    repeats: int = typer.Option(2, "--repeats", "-r"),
    steps: int = typer.Option(100, "--steps"),
):
    """Run learner-only panel and print mean Score / Advantage / Concealing."""
    if agent not in AGENTS:
        console.print(f"[red]Unknown agent[/red] {agent!r}; choose from {list(AGENTS)}")
        raise typer.Exit(1)

    agent_spec = AGENTS[agent]
    scenario_names = scenario if scenario else list_scenario_names()
    totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
    rows: list[dict] = []
    n = 0

    for scenario_name in scenario_names:
        for opp in LEARNER_OPPONENTS:
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
                rows.append(
                    {
                        "scenario": scenario_name,
                        "opponent": opp.class_path.split(".")[-1],
                        "role": role,
                        **mean,
                    }
                )
                for k in totals:
                    totals[k] += mean[k]
                n += 1

    if n == 0:
        console.print("[yellow]No successful runs[/yellow]")
        raise typer.Exit(1)

    table = Table(title=f"Learner panel — {agent_spec.label} (n={n} configs)")
    table.add_column("scenario")
    table.add_column("opponent")
    table.add_column("role")
    table.add_column("advantage")
    table.add_column("concealing")
    table.add_column("score")
    for row in sorted(rows, key=lambda r: -r["Score"]):
        table.add_row(
            row["scenario"],
            row["opponent"],
            row["role"],
            f"{row['Advantage']:.3f}",
            f"{row['Concealing']:.3f}",
            f"{row['Score']:.3f}",
        )
    console.print(table)
    console.print(
        f"\n[bold]Mean[/bold]  advantage={totals['Advantage']/n:.3f}  "
        f"concealing={totals['Concealing']/n:.3f}  "
        f"score={totals['Score']/n:.3f}"
    )


if __name__ == "__main__":
    app()
