# Weekend progress summary (since the “middle path” decision)

Summary of work since Tuesday, when we concluded the submission strategy should stay on the **decoy persona middle ground** — not Reverse (truth-first) and not Full flip (abrupt persona switch).

---

## The starting point (Tuesday)

We locked in the **middle path**: keep the **decoy persona** (V2.4), not **Reverse** (truth-first) and not **Full** (hard flip).

That choice was evidence-based:

- **Reverse** wins on Advantage / H2H, but **Concealing collapses** vs Smith learners (~0.42–0.66) — bad for ANL scoring.
- **Full flip** didn’t beat the gradient middle reliably.
- **V2.4** (`Agent360V2`) was the safe submit: min-offer gate when first, maximal-mismatch decoy pool, no opponent-type routing.

So the strategy was: **hide your prefs, don’t chase Reverse’s deal extraction.**

---

## What we built after that (V3)

We didn’t abandon the middle — we **kept V2.4’s bidding persona** and added **opponent intelligence** on top:

| Layer | Purpose |
|-------|---------|
| **Trajectory + early profiling** | Detect conceding / learner / deceptive / mirror from a few bids |
| **Recency + late-weight Smith** | Ignore opponent decoy phase (t < 0.4), track what they want now |
| **Issue-weighted Smith** | Focus on issues they actually fight over (UO-style filters) |
| **Bait guard** | Closing + acceptance: don’t chase Smith spikes vs deceptive opponents |
| **First-seat decoy rotation** | Harder for curve-fit learners to model your opening stream |
| **Competitor-aware signals** | Bait logic only when decoy/bait patterns show — not vs plain BOA/MAP |

**Published `opponent_ufun`** uses the richer model (better Advantage + steals modeling share from them). **Your bid stream** stayed V2.4 decoy logic.

Implementation: `agent360_v3.py`, class `Agent360V3`.

---

## Evaluation we stood up

- **Deceptive sparring panel** — Shochan/UO/Renting with decoy+bait on by default (matches expected 2026 entries).
- **Learners** — BOA / MAP / MiCRO in the competition run.
- **Stress panel** — Boulware, tit-for-tat, random, hybrid (weird opponents, not just decoy).
- **Metric that matters** — **excl. Mirror** (Mirror is diagnostic self-play, not the real comp).

Scripts and tooling:

- `scripts/eval_sparring.py` — competition proxy (`--panel deceptive --include-learners --repeats 4`)
- `scripts/eval_stress.py` — 12 NegMAS “weird” opponents
- `scripts/submission_preflight.py` — tests + smoke run + CSV summary
- `make_submitted_zip.bat` / `.sh` — V3 zip: `agent360.py`, `agent360_v2.py`, `agent360_v3.py`, `requirements.txt`
- Tests: `tests/test_agent360_v3.py`, `tests/test_submission.py`

---

## Results: where we landed

| Question | Answer |
|----------|--------|
| Did we stay on the middle path? | **Yes** — V3 extends V2.4, not Reverse/Full |
| V3 vs **V2.4** (competition proxy, excl. Mirror)? | **V3 wins** — ~**1.259** vs **1.228** |
| V3 vs **Reverse** on **deceptive lites**? | **V3 wins big** — **1.263** vs **1.105** (+0.16) |
| V3 vs **Reverse** in direct H2H? | Reverse still wins (truth-first vs decoy — expected, irrelevant to comp) |
| V3 vs **weird NegMAS** stress panel? | **V3 +0.009** vs V2.4 |
| vs **learners**? | **Strong** — Concealing ~0.72, Score ~1.29 |

Canonical benchmark files: `sparring_competition.csv`, `stress_v3_v2.csv`.

Tuesday’s call (“middle, not Reverse”) held up. The weekend work was: **make the middle path smarter against deceptive + learning opponents without becoming Reverse.**

---

## Strategic conclusions

1. **Middle path validated:** Decoy persona (V2.4 base) + smarter opponent model (V3) beats truth-first (Reverse) on **deceptive opponents** and **learners**.
2. **Reverse is not the competition answer** — wins H2H and NegMAS time-based panel on Advantage, loses Concealing badly when opponents model you.
3. **Three tactics (decoy / bait / Smith)** are the main threat model for tuning, not the only possible deception — V3 has learner-safe fallbacks when concealment signals aren’t present.
4. **V3 is submission-ready:** `Agent360V3`, module `agent360_v3`, zip `submitted.zip` created, smoke runs pass.

---

## What we explicitly did *not* do

- Promote Reverse or Full flip.
- Tune on Mirror or NiceOrDie means.
- Re-introduce V2.5 soft transition / anti-curve decoy (rejected earlier, −0.043 sparring).
- Opponent-type routing at runtime (design constraint throughout).

---

## Submission checklist

```text
Agent Module: agent360_v3
Agent Class:  Agent360V3
Upload:       submitted.zip

Verify:
  uv run pytest tests/test_agent360_v3.py tests/test_submission.py -q
  uv run python main.py run --scenario Camera --no-plot \
    --negotiator agent360_v3.Agent360V3 \
    --opponent negmas.sao.BoulwareTBNegotiator --negotiator-first
```

**V2.4 remains the conservative fallback; V3 is the evidence-backed submit.**

---

## Remaining optional work (not blocking submit)

- Add “weird opponents” slice to default preflight docs.
- Trace worst first-seat rows (Amsterdam/Grocery × Shochan first ~1.11).
- Update `docs/evaluation.md` / v3 plan with final numbers and submission class.
- Run `--repeats 4` stress panel if more confidence needed.

---

## One sentence

Since Tuesday we committed to **concealment-first decoy negotiation**; we built **V3** to **model and resist opponent deception** while keeping that persona — and benchmarks show it **beats V2.4 on the real comp proxy** and **crushes Reverse** on deceptive opponents, which is exactly the field we expect.
