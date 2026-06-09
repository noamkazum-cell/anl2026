# Strategy vs Cruel Agents — Competition Prep

This document captures how ANL scoring works, why the default NegMAS opponent panel
**misleadingly favors truth-first agents**, and what we must improve to win against
sophisticated student agents (preference learners + phased deception + strong closing).

Use this as the **submission decision guide**, not raw panel mean Score alone.

Related: [`decoy-strategies.md`](decoy-strategies.md), [`decoy-experiments-article.md`](decoy-experiments-article.md), [`evaluation.md`](evaluation.md).

---

## 1. How Score is calculated

Implementation: `main.calc_scores`.

| Metric | Formula / meaning | Typical range |
|--------|-------------------|---------------|
| **Advantage** | `utility(agreement) − reserved_value` | ~0–1+ |
| **Concealing** | Share of 1 point based on how **poorly** the opponent’s final model of your true `ufun` matches reality (Kendall agreement via `compare_ufuns`, normalized, zero-sum between negotiators) | ~0–1 |
| **Score** | **`Advantage + Concealing`** | ~0–2 |

Key properties:

- Concealing uses the opponent’s **final** `opponent_ufun` after the **whole** bid history — not early bids alone.
- Concealing is **zero-sum**: if they model you well, your Concealing drops.
- Your own `opponent_ufun` helps **you** negotiate (Advantage). It does **not** raise your Concealing.
- Deception = mislead **their** preference learner via bid patterns.

---

## 2. Why the example panel misleads us

Most NegMAS panel opponents (Conceder, Linear, Boulware, Tough, oriented time-based agents)
are **time-based conceders**. They barely learn your preferences.

Against them:

- **Concealing ≈ 1.0 for every agent variant** — deception does not differentiate anyone.
- Rankings are driven almost entirely by **Advantage** (deal quality).

That is why **Agent360Reverse** wins the full panel: truth-first early bids extract much
better deals from conceders (+0.08–0.15 Advantage in many matchups), while Concealing was
already capped at 1.0 anyway.

### What a cruel student agent actually looks like

Students with the same tooling (Claude, Gemini, NegMAS examples, competition docs) will
likely ship agents that:

| Capability | Evidence they’ll have it |
|------------|--------------------------|
| **Preference learning** | BOA / MAP / MiCRO in examples; Concealing is scored on their model of you |
| **Phased bidding** | Same decoy → transition → closing structure we built |
| **Strong acceptance / closing** | ACNext-style rules; opponent-frequency closing (our V1 already does this) |
| **Possibly opponent-type detection** | Same adaptive routing we attempted in V2 |

The relevant opponent is **not** Conceder. It is **another preference learner** that models
you while concealing their own priorities — i.e. **agent vs agent**.

---

## 3. Do NOT classify opponents online

**You are correct:** hard-coded opponent typing is the wrong design for competition.

### What is wrong with classification

| Problem | Why it fails in ANL |
|---------|---------------------|
| **Opponent class is unknown** | You never see `BOANeg` vs `ConcederTBNegotiator` — only an offer stream |
| **Labels are a benchmark artifact** | Our panel has named types; the tournament does not |
| **Signals overlap** | Boulware looks like a learner (high concentration); MiCRO looks like a conceder early; fast deals give too few offers |
| **Mis-routing is asymmetric** | Truth-first vs a learner → they model you → **Concealing collapse**. Decoy-first vs a conceder → Concealing was ~1.0 anyway — little cost |
| **Tuning thresholds to panel names** | Overfits to NegMAS examples; fails against student agents with different stacks |

### What we stopped doing

- **Agent360V2 (V2.4)** — full decoy pool, no routing; stronger closing (see Section 7.3, 10.8).
- **`debug_classifier.py`** shows post-hoc stats only (`if_we_routed` is diagnostic, not a pass/fail target).
- We **removed** “router match rate” as a success metric.

### Correct competition assumption

> **Every opponent might be a preference learner.**  
> Ship **one fixed persona** that maximizes Concealing under that assumption.  
> Accept that vs pure time-based conceders you leave some Advantage on the table — that is cheaper than being modeled in the tournament.

