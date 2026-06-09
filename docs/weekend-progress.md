# Weekend Progress Summary

Since the Tuesday decision to stay on the **middle path** (V2.4 decoy persona — not Reverse, not Full flip).

---

## The Starting Point (Tuesday)

We locked in the **middle path**: keep the **decoy persona** (V2.4), not **Reverse** (truth-first) and not **Full** (hard flip).

That choice was evidence-based:

- **Reverse** wins on Advantage / H2H, but **Concealing collapses** vs Smith learners (~0.42–0.66) — bad for ANL scoring.
- **Full flip** didn't beat the gradient middle reliably.
- **V2.4** (`Agent360V2`) was the safe submit: min-offer gate when first, maximal-mismatch decoy pool, no opponent-type routing.

So the strategy was: **hide your prefs, don't chase Reverse's deal extraction.**

---

## What We Built After That (V3)

We didn't abandon the middle — we **kept V2.4's bidding persona** and added **opponent intelligence** on top:

| Layer | Purpose |
|-------|---------|
| **Trajectory + early profiling** | Detect conceding / learner / deceptive / mirror from a few bids |
| **Recency + late-weight Smith** | Ignore opponent decoy phase (t < 0.4), track what they want now |
| **Issue-weighted Smith** | Focus on issues they actually fight over (UO-style filters) |
| **Bait guard** | Closing + acceptance: don't chase Smith spikes vs deceptive opponents |
| **First-seat decoy rotation** | Harder for curve-fit learners to model your opening stream |
| **Competitor-aware signals** | Bait logic only when decoy/bait patterns show — not vs plain BOA/MAP |

**Published `opponent_ufun`** uses the richer model (better Advantage + steals modeling share from them). **Your bid stream** stayed V2.4 decoy logic.

Implementation: `agent360_v3.py`, class `Agent360V3`.

---

## Evaluation We Stood Up

- **Deceptive sparring panel** — Shochan/UO/Renting with decoy+bait on by default (matches expected 2026 entries).
- **Learners** — BOA / MAP / MiCRO in the competition run.
- **Stress panel** — Boulware, tit-for-tat, random, hybrid (weird opponents, not just decoy).
- **Metric that matters** — **excl. Mirror** (Mirror is diagnostic self-play, not the real comp).

Scripts and artifacts:

- `scripts/eval_sparring.py` — competition proxy (`--panel deceptive --include-learners --repeats 4`)
- `scripts/eval_stress.py` — 12 NegMAS "weird" opponents
- `scripts/submission_preflight.py` — tests + smoke run + CSV summary
- `tests/test_agent360_v3.py`, `tests/test_submission.py`

---

## Results: Where We Landed

| Question | Answer |
|----------|--------|
| Did we stay on the middle path? | **Yes** — V3 extends V2.4, not Reverse/Full |
| V3 vs **V2.4** (competition proxy, excl. Mirror)? | **V3 wins** — ~**1.259** vs **1.228** |
| V3 vs **Reverse** on **deceptive lites**? | **V3 wins big** — **1.263** vs **1.105** (+0.16) |
| V3 vs **Reverse** in direct H2H? | Reverse still wins (truth-first vs decoy — expected, irrelevant to comp) |
| V3 vs **weird NegMAS** stress panel? | **V3 +0.009** vs V2.4 |
| vs **learners**? | **Strong** — Concealing ~0.72, Score ~1.29 |

Tuesday's call ("middle, not Reverse") held up. The weekend work was: **make the middle path smarter against deceptive + learning opponents without becoming Reverse.**

---

## Submission Readiness

- **`Agent360V3`** promoted from experiment → submit candidate
- **`submitted.zip`** — `agent360.py` + `agent360_v2.py` + `agent360_v3.py` + `requirements.txt`
- Form: **Module `agent360_v3`, Class `Agent360V3`**
- Bug fix for production (`_recent_own_bids`), tests + smoke runs passing

**V2.4 remains the conservative fallback; V3 is the evidence-backed submit.**

Verify:

```bash
uv run pytest tests/test_agent360_v3.py tests/test_submission.py -q
uv run python main.py run --scenario Camera --no-plot \
  --negotiator agent360_v3.Agent360V3 \
  --opponent negmas.sao.BoulwareTBNegotiator --negotiator-first
```

---

## What We Explicitly Did Not Do

- Promote Reverse or Full flip.
- Tune on Mirror or NiceOrDie means.
- Re-introduce V2.5 soft transition / anti-curve decoy (rejected earlier, −0.043 sparring).
- Opponent-type routing at runtime (design constraint throughout).

---

## Remaining Optional Work (Not Blocking Submit)

- Add "weird opponents" slice to default preflight docs.
- Trace worst first-seat rows (Amsterdam/Grocery × Shochan first ~1.11).
- Update `docs/evaluation.md` with final numbers and submission class.
- Run `--repeats 4` stress panel if more confidence needed.

---

## One Sentence

Since Tuesday we committed to **concealment-first decoy negotiation**; we built **V3** to **model and resist opponent deception** while keeping that persona — and benchmarks show it **beats V2.4 on the real comp proxy** and **crushes Reverse** on deceptive opponents, which is exactly the field we expect.
