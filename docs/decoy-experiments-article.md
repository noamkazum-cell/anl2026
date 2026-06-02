# Decoy Strategy Experiments — Results and V2 Design Notes

Article-ready summary of the ANL 2026 decoy comparison: three agent variants benchmarked against the NegMAS opponent
panel, plus design notes for a second-generation hybrid agent.

**Related:** [decoy-strategies.md](decoy-strategies.md) (methodology), [evaluation.md](evaluation.md) (how to run
benchmarks).

---

## 1. Research question

ANL 2026 scores agents on **Advantage** (deal quality) and **Concealing** (how poorly the opponent models your true
preferences). We compared three early-bidding personas built on the same acceptance logic, opponent model, and closing
phase:

| Variant                   | Class            | Early persona                           | Mid negotiation                        | Late negotiation              |
|---------------------------|------------------|-----------------------------------------|----------------------------------------|-------------------------------|
| **Gradient (V1)**         | `NoamNeg`        | Issue-mismatch decoy bids               | Gradual blend decoy → true band        | Opponent-model-guided closing |
| **Full flip**             | `NoamNegFull`    | Maximal issue mismatch                  | Abrupt jump to true band               | Same as V1                    |
| **Reverse / truth-first** | `NoamNegReverse` | Top rational outcomes (true priorities) | Brief misdirection mix, then true band | Same as V1                    |

**Hypotheses tested:**

- Gradient misdirection is harder for frequency learners to detect than an abrupt flip.
- Full flip maximizes Concealing at the cost of looking irrational mid-game.
- Reverse psychology (bid truth early, misdirect later) exploits opponents that mistrust offers.

---

## 2. Experimental setup

### Benchmark script

```bash
uv run python scripts/compare_decoy_agents.py --repeats 2 --output results/decoy_compare_full.csv
uv run python scripts/summarize_decoy_results.py results/decoy_compare_full.csv
```

### Configuration

| Parameter             | Value                                                                                      |
|-----------------------|--------------------------------------------------------------------------------------------|
| Scenarios             | All 7 in `scenarios/`: Amsterdam, Camera, Car, Grocery, ISBTAcquisition, Laptop, NiceOrDie |
| Repeats               | 2 per (scenario, opponent, role, agent)                                                    |
| Steps per negotiation | 100                                                                                        |
| Roles                 | Each agent tested as first mover and second mover                                          |
| Match types           | **Panel** (vs external opponents) + **head-to-head** (decoy vs decoy)                      |

### Opponent panel (15 agents)

Three opponents from the full NegMAS list failed to run in this session (`UtilBasedNegotiator`,
`NaiveTitForTatNegotiator`, `SimpleTitForTatNegotiator`). All others ran:

| Family           | Opponents                                                |
|------------------|----------------------------------------------------------|
| **Example**      | SimpleNegotiator, BOANeg, MAPNeg                         |
| **Time-based**   | Boulware, Conceder, Linear, Tough, TimeBased, Aspiration |
| **Genius-style** | MiCRONegotiator                                          |
| **Hybrid**       | HybridNegotiator                                         |
| **Oriented**     | FirstOffer, LastOffer, BestOffer oriented                |
| **Baseline**     | RandomNegotiator                                         |

**Total panel rows:** 630 (3 agents × 210 configurations).  
**Raw data:** `results/decoy_compare_full.csv` (714 rows including head-to-head).

### Metrics (competition-aligned)

- **Advantage** — `utility(agreement) − reserved_value`
- **Concealing** — share of a normalized point based on Kendall agreement between the opponent’s final model of you and
  your true utility function (higher = they modeled you worse)
- **Score** — `Advantage + Concealing`

---

## 3. Results — overall panel

Mean over all scenarios, opponents, and roles (210 configurations per agent):

| Agent              | **Score** | Advantage | Concealing |
|--------------------|-----------|-----------|------------|
| **NoamNegReverse** | **1.542** | **0.651** | 0.891      |
| NoamNeg (gradient) | 1.474     | 0.577     | **0.896**  |
| NoamNegFull (flip) | 1.452     | 0.564     | 0.888      |

**Finding:** Reverse wins on **total Score**, driven almost entirely by **Advantage** (better final deals). Gradient
edges Concealing slightly overall; full flip is in the middle on both.

---

## 4. Results — vs preference learners

Learners (BOANeg, MAPNeg, MiCRONegotiator) are the most relevant opponents for the **deception** dimension:

| Agent     | Score     | Concealing | Advantage |
|-----------|-----------|------------|-----------|
| Reverse   | **1.301** | 0.661      | **0.640** |
| Full flip | 1.288     | **0.706**  | 0.582     |
| Gradient  | 1.264     | 0.669      | 0.595     |

**Finding:**

- **Full flip** achieves the highest **Concealing** vs learners (0.706) — best at hiding preferences from Smith-style
  models.
- **Reverse** still wins **Score** vs learners because it negotiates substantially better deals (+0.058 Advantage vs
  full flip).
- Early truth does **not** collapse Concealing vs learners in practice, but it also does **not** maximize it — full flip
  remains the pure deception winner.

---

## 5. Results — by opponent family

