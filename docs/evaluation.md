# Evaluating NoamNeg

The three tutorial agents (`examples/`) are **not enough** for serious tuning — they mostly use time-based concession
and barely exploit opponent models. You should benchmark against **NegMAS built-in negotiators** too.

---

## What to measure

Local ANL score (see `main.calc_scores`):

| Metric         | Meaning                                               |
|----------------|-------------------------------------------------------|
| **Advantage**  | How good the final deal is for you                    |
| **Concealing** | How poorly the opponent modeled your true preferences |
| **Score**      | Sum of both                                           |

Run each matchup **twice** (NoamNeg first vs second) — turn order matters.

---

## 1. Single negotiation (debug one opponent)

```bash
uv run anl2026 run --scenario Camera --no-plot \
  --negotiator noam_neg.NoamNeg \
  --opponent negmas.sao.BoulwareTBNegotiator

uv run anl2026 run --scenario NiceOrDie --no-plot \
  --negotiator noam_neg.NoamNeg \
  --opponent negmas.sao.MiCRONegotiator --export-trace trace.csv
```

Any class path NegMAS can import works for `--opponent`, e.g.:

- `negmas.sao.BoulwareTBNegotiator`
- `negmas.sao.ConcederTBNegotiator`
- `negmas.sao.LinearTBNegotiator`
- `negmas.sao.ToughNegotiator`
- `negmas.sao.MiCRONegotiator`
- `negmas.sao.UtilBasedNegotiator`
- `negmas.sao.HybridNegotiator`
- `negmas.sao.RandomNegotiator`
- … (see `import negmas.sao as sao; [x for x in dir(sao) if x.endswith('Negotiator')]`)

---

## 2. Benchmark script (recommended)

`scripts/evaluate_noamneg.py` runs NoamNeg vs a **curated opponent list** across scenarios and prints a table + optional
CSV.

```bash
# Fast (~8 opponents × all scenarios × 2 roles)
uv run python scripts/evaluate_noamneg.py --quick

# Full NegMAS panel (+ oriented / tit-for-tat / random)
uv run python scripts/evaluate_noamneg.py

# One scenario, multiple repeats for stability
uv run python scripts/evaluate_noamneg.py --scenario Camera --scenario NiceOrDie --repeats 5

# Save for spreadsheets / plotting
uv run python scripts/evaluate_noamneg.py --quick --output results/benchmark.csv
```

### Opponent families in the script

| Family            | Examples                          | Typical behavior                                                       |
|-------------------|-----------------------------------|------------------------------------------------------------------------|
| **example**       | Simple, BOA, MAP                  | Tutorial baselines; MAP/BOA learn Smith but default policies ignore it |
| **time-based**    | Boulware, Conceder, Linear, Tough | Concede on **own** utility vs time (different speeds)                  |
| **genius-style**  | MiCRONegotiator                   | Stronger ANAC-style agent                                              |
| **utility-based** | UtilBasedNegotiator               | Targets utility levels directly                                        |
| **hybrid**        | HybridNegotiator                  | Mix of heuristics                                                      |
| **behavioral**    | Tit-for-tat variants              | Reacts to your last offer                                              |
| **oriented**      | First/Last/Best offer oriented    | Anchors on offer history                                               |
| **baseline**      | RandomNegotiator                  | Random rational offers                                                 |

### How to read results

- **Low Concealing** vs frequency learners (BOA, MAP, MiCRO) → your bid stream is easy to model; strengthen decoy phase
  or entropy.
- **Low Advantage** vs Tough / Boulware → you concede too slowly or accept too late; tune aspirations or closing
  `opponent_utility_weight`.
- **High Score vs Simple but low vs MiCRO** → expected; prioritize opponents that resemble competition entries.

---

## 3. Full tournament (many agents × many scenarios)

Uses NegMAS `cartesian_tournament` (same metric as competition):

```bash
uv run anl2026 tournament --scenario all \
  --competitor noam_neg.NoamNeg \
  --competitor negmas.sao.BoulwareTBNegotiator \
  --competitor negmas.sao.MiCRONegotiator \
  --competitor examples.boa.BOANeg \
  --generate-scenarios 5
```

Results directory: `~/negmas/anl2026/tournaments/<name>/`

---

## 4. Random scenarios (reduce overfitting)

```bash
uv run anl2026 run --generate-scenario --no-plot \
  --negotiator noam_neg.NoamNeg \
  --opponent negmas.sao.ConcederTBNegotiator

uv run anl2026 tournament --generate-scenarios 20 \
  --competitor noam_neg.NoamNeg \
  --competitor negmas.sao.LinearTBNegotiator
```

---

## 5. Same hooks as many NegMAS agents

`NoamNeg` uses `SAOCallNegotiator` and overrides:

- `on_preferences_changed`
- `__call__` (accept / counter-offer)
- `acceptance_strategy` / `concealing_bidding_strategy` / `update_opponent_model`

Many NegMAS agents use the **modular** path (`BOANegotiator` / `MAPNegotiator`) with separate offering/acceptance/model
components instead — same roles, different structure. Comparing scores against both styles tells you whether your custom
loop is competitive.

---

## Suggested evaluation workflow

1. `pytest tests/test_noam_neg.py` — sanity
2. `evaluate_noamneg.py --quick` — panel across scenarios
3. Inspect worst rows (low Score or Concealing)
4. `anl2026 run` + `--export-trace` on those matchups
5. Tune `DECOY_PHASE_END`, `TRANSITION_PHASE_END`, acceptance aspiration
6. `--repeats 5` on hard scenarios before submission
