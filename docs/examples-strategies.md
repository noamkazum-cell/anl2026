# ANL 2026 — Example Agent Strategies

Reference for the three tutorial negotiators in `examples/`. These are **baselines**, not concealment-focused agents.
Use them to understand NegMAS patterns and as opponents in local tournaments.

**Official tutorial:** [ANL 2026 League Tutorial PDF](https://scml.cs.brown.edu/files/anl/y2026/template2026.pdf)

---

## Overview

| Agent                | File                 | Base class          | Architecture                                            |
|----------------------|----------------------|---------------------|---------------------------------------------------------|
| **SimpleNegotiator** | `examples/simple.py` | `SAOCallNegotiator` | Single `__call__` — all logic in one place              |
| **BOANeg**           | `examples/boa.py`    | `BOANegotiator`     | BOA = Bidding + Opponent model + Acceptance             |
| **MAPNeg**           | `examples/map.py`    | `MAPNegotiator`     | MAP = modular components (models, acceptance, offering) |

In NegMAS, **BOA is implemented as a thin wrapper around MAP** (`make_boa` returns a `MAPNegotiator` with one model).
The example `boa.py` and `map.py` files are nearly identical in behavior.

---

## Shared BOA/MAP stack (both examples)

| Component          | Class                     | Role                                                                              |
|--------------------|---------------------------|-----------------------------------------------------------------------------------|
| **Offering**       | `TimeBasedOfferingPolicy` | Concedes over **your** utility as time passes (`PolyAspiration`)                  |
| **Acceptance**     | `ACNext(offering)`        | Accept if incoming offer utility ≥ utility of **your next planned bid**           |
| **Opponent model** | `GSmithFrequencyModel`    | Counts opponent issue-values; frequent values → higher estimated opponent utility |

### `GSmithFrequencyModel` (opponent modeling)

- On each **opponent offer**, increments per-issue value counts.
- `eval(offer)` = average over issues of `(count(value) / max_count_on_issue)`.
- Assumption: *values the opponent keeps proposing are more valuable to them*.
- Stored on the negotiator as `private_info["opponent_ufun"]`.

### Critical limitation for ANL

The default BOA/MAP example **learns** the opponent but **does not use** the model in offering or acceptance:

- `TimeBasedOfferingPolicy` only uses **your** `ufun`.
- `ACNext` only compares **your** utilities.

So Smith runs in the background; tactics are still **time-based self-concession + ACNext**.

### BOA vs MAP (example kwargs)

| Aspect         | `BOANeg`                                         | `MAPNeg`                                         |
|----------------|--------------------------------------------------|--------------------------------------------------|
| Model          | Single `model=GSmithFrequencyModel()`            | `models=[GSmithFrequencyModel()]`                |
| Extra          | —                                                | `acceptance_first=True`, `model_names=["Smith"]` |
| Under the hood | `BOANegotiator` → effectively MAP with one model | `MAPNegotiator` directly                         |

---

## SimpleNegotiator (`examples/simple.py`)

### Opponent model

Assumes opponent utility is the **reverse** of yours:

- Builds `self._inv = self.ufun.invert()`.
- Sets `opponent_ufun` to a weighted combination of constant max and **negative** your utility (linear reverse).

Not learned from offers — fixed assumption.

### Bidding

- First move: `self._inv.best()` (best for inverted = worst for you in a zero-sum sense — actually invert's *best* is
  opponent-favorable side of your space).
- Later: `self._inv.one_in((1.0 - relative_time, 1.0))` — time-based concession on inverted utility.

### Acceptance

- Accept if `ufun(offer) >= 0.8` (80% of your scale).

### Takeaways

| Strength                 | Weakness                               |
|--------------------------|----------------------------------------|
| Easy to read             | Opponent model is crude (reverse ufun) |
| Shows `invert()` pattern | No real concealment                    |
| Good sanity opponent     | Not competitive on complex domains     |

---

## When opponents have opposite preferences

If utilities are strongly opposed (your best ≈ their worst):

| Behavior        | What happens                                                                             |
|-----------------|------------------------------------------------------------------------------------------|
| **Offering**    | Each side still follows **own** time curve — no use of learned model in stock example    |
| **Acceptance**  | ACNext / Simple thresholds on **own** utility only                                       |
| **Smith model** | Can still estimate *their* tastes from their bids — but example stack ignores it         |
| **Outcome**     | Early conflict; agreement only if rational sets overlap; late thin compromise or timeout |

---

## Using examples in development

```bash
# Single run
uv run anl2026 run --scenario Camera --no-plot \
  --negotiator noam_neg.NoamNeg --opponent examples.boa.BOANeg

# Tournament (defaults include Simple, MAP, BOA, Boulware)
uv run anl2026 tournament --scenario Camera
```

### As baselines

Compare **Advantage** vs **Concealing** against each example to see whether you lose on deal quality or preference
leakage.

### As a component library

Explore NegMAS registry for alternatives:

```bash
uv run python -c "from negmas.registry import component_registry as CR; print(CR.keys())"
```

Swap offering, acceptance, or model while keeping MAP/BOA structure — useful before committing logic to `NoamNeg`.

---

## Concealment vs what examples teach

| Topic          | Examples                            | ANL goal                                                                    |
|----------------|-------------------------------------|-----------------------------------------------------------------------------|
| Deception      | Minimal — mostly honest concession  | Hide **your** preferences from opponent's model                             |
| Opponent model | Smith learns; policies don't use it | Your model helps **Advantage**; their model of **you** hurts **Concealing** |
| Bid pattern    | Predictable time concession         | Controlled ambiguity, phased personas                                       |

Examples teach **mechanism and modularity**. Competitive ANL play requires **custom bidding** (see
`docs/noamneg-strategy.md`).

---

## File map

```
examples/
├── simple.py   # SAOCallNegotiator, reverse-ufun assumption
├── boa.py      # BOANegotiator + TimeBased + ACNext + Smith
└── map.py      # MAPNegotiator + same stack, acceptance_first=True
```
