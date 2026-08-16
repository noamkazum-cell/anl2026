#!/usr/bin/env python3
"""
Compare decoy-strategy agents: Agent360 (gradient), Agent360Full (flip), Agent360Reverse (truth).

Runs each agent vs the NegMAS opponent panel and head-to-head vs the other decoy variants.

Usage:
  uv run python scripts/compare_decoy_agents.py --quick
  uv run python scripts/compare_decoy_agents.py --repeats 5 --output results/decoy_compare.csv
  uv run python scripts/compare_decoy_agents.py --scenario Camera --no-head-to-head
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Type

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import typer
from negmas.helpers import get_class, instantiate
from negmas.inout import Scenario
from negmas.sao import SAOMechanism
from rich.console import Console
from rich.table import Table

from evaluate_noamneg import FULL_OPPONENTS, QUICK_OPPONENTS, OpponentSpec, list_scenario_names
from main import SCENARIOS_DIR, calc_scores
from drafts.agent360 import Agent360Base
from drafts.agent360_full import Agent360Full
from drafts.agent360_reverse import Agent360Reverse
from drafts.agent360_v2 import Agent360V2, Agent360V2Adaptive, Agent360V2FirstSeat

app = typer.Typer(help="Compare decoy-strategy agents vs panel and each other")
console = Console()


@dataclass(frozen=True)
class AgentSpec:
    """One decoy-variant agent."""

    cls: Type
    mode: str
    label: str


LEARNER_OPPONENTS = {"BOANeg", "MAPNeg", "MiCRONegotiator"}
OFFICIAL_BASELINES = {
    "ConcederTBNegotiator",
    "LinearTBNegotiator",
    "BoulwareTBNegotiator",
}


def _mean_score_by_mode(rows: list[dict], field: str = "score") -> dict[str, float]:
    by_mode: dict[str, list[float]] = {}
    for row in rows:
        by_mode.setdefault(row["agent_mode"], []).append(float(row[field]))
    return {mode: sum(vals) / len(vals) for mode, vals in by_mode.items()}


def _print_weighted_blends(
    panel_rows: list[dict],
    h2h_rows: list[dict],
    *,
    weight_student: float,
) -> None:
    weight_comp = 1.0 - weight_student
    learner_rows = [
        r for r in panel_rows if r["opponent"] in LEARNER_OPPONENTS
    ]
    official_rows = [
        r for r in panel_rows if r["opponent"] in OFFICIAL_BASELINES
    ]
    student_rows = [
        r for r in panel_rows if r["opponent"] not in OFFICIAL_BASELINES
    ]

    learner = _mean_score_by_mode(learner_rows)
    official = _mean_score_by_mode(official_rows)
    student = _mean_score_by_mode(student_rows)
    h2h = _mean_score_by_mode(h2h_rows)

    blends = [
        (
            f"{weight_student:.0%} learners + {weight_comp:.0%} official baselines",
            learner,
            official,
        ),
        (
            f"{weight_student:.0%} student panel + {weight_comp:.0%} official baselines",
            student,
            official,
        ),
    ]
    if h2h:
        blends.append(
            (
                f"{weight_student:.0%} learners + {weight_comp:.0%} head-to-head",
                learner,
                h2h,
            )
        )

    console.print(
        f"\n[bold]Weighted Score blends (student weight={weight_student:.2f})[/bold]"
    )
    for label, student_slice, comp_slice in blends:
        modes = set(student_slice) | set(comp_slice)
        console.print(f"\n  {label}:")
        ranked = sorted(
            modes,
            key=lambda m: -(weight_student * student_slice.get(m, 0.0)
                            + weight_comp * comp_slice.get(m, 0.0)),
        )
        for mode in ranked:
            blended = (
                weight_student * student_slice.get(mode, 0.0)
                + weight_comp * comp_slice.get(mode, 0.0)
            )
            console.print(
                f"    {mode:10} {blended:.3f}  "
                f"(student={student_slice.get(mode, 0.0):.3f}, "
                f"comp={comp_slice.get(mode, 0.0):.3f})"
            )


DECOY_AGENTS: list[AgentSpec] = [
    AgentSpec(Agent360Base, "gradient", "Agent360Base (gradient)"),
    AgentSpec(Agent360Full, "full", "Agent360Full (flip)"),
    AgentSpec(Agent360Reverse, "reverse", "Agent360Reverse (truth)"),
    AgentSpec(Agent360V2, "v2", "Agent360V2 (full decoy)"),
    AgentSpec(Agent360V2FirstSeat, "v2.firstseat", "Agent360V2FirstSeat (first seat)"),
    AgentSpec(Agent360V2Adaptive, "v2.adaptive", "Agent360V2Adaptive (seat)"),
]


def _score_for_agent(
    scores: dict[str, dict[str, float]], agent_name: str
) -> dict[str, float] | None:
    row = scores.get(agent_name)
    if row is not None:
        return row
    for name, candidate in scores.items():
        if agent_name in name or name in agent_name:
            return candidate
    return None


def run_panel_match(
    scenario_name: str,
    agent_spec: AgentSpec,
    opponent_spec: OpponentSpec,
    *,
    n_steps: int,
    agent_goes_first: bool,
    opponent_kwargs: dict | None = None,
) -> dict[str, float] | None:
    """Run one agent vs a built-in / example opponent."""
    scenario_path = SCENARIOS_DIR / scenario_name
    scenario = Scenario.load(scenario_path, ignore_discount=True)
    if scenario is None:
        return None

    opponent_cls = get_class(opponent_spec.class_path)
    mechanism = SAOMechanism(outcome_space=scenario.outcome_space, n_steps=n_steps)

    agent = agent_spec.cls()
    opponent = instantiate(opponent_cls, **(opponent_kwargs or {}))
    agent_name = agent_spec.cls.__name__

    if agent_goes_first:
        mechanism.add(agent, ufun=scenario.ufuns[0])
        mechanism.add(opponent, ufun=scenario.ufuns[1])
    else:
        mechanism.add(opponent, ufun=scenario.ufuns[0])
        mechanism.add(agent, ufun=scenario.ufuns[1])

    mechanism.run()
    return _score_for_agent(calc_scores(mechanism), agent_name)


def run_head_to_head(
    scenario_name: str,
    agent_a: AgentSpec,
    agent_b: AgentSpec,
    *,
    n_steps: int,
    a_goes_first: bool,
) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    """Run two decoy agents against each other; return scores for both."""
    scenario_path = SCENARIOS_DIR / scenario_name
    scenario = Scenario.load(scenario_path, ignore_discount=True)
    if scenario is None:
        return None, None

    mechanism = SAOMechanism(outcome_space=scenario.outcome_space, n_steps=n_steps)
    neg_a = agent_a.cls()
    neg_b = agent_b.cls()

    if a_goes_first:
        mechanism.add(neg_a, ufun=scenario.ufuns[0])
        mechanism.add(neg_b, ufun=scenario.ufuns[1])
    else:
        mechanism.add(neg_b, ufun=scenario.ufuns[0])
        mechanism.add(neg_a, ufun=scenario.ufuns[1])

    mechanism.run()
    scores = calc_scores(mechanism)
    return (
        _score_for_agent(scores, agent_a.cls.__name__),
        _score_for_agent(scores, agent_b.cls.__name__),
    )


def _mean_row(
    *,
    match_type: str,
    scenario: str,
    agent: str,
    agent_mode: str,
    opponent: str,
    opponent_mode: str,
    family: str,
    role: str,
    runs: int,
    totals: dict[str, float],
) -> dict:
    return {
        "match_type": match_type,
        "scenario": scenario,
        "agent": agent,
        "agent_mode": agent_mode,
        "opponent": opponent,
        "opponent_mode": opponent_mode,
        "family": family,
        "agent_first": role,
        "runs": runs,
        "advantage": totals["Advantage"] / runs,
        "concealing": totals["Concealing"] / runs,
        "score": totals["Score"] / runs,
    }


@app.command()
def main(
    quick: bool = typer.Option(False, "--quick", help="Fewer opponents (faster)"),
    scenario: list[str] = typer.Option(
        None,
        "--scenario",
        "-s",
        help="Scenario folder name(s). Default: all under scenarios/",
    ),
    repeats: int = typer.Option(1, "--repeats", "-r", help="Runs per configuration"),
    steps: int = typer.Option(100, "--steps", help="Max negotiation steps"),
    head_to_head: bool = typer.Option(
        True,
        "--head-to-head/--no-head-to-head",
        help="Include decoy agent vs decoy agent matchups",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write CSV results here"),
    weight_student: float = typer.Option(
        0.85,
        "--weight-student",
        min=0.0,
        max=1.0,
        help="Weight for student-proxy slice in tournament blend summary",
    ),
):
    """Benchmark all decoy agents vs opponents and each other."""
    opponents = QUICK_OPPONENTS if quick else FULL_OPPONENTS
    scenario_names = scenario if scenario else list_scenario_names()
    rows: list[dict] = []
    panel_failures: set[tuple[str, str, str, str]] = set()
    panel_total = (
        len(scenario_names) * len(DECOY_AGENTS) * len(opponents) * 2
    )
    panel_done = 0

    console.print(
        f"Panel: {len(DECOY_AGENTS)} agents x {len(scenario_names)} scenarios x "
        f"{len(opponents)} opponents x 2 roles x {repeats} repeats "
        f"({panel_total} configs)"
    )

    # --- Panel: each decoy agent vs standard opponents ---
    for scenario_name in scenario_names:
        for agent_spec in DECOY_AGENTS:
            for opp in opponents:
                for agent_first in (True, False):
                    role = "first" if agent_first else "second"
                    panel_done += 1
                    if panel_done % 20 == 0 or panel_done == panel_total:
                        console.print(
                            f"[dim]Panel progress {panel_done}/{panel_total}[/dim] "
                            f"({scenario_name} {agent_spec.mode} vs "
                            f"{opp.class_path.split('.')[-1]} {role})"
                        )
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
                            key = (
                                scenario_name,
                                agent_spec.mode,
                                opp.class_path,
                                role,
                            )
                            if key not in panel_failures:
                                panel_failures.add(key)
                                console.print(
                                    f"[red]Failed[/red] {agent_spec.label} vs "
                                    f"{opp.class_path.split('.')[-1]} ({role}): {exc}"
                                )
                            result = None
                        if result:
                            for k in totals:
                                totals[k] += result[k]
                            ok += 1

                    if ok == 0:
                        continue

                    rows.append(
                        _mean_row(
                            match_type="panel",
                            scenario=scenario_name,
                            agent=agent_spec.cls.__name__,
                            agent_mode=agent_spec.mode,
                            opponent=opp.class_path.split(".")[-1],
                            opponent_mode=opp.strategy_label,
                            family=opp.family,
                            role=role,
                            runs=ok,
                            totals=totals,
                        )
                    )

    # --- Head-to-head: decoy agents vs each other ---
    if head_to_head:
        h2h_pairs = [
            (agent_a, agent_b)
            for i, agent_a in enumerate(DECOY_AGENTS)
            for agent_b in DECOY_AGENTS[i + 1 :]
        ]
        h2h_total = len(scenario_names) * len(h2h_pairs) * 2
        h2h_done = 0
        console.print(
            f"Head-to-head: {len(h2h_pairs)} pairs x {len(scenario_names)} scenarios "
            f"x 2 roles x {repeats} repeats ({h2h_total} configs)"
        )
        for scenario_name in scenario_names:
            for agent_a, agent_b in h2h_pairs:
                for a_first in (True, False):
                    h2h_done += 1
                    if h2h_done % 20 == 0 or h2h_done == h2h_total:
                        console.print(
                            f"[dim]H2H progress {h2h_done}/{h2h_total}[/dim] "
                            f"({scenario_name} {agent_a.mode} vs {agent_b.mode})"
                        )
                    role = "first" if a_first else "second"
                    totals_a = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
                    totals_b = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
                    ok = 0
                    for _ in range(repeats):
                        try:
                            score_a, score_b = run_head_to_head(
                                scenario_name,
                                agent_a,
                                agent_b,
                                n_steps=steps,
                                a_goes_first=a_first,
                            )
                        except Exception as exc:
                            console.print(
                                f"[red]Failed[/red] {agent_a.label} vs "
                                f"{agent_b.label} ({role}): {exc}"
                            )
                            score_a, score_b = None, None
                        if score_a and score_b:
                            for k in totals_a:
                                totals_a[k] += score_a[k]
                                totals_b[k] += score_b[k]
                            ok += 1

                    if ok == 0:
                        continue

                    rows.append(
                        _mean_row(
                            match_type="head_to_head",
                            scenario=scenario_name,
                            agent=agent_a.cls.__name__,
                            agent_mode=agent_a.mode,
                            opponent=agent_b.cls.__name__,
                            opponent_mode=agent_b.mode,
                            family="decoy",
                            role=role,
                            runs=ok,
                            totals=totals_a,
                        )
                    )
                    rows.append(
                        _mean_row(
                            match_type="head_to_head",
                            scenario=scenario_name,
                            agent=agent_b.cls.__name__,
                            agent_mode=agent_b.mode,
                            opponent=agent_a.cls.__name__,
                            opponent_mode=agent_a.mode,
                            family="decoy",
                            role="second" if a_first else "first",
                            runs=ok,
                            totals=totals_b,
                        )
                    )

    if not rows:
        console.print("[red]No results[/red]")
        raise typer.Exit(1)

    # --- Panel summary by agent mode ---
    panel_rows = [r for r in rows if r["match_type"] == "panel"]
    table = Table(title="Decoy agents vs opponent panel (mean Score)")
    for col in ("agent_mode", "scenario", "opponent", "family", "agent_first", "advantage", "concealing", "score"):
        table.add_column(col)
    for row in sorted(panel_rows, key=lambda r: (-r["score"], r["agent_mode"], r["scenario"])):
        table.add_row(
            row["agent_mode"],
            row["scenario"],
            row["opponent"],
            row["family"],
            row["agent_first"],
            f"{row['advantage']:.3f}",
            f"{row['concealing']:.3f}",
            f"{row['score']:.3f}",
        )
    console.print(table)

    console.print("\n[bold]Mean Score by agent mode (panel only)[/bold]")
    by_mode: dict[str, list[float]] = {}
    for row in panel_rows:
        by_mode.setdefault(row["agent_mode"], []).append(row["score"])
    for mode, scores in sorted(by_mode.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        console.print(f"  {mode}: {sum(scores) / len(scores):.3f}  (n={len(scores)})")

    console.print("\n[bold]Mean Concealing vs modeling-opponent proxy (BOA, MAP, MiCRO)[/bold]")
    for mode in sorted(by_mode):
        learner_rows = [
            r
            for r in panel_rows
            if r["agent_mode"] == mode and r["opponent"] in LEARNER_OPPONENTS
        ]
        if learner_rows:
            mean_c = sum(r["concealing"] for r in learner_rows) / len(learner_rows)
            console.print(f"  {mode}: {mean_c:.3f}  (n={len(learner_rows)})")

    if head_to_head:
        h2h_rows = [r for r in rows if r["match_type"] == "head_to_head"]
        console.print("\n[bold]Head-to-head mean Score by agent mode[/bold]")
        h2h_by_mode: dict[str, list[float]] = {}
        for row in h2h_rows:
            h2h_by_mode.setdefault(row["agent_mode"], []).append(row["score"])
        for mode, scores in sorted(h2h_by_mode.items(), key=lambda x: -sum(x[1]) / len(x[1])):
            console.print(f"  {mode}: {sum(scores) / len(scores):.3f}  (n={len(scores)})")
    else:
        h2h_rows = []

    _print_weighted_blends(panel_rows, h2h_rows, weight_student=weight_student)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        console.print(f"\n[green]Wrote[/green] {output}")


if __name__ == "__main__":
    app()
