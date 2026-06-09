#!/usr/bin/env python3
"""Stress-test agent vs non-deceptive NegMAS baselines (weird opponents).

Complements eval_sparring.py (deceptive sparring + learners). Use before submission
to catch regressions vs time-based, behavioral, and noisy negotiators.

Usage:
  uv run python scripts/eval_stress.py --agent v3
  uv run python scripts/eval_stress.py --agent v3 --agent v2 --repeats 2 -o results/stress_v3.csv
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

from agent360_submit import Agent360
from agent360_v2 import Agent360V2
from agent360_v4 import Agent360V4
from agent360_v4_2 import Agent360V42
from compare_decoy_agents import AgentSpec, run_panel_match
from evaluate_noamneg import OpponentSpec, list_scenario_names

app = typer.Typer(help="Stress panel: time-based, behavioral, hybrid, random")
console = Console()

AGENTS: dict[str, AgentSpec] = {
    "v2": AgentSpec(Agent360V2, "v2", "Agent360V2 (V2.4)"),
    "v3": AgentSpec(Agent360, "v3", "Agent360 (submission)"),
    "v4": AgentSpec(Agent360V4, "v4.3", "Agent360 V4.3 (submission)"),
    "v4.2": AgentSpec(Agent360V42, "v4.2", "Agent360 V4.2"),
}

# NegMAS styles outside decoy/bait/Smith cluster
STRESS_OPPONENTS: list[OpponentSpec] = [
    OpponentSpec("negmas.sao.BoulwareTBNegotiator", "slow time conceder", "time-based"),
    OpponentSpec("negmas.sao.ConcederTBNegotiator", "fast time conceder", "time-based"),
    OpponentSpec("negmas.sao.LinearTBNegotiator", "linear time conceder", "time-based"),
    OpponentSpec("negmas.sao.ToughNegotiator", "hard line", "time-based"),
    OpponentSpec("negmas.sao.TimeBasedNegotiator", "generic time-based", "time-based"),
    OpponentSpec("negmas.sao.AspirationNegotiator", "aspiration-based", "time-based"),
    OpponentSpec("negmas.sao.HybridNegotiator", "hybrid", "hybrid"),
    OpponentSpec("negmas.sao.RandomNegotiator", "random rational", "baseline"),
    OpponentSpec("negmas.sao.NaiveTitForTatNegotiator", "tit-for-tat", "behavioral"),
    OpponentSpec("negmas.sao.SimpleTitForTatNegotiator", "simple tit-for-tat", "behavioral"),
    OpponentSpec("negmas.sao.FirstOfferOrientedTBNegotiator", "first-offer anchor", "oriented"),
    OpponentSpec("negmas.sao.LastOfferOrientedTBNegotiator", "last-offer follow", "oriented"),
]


@dataclass(frozen=True)
class Summary:
    n: int
    advantage: float
    concealing: float
    score: float


def _summarize(rows: list[dict]) -> Summary:
    if not rows:
        return Summary(0, 0.0, 0.0, 0.0)
    n = len(rows)
    return Summary(
        n=n,
        advantage=sum(float(r["advantage"]) for r in rows) / n,
        concealing=sum(float(r["concealing"]) for r in rows) / n,
        score=sum(float(r["score"]) for r in rows) / n,
    )


@app.command()
def main(
    agent: list[str] = typer.Option(
        ["v3"],
        "--agent",
        "-a",
        help=f"Agent(s): {', '.join(AGENTS)}",
    ),
    scenario: list[str] | None = typer.Option(
        None, "--scenario", "-s", help="Scenario name(s); default all"
    ),
    repeats: int = typer.Option(2, "--repeats", "-r"),
    steps: int = typer.Option(100, "--steps"),
    output: Path | None = typer.Option(None, "--output", "-o"),
):
    """Run stress panel and print mean Score / Advantage / Concealing."""
    specs = []
    for name in agent:
        if name not in AGENTS:
            console.print(f"[red]Unknown agent[/red] {name!r}")
            raise typer.Exit(1)
        specs.append(AGENTS[name])

    scenario_names = scenario if scenario else list_scenario_names()
    total_runs = (
        len(specs) * len(STRESS_OPPONENTS) * len(scenario_names) * 2 * repeats
    )
    console.print(
        f"[bold]Stress panel[/bold]: {len(STRESS_OPPONENTS)} opponents x "
        f"{len(scenario_names)} scenarios x 2 roles x {repeats} repeats x "
        f"{len(specs)} agent(s) ({total_runs} runs)"
    )

    all_rows: list[dict] = []
    for agent_spec in specs:
        rows: list[dict] = []
        for scenario_name in scenario_names:
            for opp in STRESS_OPPONENTS:
                for agent_first in (True, False):
                    role = "first" if agent_first else "second"
                    totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
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
                                f"[red]Failed[/red] {agent_spec.mode} "
                                f"{scenario_name} vs {opp.class_path.split('.')[-1]} "
                                f"({role}): {exc}"
                            )
                            result = None
                        if result:
                            for k in totals:
                                totals[k] += result[k]
                            ok += 1
                    if ok == 0:
                        continue
                    mean = {k: totals[k] / ok for k in totals}
                    row = {
                        "agent_mode": agent_spec.mode,
                        "panel": "stress",
                        "group": "baseline",
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
                    all_rows.append(row)

        if not rows:
            console.print(f"[yellow]No runs for {agent_spec.label}[/yellow]")
            continue

        summary = _summarize(rows)
        table = Table(title=f"Stress — {agent_spec.label} (n={summary.n})")
        table.add_column("scenario")
        table.add_column("opponent")
        table.add_column("role")
        table.add_column("score")
        table.add_column("advantage")
        table.add_column("concealing")
        for row in sorted(rows, key=lambda r: r["score"])[:8]:
            table.add_row(
                row["scenario"],
                row["opponent"],
                row["agent_first"],
                f"{row['score']:.3f}",
                f"{row['advantage']:.3f}",
                f"{row['concealing']:.3f}",
            )
        console.print(table)
        console.print(
            f"[bold]{agent_spec.mode} mean[/bold]  score={summary.score:.3f}  "
            f"advantage={summary.advantage:.3f}  concealing={summary.concealing:.3f}"
        )
        worst = min(rows, key=lambda r: r["score"])
        console.print(
            f"  worst: {worst['scenario']} x {worst['opponent']} "
            f"{worst['agent_first']} score={worst['score']:.3f}"
        )

    if len(specs) == 2 and all_rows:
        v2 = [r for r in all_rows if r["agent_mode"] == "v2"]
        v3 = [r for r in all_rows if r["agent_mode"] == "v3"]
        if v2 and v3:
            s2, s3 = _summarize(v2), _summarize(v3)
            console.print(
                f"\n[bold]V3 vs V2.4 stress delta[/bold]  score {s3.score - s2.score:+.3f}  "
                f"advantage {s3.advantage - s2.advantage:+.3f}  "
                f"concealing {s3.concealing - s2.concealing:+.3f}"
            )

    if output and all_rows:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)
        console.print(f"\nWrote [green]{output}[/green]")


if __name__ == "__main__":
    app()
