#!/usr/bin/env python3
"""Compare two sparring CSVs (sparring rows only).

Default canonical baseline is the **deceptive** panel (Shochan/UO/Renting with decoy+bait).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_BASELINE = ROOT / "results" / "sparring_v24_deceptive.csv"
DEFAULT_CANDIDATE = ROOT / "results" / "sparring_v3.csv"


def load(path: Path) -> list[dict[str, str]]:
    return [r for r in csv.DictReader(path.open()) if r.get("group") == "sparring"]


def panel_label(rows: list[dict[str, str]]) -> str:
    panels = {r.get("panel", "unknown") for r in rows}
    if len(panels) == 1:
        return panels.pop()
    return "mixed"


def mean(rows: list[dict[str, str]], key: str) -> float:
    vals = [float(r[key]) for r in rows]
    return sum(vals) / len(vals)


def keyed(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, float]]:
    out: dict[tuple[str, str, str], dict[str, float]] = {}
    for r in rows:
        k = (r["scenario"], r["opponent"], r["agent_first"])
        out[k] = {m: float(r[m]) for m in ("advantage", "concealing", "score")}
    return out


def main() -> None:
    if len(sys.argv) == 1:
        baseline_path = DEFAULT_BASELINE
        candidate_path = DEFAULT_CANDIDATE
    elif len(sys.argv) == 3:
        baseline_path = Path(sys.argv[1])
        candidate_path = Path(sys.argv[2])
    else:
        print(
            "Usage: python scripts/_compare_sparring_csvs.py "
            "[baseline.csv candidate.csv]\n"
            f"Defaults: {DEFAULT_BASELINE.name} vs {DEFAULT_CANDIDATE.name}"
        )
        sys.exit(1)

    base = load(baseline_path)
    cand = load(candidate_path)
    base_panel = panel_label(base)
    cand_panel = panel_label(cand)

    print(f"Baseline: {baseline_path.name}  panel={base_panel}")
    print(f"  { {m: round(mean(base, m), 3) for m in ('advantage', 'concealing', 'score')} }")
    print(f"Candidate: {candidate_path.name}  panel={cand_panel}")
    print(f"  { {m: round(mean(cand, m), 3) for m in ('advantage', 'concealing', 'score')} }")

    if base_panel != cand_panel:
        print(
            f"\n[warning] Panel mismatch ({base_panel} vs {cand_panel}). "
            "Re-run with: uv run python scripts/eval_sparring.py --panel deceptive"
        )

    print(f"Delta score: {mean(cand, 'score') - mean(base, 'score'):+.3f}")

    k_base, k_cand = keyed(base), keyed(cand)
    deltas = [
        (k, k_cand[k]["score"] - k_base[k]["score"], k_base[k], k_cand[k])
        for k in k_base
        if k in k_cand
    ]
    deltas.sort(key=lambda x: x[1])

    print("\nBiggest regressions:")
    for k, delta, a, b in deltas[:10]:
        print(
            f"  {k[0]:16} {k[1]:14} {k[2]:6}  {delta:+.3f}  "
            f"con {a['concealing']:.3f}->{b['concealing']:.3f}"
        )
    print("\nBiggest gains:")
    for k, delta, a, b in deltas[-10:]:
        print(
            f"  {k[0]:16} {k[1]:14} {k[2]:6}  {delta:+.3f}  "
            f"con {a['concealing']:.3f}->{b['concealing']:.3f}"
        )


if __name__ == "__main__":
    main()
