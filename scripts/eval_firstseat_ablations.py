#!/usr/bin/env python3
"""Run all first-seat ablation variants vs the sparring panel and compare to V2.3.

Usage:
  uv run python scripts/eval_firstseat_ablations.py
  uv run python scripts/eval_firstseat_ablations.py --repeats 2 --output-dir results/ablations
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import typer
from rich.console import Console
from rich.table import Table

from agent360_v2 import (
    Agent360V2,
    Agent360V2FirstSeat,
    Agent360V2FirstSeatLongDecoy,
    Agent360V2FirstSeatLongDecoy38,
    Agent360V2FirstSeatMinOffersAblate,
    Agent360V2FirstSeatMinOffersLong38,
    Agent360V2FirstSeatRotate,
)
from compare_decoy_agents import AgentSpec, run_panel_match
from evaluate_noamneg import list_scenario_names
from eval_sparring import _sparring_specs

app = typer.Typer(help="Benchmark first-seat ablations vs sparring pool")
console = Console()

ABLATIONS: dict[str, AgentSpec] = {
    "v2": AgentSpec(Agent360V2, "v2", "Agent360V2 (V2.4)"),
    "v2.fs.minoffers": AgentSpec(
        Agent360V2FirstSeatMinOffersAblate,
        "v2.fs.minoffers",
        "min offers only (ablate)",
    ),
    "v2.fs.rotate": AgentSpec(
        Agent360V2FirstSeatRotate, "v2.fs.rotate", "decoy rotate only"
    ),
    "v2.fs.longdecoy": AgentSpec(
        Agent360V2FirstSeatLongDecoy, "v2.fs.longdecoy", "long decoy 0.42"
    ),
    "v2.fs.longdecoy38": AgentSpec(
        Agent360V2FirstSeatLongDecoy38, "v2.fs.longdecoy38", "long decoy 0.38"
    ),
    "v2.fs.min38": AgentSpec(
        Agent360V2FirstSeatMinOffersLong38, "v2.fs.min38", "min offers + decoy 0.38"
    ),
    "v2.firstseat": AgentSpec(
        Agent360V2FirstSeat, "v2.firstseat", "full V2.4 combo"
    ),
}

TARGET_MATCHUP = ("Laptop", "RentingLite", "first")


def _run_variant(
    agent_spec: AgentSpec,
    scenario_names: list[str],
    *,
    repeats: int,
    steps: int,
) -> tuple[list[dict], dict[str, float], int]:
    opponents = _sparring_specs()
    rows: list[dict] = []
    totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
    n = 0

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
                        )
                    except Exception as exc:
                        console.print(
                            f"[red]Failed[/red] {agent_spec.mode} "
                            f"{scenario_name} vs {opp.class_path.split('.')[-1]} "
                            f"({role}): {exc}"
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
                        "agent_mode": agent_spec.mode,
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
                )
                for k in totals:
                    totals[k] += mean[k]
                n += 1

    means = {k: totals[k] / n for k in totals} if n else {}
    return rows, means, n


def _target_score(rows: list[dict]) -> float | None:
    for row in rows:
        if (
            row["scenario"] == TARGET_MATCHUP[0]
            and row["opponent"] == TARGET_MATCHUP[1]
            and row["agent_first"] == TARGET_MATCHUP[2]
        ):
            return float(row["score"])
    return None


@app.command()
def main(
    repeats: int = typer.Option(2, "--repeats", "-r"),
    steps: int = typer.Option(100, "--steps"),
    scenario: list[str] | None = typer.Option(
        None, "--scenario", "-s", help="Scenario name(s); default all"
    ),
    output_dir: Path = typer.Option(
        Path("results/ablations"),
        "--output-dir",
        "-o",
        help="Directory for per-variant CSV files",
    ),
    skip_baseline: bool = typer.Option(
        False,
        "--skip-baseline",
        help="Skip V2.3 re-run (use existing results/sparring_v2_full.csv for delta)",
    ),
    variants: list[str] | None = typer.Option(
        None,
        "--variant",
        "-v",
        help=f"Run subset only: {', '.join(ABLATIONS)}",
    ),
):
    """Run first-seat ablations; print ranked summary vs V2.3."""
    scenario_names = scenario if scenario else list_scenario_names()
    to_run = variants if variants else [k for k in ABLATIONS if k != "v2" or not skip_baseline]
    unknown = [v for v in to_run if v not in ABLATIONS]
    if unknown:
        console.print(f"[red]Unknown variant(s):[/red] {unknown}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = ROOT / "results" / "sparring_v2_full.csv"
    baseline_mean: dict[str, float] | None = None
    summaries: list[dict] = []

    if "v2" in to_run:
        console.print("[bold]Running V2.3 baseline…[/bold]")
        baseline_rows, baseline_mean, n = _run_variant(
            ABLATIONS["v2"], scenario_names, repeats=repeats, steps=steps
        )
        _write_csv(output_dir / "v2_baseline.csv", baseline_rows)
        summaries.append(
            {
                "variant": "v2",
                "label": ABLATIONS["v2"].label,
                **baseline_mean,
                "target": _target_score(baseline_rows),
                "delta": 0.0,
            }
        )
    elif baseline_path.is_file():
        baseline_mean = _mean_from_csv(baseline_path)
        console.print(f"Using baseline from [green]{baseline_path}[/green]")

    for key in to_run:
        if key == "v2":
            continue

        console.print(f"[bold]Running {key}…[/bold]")
        rows, means, n = _run_variant(
            ABLATIONS[key], scenario_names, repeats=repeats, steps=steps
        )
        _write_csv(output_dir / f"{key.replace('.', '_')}.csv", rows)
        entry = {
            "variant": key,
            "label": ABLATIONS[key].label,
            **means,
            "target": _target_score(rows),
        }
        if baseline_mean:
            entry["delta"] = means["Score"] - baseline_mean["Score"]
        summaries.append(entry)

    table = Table(title="First-seat ablations — sparring panel means")
    table.add_column("variant")
    table.add_column("label")
    table.add_column("score")
    table.add_column("Δ vs v2.3")
    table.add_column("concealing")
    table.add_column("advantage")
    table.add_column("Laptop×Rent first")
    for s in sorted(summaries, key=lambda x: -x["Score"]):
        delta = s.get("delta")
        table.add_row(
            s["variant"],
            s["label"],
            f"{s['Score']:.3f}",
            f"{delta:+.3f}" if delta is not None else "—",
            f"{s['Concealing']:.3f}",
            f"{s['Advantage']:.3f}",
            f"{s['target']:.3f}" if s.get("target") is not None else "—",
        )
    console.print(table)

    summary_path = output_dir / "ablation_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "variant",
            "label",
            "Score",
            "Advantage",
            "Concealing",
            "delta",
            "target_laptop_renting_first",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in sorted(summaries, key=lambda x: -x["Score"]):
            writer.writerow(
                {
                    "variant": s["variant"],
                    "label": s["label"],
                    "Score": s["Score"],
                    "Advantage": s["Advantage"],
                    "Concealing": s["Concealing"],
                    "delta": s.get("delta"),
                    "target_laptop_renting_first": s.get("target"),
                }
            )
    console.print(f"\nWrote [green]{summary_path}[/green]")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _mean_from_csv(path: Path) -> dict[str, float]:
    rows = [r for r in csv.DictReader(path.open()) if r.get("group") == "sparring"]
    n = len(rows)
    totals = {"Advantage": 0.0, "Concealing": 0.0, "Score": 0.0}
    for r in rows:
        totals["Advantage"] += float(r["advantage"])
        totals["Concealing"] += float(r["concealing"])
        totals["Score"] += float(r["score"])
    return {k: totals[k] / n for k in totals}


if __name__ == "__main__":
    app()
