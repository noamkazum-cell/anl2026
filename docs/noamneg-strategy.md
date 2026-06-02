# NoamNeg — Agent Strategy Documentation - before rename to 360

**Implementation:** `noam_neg.py`  
**Class:** `NoamNeg`  
**CLI default:** `noam_neg.NoamNeg` (set in `main.py`)

---

## Competition goals (ANL 2026)

Your agent negotiates bilaterally in NegMAS. Local score (see `main.py` → `calc_scores`):

| Metric         | Meaning                                                                                                                                                                                            |
|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Advantage**  | `utility(agreement) - reserved_value` — get a good deal for yourself                                                                                                                               |
| **Concealing** | Share of a point based on how well the **opponent's** model of **your** utility matches your true `ufun` (Kendall agreement, normalized). **Lower opponent accuracy → higher concealing for you.** |
| **Score**      | `Advantage + Concealing`                                                                                                                                                                           |

Implications:

- Your `opponent_ufun` mainly helps **you** negotiate (Advantage).
- **Concealing** is won by confusing **their** model — via bid patterns, not by improving your own model.

---

## Architecture

`NoamNeg` extends `SAOCallNegotiator` (same pattern as the original skeleton, not the BOA example shell).

| Method                        | Responsibility                                                             |
|-------------------------------|----------------------------------------------------------------------------|
| `on_preferences_changed`      | Build `rational_outcomes`, `decoy_outcomes`, init frequency opponent model |
| `__call__`                    | Main loop: update model → accept or counter-offer                          |
| `acceptance_strategy`         | Dynamic thresholds                                                         |
| `concealing_bidding_strategy` | Phased bids (decoy → transition → closing)                                 |
| `update_opponent_model`       | Observe opponent offers into frequency counts                              |

---

## Opponent modeling (V1)

**Choice:** Smith-style **frequency model** (`_FrequencyOpponentModel`).

| Property      | Detail                                                        |
|---------------|---------------------------------------------------------------|
| Signal        | Opponent's proposed outcomes only                             |
| Update        | Increment count per `(issue, value)`                          |
| `eval(offer)` | Per issue: `count(value) / max_count`; average across issues  |
| Exposure      | Wrapped as `LambdaMultiFun` → `private_info["opponent_ufun"]` |

**Why this model**

- Matches what many opponents use (`GSmithFrequencyModel` in BOA/MAP).
- Lightweight, no training pipeline.
- Good enough for **late-phase** bids that look attractive to them.

**Future upgrades (not implemented)**

| Model                       | When to consider                            |
|-----------------------------|---------------------------------------------|
| `GAgentXFrequencyModel`     | Issue-weighted frequencies                  |
| `GHardHeadedFrequencyModel` | Alternative Genius-style assumptions        |
| Linear / Bayesian           | If you add offline fitting and more compute |

---

## Deception strategy — design intent

### Bait-and-switch persona (your idea, refined)

| Do                                                                      | Avoid                                                 |
|-------------------------------------------------------------------------|-------------------------------------------------------|
| Early bids **rational for you** but emphasizing **wrong issues**        | Insisting on outcomes that are actually bad for you   |
| **Gradual** shift mid-negotiation                                       | Sudden random flip that looks irrational              |
| Late offers **good for you** and **high on estimated opponent utility** | Revealing true top outcomes in the first ~30% of time |

Concept: mislead on **which issues you care about**, then “concede” toward what they think you want while keeping
utility high.

### Three phases (V1)

| Phase          | Time (`relative_time`)               | Bidding behavior                                                    |
|----------------|--------------------------------------|---------------------------------------------------------------------|
| **Decoy**      | `t < 0.35` (`DECOY_END`)             | Random choice from `decoy_outcomes`                                 |
| **Transition** | `0.35 ≤ t < 0.75` (`TRANSITION_END`) | Blend decoy pool + gradually lower true aspiration band             |
| **Closing**    | `t ≥ 0.75`                           | Sample candidates; score `(1 - w_opp) * u_self + w_opp * opp_model` |

Constants (tunable in `noam_neg.py`):

```python
DECOY_END = 0.35
TRANSITION_END = 0.75
```

### Decoy pool construction (`_build_decoy_pool`)

