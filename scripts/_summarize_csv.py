import csv
import sys
from collections import defaultdict
from pathlib import Path

path = Path(sys.argv[1])
rows = list(csv.DictReader(path.open()))
learners = {"BOANeg", "MAPNeg", "MiCRONegotiator"}
official = {"ConcederTBNegotiator", "LinearTBNegotiator", "BoulwareTBNegotiator"}


def summarize(label, subset):
    by = defaultdict(lambda: {"score": [], "adv": [], "con": []})
    for r in subset:
        m = r["agent_mode"]
        by[m]["score"].append(float(r["score"]))
        by[m]["adv"].append(float(r["advantage"]))
        by[m]["con"].append(float(r["concealing"]))
    print(f"\n=== {label} ===")
    for m in sorted(by, key=lambda x: -sum(by[x]["score"]) / len(by[x]["score"])):
        n = len(by[m]["score"])
        print(
            f"  {m:10}  score={sum(by[m]['score'])/n:.3f}  "
            f"adv={sum(by[m]['adv'])/n:.3f}  con={sum(by[m]['con'])/n:.3f}  n={n}"
        )


summarize(
    "Panel vs learners",
    [r for r in rows if r["match_type"] == "panel" and r["opponent"] in learners],
)
summarize("Head-to-head", [r for r in rows if r["match_type"] == "head_to_head"])
