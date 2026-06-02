#!/usr/bin/env python3
"""
Benchmark Agent360 against tutorial examples and NegMAS built-in negotiators.

Usage:
  uv run python scripts/evaluate_noamneg.py
  uv run python scripts/evaluate_noamneg.py --quick
  uv run python scripts/evaluate_noamneg.py --scenario Camera --repeats 3
  uv run python scripts/evaluate_noamneg.py --output results/benchmark.csv
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import typer
from negmas.helpers import get_class, instantiate
from negmas.inout import Scenario
from negmas.sao import SAOMechanism
from rich.console import Console
from rich.table import Table

from main import SCENARIOS_DIR, calc_scores
from agent360 import Agent360

app = typer.Typer(help="Benchmark Agent360 vs NegMAS and example opponents")
console = Console()


@dataclass(frozen=True)
class OpponentSpec:
    """One opponent class plus a short strategy label for the report."""

    class_path: str
    strategy_label: str
    family: str  # e.g. "example", "time-based", "genius-style"


# Tutorial + representative NegMAS SAO negotiators (see negmas.sao exports)
QUICK_OPPONENTS: list[OpponentSpec] = [
    OpponentSpec("examples.simple.SimpleNegotiator", "reverse-ufun + time concede", "example"),
    OpponentSpec("examples.boa.BOANeg", "BOA: time offer + Smith + ACNext", "example"),
    OpponentSpec("examples.map.MAPNeg", "MAP: same stack, acceptance_first", "example"),
    OpponentSpec("negmas.sao.BoulwareTBNegotiator", "slow concession (Boulware)", "time-based"),
    OpponentSpec("negmas.sao.ConcederTBNegotiator", "fast concession", "time-based"),
    OpponentSpec("negmas.sao.LinearTBNegotiator", "linear time concession", "time-based"),
    OpponentSpec("negmas.sao.ToughNegotiator", "hard line, slow give", "time-based"),
    OpponentSpec("negmas.sao.MiCRONegotiator", "MiCRO (Genius-style)", "genius-style"),
]

FULL_OPPONENTS: list[OpponentSpec] = QUICK_OPPONENTS + [
    OpponentSpec("negmas.sao.TimeBasedNegotiator", "generic time-based", "time-based"),
    OpponentSpec("negmas.sao.AspirationNegotiator", "aspiration-based", "time-based"),
    OpponentSpec("negmas.sao.UtilBasedNegotiator", "utility-based offers", "utility-based"),
    OpponentSpec("negmas.sao.HybridNegotiator", "hybrid time + utility", "hybrid"),
    OpponentSpec("negmas.sao.RandomNegotiator", "random rational offers", "baseline"),
    OpponentSpec("negmas.sao.NaiveTitForTatNegotiator", "tit-for-tat", "behavioral"),
    OpponentSpec("negmas.sao.SimpleTitForTatNegotiator", "simple tit-for-tat", "behavioral"),
    OpponentSpec("negmas.sao.FirstOfferOrientedTBNegotiator", "anchors on first offer", "oriented"),
    OpponentSpec("negmas.sao.LastOfferOrientedTBNegotiator", "follows last offer", "oriented"),
    OpponentSpec("negmas.sao.BestOfferOrientedTBNegotiator", "tracks best offer seen", "oriented"),
]


def list_scenario_names() -> list[str]:
    return sorted(p.name for p in SCENARIOS_DIR.iterdir() if p.is_dir())


def run_one(
    scenario_name: str,
    opponent_spec: OpponentSpec,
    *,
    n_steps: int = 100,
    agent_goes_first: bool,
) -> dict[str, float] | None:
    """Run one bilateral negotiation; return Agent360 score dict or None on failure."""
    scenario_path = SCENARIOS_DIR / scenario_name
    scenario = Scenario.load(scenario_path, ignore_discount=True)
    if scenario is None:
        return None

    opponent_cls = get_class(opponent_spec.class_path)
    mechanism = SAOMechanism(outcome_space=scenario.outcome_space, n_steps=n_steps)

    agent = Agent360()
    opponent = instantiate(opponent_cls)

    if agent_goes_first:
        mechanism.add(agent, ufun=scenario.ufuns[0])
        mechanism.add(opponent, ufun=scenario.ufuns[1])
    else:
        mechanism.add(opponent, ufun=scenario.ufuns[0])
        mechanism.add(agent, ufun=scenario.ufuns[1])

    mechanism.run()
    scores = calc_scores(mechanism)
    agent_row = scores.get("Agent360")
    if agent_row is None:
        # negotiator class name might differ if wrapped
        for name, row in scores.items():
            if "Agent360" in name:
                return row
        return None
    return agent_row


@app.command()
def main(
    quick: bool = typer.Option(False, "--quick", help="Fewer opponents (faster)"),
    scenario: list[str] = typer.Option(
        None,
        "--scenario",
        "-s",
        help="Scenario folder name(s). Default: all under scenarios/",
    ),
    repeats: int = typer.Option(1, "--repeats", "-r", help="Runs per (scenario, opponent, role)"),
    steps: int = typer.Option(100, "--steps", help="Max negotiation steps"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write CSV results here"),
):
    """Run Agent360 vs many opponents and print Advantage / Concealing / Score."""
    opponents = QUICK_OPPONENTS if quick else FULL_OPPONENTS
    scenario_names = scenario if scenario else list_scenario_names()

    rows: list[dict] = []
    for scenario_name in scenario_names:
        for opp in opponents:
            for agent_first in (True, False):
                role = "first" if agent_first else "second"
                totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
                ok = 0
                for _ in range(repeats):
                    try:
                        result = run_one(
                            scenario_name,
                            opp,
                            n_steps=steps,
                            agent_goes_first=agent_first,
                        )
                    except Exception as exc:
                        console.print(
                            f"[red]Failed[/red] {scenario_name} vs {opp.class_path} ({role}): {exc}"
                        )
                        result = None
                    if result:
                        for k in totals:
                            totals[k] += result[k]
                        ok += 1

                if ok == 0:
                    continue

                row = {
                    "scenario": scenario_name,
                    "opponent": opp.class_path.split(".")[-1],
                    "opponent_class": opp.class_path,
                    "strategy": opp.strategy_label,
                    "family": opp.family,
                    "agent_first": role,
                    "runs": ok,
                    "advantage": totals["Advantage"] / ok,
                    "concealing": totals["Concealing"] / ok,
                    "score": totals["Score"] / ok,
                }
                rows.append(row)

    if not rows:
        console.print("[red]No results[/red]")
        raise typer.Exit(1)

    table = Table(title="Agent360 benchmark (mean per configuration)")
    for col in (
        "scenario",
        "opponent",
        "strategy",
        "family",
        "agent_first",
        "advantage",
        "concealing",
        "score",
    ):
        table.add_column(col)
    for row in sorted(rows, key=lambda r: (-r["score"], r["scenario"], r["opponent"])):
        table.add_row(
            row["scenario"],
            row["opponent"],
            row["strategy"][:40],
            row["family"],
            row["agent_first"],
            f"{row['advantage']:.3f}",
            f"{row['concealing']:.3f}",
            f"{row['score']:.3f}",
        )
    console.print(table)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        console.print(f"[green]Wrote[/green] {output}")

    # Summary by opponent family
    by_family: dict[str, list[float]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row["score"])
    console.print("\n[bold]Mean Score by opponent family[/bold]")
    for family, scores in sorted(by_family.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        console.print(f"  {family}: {sum(scores) / len(scores):.3f}  (n={len(scores)})")


if __name__ == "__main__":
    app()
