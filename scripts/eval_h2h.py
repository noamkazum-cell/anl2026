#!/usr/bin/env python3
"""Head-to-head two agent classes across all scenarios (both roles).

Usage:
  uv run python scripts/eval_h2h.py --agent-a v2 --agent-b v2.6a
  uv run python scripts/eval_h2h.py --agent-a v2 --agent-b v2.6a --repeats 3
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

from drafts.agent360_submit import Agent360
from drafts.agent360_v2 import Agent360V2, Agent360V2Adaptive, Agent360V2ClosingA
from drafts.agent360_v4 import Agent360V4
from drafts.agent360_v4_2 import Agent360V42
from compare_decoy_agents import AgentSpec, run_head_to_head
from evaluate_noamneg import list_scenario_names

app = typer.Typer(help="Head-to-head benchmark between two agent classes")
console = Console()

AGENTS: dict[str, AgentSpec] = {
    "v2": AgentSpec(Agent360V2, "v2", "Agent360V2 (V2.4)"),
    "v3": AgentSpec(Agent360, "v3", "Agent360 (submission)"),
    "v4": AgentSpec(Agent360V4, "v4.5", "Agent360 V4.5 (submission)"),
    "v4.2": AgentSpec(Agent360V42, "v4.2", "Agent360 V4.2"),
    "v2.6a": AgentSpec(Agent360V2ClosingA, "v2.6a", "Agent360V2ClosingA"),
    "v2.adaptive": AgentSpec(Agent360V2Adaptive, "v2.adaptive", "Agent360V2Adaptive"),
}


@app.command()
def main(
    agent_a: str = typer.Option("v2", "--agent-a", help=f"First agent: {', '.join(AGENTS)}"),
    agent_b: str = typer.Option("v2.6a", "--agent-b", help=f"Second agent: {', '.join(AGENTS)}"),
    scenario: list[str] | None = typer.Option(None, "--scenario", "-s"),
    repeats: int = typer.Option(2, "--repeats", "-r"),
    steps: int = typer.Option(100, "--steps"),
):
    """Run H2H and print per-config and mean scores for agent_a."""
    for name in (agent_a, agent_b):
        if name not in AGENTS:
            console.print(f"[red]Unknown agent[/red] {name!r}")
            raise typer.Exit(1)

    spec_a = AGENTS[agent_a]
    spec_b = AGENTS[agent_b]
    scenario_names = scenario if scenario else list_scenario_names()

    totals_a = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
    totals_b = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
    rows: list[dict] = []
    n = 0

    for scenario_name in scenario_names:
        for a_first in (True, False):
            role = "first" if a_first else "second"
            run_a = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
            run_b = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
            ok = 0
            for _ in range(repeats):
                try:
                    score_a, score_b = run_head_to_head(
                        scenario_name,
                        spec_a,
                        spec_b,
                        n_steps=steps,
                        a_goes_first=a_first,
                    )
                except Exception as exc:
                    console.print(
                        f"[red]Failed[/red] {scenario_name} ({role}): {exc}"
                    )
                    score_a, score_b = None, None
                if score_a and score_b:
                    for k in run_a:
                        run_a[k] += score_a[k]
                        run_b[k] += score_b[k]
                    ok += 1

            if ok == 0:
                continue

            mean_a = {k: run_a[k] / ok for k in run_a}
            mean_b = {k: run_b[k] / ok for k in run_b}
            rows.append(
                {
                    "scenario": scenario_name,
                    "role": role,
                    "a": mean_a,
                    "b": mean_b,
                }
            )
            for k in totals_a:
                totals_a[k] += mean_a[k]
                totals_b[k] += mean_b[k]
            n += 1

    if n == 0:
        console.print("[yellow]No successful runs[/yellow]")
        raise typer.Exit(1)

    title = f"H2H: {spec_a.label} vs {spec_b.label} (n={n} configs, {repeats} repeats)"
    table = Table(title=title)
    table.add_column("scenario")
    table.add_column("role")
    table.add_column(f"{agent_a} score")
    table.add_column(f"{agent_b} score")
    table.add_column("delta score")
    for row in sorted(rows, key=lambda r: r["a"]["Score"] - r["b"]["Score"], reverse=True):
        delta = row["a"]["Score"] - row["b"]["Score"]
        table.add_row(
            row["scenario"],
            row["role"],
            f"{row['a']['Score']:.3f}",
            f"{row['b']['Score']:.3f}",
            f"{delta:+.3f}",
        )
    console.print(table)

    def _line(label: str, t: dict[str, float]) -> str:
        return (
            f"{label}: score={t['Score']/n:.3f}  "
            f"adv={t['Advantage']/n:.3f}  con={t['Concealing']/n:.3f}"
        )

    console.print(f"\n[bold]Mean {agent_a}[/bold]  {_line(agent_a, totals_a)}")
    console.print(f"[bold]Mean {agent_b}[/bold]  {_line(agent_b, totals_b)}")
    delta_score = totals_a["Score"] / n - totals_b["Score"] / n
    console.print(f"[bold]Delta ({agent_a} - {agent_b})[/bold]  score={delta_score:+.3f}")


if __name__ == "__main__":
    app()
