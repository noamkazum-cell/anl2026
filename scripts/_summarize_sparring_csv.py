#!/usr/bin/env python3
"""Print sparring-only means from eval_sparring CSV (exclude learners)."""

import csv
import sys
from collections import defaultdict
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/sparring_v2_full.csv")
rows = list(csv.DictReader(path.open()))
sp = [r for r in rows if r["group"] == "sparring"]
if not sp:
    print("No sparring rows")
    sys.exit(1)

for r in sp:
    for k in ("advantage", "concealing", "score"):
        r[k] = float(r[k])

n = len(sp)
agent = sp[0].get("agent_mode", "?")
print(f"{agent} — sparring only (n={n} configs)")
print(f"  advantage={sum(r['advantage'] for r in sp) / n:.3f}")
print(f"  concealing={sum(r['concealing'] for r in sp) / n:.3f}")
print(f"  score={sum(r['score'] for r in sp) / n:.3f}")

by_opp: dict[str, list[float]] = defaultdict(list)
for r in sp:
    by_opp[r["opponent"]].append(r["score"])
print("  by opponent (mean score):")
for opp, scores in sorted(by_opp.items(), key=lambda x: -sum(x[1]) / len(x[1])):
    print(f"    {opp:14} {sum(scores) / len(scores):.3f}")
