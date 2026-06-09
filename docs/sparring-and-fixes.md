# Sparring benchmarks and fix backlog

After building in-house sparring opponents inspired by ANL 2024 top agents (`sparring/`), we identified systematic weaknesses when **opening the negotiation (seat 0)**. This document tracks findings, ablations, and the **V2.4** first-seat fix merged into `Agent360V2`.

**Report / submission strategy:** [agent360-v2.4-strategy.md](agent360-v2.4-strategy.md)  
**Next version plan:** [agent360-v3-plan.md](agent360-v3-plan.md)

**Related:** [evaluation.md](evaluation.md), [decoy-strategies.md](decoy-strategies.md), [noamneg-strategy.md](noamneg-strategy.md).

---

## Why first seat matters

Turn order is not neutral in ANL 2026:

- **First seat** — you define the opening bid stream before the opponent has offered. Curve-fit learners (RentingLite) and rational filters (UOAgentLite) can learn from that solo stream.
- **Second seat** — you react to their offers first; decoy still poisons their Smith model (e.g. ISBT × RentingLite second → Concealing 1.0).

V2.4 adds a **first-seat-only** rule: stay in decoy until the opponent has bid at least **3** times, even if decoy time (0.35) has passed. No opponent-type routing — uses mechanism add-order only.

---

## Sparring pool

| Class | File | Inspired by | Threat |
|-------|------|-------------|--------|
| `ShochanLite` | `sparring/shochan_lite.py` | Shochan 2024 | Boulware aspiration + Smith; **decoy/bait by default** |
| `UOAgentLite` | `sparring/uoagent_lite.py` | UOAgent 2024 | Rational filter + RV tracking; **decoy/bait by default** |
| `RentingLite` | `sparring/renting_lite.py` | AgentRenting2024 | Curve-fit learner; **decoy/bait by default** |
| `LearnerStrong` | `sparring/learner_strong.py` | BOANeg + GSmith | Strong Smith learner |
| `MirrorAgent` | `sparring/mirror.py` | Self-play V2 | Diagnostic only (identical strategy) |

Run sparring benchmarks (default: **deceptive** panel — Shochan/UO/Renting use decoy+bait):

```bash
uv run python scripts/eval_sparring.py --agent v3 --repeats 2 -o results/sparring_v3.csv
uv run python scripts/eval_sparring.py --agent v2 --repeats 2 -o results/sparring_v24_deceptive.csv
uv run python scripts/_compare_sparring_csvs.py
```

Legacy honest lite opponents: add `--panel honest`. Old `results/sparring_v24.csv` is pre-deception (Score ~1.179).

---

## V2.3 sparring baseline (historical reference)

Sparring-only means from `results/sparring_v2_full.csv` (2 repeats):

| Metric | V2.3 |
|--------|------|
| Score | ~1.188 |
| Advantage | ~0.567 |
| Concealing | ~0.621 |

---

## V2.4 submission (`Agent360V2`)

**Change:** `FIRST_MIN_OPPONENT_OFFERS = 3` when `negotiation_seat == 0`. Decoy end stays **0.35**; second seat unchanged.

**Ablation result** (`v2.fs.minoffers`, May 2026):

| Panel | V2.3 | V2.4 (min offers) | Δ |
|-------|------|-------------------|---|
| Sparring all (70) | 1.188 | 1.138 | −0.050 |
| Sparring **excl. Mirror** (56) | 1.140 | **1.150** | **+0.011** |
| Laptop × RentingLite **first** | 0.889 | **1.151** | **+0.26** |

Full-panel mean drops mainly on **Mirror first** (self-play diagnostic). Real sparring opponents improve. **Submit V2.4** (`agent360_v2.Agent360V2`, `--agent v2`).

Re-benchmark after merge:

```bash
uv run python scripts/eval_sparring.py --agent v2 --repeats 2 --output results/sparring_v24.csv
uv run python scripts/eval_sparring.py --agent v2 --repeats 2 --include-learners --output results/sparring_v24_full.csv
```

---

## Trace evidence (May 2026)

Debug runs with `--export-trace`:

| Matchup | Seat | Score | Concealing | Notes |
|---------|------|-------|------------|-------|
| Laptop × RentingLite | **first** | 1.171 | 0.594 | Worst sparring bucket historically (~0.888 mean); single run better than panel mean |
| ISBT × RentingLite | **second** | 1.512 | **1.0** | Opponent opens; our decoy poisons their model |

Commands:

```bash
uv run anl2026 run --scenario Laptop --no-plot --negotiator agent360_v2.Agent360V2 \
  --opponent sparring.renting_lite.RentingLite --negotiator-first \
  --export-trace results/laptop_renting_first.csv

uv run anl2026 run --scenario ISBTAcquisition --no-plot --negotiator agent360_v2.Agent360V2 \
  --opponent sparring.renting_lite.RentingLite --opponent-first \
  --export-trace results/isbt_renting_second.csv
```

**Pattern:** Going **first** against **curve-fit** (RentingLite) and **rational-filter** (UOAgentLite) learners leaks Concealing when our solo bid stream looks like a smooth concession curve (decoy → transition).

---

## Fix backlog

