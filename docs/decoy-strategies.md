# Decoy Strategies — Design, Evaluation, and Opponent Detection

Reference for comparing **gradient** (V1 `NoamNeg`), **full flip** (`NoamNegFull`), and **reverse / truth** (`NoamNegReverse`) decoy personas in ANL 2026.

---

## How ANL measures deception (Concealing)

ANL does not score “lying” directly. It scores **preference concealment**:

| Metric | Meaning |
|--------|---------|
| **Advantage** | `utility(agreement) − reserved_value` — how good the deal is for you |
| **Concealing** | How poorly the **opponent’s learned model** of **your** true utility matches reality |
| **Score** | `Advantage + Concealing` |

After each negotiation, the organizer compares:

1. Your **true** utility function (`ufun`)
2. The **opponent’s** model of you (`opponent_ufun` on their side)

Agreement is measured with **Kendall rank correlation** (`compare_ufuns`), mapped to roughly `[0, 1]`. One concealing point is split between the two agents (zero-sum): **if the opponent modeled you well, your Concealing is low**.

Implementation: `main.calc_scores`.

**Implication:** deception = make your **bid stream** mislead the opponent’s preference learner (wrong issue weights, fake priorities), not natural-language claims.

---

## Three decoy variants in this repo

| Agent | File | Early phase | Transition | Hypothesis |
|-------|------|-------------|------------|------------|
| **Gradient** | `noam_neg.py` → `NoamNeg` | Rational outcomes that mismatch true issue priorities | Gradual blend decoy → true aspiration band | Hardest to detect; default V1 |
| **Full flip** | `noam_neg_full.py` → `NoamNegFull` | Maximum issue mismatches (strong opposite persona) | Abrupt jump to true band (no decoy mixing) | High Concealing if flip is late enough; risky vs learners |
| **Reverse / truth** | `noam_neg_reverse.py` → `NoamNegReverse` | Top `rational_outcomes` (true preferences) | Shift toward misdirection pool, then true band | Exploits opponents that mistrust bids; likely **hurts** vs BOA/MAP/MiCRO |

Shared across all three: acceptance logic, frequency opponent model, closing-phase scoring (inherited from `NoamNeg`).

---

## Truth mechanism vs reverse psychology

**Truth mechanisms** (VCG, etc.) make honesty a dominant strategy when the **rules** are designed for it.

ANL 2026 is the opposite on the concealing dimension: being modeled correctly **lowers** your score. Most competition agents learn from offers (Smith / frequency models).

| Opponent type | Likely effect of bidding true preferences early |
|---------------|--------------------------------------------------|
| **BOA, MAP, MiCRO** | Easy to model you → **low Concealing** |
| **Time-based** (Boulware, Conceder, …) | Barely learn preferences → Concealing matters less |
| **SimpleNegotiator** (inverted opponent model) | Niche case — might help only vs agents that systematically mistrust bids |

`examples/simple.py` bids on **inverted** utility, not truth. Treat reverse-truth as a **hypothesis to test**, not a default.

---

## How to compare strategies

### Benchmark script (recommended)

```bash
# Fast panel (~8 opponents × all scenarios × 2 roles × 3 agents + head-to-head)
uv run python scripts/compare_decoy_agents.py --quick

# More opponents, repeated runs for stability
uv run python scripts/compare_decoy_agents.py --repeats 2

# Full run with tournament-weight summary (85% student / 15% official default)
uv run python scripts/compare_decoy_agents.py --repeats 2 --weight-student 0.85 --output results/decoy_compare_v24_full.csv

# One scenario, save CSV
uv run python scripts/compare_decoy_agents.py --quick --scenario Camera --output results/decoy_compare.csv

# Skip head-to-head (panel only)
uv run python scripts/compare_decoy_agents.py --quick --no-head-to-head
```

The script reports per-agent results vs the NegMAS panel **and** each decoy agent vs the other two.