| Family       | Gradient  | Full flip | **Reverse** |
|--------------|-----------|-----------|-------------|
| hybrid       | 1.580     | 1.517     | **1.711**   |
| oriented     | 1.605     | 1.605     | **1.645**   |
| time-based   | 1.554     | 1.521     | **1.631**   |
| genius-style | 1.533     | 1.538     | **1.632**   |
| baseline     | **1.491** | 1.385     | 1.427       |
| example      | 1.120     | 1.136     | **1.213**   |

Reverse wins or ties in five of six families. Example opponents (tutorial agents) remain hard for all variants (~1.1–1.2
Score).

---

## 6. Results — per opponent (who wins where)

Best mean Score per opponent (aggregated over scenarios and roles):

| Opponent             | Gradient  | Full      | Reverse   | Winner               |
|----------------------|-----------|-----------|-----------|----------------------|
| ConcederTBNegotiator | 1.598     | 1.463     | **1.777** | reverse              |
| LinearTBNegotiator   | 1.586     | 1.561     | **1.772** | reverse              |
| HybridNegotiator     | 1.580     | 1.517     | **1.711** | reverse              |
| SimpleNegotiator     | 1.102     | 1.081     | **1.369** | reverse              |
| MiCRONegotiator      | 1.533     | 1.538     | **1.632** | reverse              |
| BOANeg               | 1.113     | **1.176** | 1.130     | full                 |
| MAPNeg               | 1.144     | **1.149** | 1.140     | full                 |
| RandomNegotiator     | **1.491** | 1.385     | 1.427     | gradient             |
| ToughNegotiator      | **1.308** | 1.272     | 1.308     | gradient/reverse tie |

**Win count (best Score per opponent):** reverse **11/15**, full **2/15**, gradient **2/15**.

Notable patterns:

- **SimpleNegotiator** assumes an inverted opponent utility — reverse’s early truth bids are highly effective (+0.27
  Score vs gradient).
- **Conceder / Linear** — reverse gains huge Advantage; time-based agents barely learn preferences, so Concealing is
  often ~1.0 for all variants.
- **BOA / MAP** — full flip slightly best; all variants stay near ~1.15 Score (learners are tough).

---

## 7. Results — by scenario

| Scenario        | Gradient | Full  | **Reverse** |
|-----------------|----------|-------|-------------|
| Car             | 1.655    | 1.625 | **1.676**   |
| Laptop          | 1.481    | 1.433 | **1.671**   |
| Grocery         | 1.571    | 1.563 | **1.643**   |
| Amsterdam       | 1.540    | 1.535 | **1.604**   |
| ISBTAcquisition | 1.530    | 1.446 | **1.599**   |
| Camera          | 1.509    | 1.524 | **1.549**   |
| NiceOrDie       | 1.029    | 1.041 | 1.052       |

**NiceOrDie** is an outlier: many matchups collapse to ~0.665 Score regardless of decoy strategy (scenario structure
dominates).

---

## 8. Results — head-to-head (decoy vs decoy)

When the three variants negotiate directly against each other (7 scenarios × 3 pairs × 2 roles × 2 repeats):

| Agent       | Score     | Advantage | Concealing |
|-------------|-----------|-----------|------------|
| **Reverse** | **1.212** | **0.789** | 0.423      |
| Gradient    | 1.125     | 0.602     | 0.523      |
| Full flip   | 1.111     | 0.556     | 0.554      |

Pairwise means:

| Matchup             | Agent A   | Agent B |
|---------------------|-----------|---------|
| reverse vs gradient | **1.228** | 1.149   |
| reverse vs full     | **1.195** | 1.129   |
| full vs gradient    | 1.092     | 1.100   |

When both sides use frequency learning, **Concealing becomes a zero-sum fight** — both models improve, so Concealing
drops (~0.42–0.55). Reverse wins by extracting **Advantage** in the closing phase.

---

## 9. Interpretation for the article

### What we learned

1. **There is no single “best lie.”** Full flip best hides preferences from learners; reverse best wins deals and total
   Score; gradient is a stable middle ground.

2. **Truth-first was not harmful** in this benchmark — contrary to the initial hypothesis that BOA/MAP/MiCRO would
   easily model honest early bids. Reverse still won vs learners on Score because Advantage gains outweighed slightly
   lower Concealing.

3. **Opponent type matters more than scenario.** Example learners (BOA, MAP) cap all variants near ~1.15 Score;
   time-based conceders let reverse reach ~1.77.

4. **Concealing is scored on the opponent’s final model**, not on early bids alone. Late-phase behavior and whether the
   opponent is a learner at all dominate the metric.

5. **Fixed three-phase schedules are a simplification.** All variants share the same coarse calendar (`t < 0.35`,
   `0.35 ≤ t < 0.75`, `t ≥ 0.75`). Performance differences come mainly from *which outcome pool* is sampled in each
   window, not from having “more phases.”

---

## 10. How much time does a negotiation actually have?

This section answers: *“How can we tell the truth, then decoy, then return to truth — is there enough time?”*

### Wall-clock vs relative time

NegMAS bilateral negotiations use a step limit (default **100 steps**) and a normalized clock **`relative_time` ∈ [0, 1]
**. Your V1 boundaries:

| Phase         | Relative time window | Approx. steps | Your bids (approx.)       |
|---------------|----------------------|---------------|---------------------------|
| Early persona | before 0.35          | 0–35          | ~15–18 (every other step) |
| Transition    | 0.35 to 0.75         | 35–75         | ~18–20                    |
| Closing       | 0.75 to 1.00         | 75–100        | ~10–12                    |