**Agent360V2 (current):** Full-flip decoy pool + V1 gradient transition + V1 closing — same schedule regardless of opponent.

### How to evaluate without pretending we know types

| Use | Do not use |
|-----|------------|
| **Modeling-opponent proxy:** mean Score/Concealing vs BOANeg, MAPNeg, MiCRONegotiator | “Router correctly labels Conceder” |
| **Head-to-head** between our variants | Panel headline Score alone |
| **Full panel** as sanity check only | Optimizing for Concealing = 1.0 vs time-based bots |
| **Future sparring agents** (student-like composites) | Per-opponent-type persona tables in production code |

The BOA/MAP/MiCRO subset is a **stress-test group** for “opponents that model you” — not a list of types we should detect at runtime.

---

## 4. Benchmark evidence (what matters for competition)

### 4.1 Panel vs modeling-opponent proxy (BOANeg, MAPNeg, MiCRONegotiator)

Only here does **Concealing actually differ** between our variants.

From the first full 4-agent benchmark (`results/decoy_compare_v2_full.csv`):

| Agent | Score (learners) | Concealing | Advantage |
|-------|------------------|------------|-----------|
| Reverse | ~best | ~worst (~0.66) | ~best (~0.64) |
| Full flip | middle | **~best (~0.70)** | lower (~0.58) |
| Gradient (submitted V1) | middle | middle (~0.65) | middle (~0.57) |
| V2 adaptive (old) | middle | middle | middle |

All variants stay near **~1.15 Score** vs learners — this is the hard ceiling.

**Takeaway:** vs modelers, the trade-off is real but not huge (~0.05 Concealing between
Full and Reverse). Advantage still matters, but **telegraphing truth early is dangerous**
if the field is mostly learners.

### 4.2 Head-to-head (decoy agent vs decoy agent)

Closest proxy for **student vs student** (`results/decoy_compare_full.csv`, 3-agent run):

| Agent | Score | Advantage | Concealing |
|-------|-------|-----------|------------|
| **Reverse** | **1.212** | **0.789** | 0.423 |
| Gradient | 1.125 | 0.602 | 0.523 |
| Full flip | 1.111 | 0.556 | 0.554 |

When **both sides** use frequency learning:

- Concealing **collapses for everyone** (~0.42–0.55).
- The fight moves to **Advantage in closing**.
- Reverse still wins H2H — but even it only gets **~0.42 Concealing**.

**Takeaway:** against a cruel field, assume Concealing will be **0.4–0.6**, not 1.0. Win on
closing and deal extraction, but **do not optimize for panel opponents that give free Concealing**.

### 4.3 What the full panel headline hides

Full 4-agent panel (7 scenarios × 15 opponents):

| Agent | Mean Score | Advantage | Concealing |
|-------|------------|-----------|------------|
| Reverse | **1.549** | **0.652** | 0.898 |
| Gradient (submitted) | 1.452 | 0.569 | 0.883 |
| V2 adaptive | 1.447 | 0.567 | 0.880 |
| Full | 1.446 | 0.560 | 0.886 |

Reverse wins on **Advantage**, not Concealing. Most of the panel never tests deception.

---

## 5. Submission decision rule (competition-weighted)

**Do not use:** highest mean Score on the full 15-opponent panel.

**Use instead:**

> Pick the agent with the highest **competition-weighted Score**, subject to guardrails on
> Concealing vs learners.

### Priority order

| Priority | Metric | Why |
|----------|--------|-----|
| **1** | Mean **Score** vs BOANeg + MAPNeg + MiCRONegotiator | Models what serious entries will do |
| **2** | Mean **Score** in head-to-head (agent vs agent) | Models student vs student |
| **3** | Mean **Concealing** vs learners | Direct deception vs modelers |
| **4** | Mean **Advantage** vs learners | Still need the deal, not just the lie |
| **5** | Full panel mean Score | Sanity check only — inflated by time-based opponents |

### Pass / fail guardrails

When comparing a candidate to the current submission (gradient V1):

