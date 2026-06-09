#!/usr/bin/env python3
"""Analyze V2.3 sparring wins/losses from CSV."""

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> list[dict]:
    rows = [r for r in csv.DictReader((ROOT / path).open()) if r["group"] == "sparring"]
    for r in rows:
        for k in ("advantage", "concealing", "score"):
            r[k] = float(r[k])
    return rows


def main() -> None:
    v2_path = sys.argv[1] if len(sys.argv) > 1 else "results/sparring_v2_full.csv"
    rev_path = sys.argv[2] if len(sys.argv) > 2 else "results/sparring_reverse_r1.csv"

    v2 = load(v2_path)
    rev = {
        (r["scenario"], r["opponent"], r["agent_first"]): r
        for r in load(rev_path)
    }

    print("=== V2.3 by scenario (sparring mean) ===")
    by_sc: dict[str, list[float]] = defaultdict(list)
    for r in v2:
        by_sc[r["scenario"]].append(r["score"])
    for sc, scores in sorted(by_sc.items(), key=lambda x: sum(x[1]) / len(x[1])):
        print(f"  {sc:16} score={sum(scores)/len(scores):.3f}  (n={len(scores)})")

    print("\n=== Worst 12 matchups (V2.3) ===")
    for r in sorted(v2, key=lambda x: x["score"])[:12]:
        print(
            f"  {r['score']:.3f}  {r['scenario']:14} vs {r['opponent']:14} "
            f"{r['agent_first']:6}  adv={r['advantage']:.3f} con={r['concealing']:.3f}"
        )

    print("\n=== Best 8 matchups (V2.3) ===")
    for r in sorted(v2, key=lambda x: -x["score"])[:8]:
        print(
            f"  {r['score']:.3f}  {r['scenario']:14} vs {r['opponent']:14} "
            f"{r['agent_first']:6}  adv={r['advantage']:.3f} con={r['concealing']:.3f}"
        )

    print("\n=== MirrorAgent breakdown ===")
    mir = [r for r in v2 if r["opponent"] == "MirrorAgent"]
    for r in sorted(mir, key=lambda x: -x["score"]):
        print(
            f"  {r['score']:.3f}  {r['scenario']:14} {r['agent_first']:6}  "
            f"adv={r['advantage']:.3f} con={r['concealing']:.3f}"
        )
    print(f"  mean score={sum(r['score'] for r in mir)/len(mir):.3f}")

    print("\n=== Where reverse beat V2.3 by >0.02 ===")
    beats = []
    for r in v2:
        k = (r["scenario"], r["opponent"], r["agent_first"])
        if k in rev and rev[k]["score"] > r["score"] + 0.02:
            beats.append((rev[k]["score"] - r["score"], r, rev[k]))
    for d, r, rv in sorted(beats, reverse=True)[:15]:
        print(
            f"  +{d:.3f}  {r['scenario']:14} vs {r['opponent']:14} {r['agent_first']:6}  "
            f"v2={r['score']:.3f} rev={rv['score']:.3f}"
        )

    print("\n=== Lowest concealing (V2.3) ===")
    for r in sorted(v2, key=lambda x: x["concealing"])[:10]:
        print(
            f"  con={r['concealing']:.3f}  {r['scenario']:14} vs {r['opponent']:14} "
            f"{r['agent_first']:6}  score={r['score']:.3f}"
        )

    print("\n=== By opponent (mean score, mean concealing) ===")
    by_opp: dict[str, list[dict]] = defaultdict(list)
    for r in v2:
        by_opp[r["opponent"]].append(r)
    for opp, rows in sorted(by_opp.items(), key=lambda x: -sum(r["score"] for r in x[1]) / len(x[1])):
        print(
            f"  {opp:14} score={sum(r['score'] for r in rows)/len(rows):.3f}  "
            f"con={sum(r['concealing'] for r in rows)/len(rows):.3f}"
        )


if __name__ == "__main__":
    main()