You do **not** need long “truth sessions” or “decoy sessions.” Each bid is **one sample** from an outcome pool.
Opponents like BOA/MAP/MiCRO aggregate **frequencies per issue-value** over the whole run. A persona is defined by *
*which values appear often**, not by explicit announcements.

### What reverse actually does (not truth → decoy → truth)

`NoamNegReverse` is **not** a three-act play returning to truth at the end. It is:

| Relative time window | What you bid |
|----------------------|--------------|
| 0.00 – 0.35 | Sample from **truth pool** (your top outcomes) |
| 0.35 – ~0.57 | **Mix** misleading outcomes with your true aspiration band |
| ~0.57 – 0.75 | **True aspiration band only** |
| 0.75 – 1.00 | **Closing** — opponent-model-weighted offers (same as Version 1) |

Misdirection occupies only the **first half of the middle window** — roughly **12% of total negotiation time** (
about 12 steps out of 100). After that, behavior converges to true preferences and closing logic. There is no separate
“return to truth” phase because **truth is the default** after the brief misdirection window.

### Why “full truth → full decoy → full truth” is the wrong mental model

| Misconception                              | Reality                                                                                         |
|--------------------------------------------|-------------------------------------------------------------------------------------------------|
| Each phase must “complete” before the next | Phases are **sampling weights**, not sequential stories                                         |
| Truth means revealing your best outcome    | Truth means biasing bids toward **high self-utility** outcomes — still many distinct offers     |
| Decoy needs half the negotiation           | A few decoy-leaning bids can shift a frequency model if they are **consistent on issue-values** |
| You need time for three personas           | You need **one closing trajectory** toward agreement; early/mid signals are cheap               |

Concealing is measured **once**, on the opponent’s **final** `opponent_ufun`. What matters is the **balance of signals
they accumulated**, especially in the second half when their model has locked in somewhat.

### Worked example: how a frequency learner “sees” you

Suppose a scenario has 3 issues and your **true** top values are `(A, X, 1)`. A Smith-style opponent (like BOANeg) counts
how often you bid each value per issue.

**Reverse agent, first 20 of your bids:**

| Issue 1 | Issue 2 | Issue 3 | Pool |
|---------|---------|---------|------|
| A, A, A, A, A … | X, X, X … | 1, 1, 1 … | truth pool (relative time before 0.35) |

After 20 bids the opponent’s inferred model says: “They love A, X, 1 on every issue.” Kendall agreement with your true
utility rises quickly → **low Concealing** for you unless later bids contradict this.

**Full-flip agent, first 20 bids** (decoy pool emphasizes `(B, Y, 2)` — wrong but still rational):

| Issue 1 | Issue 2 | Issue 3 | Pool |
|---------|---------|---------|------|
| B, B, B, B … | Y, Y, Y … | 2, 2, 2 … | decoy |

The opponent locks onto the wrong issue priorities. Even if you shift toward `(A, X, 1)` after relative time 0.35, the
**early counts still anchor** their model → **higher Concealing**.

**Key insight for V2:** you are not managing three narrative acts; you are managing **what the opponent’s counter
remembers**. Frequency learners remember the whole run; time-based agents mostly ignore it.

### Bid budget cheat sheet (100 steps, bilateral SAO)

| Quantity | Typical value | Notes |
|----------|---------------|-------|
| Total steps | 100 | Configurable via `--steps` |
| Steps where you bid | ~25–35 | Alternating offers; depends on first mover |
| Steps where opponent bids | ~25–35 | You learn from these in `update_opponent_model` |
| Minimum offers to classify opponent | 5–8 | Enough for correlation / frequency features |
| Minimum decoy-leaning offers to skew Smith model | 8–12 | If consistent on issue-values |
| Closing offers (relative time > 0.75) | ~8–12 | Where Advantage is usually won or lost |

You **always** have enough steps for: (1) a short persona seed, (2) a blend or exploit window, (3) closing. You do
**not** have enough steps for three full-length personas at equal weight — and you do not need them.

---

## 11. Version 2 direction — hybrid adaptive agent

Version 2 should **not** use one fixed persona for every opponent. The benchmark showed that different early bidding
styles win in different situations. Version 2 combines four ideas:

| Idea | What problem it solves | What the benchmark showed |
|------|------------------------|---------------------------|
| **Pick the persona based on opponent type** | Stop using one early strategy for everyone | Reverse beat Simple by +0.27 Score; full flip beat reverse on Concealing vs learners by +0.045 |
| **Blend bids smoothly over time** | Avoid an obvious “personality change” at one timestamp | Full flip’s abrupt switch is easier to detect than gradient’s gradual blend |
| **Protect Concealing late in the game** | The final opponent model uses the whole bid history | Concealing is scored once at the end; late bids still update the opponent’s model |
| **Keep Version 1 acceptance and closing** | Do not break what already wins good deals | Reverse won mainly on Advantage in closing, especially vs conceding opponents |

---

### 11.1 What Version 2 adds (plain overview)

Think of Version 1 as one script: *early decoy → gradual shift → closing*. Version 2 adds a **decision at the start of
the negotiation**: *who am I playing against?* Then it runs the persona schedule that fits that opponent.

**Three new pieces of logic:**

1. **Opponent type detector** — watches the opponent’s offers and guesses whether they learn your preferences, concede
   over time, assume you are lying, or use their own phased deception.