| Guardrail | Threshold |
|-----------|-----------|
| Concealing vs learners | Not more than **0.05** below Full flip (best deceiver) |
| Advantage vs learners | Not more than **0.05** below Reverse (best deal-maker) |
| Score vs learners | Beat gradient by at least **+0.02** (or match within 0.01 if Concealing gain is large) |
| Head-to-head Score | At least match gradient; target beat Reverse |

### Current submission status

- **Submitted:** `agent360.Agent360` (gradient decoy, V1) — stable middle ground.
- **Do not submit Reverse** despite panel win — too exposed to preference learners.
- **V2.1 hybrid** (Reverse schedule + Full misdirection pool, no router) — under evaluation.

---

## 6. What cruel agents will exploit

If opponents are digging with the same tools we are, they will target:

| Weakness | What they exploit | Our risk today |
|----------|-------------------|----------------|
| **Truth-first early bids** | Frequency learners lock real issue priorities fast | Reverse, V2 hybrid (always truth early) |
| **Fixed phase boundaries** (0.35 / 0.75) | Weight early vs late offers differently; detect phase shifts | All V1 variants |
| **Predictable decoy pool** | Same mismatch pattern every negotiation | Gradient; Full if pool is static |
| **Weak or late closing** | Extract Advantage while we still decoy | Any agent that decoys past ~0.75 |
| **Smith-frequency closing** | If they detect we optimize `(1−w)·my_u + w·their_est`, they can bait us | V1 closing logic |

They will **not** beat us by being Conceder. They beat us by **modeling us early** and
**winning closing**.

---

## 7. What we need to improve to win (action list)

These are ordered by impact against a cruel student field.

### 7.1 Default persona: fixed, learner-safe (no routing)

**Problem:** Any online classifier can mislabel; wrong label hurts more than a robust default.

**Improve:**

- **One schedule for all opponents:** Full-flip decoy pool + gradient transition + V1 closing (Agent360V2 today).
- Tune pool size, phase boundaries, and closing weights — **not** detection thresholds.
- Re-benchmark on **modeling-opponent proxy + H2H**, not router accuracy.

**Target:** Beat gradient on Concealing vs BOA/MAP/MiCRO without losing >0.03 Score there.

### 7.2 Stronger decoy pool (already in V2)

**Problem:** Gradient decoys are easier for frequency learners to see through than
maximal-mismatch decoys.

**Improve:**

- Use **Full-flip maximal mismatch** outcomes as the misdirection pool (V2.1 direction).
- Keep **gradient blending** in transition (harder to detect than abrupt flip).
- Extend misdirection slightly later (e.g. transition_progress < 0.65) **only vs learners**.

**Target:** +0.03–0.05 Concealing vs learners vs gradient V1.

### 7.3 Closing phase — where H2H is won

**Problem:** Head-to-head Concealing collapses (~0.42). Reverse wins H2H on **Advantage
(+0.19 over Full)** in closing. V2.3 won Concealing vs learners (0.730) but had the lowest
learner Advantage (0.572).

**V2.4 changes (implemented in `agent360_v2.py`):**

| Parameter | V2.3 (Agent360) | V2.4 |
|-----------|-----------------|------|
| `DECOY_PHASE_END` | 0.35 | **0.32** |
| `TRANSITION_PHASE_END` | 0.75 | **0.72** |
| Decoy mix in transition | until progress 0.6 | until progress **0.45** |
| Closing min utility floor | 0.72 → 0.52 | **0.78 → 0.64** |
| Closing opponent weight cap | 0.45 | **0.38** |
| Late acceptance | V1 only | V1 + **late floor** after transition |

**Hypothesis:** Keep maximal-mismatch decoy long enough for Concealing, but enter a
stronger closing phase earlier so Advantage vs learners and H2H recover without routing.

**Target (vs V2.3 baseline):**

- Concealing vs BOA/MAP/MiCRO ≥ **0.700** (allow −0.03 vs 0.730)
- Score vs BOA/MAP/MiCRO ≥ **1.302** (match or beat V2.3)
- H2H Score ≥ **1.119** (match or beat V2.3)
- Advantage vs learners ≥ **0.600** (+0.028 vs V2.3)

### 7.4 Sparring partners (build our own cruel agents)

