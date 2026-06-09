#!/usr/bin/env python3
"""Summarize compare_decoy_agents CSV output."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEARNERS = {"BOANeg", "MAPNeg", "MiCRONegotiator"}


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "decoy_compare_full.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    panel = [r for r in rows if r["match_type"] == "panel"]
    h2h = [r for r in rows if r["match_type"] == "head_to_head"]

    modes = sorted({r["agent_mode"] for r in panel})
    if not modes:
        print("No panel rows found.")
        return

    print(f"=== OVERALL PANEL (modes: {', '.join(modes)}) ===")
    for mode in modes:
        sub = [r for r in panel if r["agent_mode"] == mode]
        print(
            f"{mode:10}  n={len(sub):4}  Score={mean([float(r['score']) for r in sub]):.3f}  "
            f"Adv={mean([float(r['advantage']) for r in sub]):.3f}  "
            f"Conceal={mean([float(r['concealing']) for r in sub]):.3f}"
        )

    ranked = sorted(
        modes,
        key=lambda m: -mean([float(r["score"]) for r in panel if r["agent_mode"] == m]),
    )
    print(f"\nOverall rank by mean Score: {' > '.join(ranked)}")

    print("\n=== MEAN SCORE BY OPPONENT FAMILY ===")
    for mode in modes:
        print(f"  [{mode}]")
        by_fam: dict[str, list[float]] = defaultdict(list)
        for r in panel:
            if r["agent_mode"] == mode:
                by_fam[r["family"]].append(float(r["score"]))
        for fam, scores in sorted(by_fam.items(), key=lambda x: -mean(x[1])):
            print(f"    {fam:12}  {mean(scores):.3f}  (n={len(scores)})")

    print("\n=== vs LEARNERS (BOA, MAP, MiCRO) ===")
    for mode in modes:
        sub = [r for r in panel if r["agent_mode"] == mode and r["opponent"] in LEARNERS]
        if not sub:
            continue
        print(
            f"{mode:10}  Score={mean([float(r['score']) for r in sub]):.3f}  "
            f"Conceal={mean([float(r['concealing']) for r in sub]):.3f}  "
            f"Adv={mean([float(r['advantage']) for r in sub]):.3f}  n={len(sub)}"
        )

    print("\n=== MEAN SCORE vs EACH OPPONENT ===")
    by_opp: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in panel:
        by_opp[r["opponent"]][r["agent_mode"]].append(float(r["score"]))
    wins: dict[str, int] = defaultdict(int)
    for opp in sorted(by_opp.keys()):
        scores_by_mode = {m: mean(by_opp[opp][m]) for m in modes if by_opp[opp][m]}
        if not scores_by_mode:
            continue
        best_score = max(scores_by_mode.values())
        winners = [m for m, s in scores_by_mode.items() if abs(s - best_score) < 1e-9]
        winner = winners[0]
        wins[winner] += 1
        cols = "  ".join(f"{m[:4]}={scores_by_mode.get(m, 0):.3f}" for m in modes)
        print(f"  {opp:35}  {cols}  best={winner}")

    print("\n=== WIN COUNT (best mean score per opponent) ===")
    for m, c in sorted(wins.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}/{len(by_opp)} opponents")

    print("\n=== MEAN SCORE BY SCENARIO ===")
    for mode in modes:
        print(f"  [{mode}]")
        by_sc: dict[str, list[float]] = defaultdict(list)
        for r in panel:
            if r["agent_mode"] == mode:
                by_sc[r["scenario"]].append(float(r["score"]))
        for sc, scores in sorted(by_sc.items(), key=lambda x: -mean(x[1])):
            print(f"    {sc:15}  {mean(scores):.3f}")

    if h2h:
        print("\n=== HEAD-TO-HEAD (agent vs agent) ===")
        for mode in modes:
            sub = [r for r in h2h if r["agent_mode"] == mode]
            if not sub:
                continue
            print(
                f"{mode:10}  Score={mean([float(r['score']) for r in sub]):.3f}  "
                f"Adv={mean([float(r['advantage']) for r in sub]):.3f}  "
                f"Conceal={mean([float(r['concealing']) for r in sub]):.3f}  n={len(sub)}"
            )

        print("\n=== PAIRWISE HEAD-TO-HEAD ===")
        pairs: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
        for r in h2h:
            key = tuple(sorted([r["agent_mode"], r["opponent_mode"]]))
            pairs[key].append((r["agent_mode"], float(r["score"])))
        for key in sorted(pairs):
            a, b = key
            scores_a = [s for m, s in pairs[key] if m == a]
            scores_b = [s for m, s in pairs[key] if m == b]
            print(
                f"  {a} vs {b}:  {a}={mean(scores_a):.3f}  {b}={mean(scores_b):.3f}  "
                f"(n={len(scores_a)} each)"
            )


if __name__ == "__main__":
    main()