2. **Persona schedule chooser** — once the opponent type is known (or while still uncertain), picks **how much** of each
   bid should come from the decoy pool, the truth pool, or the closing pool at the current point in the negotiation.
3. **Weighted bid picker** — instead of “if before 35% of time, use decoy only”, each counter-offer is drawn from a
   **mix** of pools according to the schedule.

**What stays exactly as in Version 1:**

- **Acceptance rules** — when to say yes to the opponent’s offer (explained in Section 11.2).
- **Closing bid logic** — how to pick late offers using your estimate of the opponent’s preferences.
- **Your opponent model** — the frequency counter that tracks which issue-values the opponent repeats.

---

### 11.2 Glossary — terms used in Version 1 and Version 2

These names appear in the code and in this document. No shortcuts.

| Term | Plain meaning |
|------|---------------|
| **Relative time** | A number from 0.0 (negotiation start) to 1.0 (deadline). At 0.35, about 35% of the step budget has passed. |
| **Outcome pool** | A list of candidate deals your agent randomly samples from when making the next offer. |
| **Decoy pool** | Outcomes that are still good for you but emphasize the **wrong issues** — they teach the opponent a false picture of your priorities. Built by `NoamNeg._build_decoy_pool`. |
| **Truth pool** | Your highest-utility outcomes — what you actually want. Used by `NoamNegReverse` in the early phase. |
| **Closing pool** | Late-game outcomes above a utility floor; scored using both your utility and your estimate of the opponent’s utility. |
| **Aspiration acceptance** | Accept if the opponent’s offer is at least as good as a **time-decaying target**: `max_utility × (1 − 0.55 × relative_time)`. As the deadline nears, you lower your standards. |
| **Accept-if-not-better-than-our-next-bid** | Before rejecting, compute the offer you **would** send next. If the opponent’s current offer is at least as good for you as that counter-offer would be, **accept**. This is the rule called “ACNext” in negotiation literature and in `acceptance_strategy` comments — it prevents rejecting a deal you would have worsened yourself on the next step. |
| **Deadline acceptance** | If relative time > 0.92 and the offer is even slightly above your reservation value, accept to avoid timeout with no deal. |
| **Concealing** | Competition metric: how poorly the opponent’s learned model of your utility matches your true preferences. |
| **Advantage** | Competition metric: utility of the final agreement minus your reservation value. |
| **Preference learner** | An opponent (like BOANeg, MAPNeg, MiCRONegotiator) that counts how often you use each issue-value and builds a Smith-style frequency model of you. |
| **Time-based opponent** | An opponent (like Conceder, Boulware, Linear) that mainly lowers its own demands over time and barely learns your preferences from your bids. |
| **Persona schedule** | A table that says, at each point in relative time, what **fraction** of your bids should look decoy-like, truthful, or closing-focused. |

---

### 11.3 How the agent is structured (readable architecture)

Each time the opponent sends an offer, the following happens in order:

```
1. OPPONENT SENDS OFFER
        │
        ▼
2. UPDATE YOUR OPPONENT MODEL
   (count which values they repeat — same as Version 1)
        │
        ▼
3. UPDATE OPPONENT TYPE DETECTOR
   (after enough offers: learner? time-based? inverted? phased?)
        │
        ▼
4. PERSONA SCHEDULE CHOOSER
   (based on opponent type + relative time:
    what fraction decoy / truth / closing?)
        │
        ▼
5. WEIGHTED BID PICKER
   (draw one outcome from the mixed pools)
        │
        ▼
6. ACCEPTANCE CHECK
   (aspiration? accept-if-not-better-than-next-bid? deadline?)
        │
        ├── yes → ACCEPT opponent offer
        └── no  → send the picked counter-offer
```

**Outcome pools** (built once when preferences are loaded):

- **Rational outcomes** — all deals above your reservation value, sorted best-for-you first.
- **Decoy outcomes** — rational deals that mismatch your true issue priorities (from gradient / full flip builders).
- **Truth outcomes** — top slice of rational outcomes (from reverse builder).

The **persona schedule chooser** is not a calendar in the everyday sense. It is simply: *given who we think the
opponent is, and how close we are to the deadline, what mix of pools should the next bid come from?*

---

### 11.4 Choosing the early persona by opponent type

After about **8 opponent offers** (roughly 16–20 steps, relative time around 0.16–0.20), commit to an opponent type.
Before that, use the **gradient persona** (Version 1 default) — the safest all-round choice from the benchmark.

| Detected opponent type | What you observe in their offers | Early persona to use | Why |
|------------------------|----------------------------------|----------------------|-----|
| **Preference learner** | Same issue-values repeat; stable “favorite” values per issue; they are building a model of you | **Decoy-first** (gradient or full flip style) | If you bid truth early, they learn your real priorities → low Concealing |
| **Time-based conceder** | Their own utility on their offers drops steadily as relative time increases; weak use of your bid history | **Truth-first** (reverse style) | They barely update a model of you; Concealing is often ~1.0 anyway — push for Advantage |
| **Inverted-model opponent** | They act as if your utility is the opposite of what your bids suggest (SimpleNegotiator-like) | **Short truth anchor**, then exploit their wrong belief | Benchmark: reverse +0.27 vs Simple vs gradient |
| **Phased opponent** | Their favorite issue-values in the first half of offers differ sharply from the second half | **Decoy-first for you** + weight your opponent model toward their **recent** offers | They are deceiving too; do not trust their early persona |
| **Unknown / not sure yet** | Fewer than 8 offers, or conflicting signals | **Gradient decoy** (Version 1) | Middle ground; avoid a risky guess |