**Problem:** NegMAS examples are too simple to stress-test.

**Improve:** Add internal opponents that mirror a serious student entry:

| Sparring agent | Composition |
|----------------|-------------|
| **StudentLearner** | BOANeg acceptance + Full-flip decoy + our closing |
| **StudentAdaptive** | Opponent router + gradient decoy + strong acceptance |
| **MirrorAgent** | Copy of our submitted agent (self-play) |

Run round-robin: candidate vs sparring pool + learners + H2H.

**Target:** Beat gradient on Score vs StudentLearner and in mirror matchups.

### 7.5 Anti-deception (lower priority — V3)

Detecting **opponent** deception (phased opponents, inverted models) matters less than
**not being modeled ourselves**. Defer until in-house persona (6.1–6.4) beats gradient on
learner-weighted metrics.

---

## 8. Agent variant reference

| Agent | File | Persona | Notes |
|-------|------|---------|-------|
| **Gradient (V1, submitted)** | `agent360.py` | Partial mismatch decoy, gradient transition | Stable baseline |
| **Full flip** | `agent360_full.py` | Max mismatch, abrupt transition | Best Concealing proxy; weaker Advantage |
| **Reverse** | `agent360_reverse.py` | Truth-first | Panel winner; bad vs modelers — not for submission |
| **V2 (current)** | `agent360_v2.py` | Full decoy + V1 transition/closing, no routing | **V2.3 baseline** |

**Competition target (V2.3, fixed persona):**

```
Early (0–0.35):        maximal-mismatch decoy pool
Transition (0.35–0.75): gradient blend (decoy mix until progress 0.6)
Closing (0.75–1.0):    V1 acceptance + frequency-model closing
```

Closing knobs live on `Agent360` as class constants (`CLOSING_*`, `TRANSITION_DECOY_MIX_UNTIL`) for ablations without touching decoy phase length.

---

## 9. Evaluation commands

```powershell
# Full panel + head-to-head + 85/15 weighted blends (~25–35 min)
uv run python scripts/compare_decoy_agents.py --repeats 2 --output results/decoy_compare_v24_full.csv

# Adjust tournament mix assumption (default 0.85 = 85% student proxy)
uv run python scripts/compare_decoy_agents.py --repeats 2 --weight-student 0.85 --output results/decoy_compare_v24_full.csv

# Quick smoke only — do not use for submission decisions
uv run python scripts/compare_decoy_agents.py --quick --repeats 1 --output results/decoy_compare_v24_quick.csv

# Post-hoc offer stats (not pass/fail)
uv run python scripts/debug_classifier.py --scenario Camera
```

The compare script prints **weighted Score blends** at the end (learners + official baselines,
student panel + official, learners + H2H). Use `--weight-student` to match your field estimate.

After the full run, paste the summary block (learner Concealing, H2H, weighted blends) or share
`results/decoy_compare_v24_full.csv`.

### V2.4 pass/fail checklist (compare to V2.3 in Section 10)

| Metric | V2.3 baseline | V2.4 pass |
|--------|---------------|-----------|
| Concealing vs BOA/MAP/MiCRO | 0.730 | ≥ 0.700 |
| Score vs BOA/MAP/MiCRO | 1.302 | ≥ 1.302 |
| Advantage vs BOA/MAP/MiCRO | 0.572 | ≥ 0.600 |
| H2H Score | 1.119 | ≥ 1.119 |

**Replace V2.3 submission recommendation** only if V2.4 passes Score + Concealing rows and
improves Advantage or H2H without failing Concealing.

### Learner-only summary script (paste into terminal)

