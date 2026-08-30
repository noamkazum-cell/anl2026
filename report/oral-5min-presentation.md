# 5-Minute Oral Presentation — ANAC 2026

**Presenter:** Noam Kazum  
**Team:** Noam Kazum · Omer Shani Steinmetz  
**Supervisors:** Dr. Galit Haim · Dr. Raz Lin  
**Institution:** The College of Management Academic Studies  
**Duration:** ~5 minutes (~700–750 words at ~140–150 wpm)  
**Context:** Background colloquium deck loops; Agent360 + GunnerAgent posters on display

---

## How to use this on the day

- Speak to the room; posters and the looping deck carry the visuals — this is a spoken tour, not a slide read.
- Point at the relevant poster when you name each agent.
- If cut short: keep the **bold closers** in each block and jump to the comparison + thank-you.
- Credit **Omer** once as co-author in the opening. Do **not** assign agents or tasks to either of you — present both as joint work. Be ready to answer Gunner and Agent360 questions with equal fluency.

---

## Timing map

| Time      | Block                | ~Words |
|-----------|----------------------|--------|
| 0:00–0:40 | Opening              | ~90    |
| 0:40–1:20 | Competition frame    | ~100   |
| 1:20–3:00 | Agent360 (ANL)       | ~260   |
| 3:00–4:20 | GunnerAgent (HAN)    | ~200   |
| 4:20–5:00 | Comparison + close   | ~120   |

---

## Pocket cue card

1. Two leagues → two agents
2. ANL = Advantage + Concealing → decoy persona (gradient won)
3. Three layers: bid / model / accept
4. HAN = utility + perception → Core + LLM (LLM never changes numbers)
5. Two-phase concession + first-offer template
6. Thesis: scoring rule + data budget; separate concerns; test broadly

---

## Full spoken script

### 0:00–0:40 — Opening

Good morning. I’m **Noam Kazum**. This is our semester project with **Omer Shani**, supervised by **Dr. Galit Haim** and **Dr. Raz Lin**, from the College of Management.

This semester we competed in **ANAC 2026** — the international Automated Negotiating Agents Competition at IJCAI. We didn’t submit one agent; we submitted **two**, for **two different leagues**, because each league asked a different research question.

You’ll see both on the posters: **Agent360** for the Automated Negotiation League, and **GunnerAgent** for the Human–Agent Negotiation League.

---

### 0:40–1:20 — Competition frame

ANAC has run since 2010. Every year the challenge changes. You submit Python agents; they run in tournaments you don’t fully control.

Both of our leagues use **bilateral alternating offers** over **multi-issue** deals — packages, not just a single price — on the **NegMAS** platform.

What’s different is the **opponent** and the **score**:

- In **ANL**, you negotiate against **other agents**, and in 2026 you’re scored on **Advantage plus Concealing**.
- In **HAN**, you negotiate against **real humans**, every move needs an **offer plus a short message**, and you’re scored on **deal utility plus human perception**.

Same stack, opposite pressures.

---

### 1:20–3:00 — Agent360 (ANL)

**Agent360** answers: how do you get a good deal while preventing the opponent from learning your true preferences from your bids?

Most league agents are **frequency learners**: values you bid often look like high priorities. If we bid sincerely from round one, Advantage may look fine, but **Concealing collapses**.

So we treated the early bid stream as a **research problem**. We tested three bidding personas:

1. **Reverse** — honest top outcomes first, misdirect later
2. **Full flip** — completely wrong early, then abrupt switch
3. **Gradient** — sustained mismatch, gradual transition to truth

**Reverse** and **full flip** failed against the learner-heavy field. The winner was the **gradient / decoy persona**: early bids that **misrepresent** issue priorities, then a controlled transition, then closing for deal quality.

Architecturally we kept three separate layers so one change doesn’t break the other:

1. **Bidding persona** — decoy → transition → closing
2. **Opponent model** — Smith-style frequency models plus behavioral modes — learner, conceding, deceptive, mirror
3. **Deal extraction** — when we accept, including bait rejection near the deadline

We also learned that **who opens matters**: the first seat exposes more bids to the learner, so we hold the decoy longer there. Everything runs from the bid stream only — **no oracle** access to the opponent’s class or true utility.

Local panels against learners, time-based stress agents, and deceptive sparring partners guided what we kept and what we rolled back — for example we rejected reverse-psychology and mid-game escape acceptance after they hurt the combined score.

---

### 3:00–4:20 — GunnerAgent (HAN)

**GunnerAgent** is the opposite problem: short, human-paced sessions — about **ten offers per side** — and half the score is whether you **sound trustworthy**.

The key design decision is a **hard split**:

- **GunnerCore** decides every accept/reject and every offer — deterministic strategy, adapted from **Shochan**, the ANAC 2024 winner, but without access to the partner’s true utility.
- An **LLM wrapper** only writes the two-to-three sentence message **after** the move is fixed. If the model fails, we send a **fallback** — never a bad numerical offer.

One concession curve doesn’t work with humans: Boulware looks robotic, Conceder gives value away, linear is too predictable. So we use **two phases by relative time**:

- Early **anchor**: show movement without giving real value
- Later **settle**: hold, then concede sharply near the deadline

For opponent modeling with so little data, classical frequency tables fail — humans open near their preferences, then concede. We treat the **first offer as a template**, and for larger issue spaces we weight issues the partner **keeps stable**.

---

### 4:20–5:00 — Comparison + close

So the thesis of the project is simple: **match strategy to the scoring rule and the data budget**.

- **Agent360** faces learning agents, many rounds, offers only — optimize deal quality **and hide** preferences; early game is a decoy persona with gradual truth.
- **GunnerAgent** faces humans, about ten rounds, message every turn — optimize utility **and perceived trust**; early game anchors without giving value; numbers core stays separate from the language layer.

Five lessons we take away:

1. The scoring rule defines the strategy
2. Opponent modeling must fit how much data you get
3. Evaluate across opponent families, not one benchmark
4. Separate layers that fail independently
5. Prefer empirical iteration over intuition

Thank you — happy to take questions about either agent, the experiments, or the design tradeoffs.

---

## Optional shortened close (~30s) if time is cut

We built two agents for two leagues: Agent360 hides preferences from learners with a decoy persona; GunnerAgent gets good deals with humans while sounding trustworthy via a Core-plus-LLM split. The lesson: strategy follows the scoring rule and the data budget. Thank you — questions welcome.

---

## Practice checklist

- [ ] Read the full script out loud once with a timer; land under 5:00
- [ ] Mark one breath pause after each block
- [ ] Practice pointing: Agent360 poster → GunnerAgent poster → both for the thesis
- [ ] Drill Gunner cold as hard as Agent360 (Core/LLM, two phases, first-offer template)
- [ ] Prep three answers cold: why reverse lost · Core vs LLM · first-offer template vs frequency
- [ ] If asked something unknown: “We didn’t measure that directly; what we did measure was …” then pivot
- [ ] Never assign “I did X / Omer did Y” — always “we”
