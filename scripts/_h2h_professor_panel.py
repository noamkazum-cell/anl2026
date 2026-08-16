# -*- coding: utf-8 -*-
"""Fresh H2H panel: Agent360 Score vs opponent Score → win counts."""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from negmas.helpers import get_class, instantiate
from negmas.inout import Scenario
from negmas.sao import SAOMechanism

from drafts.agent360_submit import Agent360
from evaluate_noamneg import OpponentSpec, list_scenario_names
from main import SCENARIOS_DIR, calc_scores
from sparring import sparring_opponent_kwargs

OUT = ROOT / "results" / "h2h_professor_panel.csv"

OPPONENTS: list[tuple[OpponentSpec, str, dict | None]] = [
    # learners
    (OpponentSpec("examples.boa.BOANeg", "BOA", "learner"), "learner", None),
    (OpponentSpec("examples.map.MAPNeg", "MAP", "learner"), "learner", None),
    (OpponentSpec("negmas.sao.MiCRONegotiator", "MiCRO", "learner"), "learner", None),
    # stress / time-based
    (OpponentSpec("negmas.sao.BoulwareTBNegotiator", "Boulware", "stress"), "stress", None),
    (OpponentSpec("negmas.sao.ConcederTBNegotiator", "Conceder", "stress"), "stress", None),
    (OpponentSpec("negmas.sao.LinearTBNegotiator", "Linear", "stress"), "stress", None),
    (OpponentSpec("negmas.sao.ToughNegotiator", "Tough", "stress"), "stress", None),
    # deceptive sparring
    (OpponentSpec("sparring.shochan_lite.ShochanLite", "ShochanLite", "deceptive"), "deceptive",
     sparring_opponent_kwargs("sparring.shochan_lite.ShochanLite", deceptive=True)),
    (OpponentSpec("sparring.renting_lite.RentingLite", "RentingLite", "deceptive"), "deceptive",
     sparring_opponent_kwargs("sparring.renting_lite.RentingLite", deceptive=True)),
    (OpponentSpec("sparring.learner_strong.LearnerStrong", "LearnerStrong", "deceptive"), "deceptive",
     sparring_opponent_kwargs("sparring.learner_strong.LearnerStrong", deceptive=True)),
]

REPEATS = 2
STEPS = 100


def run_h2h(scenario_name: str, opp: OpponentSpec, agent_first: bool, opp_kwargs: dict | None):
    scenario = Scenario.load(SCENARIOS_DIR / scenario_name, ignore_discount=True)
    if scenario is None:
        return None
    mechanism = SAOMechanism(outcome_space=scenario.outcome_space, n_steps=STEPS)
    agent = Agent360()
    opponent = instantiate(get_class(opp.class_path), **(opp_kwargs or {}))
    if agent_first:
        mechanism.add(agent, ufun=scenario.ufuns[0])
        mechanism.add(opponent, ufun=scenario.ufuns[1])
    else:
        mechanism.add(opponent, ufun=scenario.ufuns[0])
        mechanism.add(agent, ufun=scenario.ufuns[1])
    mechanism.run()
    scores = calc_scores(mechanism)
    # find Agent360 row and the other
    ours = None
    theirs = None
    for name, row in scores.items():
        if "Agent360" in name:
            ours = row
        else:
            theirs = row
    if ours is None or theirs is None:
        return None
    return ours, theirs


def main():
    scenarios = list_scenario_names()
    rows = []
    total = len(scenarios) * len(OPPONENTS) * 2 * REPEATS
    print(f"Running {total} negotiations...", flush=True)
    done = 0
    for scen in scenarios:
        for opp, group, kwargs in OPPONENTS:
            for agent_first in (True, False):
                for rep in range(REPEATS):
                    done += 1
                    try:
                        result = run_h2h(scen, opp, agent_first, kwargs)
                    except Exception as e:
                        print(f"FAIL {scen} vs {opp.strategy_label}: {e}", flush=True)
                        result = None
                    if not result:
                        continue
                    ours, theirs = result
                    win = ours["Score"] > theirs["Score"]
                    tie = abs(ours["Score"] - theirs["Score"]) < 1e-9
                    row = {
                        "scenario": scen,
                        "opponent": opp.strategy_label,
                        "group": group,
                        "agent_first": "first" if agent_first else "second",
                        "repeat": rep,
                        "our_adv": ours["Advantage"],
                        "our_conc": ours["Concealing"],
                        "our_score": ours["Score"],
                        "opp_adv": theirs["Advantage"],
                        "opp_conc": theirs["Concealing"],
                        "opp_score": theirs["Score"],
                        "win": int(win),
                        "tie": int(tie),
                    }
                    rows.append(row)
                    if done % 20 == 0:
                        print(f"  {done}/{total}", flush=True)

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # summary
    def summarize(subset, label):
        n = len(subset)
        if n == 0:
            return
        wins = sum(r["win"] for r in subset)
        ties = sum(r["tie"] for r in subset)
        losses = n - wins - ties
        a = sum(r["our_adv"] for r in subset) / n
        c = sum(r["our_conc"] for r in subset) / n
        s = sum(r["our_score"] for r in subset) / n
        print(f"\n{label} (n={n})")
        print(f"  Outperformed opponent on Score: {wins}/{n} ({100*wins/n:.1f}%)")
        print(f"  Ties: {ties}/{n}  Losses: {losses}/{n}")
        print(f"  Mean Advantage={a:.3f}  Concealing={c:.3f}  Score={s:.3f}")
        print(f"  Score>=1.0: {sum(r['our_score']>=1 for r in subset)}/{n}")
        print(f"  Concealing>=0.7: {sum(r['our_conc']>=0.7 for r in subset)}/{n}")

    print("\n" + "=" * 70)
    print("PROFESSOR PANEL RESULTS")
    summarize(rows, "ALL")
    for g in sorted({r["group"] for r in rows}):
        summarize([r for r in rows if r["group"] == g], g.upper())
    for opp in sorted({r["opponent"] for r in rows}):
        subset = [r for r in rows if r["opponent"] == opp]
        wins = sum(r["win"] for r in subset)
        print(f"  vs {opp}: beat {wins}/{len(subset)}  mean_score={sum(r['our_score'] for r in subset)/len(subset):.3f}")

    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