```powershell
uv run python -c @"
import csv
from collections import defaultdict
from pathlib import Path

path = Path('results/decoy_compare_v24_full.csv')  # adjust filename
rows = list(csv.DictReader(path.open()))
learners = {'BOANeg', 'MAPNeg', 'MiCRONegotiator'}
official = {'ConcederTBNegotiator', 'LinearTBNegotiator', 'BoulwareTBNegotiator'}

def summarize(label, subset):
    by = defaultdict(lambda: {'score': [], 'adv': [], 'con': []})
    for r in subset:
        m = r['agent_mode']
        by[m]['score'].append(float(r['score']))
        by[m]['adv'].append(float(r['advantage']))
        by[m]['con'].append(float(r['concealing']))
    print(f'\n=== {label} ===')
    for m in sorted(by, key=lambda x: -sum(by[x]['score'])/len(by[x]['score'])):
        n = len(by[m]['score'])
        print(f\"  {m:10}  score={sum(by[m]['score'])/n:.3f}  adv={sum(by[m]['adv'])/n:.3f}  con={sum(by[m]['con'])/n:.3f}  n={n}\")

summarize('Panel vs learners', [r for r in rows if r['match_type']=='panel' and r['opponent'] in learners])
summarize('Official baselines', [r for r in rows if r['match_type']=='panel' and r['opponent'] in official])
summarize('Head-to-head', [r for r in rows if r['match_type']=='head_to_head'])
summarize('Full panel', [r for r in rows if r['match_type']=='panel'])
"@
```

After each run, update **Section 10.8** with results.

---

## 10. Latest benchmark results

**Source:** `results/decoy_compare_v23_full.csv` — 7 scenarios × 15 opponents × 2 roles × 2 repeats + head-to-head.

### 10.1 Run metadata

| Field | Value |
|-------|-------|
| CSV file | `results/decoy_compare_v23_full.csv` |
| Agents tested | gradient (V1 submitted), full, reverse, **v2** (V2.3 fixed persona) |
| Repeats | 2 |
| V2.3 design | Full decoy pool + V1 gradient transition + V1 closing — **no routing** |

### 10.2 Full panel (sanity check — **do not use for submission decision**)

| Agent | Mean Score | Advantage | Concealing | n |
|-------|------------|-----------|------------|---|
| reverse | **1.560** | **0.665** | 0.895 | 210 |
| gradient | 1.467 | 0.575 | 0.892 | 210 |
| full | 1.460 | 0.569 | 0.891 | 210 |
| **v2** | 1.454 | 0.554 | **0.899** | 210 |

Reverse wins panel by **+0.093** over gradient — almost entirely from Advantage vs time-based opponents
(Concealing ≈ 1.0 for all agents in those matchups). **V2 has highest panel Concealing** but lowest Advantage.

### 10.3 Panel vs learners — **primary decision table**

BOANeg, MAPNeg, MiCRONegotiator — the proxy for cruel student agents.

| Agent | Mean Score | Advantage | Concealing | n |
|-------|------------|-----------|------------|---|
| reverse | **1.306** | **0.646** | 0.660 | 42 |
| **v2** | **1.302** | 0.572 | **0.730** | 42 |
| full | 1.296 | 0.586 | 0.711 | 42 |
| gradient | 1.271 | 0.596 | 0.676 | 42 |

**Pass criteria for replacing submission:**

| Criterion | Target | v2 | Pass? |
|-----------|--------|-----|-------|
| Score vs learners | ≥ 1.286 (gradient 1.271 + 0.02) | **1.302** | ✓ |
| Concealing vs learners | ≥ 0.676 | **0.730** | ✓ |
| H2H Score | ≥ 1.134 | 1.119 | ✗ (−0.015) |

**V2.3 verdict:** **Passes cruel-field primary metrics.** Best Concealing vs modelers (+0.054 vs gradient,
+0.070 vs reverse). Wins learner **Score** (+0.031 vs gradient) by trading Advantage for deception —
exactly the intended trade-off. H2H narrowly misses the gradient floor but still beats gradient (+0.017).

### 10.4 Other slices

**Official baselines** (ConcederTBNegotiator, LinearTBNegotiator, BoulwareTBNegotiator):

| Agent | Mean Score | Advantage | Concealing | n |
|-------|------------|-----------|------------|---|
| reverse | **1.739** | **0.739** | 1.000 | 42 |
| gradient | 1.567 | 0.603 | 0.964 | 42 |
| full | 1.545 | 0.593 | 0.952 | 42 |
| v2 | 1.537 | 0.573 | 0.964 | 42 |

V2 gives up **−0.030 Score** vs gradient on official ANL baselines — acceptable if the field is mostly students.