1. Take top ~10% of `rational_outcomes` (min 3, max 30).
2. Per issue, find **mode** value in top outcomes → “true” preferred value.
3. **Decoy** = rational outcomes with utility ≥ floor (≥ 55% of top-tier utility) and mismatches on ≥ `n_issues // 3`
   issues.
4. Fallback: mid-ranked rational outcomes if too few decoys.

---

## Acceptance strategy (V1)

Accept offer if **any** holds:

| Rule         | Condition                                                 |
|--------------|-----------------------------------------------------------|
| Aspiration   | `u(offer) ≥ u_max * (1 - 0.55 * t)` and above reservation |
| ACNext-style | `u(offer) ≥ u(planned_next_bid)`                          |
| Deadline     | `t > 0.92` and `u(offer) > 1.02 * reservation`            |

---

## Closing bid scoring (late phase)

```
score(o) = (1 - w_opp) * (u_self(o) / u_max) + w_opp * opp_model.eval(o)
w_opp = min(0.45, 0.15 + 0.35 * (t - TRANSITION_END))
```

- Samples up to 40 candidates from the late utility floor band.
- Picks uniformly among ties at max score.
- If opponent model has no observations yet → random from top candidates.

---

## Randomness

Bids use `random.Random(hash((self.id, state.step)))` for **reproducible** stochasticity per step (not global `random`).

---

## Code naming (readability)

| Old / internal   | New name in `noam_neg.py`    |
|------------------|------------------------------|
| `_counts`        | `opponent_preference_counts` |
| `observe`        | `record_opponent_offer`      |
| `eval`           | `estimated_opponent_utility` |
| `DECOY_END`      | `DECOY_PHASE_END`            |
| `TRANSITION_END` | `TRANSITION_PHASE_END`       |
| `_opp_freq`      | `opponent_frequency_model`   |

See **[evaluation.md](evaluation.md)** for benchmarking beyond tutorial examples.

---

## V1 sample results (local)

Command:

```bash
uv run anl2026 run --scenario Camera --no-plot \
  --negotiator noam_neg.NoamNeg --opponent examples.boa.BOANeg
```

Example outcome (one run):

| Agent   | Advantage | Concealing | Score |
|---------|-----------|------------|-------|
| NoamNeg | ~0.62     | ~0.47      | ~1.09 |
| BOANeg  | ~0.74     | ~0.53      | ~1.27 |

Use tournaments for stable comparison:

```bash
uv run anl2026 tournament --scenario Camera --competitor noam_neg.NoamNeg --competitor examples.boa.BOANeg
uv run pytest tests/test_noam_neg.py -q
```

---

## Scenarios (development)

| Scenario      | Issues | Outcomes | Notes                                    |
|---------------|--------|----------|------------------------------------------|
| **NiceOrDie** | 1      | 3        | Max opposition — concealment stress test |
| **Camera**    | 6      | 3600     | Multi-issue, moderate opposition         |
| **Grocery**   | 5      | 1600     | Medium scale                             |

Runtime agent sees: `outcome_space`, `ufun`, offers, time — **not** `_info.yml` / `_stats.yaml` (local analysis only;
excluded from submission zip).

---

## Tuning knobs (next iterations)

| Parameter                | Location              | Effect                                    |
|--------------------------|-----------------------|-------------------------------------------|
| `DECOY_END`              | class constant        | How long fake persona lasts               |
| `TRANSITION_END`         | class constant        | When to start opponent-aware closing      |
| Decoy mismatch threshold | `_build_decoy_pool`   | How “wrong” early bids look               |
| `0.55` in aspiration     | `acceptance_strategy` | Concession speed                          |
| `w_opp` caps             | `_closing_bid`        | How much you cater to opponent model late |

---

## Roadmap (discussed, not yet coded)

- [ ] Export traces and measure opponent model accuracy on your bids
- [ ] Tournament across all scenarios + random generated domains
- [ ] Stronger opponent model (AgentX / issue weights)
- [ ] Explicit “decoy set” rotation (anchor / decoy / convergence pools)
- [ ] Acceptance that uses opponent model when confidence is high

---

## Related docs

- Example baselines: [`examples-strategies.md`](examples-strategies.md)
- Competition README: [`../README.md`](../README.md)
- Tutorial PDF: https://scml.cs.brown.edu/files/anl/y2026/template2026.pdf