This table is the core Version 2 idea: **you only run truth-first when the opponent is unlikely to punish you for it.**

---

### 11.5 Persona schedules in detail (four templates)

Each schedule defines **mixing weights** at a given relative time:

- **Weight on decoy pool** — how often to bid misleading-but-rational outcomes.
- **Weight on truth pool** — how often to bid high-utility outcomes that reveal real priorities.
- **Weight on closing pool** — how often to use late-game opponent-model scoring.

The three weights always sum to 1.0 for each moment in the negotiation.

#### Schedule A — Decoy-first (for preference learners and unknown opponents)

Use when: BOANeg, MAPNeg, MiCRONegotiator detected, or type still unknown.

| Phase name | Relative time | Approx. steps | Decoy weight | Truth weight | Closing weight | What you are trying to do |
|------------|---------------|---------------|--------------|--------------|----------------|---------------------------|
| **Decoy seed** | 0.00 – 0.25 | 0–25 | 0.85 | 0.15 | 0.00 | Teach the wrong issue priorities |
| **Gradual blend** | 0.25 – 0.55 | 25–55 | 0.85 → 0.20 (linear) | 0.15 → 0.65 | 0.00 | Shift smoothly toward real preferences — no cliff at 0.35 |
| **Exploit** | 0.55 – 0.75 | 55–75 | 0.10 | 0.70 | 0.20 | Bid in your true band; bait using your opponent model |
| **Close** | 0.75 – 1.00 | 75–100 | 0.00 | 0.30 | 0.70 | Version 1 closing logic dominates |

**Rule:** While decoy weight > 0.5, do not sample your global top 3 outcomes — save the best deals for closing.

This schedule is **not** “truth → decoy → truth”. It is **decoy → blend → real preferences → close**.

#### Schedule B — Truth-first (for time-based opponents)

Use when: Conceder, Linear, Boulware, or similar detected.

| Phase name | Relative time | Approx. steps | Decoy weight | Truth weight | Closing weight | What you are trying to do |
|------------|---------------|---------------|--------------|--------------|----------------|---------------------------|
| **Truth anchor** | 0.00 – 0.20 | 0–20 | 0.05 | 0.95 | 0.00 | Lock in good deals early; Concealing barely matters |
| **Gradual press** | 0.20 – 0.80 | 20–80 | 0.00 | 0.85 | 0.15 | Slowly concede on your own utility as deadline nears |
| **Close** | 0.80 – 1.00 | 80–100 | 0.00 | 0.25 | 0.75 | Accept when offer ≥ what you would bid next |

Benchmark: reverse scored **1.777** vs Conceder; all variants had Concealing ≈ 1.0 vs time-based agents.

#### Schedule C — Truth anchor then exploit (for inverted-model opponents)

Use when: SimpleNegotiator-like behavior detected.

| Phase name | Relative time | Approx. steps | Decoy weight | Truth weight | Closing weight | What you are trying to do |
|------------|---------------|---------------|--------------|--------------|----------------|---------------------------|
| **Truth anchor** | 0.00 – 0.30 | 0–30 | 0.10 | 0.90 | 0.00 | Let them build an inverted model of you |
| **Exploit** | 0.30 – 0.75 | 30–75 | 0.20 | 0.50 | 0.30 | Shift toward outcomes they think you want |
| **Close** | 0.75 – 1.00 | 75–100 | 0.00 | 0.20 | 0.80 | Close on bait offers |

Benchmark: reverse **1.369** vs Simple vs gradient **1.102**.

#### Schedule D — Opponent is also deceiving (phased opponent)

Use when: opponent’s early issue favorites differ strongly from late issue favorites.

- When estimating **their** utility, weight the **last 40%** of their offers more heavily.
- For **your** bids, use **Schedule A (decoy-first)** — do not mirror their complexity with honesty.

---

### 11.6 Version 1 persona schedules (for comparison)

These are what the three Version 1 agents actually run today — useful for the article and for understanding Version 2
changes.

| Agent | Early persona (relative time < 0.35) | Middle (0.35 – 0.75) | Late (≥ 0.75) |
|-------|----------------------------------------|----------------------|---------------|
| **Gradient (`NoamNeg`)** | Random from decoy pool (wrong issue emphasis) | Gradual mix of decoy + true aspiration band | Opponent-model-weighted closing |
| **Full flip (`NoamNegFull`)** | Random from **maximum-mismatch** decoy pool | **Abrupt** jump to true band only (no decoy mix) | Same closing as gradient |
| **Reverse (`NoamNegReverse`)** | Random from **truth** pool (top outcomes) | Brief misdirection mix, then true band | Same closing as gradient |

**Reverse timeline in plain language** (not three equal acts):

| Relative time | What happens |
|---------------|--------------|
| 0.00 – 0.35 | Bid mostly what you truly want |
| 0.35 – ~0.57 | Mix in misleading outcomes (~12% of total negotiation) |
| ~0.57 – 0.75 | Back to your true aspiration band |
| 0.75 – 1.00 | Closing: pick offers good for you and attractive to them (per your model) |