**Example agents** (BOA, MAP, MiCRO, SimpleNegotiator):

| Agent | Mean Score | Advantage | Concealing | n |
|-------|------------|-----------|------------|---|
| reverse | **1.322** | **0.679** | 0.643 | 56 |
| v2 | 1.250 | 0.565 | **0.685** | 56 |
| gradient | 1.233 | 0.586 | 0.647 | 56 |
| full | 1.226 | 0.572 | 0.654 | 56 |

SimpleNegotiator pulls v2 down on Advantage (example-family slice); Concealing still leads.

### 10.5 Head-to-head — **secondary decision table**

| Agent | Mean Score | Advantage | Concealing | n |
|-------|------------|-----------|------------|---|
| reverse | **1.211** | **0.799** | 0.412 | 42 |
| **v2** | 1.119 | 0.571 | **0.548** | 42 |
| full | 1.109 | 0.563 | 0.546 | 42 |
| gradient | 1.102 | 0.608 | 0.494 | 42 |

V2 beats gradient and full on H2H; reverse still wins on closing Advantage when both sides model.

### 10.6 Interpretation

| Finding | Implication |
|---------|-------------|
| V2 Concealing vs learners = **0.730** | Best result so far — Full pool + gradient transition works |
| V2 Score vs learners = **1.302** | Beats gradient (+0.031) despite lower Advantage |
| Reverse panel +0.093 over gradient | Still misleading — worst Concealing vs modelers (0.660) |
| V2 −0.030 vs gradient on official baselines | Pay for deception with slightly worse conceder closing |
| No runtime classification | Correct tournament design; evaluate proxy groups post-hoc only |

### 10.7 Submission recommendation

**Switch submission to Agent360V2 (V2.3)** if you expect a cruel student field (modelers + deceivers).

- Wins the metrics that matter: learner Score and Concealing
- Fixed persona — no mis-routing risk
- Keep gradient V1 only if you weight official baselines / panel Advantage heavily

Do **not** submit Reverse despite panel win.

### 10.8 V2.4 full benchmark — **failed, reverted to V2.3**

**Source:** `results/decoy_compare_v24_full.csv` — 7 scenarios × 15 opponents × 2 roles × 2 repeats + H2H.

V2.4 tried earlier closing + stronger utility focus (see §7.3). **Reverted in code** — results below.

#### Pass/fail vs V2.3 baseline

| Metric | V2.3 | V2.4 | Target | Result |
|--------|------|------|--------|--------|
| Concealing vs BOA/MAP/MiCRO | 0.730 | **0.715** | ≥ 0.700 | ✓ floor, −0.015 vs V2.3 |
| Score vs learners | **1.302** | 1.289 | ≥ 1.302 | ✗ |
| Advantage vs learners | 0.572 | 0.574 | ≥ 0.600 | ✗ |
| H2H Score | **1.119** | 1.085 | ≥ 1.119 | ✗ (−0.034, last of four) |

#### Full panel summary

| Agent | Panel Score | Concealing vs learners | H2H Score |
|-------|-------------|------------------------|-----------|
| reverse | **1.536** | 0.661 | **1.220** |
| gradient | 1.460 | 0.678 | 1.121 |
| full | 1.454 | 0.707 | 1.141 |
| **v2** | 1.444 | **0.715** | 1.085 |

#### Learner slice (primary)

| Agent | Score | Advantage | Concealing |
|-------|-------|-----------|------------|
| reverse | **1.307** | **0.645** | 0.661 |
| **v2** | 1.289 | 0.574 | **0.715** |
| full | 1.279 | 0.572 | 0.707 |
| gradient | 1.267 | 0.588 | 0.678 |

#### Weighted 85/15 blends

| Blend | reverse | v2 | gradient |
|-------|---------|-----|----------|
| 85% learners + 15% official | **1.372** | 1.328 | 1.309 |
| 85% student panel + 15% official | **1.523** | 1.437 | 1.454 |
| 85% learners + 15% H2H | **1.294** | 1.258 | 1.245 |

**Verdict:** V2.4 **does not replace V2.3**. Earlier closing hurt H2H and learner Score without
meaningful Advantage gain. **Submission candidate remains V2.3** (`agent360_v2.py` reverted).

