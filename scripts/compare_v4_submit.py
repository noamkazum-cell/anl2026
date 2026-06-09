#!/usr/bin/env python3
"""Head-to-head V4.2 vs V4.3 (and optional V3) on tournament proxy panels.

Usage:
  uv run python scripts/compare_v4_submit.py
  uv run python scripts/compare_v4_submit.py --repeats 3 -o results/v4_compare.csv
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

from agent360_submit import Agent360 as Agent360V3
from agent360_v4 import Agent360V4
from agent360_v4_2 import Agent360V42
from compare_decoy_agents import AgentSpec, run_panel_match
from evaluate_noamneg import FULL_OPPONENTS, OpponentSpec, list_scenario_names
from eval_stress import STRESS_OPPONENTS
from sparring import SPARRING_OPPONENTS, sparring_opponent_kwargs

app = typer.Typer(help="Compare V4.2 vs V4.3 submission candidates")
console = Console()

LEARNER_PATHS = {
    "examples.boa.BOANeg",
    "examples.map.MAPNeg",
    "negmas.sao.MiCRONegotiator",
}

AGENTS: dict[str, AgentSpec] = {
    "v3": AgentSpec(Agent360V3, "v3", "V3 (submitted 0.0.4)"),
    "v4.2": AgentSpec(Agent360V42, "v4.2", "V4.2"),
    "v4.3": AgentSpec(Agent360V4, "v4.3", "V4.3 (current)"),
}


@dataclass(frozen=True)
class Panel:
    name: str
    opponents: list[OpponentSpec]
    kwargs_fn: object | None = None


def _learner_panel() -> Panel:
    opps = [o for o in FULL_OPPONENTS if o.class_path in LEARNER_PATHS]
    return Panel("learners", opps)


def _stress_panel() -> Panel:
    return Panel("stress", STRESS_OPPONENTS)


def _sparring_panel() -> Panel:
    opps = [
        OpponentSpec(path, label, family)
        for path, label, family in SPARRING_OPPONENTS
    ]
    return Panel("sparring", opps, sparring_opponent_kwargs)


def _run_panel(
    panel: Panel,
    agent_spec: AgentSpec,
    scenario_names: list[str],
    repeats: int,
    steps: int,
) -> list[dict]:
    rows: list[dict] = []
    for scenario_name in scenario_names:
        for opp in panel.opponents:
            for agent_first in (True, False):
                role = "first" if agent_first else "second"
                totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
                ok = 0
                for _ in range(repeats):
                    kwargs = {}
                    if panel.kwargs_fn is not None:
                        kwargs = panel.kwargs_fn(opp.class_path)
                    try:
                        result = run_panel_match(
                            scenario_name,
                            agent_spec,
                            opp,
                            n_steps=steps,
                            agent_goes_first=agent_first,
                            opponent_kwargs=kwargs,
                        )
                    except Exception as exc:
                        console.print(
                            f"[red]fail[/red] {agent_spec.mode} {panel.name} "
                            f"{scenario_name} vs {opp.class_path.split('.')[-1]} ({role}): {exc}"
                        )
                        result = None
                    if result:
                        for k in totals:
                            totals[k] += result[k]
                        ok += 1
                if ok == 0:
                    continue
                mean = {k: totals[k] / ok for k in totals}
                rows.append(
                    {
                        "panel": panel.name,
                        "agent": agent_spec.mode,
                        "scenario": scenario_name,
                        "opponent": opp.class_path.split(".")[-1],
                        "role": role,
                        "advantage": mean["Advantage"],
                        "concealing": mean["Concealing"],
                        "score": mean["Score"],
                    }
                )
    return rows


def _summarize(rows: list[dict], *, panel: str | None = None, agent: str | None = None) -> dict:
    filtered = rows
    if panel:
        filtered = [r for r in filtered if r["panel"] == panel]
    if agent:
        filtered = [r for r in filtered if r["agent"] == agent]
    if not filtered:
        return {"n": 0, "advantage": 0.0, "concealing": 0.0, "score": 0.0}
    n = len(filtered)
    return {
        "n": n,
        "advantage": sum(float(r["advantage"]) for r in filtered) / n,
        "concealing": sum(float(r["concealing"]) for r in filtered) / n,
        "score": sum(float(r["score"]) for r in filtered) / n,
    }


@app.command()
def main(
    agents: list[str] = typer.Option(
        ["v4.2", "v4.3"],
        "--agent",
        "-a",
        help=f"Agents: {', '.join(AGENTS)}",
    ),
    repeats: int = typer.Option(3, "--repeats", "-r"),
    steps: int = typer.Option(100, "--steps"),
    include_v3: bool = typer.Option(False, "--include-v3"),
    output: Path | None = typer.Option(None, "--output", "-o"),
):
    """Run learners + stress + sparring panels and pick the stronger submission."""
    names = list(agents)
    if include_v3 and "v3" not in names:
        names.append("v3")
    for name in names:
        if name not in AGENTS:
            console.print(f"[red]Unknown agent[/red] {name!r}")
            raise typer.Exit(1)

    scenario_names = list_scenario_names()
    panels = [_learner_panel(), _stress_panel(), _sparring_panel()]
    all_rows: list[dict] = []

    for panel in panels:
        console.print(f"\n[bold]Panel: {panel.name}[/bold] ({len(panel.opponents)} opponents)")
        for name in names:
            spec = AGENTS[name]
            console.print(f"  running {spec.label} ...")
            all_rows.extend(_run_panel(panel, spec, scenario_names, repeats, steps))

    table = Table(title=f"V4 submit comparison (repeats={repeats})")
    table.add_column("Panel")
    table.add_column("Agent")
    table.add_column("Cells", justify="right")
    table.add_column("Advantage", justify="right")
    table.add_column("Concealing", justify="right")
    table.add_column("Score", justify="right")

    for panel in panels:
        for name in names:
            s = _summarize(all_rows, panel=panel.name, agent=AGENTS[name].mode)
            table.add_row(
                panel.name,
                AGENTS[name].label,
                str(s["n"]),
                f"{s['advantage']:.3f}",
                f"{s['concealing']:.3f}",
                f"{s['score']:.3f}",
            )

    overall: dict[str, dict] = {}
    for name in names:
        overall[name] = _summarize(all_rows, agent=AGENTS[name].mode)

    table.add_section()
    for name in names:
        s = overall[name]
        table.add_row(
            "ALL",
            AGENTS[name].label,
            str(s["n"]),
            f"{s['advantage']:.3f}",
            f"{s['concealing']:.3f}",
            f"{s['score']:.3f}",
        )
    console.print(table)

    ranked = sorted(names, key=lambda n: overall[n]["score"], reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    delta = 0.0
    if second:
        delta = overall[best]["score"] - overall[second]["score"]
    console.print(
        f"\n[bold green]Recommend upload:[/bold green] {AGENTS[best].label} "
        f"(mean score {overall[best]['score']:.3f}"
        + (f", +{delta:.3f} vs {AGENTS[second].label}" if second else "")
        + ")"
    )

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "panel",
                    "agent",
                    "scenario",
                    "opponent",
                    "role",
                    "advantage",
                    "concealing",
                    "score",
                ],
            )
            writer.writeheader()
            writer.writerows(all_rows)
        console.print(f"Wrote {output}")


if __name__ == "__main__":
    app()