---

### 11.7 Opponent type detector — how it works

The detector runs after **every** opponent offer but only **commits** to a type after **8 offers**. Until then, label
is **Unknown** and Schedule A’s first rows apply with gradient-style decoy.

#### Signals computed from opponent offers only

| Signal | How to compute it | Preference learner | Time-based conceder |
|--------|-------------------|--------------------|---------------------|
| **Frequency concentration** | For each issue, (most common value count) / (total offers); average over issues | High (> 0.55) | Low |
| **Time–utility correlation** | Correlation between opponent’s self-utility on their offer and relative time | Near zero | Strongly negative (< −0.6) |
| **Utility variance** | Standard deviation of opponent self-utility over their offers | Low to medium | Medium (steady drop) |
| **Early vs late issue favorites** | Compare most common value per issue in first half vs second half of their offers | Stable early | Used for phased-opponent detection |
| **Tit-for-tat pattern** | Correlation between your last utility change and their next utility change | — | — |

**Inverted-model detection:** After you bid values you strongly prefer on an issue, check whether the opponent keeps
 bidding values that would be good for you under a naive “they want the opposite of what I bid” assumption. If this
 happens often → inverted-model opponent (Schedule C).

#### Why wait for 8 offers?

- Fewer than 5 offers: correlation and frequency numbers are mostly noise.
- 8 offers ≈ relative time 0.16–0.20 — still early; most of your bids are still ahead.
- Wrong classification is costly but not fatal: Unknown falls back to gradient decoy.

---

### 11.8 Weighted bid picking — one step explained

Version 1 uses hard boundaries: `if relative_time < 0.35: decoy`. Version 2 replaces that with a weighted random choice:

1. Read the three weights from the active persona schedule (decoy, truth, closing).
2. Build a combined list of candidate outcomes from each pool that has weight > 0.
3. Assign each candidate a selection probability proportional to its pool’s weight.
4. Draw one outcome at random.

**Why this is better than a hard flip:**

- No single step where you jump from 100% decoy to 100% truth (the main weakness of full flip).
- When the opponent type is recognized at relative time ≈ 0.20, only the **weights** change — not a visible phase break.
- The same code path handles all opponent types; only the schedule table differs.

---

### 11.9 Late-game tactics for Concealing

Concealing uses the opponent’s **final** model after all offers. Tactics:

**Mid-game contradiction (learners only, relative time 0.40 – 0.65):**

If you accidentally ran truth-first but then detect a preference learner, inject a **short burst of 3–5 decoy-leaning
bids** before returning to your true band. This is the inverse of `NoamNegReverse` and targets BOA/MAP.

**Closing without showing your absolute best deal (relative time > 0.75):**

Version 1 closing already avoids always picking `rational_outcomes[0]`. Version 2 adds: exclude your top 3 outcomes from
the closing pool unless relative time > 0.92 **or** the opponent’s offer already passes the
**accept-if-not-better-than-our-next-bid** rule.

**Head-to-head note:**

When both agents are preference learners, Concealing collapses (~0.42 in our benchmark) because both models improve.
In those matchups, prioritize **Advantage** (Schedule B-style closing) over mid-game misdirection.

---

### 11.10 What Version 2 is NOT

| Wrong idea | Why it fails |
|------------|--------------|
| Run all three Version 1 agent classes in one negotiation | They are separate classes with no shared state; bids would be incoherent |
| Equal-length truth, decoy, and truth acts | Wastes bid budget; the third act rarely changes the final Kendall score |
| Optimize Concealing alone | Score = Advantage + Concealing; reverse gained +0.058 Advantage vs full flip on learners |
| One fixed schedule for all opponents | Reverse won 11/15 opponents but lost BOA/MAP to full flip |
| Heavy decoy after relative time 0.75 | Misses the agreement window; hurts Advantage |
| Perfect opponent detection | Misclassification will happen; Unknown must fall back to safe gradient decoy |

---

## 12. Implementation roadmap (step-by-step)

This section is the **concrete build plan** before touching `noam_neg_v2.py`. Each step has deliverables and a pass/fail
check.

### Step 0 — Baseline lock-in (no new code)

**Goal:** Freeze comparison point so V2 gains are measurable.

**Actions:**

1. Confirm `results/decoy_compare_full.csv` exists and matches documented numbers.
2. Run `pytest tests/test_noam_neg.py`.
3. Export 3 reference traces (one per V1 variant vs BOANeg):

```bash
uv run anl2026 run --scenario Camera --no-plot --negotiator noam_neg.NoamNeg \
  --opponent examples.boa.BOANeg --export-trace results/trace_v1_gradient_boa.csv
uv run anl2026 run --scenario Camera --no-plot --negotiator noam_neg_full.NoamNegFull \
  --opponent examples.boa.BOANeg --export-trace results/trace_v1_full_boa.csv
uv run anl2026 run --scenario Camera --no-plot --negotiator noam_neg_reverse.NoamNegReverse \
  --opponent examples.boa.BOANeg --export-trace results/trace_v1_reverse_boa.csv
```

**Pass criteria:** V1 mean Score in quick panel within ±0.05 of article table (regression guard).

---

### Step 1 — Outcome pool builders

**Goal:** One shared module for the three outcome pools used by both Version 1 logic and Version 2 persona schedules.

**New file:** `noam_neg_pools.py`