**Next in-house targets:**

1. ~~Per-negotiation phase jitter~~ — V2.5 failed, reverted
2. **Closing-only tuning** (§10.10) — `CLOSING_*` constants
3. Sparring agents (§7.4) for iteration loop

### 10.9 V2.5 — phase jitter — **failed, reverted to V2.3**

**Source:** `results/decoy_compare_v25_full.csv`.

| Metric | V2.3 | V2.5 | Result |
|--------|------|------|--------|
| Score vs learners | **1.302** | 1.288 | −0.014 |
| Concealing vs learners | **0.730** | 0.722 | −0.008 |
| H2H Score | 1.119 | **1.135** | +0.016 |

Jitter + decoy shuffle improved H2H but regressed learner metrics. **Code reverted to V2.3.**

### 10.10 Next ablations (V2.3 baseline)

**Do not change:** decoy phase end (0.35), transition end (0.75), opponent routing.

**V2.4 lesson:** moving phase boundaries hurt Concealing more than they helped Advantage.

**V2.6 direction — closing-only tuning** (override `CLOSING_*` on `Agent360V2`, phases unchanged):

| Knob | V2.3 / V1 default | Hypothesis |
|------|-------------------|------------|
| `CLOSING_OPPONENT_WEIGHT_CAP` | 0.45 | Lower → bid for our utility, +Advantage |
| `CLOSING_MIN_UTILITY_START` | 0.72 | Raise → hold for better deals in closing |
| `TRANSITION_DECOY_MIX_UNTIL` | 0.6 | Leave alone unless Concealing drops |

Fast iteration:

```powershell
uv run python scripts/eval_learners.py --agent v2 --repeats 2
uv run python scripts/eval_learners.py --agent gradient --repeats 2
```

Pass vs V2.3: learner Score ≥ **1.302**, Concealing ≥ **0.700**, Advantage ≥ **0.572**.

**Other levers (not yet benchmarked):**

1. **Sparring agents** (§7.4) — StudentLearner = BOA acceptance + full-flip decoy.
2. **Opening offer** — first bid from decoy pool vs mid decoy.
3. **Acceptance in closing only** — steeper aspiration after `transition_phase_end()`.

---

## 11. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| Pre-V2.1 | Keep submitting gradient V1 | Stable middle; Reverse wins panel but weak vs learners |
| May 2026 | **Keep submitting gradient V1** | V2.1 hybrid failed vs learners (Concealing 0.661 = Reverse); gradient best trade-off (Score 1.266, Concealing 0.676) |
| May 2026 | **V2.3 — remove all routing** | User correct: classification is wrong for competition; fixed Full+gradient persona |
| May 2026 | **Recommend V2.3 for submission** | V2.3 passes learner Score (1.302) and Concealing (0.730); beats gradient on cruel-field metrics |
| May 2026 | **V2.4 — stronger closing** | Shorter decoy, earlier closing, late acceptance; pending `decoy_compare_v24_full.csv` |
| May 2026 | **Revert to V2.3 after V2.4 fail** | V2.4: Concealing 0.715 OK but Score 1.289 & H2H 1.085 regressed; keep V2.3 for submission |
| May 2026 | **V2.5 — phase jitter + decoy shuffle** | Failed vs V2.3 on learners; reverted to V2.3 |
| May 2026 | **V2.6 — closing-only ablations** | Tune `CLOSING_*` constants; use `scripts/eval_learners.py` |

---

## 12. One-page summary

1. **Score = Advantage + Concealing** — equal weight, but most panel opponents cap Concealing at 1.0.
2. **Cruel agents = preference learners** — assume every opponent might model you.
3. **Do not classify opponents online** — unknown type, overlapping signals, mis-route risk.
4. **Ship one fixed persona** — V2.4 = Full decoy pool + faster transition + strong closing.
5. **Evaluate on modeling-opponent proxy + H2H + weighted blends** — not panel headline alone.
6. **Reverse wins the panel for the wrong reason** — do not submit it for a student field.
7. **Next:** tune phase weights and sparring agents, not detection thresholds.