### Metrics to prioritize

| Metric | Use |
|--------|-----|
| **Concealing** | Primary for deception — did the decoy fool their model? |
| **Advantage** | Did you still get a good deal? |
| **Score** | Tournament ranking metric |

Focus on **learner** opponents when comparing decoy modes:

- `examples.boa.BOANeg`
- `examples.map.MAPNeg`
- `negmas.sao.MiCRONegotiator`

### Decision rule (after `--repeats 5` or more)

Pick the mode with the **highest mean Score**, subject to:

- Mean **Concealing** vs BOA + MAP + MiCRO is not more than ~0.05 below your best Concealing mode
- Mean **Advantage** is not more than ~0.05 below your best Advantage mode

Avoid modes that win only by accepting bad deals or only on non-learners.

### Trace inspection (why a strategy failed)

```bash
uv run anl2026 run --scenario Camera --no-plot \
  --negotiator noam_neg_full.NoamNegFull \
  --opponent negmas.sao.MiCRONegotiator \
  --export-trace trace_full_vs_micro.csv
```

Check: your utility over time, issue values in early vs late phase, sharp tells at phase boundaries.

### Optional: mid-negotiation opponent-model accuracy

After each opponent bid, compute Kendall agreement between their `opponent_ufun` and your true `ufun`. Plot vs `relative_time`. Goal: opponent accuracy **flat or wrong** in the first ~40%, not climbing from step 3.

---

## Detecting opponent strategy (from bids only)

You never see opponent source code in competition — only their **offer stream**. Classify with simple features:

| Pattern in opponent bids | Likely strategy |
|--------------------------|-----------------|
| Their self-utility drops roughly monotonically with time | **Time-based** (Boulware, Conceder, Linear) |
| Same issue-values repeat; model stabilizes early | **Frequency / Smith learner** (BOA, MAP, MiCRO) |
| Early persona, then sharp shift in issue priorities | **Decoy / flip** (phased agents) |
| Early bids align with your estimated top values | **Truth early** or naive honest bidding |
| Concessions mirror your last concession | **Tit-for-tat** |
| Behavior consistent with inverted model of you | **Inverted model** (SimpleNegotiator-style) |

### Features to compute in `update_opponent_model` (V2 idea)

1. **Time correlation:** `corr(opponent_self_utility, relative_time)` — strongly negative → time-based
2. **Frequency concentration:** max frequency / total per issue — high → learner
3. **Phase-change score:** compare per-issue mode vectors in early vs late halves — big change → flip/decoy opponent
4. **Tit-for-tat:** correlation between your last utility change and their next change

Adaptation sketch:

- vs **learners** → gradient decoy, longer decoy phase
- vs **time-based** → shorter decoy, push Advantage
- vs **detected flip** → weight recent offers more in your opponent model

Validate offline: run known opponent classes locally and check classified label vs ground truth.

---

## Suggested workflow before improving V1

1. `pytest tests/test_noam_neg.py` — sanity on base agent
2. `compare_decoy_agents.py --quick --repeats 5` — panel + head-to-head
3. Rank by **Score**; sanity-check **Concealing** vs BOA/MAP/MiCRO
4. `--export-trace` on worst matchups per agent
5. Tune phase boundaries on the **winning** variant only

---

## Related docs

- [decoy-experiments-article.md](decoy-experiments-article.md) — full benchmark results, V2 design, implementation roadmap (article)
- [evaluation.md](evaluation.md) — general benchmarking with `evaluate_noamneg.py`
- [noamneg-strategy.md](noamneg-strategy.md) — V1 gradient agent design
- [examples-strategies.md](examples-strategies.md) — tutorial opponent behavior
- [ANL 2026 CFP](https://anac.cs.brown.edu/files/anl/y2026/2026cfp.pdf)
- [Tutorial PDF](https://anac.cs.brown.edu/files/anl/y2026/template2026.pdf)