| Pool | What it contains | Source in current code |
|------|------------------|------------------------|
| Decoy outcomes | Rational deals that emphasize wrong issue priorities | Copy from `NoamNeg._build_decoy_pool` |
| Truth outcomes | Top slice of your best rational deals | Copy from `NoamNegReverse._build_truth_pool` |
| Closing band | Late-game candidates above a utility floor; optionally excludes top 3 global best | Extend `NoamNeg._pick_closing_bid` filter |

**Pass criteria:** Unit test — pools are non-empty on Camera and NiceOrDie; decoy outcomes mismatch true issue modes
on at least one third of issues.

---

### Step 2 — Opponent type detector

**Goal:** Guess opponent type from their offer stream with at least 70% accuracy on the local opponent panel.

**New file:** `opponent_classifier.py` (name in code can stay technical; behavior is described in Section 11.7)

**Actions:**

1. Implement feature extraction from the opponent’s offer history (frequency concentration, time–utility correlation,
   early vs late issue favorites, and so on).
2. Implement scoring for: preference learner, time-based conceder, inverted-model opponent, phased opponent.
3. Add a debug script that runs each **known** opponent class and prints a confusion matrix:

```bash
# To be added when Version 2 is implemented
uv run python scripts/debug_classifier.py --scenario Camera --steps 100
```

**Pass criteria (offline):**

| Opponent | Expected detected type |
|----------|------------------------|
| BOANeg, MAPNeg, MiCRONegotiator | Preference learner |
| ConcederTBNegotiator, LinearTBNegotiator, BoulwareTBNegotiator | Time-based conceder |
| SimpleNegotiator | Inverted-model opponent |

At least 70% correct by step 20 across all 7 scenarios (2 repeats). Label **Unknown** is acceptable before 8 opponent
offers.

---

### Step 3 — Persona schedule chooser and weighted bid picking

**Goal:** Replace Version 1’s hard `if relative_time < 0.35` branches with persona schedules (Section 11.5).

**New file:** `noam_neg_v2.py` — class `NoamNegV2`

**Actions:**

1. Connect the opponent type detector to the persona schedule chooser (commit after 8 opponent offers).
2. Implement the four schedules: decoy-first (A), truth-first (B), inverted exploit (C), phased opponent (D).
3. Implement weighted bid picking (Section 11.8).
4. Keep Version 1 **acceptance rules** and **closing bid logic** unchanged:
   - Aspiration acceptance (time-decaying target)
   - Accept-if-not-better-than-our-next-bid
   - Deadline acceptance
   - Opponent-model-weighted closing offers

**Pass criteria:**

- Trace inspection: no single-step jump in your own utility greater than 0.25 compared to your previous bid.
- Versus Conceder on Camera (5 repeats): mean Advantage at least reverse Version 1 minus 0.03.
- Versus BOANeg on Camera (5 repeats): mean Concealing at least full flip Version 1 minus 0.03.

---

### Step 4 — Benchmark integration

**Goal:** Run Version 2 in the same harness as the three Version 1 variants.

**Actions:**

1. Add `NoamNegV2` as a fourth row in `scripts/compare_decoy_agents.py` (when implementing — new file entry only).
2. Run the full panel:

```bash
uv run python scripts/compare_decoy_agents.py --repeats 3 --output results/decoy_compare_with_v2.csv
uv run python scripts/summarize_decoy_results.py results/decoy_compare_with_v2.csv
```

**Pass criteria (Version 2 should beat the best Version 1 on the combined metrics):**

| Metric | Target compared to best Version 1 |
|--------|-----------------------------------|
| Mean **Score** (full panel) | At least best Version 1 plus 0.02 |
| Mean **Concealing** vs BOANeg, MAPNeg, MiCRONegotiator | At least 0.68 (between full flip 0.706 and reverse 0.661) |
| Mean **Advantage** vs same learners | At least 0.62 (near reverse 0.640) |
| Mean **Score** vs BOANeg and MAPNeg combined | At least 1.18 (beat full flip ~1.16) |

If targets are missed: tune persona schedule boundaries first (not acceptance rules), then re-run Step 4 only.

---

### Step 5 — Mid-negotiation Concealing telemetry

**Goal:** Understand **why** Version 2 wins or loses on deception, not just the final Score.

**Actions:**

1. Add optional logging to the benchmark script: after each opponent bid, measure how closely their model of your
   utility matches your true utility (Kendall agreement).
2. Write a CSV or plot: negotiation step, relative time, opponent-model accuracy.

**How to read the logs:**

| Pattern in the log | Meaning |
|--------------------|---------|
| Accuracy rises quickly before relative time 0.30 | Early persona was too truthful — bad if opponent is a preference learner |
| Accuracy stays flat until relative time 0.60, then rises | Good decoy seed; late shift to truth hurt Concealing less than expected |
| Accuracy high throughout versus BOANeg | Decoy-first schedule failed — check decoy pool mismatch strength |

**Pass criteria:** Versus BOANeg, final opponent-model accuracy should be less than or equal to full flip Version 1’s
final accuracy in at least 60% of runs.

---

### Step 6 — Article and report artifacts

**Goal:** Reproducible tables and figures for your paper.

**Deliverables:**