| ID | Problem | Root cause | Status |
|----|---------|------------|--------|
| **F1** | Laptop × RentingLite **first** — low Concealing | Opponent fits utility vs time on our opening stream | **Fixed in V2.4** (min-offer gate) |
| **F2** | Amsterdam/Camera/ISBT × UOAgentLite **first** | Rational filter narrows search from our early bids | Partially addressed by F1 (longer decoy, delayed transition) |
| **F3** | NiceOrDie low scores | Degenerate domain (1 issue) | **Ignore** for tuning aggregates |
| **F4** | Seat-aware closing only (`v2.adaptive`) | Selfish closing when first did not beat V2.3 on sparring | **Deprioritized** |
| **F5** | Reverse beats V2 on some first-seat matchups | Truth-first wins Advantage when decoy fails | **Not for submission** — kills Concealing globally |
| **F6** | Phase jitter / shuffle (V2.5 experiments) | Hurt reproducibility without net gain | **Reverted** |
| **F7** | V3: model opponent deception, exploit for Advantage | Need richer opponent model than Smith | **Planned** — [agent360-v3-plan.md](agent360-v3-plan.md) |
| **F8** | V2.5 soft transition + anti-curve decoy | Tested May 2026 | **Rejected** — sparring 1.135 vs V2.4 1.179 (−0.043) |

---

## V2.5 trial (rejected)

`Agent360V2_5` added soft first-seat transition (decoy mix 0.85, progress scale 0.72) + utility-jump decoy picks. Full sparring mean **1.123** vs V2.4 **1.179** (−0.056). **Keep V2.4 for submission.**

```bash
uv run python scripts/eval_sparring.py --agent v2.5 --repeats 2 -o results/sparring_v25.csv
uv run python scripts/_compare_sparring_csvs.py results/sparring_v24.csv results/sparring_v25.csv
```

---

## First-seat ablations (experiments)

Full combo (`Agent360V2FirstSeat`: long decoy + min + rotate) regressed −0.069 — **not merged**.

| Label | Class | Knob | Sparring mean |
|-------|-------|------|---------------|
| **`v2` (V2.4)** | **`Agent360V2`** | **min offers (merged)** | **1.138** |
| `v2.fs.longdecoy38` | `Agent360V2FirstSeatLongDecoy38` | Decoy end 0.38 | 1.138 |
| `v2.fs.minoffers` | `Agent360V2FirstSeatMinOffersAblate` | Same as V2.4 | 1.138 |
| `v2.fs.longdecoy` | `Agent360V2FirstSeatLongDecoy` | Decoy end 0.42 | 1.135 |
| `v2.fs.min38` | `Agent360V2FirstSeatMinOffersLong38` | Min + 0.38 | 1.128 |
| `v2.fs.rotate` | `Agent360V2FirstSeatRotate` | Decoy rotation | 1.119 |
| `v2.firstseat` | `Agent360V2FirstSeat` | All three | 1.119 |

```bash
uv run python scripts/eval_firstseat_ablations.py --skip-baseline --repeats 2
uv run python scripts/_compare_sparring_csvs.py results/sparring_v2_full.csv results/ablations/v2_fs_minoffers.csv
```

---

## Deferred: V3 opponent modeling

See **[agent360-v3-plan.md](agent360-v3-plan.md)** for the full implementation plan. Summary: offer-utility trajectory, bluff detection, blended closing—**V2.4 decoy persona unchanged**.

---

## Agent variant map

| Label | Class | Role |
|-------|-------|------|
| `gradient` | `Agent360` | V1 baseline |
| **`v2`** | **`Agent360V2`** | **V2.4 submission — min-offer gate when first** |
| `v2.fs.minoffers` | `Agent360V2FirstSeatMinOffersAblate` | Ablate alias (same knob as V2.4) |
| `v2.fs.rotate` | `Agent360V2FirstSeatRotate` | Ablate: decoy rotation |
| `v2.fs.longdecoy` | `Agent360V2FirstSeatLongDecoy` | Ablate: decoy end 0.42 |
| `v2.fs.longdecoy38` | `Agent360V2FirstSeatLongDecoy38` | Ablate: decoy end 0.38 |
| `v2.fs.min38` | `Agent360V2FirstSeatMinOffersLong38` | Ablate: min offers + 0.38 |
| `v2.firstseat` | `Agent360V2FirstSeat` | Full combo experiment (not merged) |
| `v2.adaptive` | `Agent360V2Adaptive` | Seat-aware closing (did not beat V2.3) |
| `full` | `Agent360Full` | Max flip decoy |
| `reverse` | `Agent360Reverse` | Truth-first — high Advantage, poor Concealing |

---

## Worst V2.3 sparring losses (excluding NiceOrDie)

| Score | Matchup | Issue |
|-------|---------|-------|
| 0.888 | Laptop × RentingLite first | Concealing ~0.31 |
| 0.819 | ISBT × UOAgentLite first | Low Advantage + weak Concealing |
| ~1.03–1.05 | Amsterdam/Camera × UOAgentLite first | Concealing ~0.50 |

By scenario (sparring mean): NiceOrDie 0.76, Amsterdam 1.16, Camera 1.19, Laptop 1.24, Grocery 1.24, ISBT 1.30, Car 1.42.