1. Summary table: Score, Advantage, Concealing for all three Version 1 variants plus Version 2.
2. Bar chart: mean Score by opponent family.
3. Line chart: opponent-model accuracy over relative time (Version 2 vs reverse vs full flip on BOANeg).
4. One exported negotiation trace with timestamps where the persona schedule changed.

Update Section 3 of this document with a Version 2 results row when Step 4 passes.

---

### Step 7 — Choosing what to submit to ANL 2026

**Goal:** Pick the agent class to upload.

| Outcome of Step 4 | Recommendation |
|-------------------|----------------|
| Version 2 passes all targets | Submit `noam_neg_v2.NoamNegV2` |
| Version 2 wins Score but loses Concealing vs learners | Hybrid: truth-first vs time-based opponents, decoy-first vs learners only |
| Version 2 loses Advantage | Keep Schedule B (truth-first) as default; shorten decoy for learners |
| Opponent detector is unstable | Disable adaptive switching; submit reverse Version 1 (best overall Score in benchmark) |

Always run `anl2026 tournament` and a submission zip dry-run before uploading.

---

## 13. Conclusions and open questions

### Summary table (V1 benchmark)

| Goal | Best current variant | Score evidence |
|------|---------------------|----------------|
| Max **Score** (tournament) | Reverse | 1.542 panel mean |
| Max **Concealing** vs learners | Full flip | 0.706 vs BOA/MAP/MiCRO |
| Max **Advantage** | Reverse | 0.651 panel; 0.640 vs learners |
| Robust all-round fallback | Gradient | Wins Random + Tough; middle on learners |

### Design principles for Version 2 (derived from data)

1. **Different opponents need different early personas.** No single Version 1 variant wins all 15 opponents.
2. **Advantage and Concealing trade off versus learners**, but the trade-off is not harsh — full flip gains +0.045
   Concealing but loses −0.058 Advantage compared to reverse on learners.
3. **Time-based opponents do not punish honest early bids** — save decoy effort for preference learners.
4. **Wrong opponent detection must not ruin the run** — when unsure, fall back to gradient decoy (Version 1 default).
5. **Closing and acceptance rules matter as much as early deception** — reverse won head-to-head on Advantage even when
   Concealing was low.

### Open questions for future experiments

| Question | How to test |
|----------|-------------|
| Does late decoy burst (3–5 bids) erase early truth vs BOA? | Step 5 telemetry + ablation calendar |
| Optimal `MIN_OBSERVATIONS` for classifier? | Sweep 5, 8, 12 on full panel |
| Does excluding top-3 outcomes in closing hurt agreement rate? | Timeout rate in benchmark |
| NiceOrDie failure mode — scenario or agent? | Trace + reserved-value analysis |
| Will competition agents resemble BOA or Conceder more? | Weight learner vs time-based targets in V2 tuning |

---

## 14. Reproducibility and reading the CSV

### Commands

```bash
# Full panel + head-to-head (≈8–9 minutes, 2 repeats)
uv run python scripts/compare_decoy_agents.py --repeats 2 --output results/decoy_compare_full.csv

# Summary tables
uv run python scripts/summarize_decoy_results.py results/decoy_compare_full.csv

# Quick sanity (≈2 minutes)
uv run python scripts/compare_decoy_agents.py --quick --repeats 1

# Single trace for inspection
uv run anl2026 run --scenario Camera --no-plot \
  --negotiator noam_neg_reverse.NoamNegReverse \
  --opponent examples.boa.BOANeg \
  --export-trace trace_reverse_boa.csv
```

### CSV column reference (`decoy_compare_full.csv`)

| Column | Meaning |
|--------|---------|
| `match_type` | `panel` (vs NegMAS opponents) or `head_to_head` (decoy vs decoy) |
| `scenario` | Scenario folder name |
| `agent` | Class name (`NoamNeg`, `NoamNegFull`, `NoamNegReverse`) |
| `agent_mode` | `gradient`, `full`, or `reverse` |
| `opponent` | Opponent class short name |
| `family` | Opponent family label |
| `agent_first` | `first` or `second` mover |
| `runs` | Successful repeats aggregated |
| `advantage`, `concealing`, `score` | Mean metrics over `runs` |

### How to filter in analysis

```python
import csv
rows = list(csv.DictReader(open("results/decoy_compare_full.csv")))
learners = [r for r in rows if r["opponent"] in ("BOANeg", "MAPNeg", "MiCRONegotiator") and r["match_type"] == "panel"]
reverse_vs_boa = [r for r in rows if r["agent_mode"] == "reverse" and r["opponent"] == "BOANeg"]
```

### File map

| File | Role |
|------|------|
| `noam_neg.py` | Gradient (V1 baseline) |
| `noam_neg_full.py` | Full flip variant |
| `noam_neg_reverse.py` | Truth-first variant |
| `scripts/compare_decoy_agents.py` | Benchmark runner |
| `scripts/summarize_decoy_results.py` | CSV aggregator |
| `results/decoy_compare_full.csv` | Raw results (714 rows) |
| `docs/decoy-experiments-article.md` | This document |

---

## References

- ANL 2026 CFP: https://anac.cs.brown.edu/files/anl/y2026/2026cfp.pdf
- Tutorial PDF: https://scml.cs.brown.edu/files/anl/y2026/template2026.pdf
- Local scoring: `main.calc_scores`
- Methodology: [decoy-strategies.md](decoy-strategies.md)
- V1 design: [noamneg-strategy.md](noamneg-strategy.md)
