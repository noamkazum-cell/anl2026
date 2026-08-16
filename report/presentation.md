# Semester Presentation — ANL 2026 & HAN 2026

**Duration:** ~20 minutes (~20 slides in md; v2 deck has section dividers → 25 slides)  
**Design rule:** max 3–4 bullets per slide — detail lives in speaker notes  
**Regenerate pptx:** `python scripts/build_presentation_pptx.py` → `report/presentation_v2.pptx`

---

## Slide 1 — Title

### Bullets
- Noam Kazum · Omer Shani
- Dr. Galit Haim · Dr. Raz Lin
- **Agent360** · **GunnerAgent**

### Speaker script

Good morning. This semester our project focused on the Automated Negotiating Agents Competition — ANAC 2026, which runs as part of IJCAI. We built two negotiation agents for two different leagues in the same competition, and each league posed a genuinely different research problem.

---

## Slide 2 — What Is ANAC?

### Bullets
- International negotiation agent competition since 2010 (IJCAI / AAMAS)
- New research challenge every year
- Submit Python code → online round-robin tournaments

### Speaker script

ANAC is essentially the world cup of automated negotiation. Teams from universities around the world design agents that bargain over multi-issue deals — not just haggling over a price, but packages like price, warranty, delivery time, and so on. You submit your code, the organizers run it on scenarios and opponents you don't fully control, and the best strategies are presented at IJCAI.

What's important: the challenge changes every year. Our semester wasn't "tweak last year's winner" — it was read the new rules, research, benchmark, iterate, write up.

---

## Slide 3 — What Is the ANL?

### Bullets
- **Automated Negotiation League** — agents negotiate against other agents
- Bilateral **alternating offers** over multi-issue deals (NegMAS)
- Each year a **different research challenge**
- Our agent: **Agent360**

### Speaker script

The Automated Negotiation League is the classic ANAC track: your agent faces other submitted agents in bilateral negotiation over multi-issue scenarios — implemented in NegMAS.

Every year the league poses a different research question. 2026 is concealment — next slide. Agent360 is our answer.

---

## Slide 4 — ANL 2026: What's New

### Bullets
- Back to **bilateral** agent vs agent
- **Score = Advantage + Concealing**
- Concealing: how *poorly* the opponent learned your true preferences from your bids
- Being modeled correctly **hurts** your score — strategic misrepresentation matters

### Speaker script

2026 brings us back to bilateral negotiation, but with a new scoring dimension: concealment. You're still rewarded for a good deal — Advantage — but also for how poorly your opponent learned your true preferences from your bids.

If opponents figure out what you care about, your concealment score drops even if the deal is fine. Agent360 was built for that tradeoff.

---

## Slide 5 — What Is the HAN?

### Bullets
- **Human–Agent Negotiation League** — agent vs **real people**
- **2026:** every move = offer **+ text**; scored on utility **and** human **perception**
- ~**10 offers per side** — human-paced; LLM round → then real humans
- Our agent: **GunnerAgent**

### Speaker script

The Human–Agent Negotiation League is the opposite opponent type: real humans, not algorithms. Last year was a pilot at IJCAI — offers only, utility only, no text channel.

2026 is a full league track: every move needs a natural-language message, and you're scored on the deal plus post-negotiation questionnaires about whether you seemed trustworthy. About ten propose calls per side — every round counts.

GunnerAgent is our HAN submission. Core tension: extract a good deal while passing as a real negotiator.

---

## Slide 6 — Two Agents, Two Challenges

### Bullets
- **Agent360 (ANL)** — good deal + **hide** preferences from learning agents
- **GunnerAgent (HAN)** — good deal + **sound human** to a real partner
- Both: **NegMAS**, alternating offers, multi-issue deals
- **Next:** Agent360 deep dive → GunnerAgent → full comparison at the end

### Speaker script

Our two submissions mirror the two leagues.

Agent360 targets concealment against learning opponents. GunnerAgent targets human-paced negotiation with a message every turn.

Same stack — different strategy. Agent360 first, then GunnerAgent, then compare at the end.

---

## Slide 7 — Agent360: Two Goals at Once

### Bullets
- **Score = Advantage + Concealing** — both count equally
- **Advantage:** final deal utility minus your reservation value
- **Concealing:** opponent's learned model of you should stay **wrong**
- Designing Agent360 means balancing both — not maximizing either alone

### Speaker script

Let's zoom into Agent360. Remember the 2026 ANL rule from earlier: you're scored on two things at once.

Advantage is the familiar part — did you close a deal better than your walk-away value?

Concealing is what's new — after the negotiation, organizers check how well your opponent modeled your true preferences from your bids.

So Agent360 isn't a pure deal-maximizer. Every bid is both a negotiation move and a signal about your priorities.

---

## Slide 8 — Agent360: Why the Bid Stream Is the Battleground

### Bullets
- Most ANL opponents are **frequency learners** — infer priorities from repeated bid values
- Bid sincerely from round one → decent deals, **terrible concealment**
- Research question: **which early persona misleads them?**

### Speaker script

Why does the scoring rule matter? Most league agents learn from your bid stream — frequent values look like high priorities.

Bid sincerely and Advantage may look fine, but the opponent's model converges quickly and Concealing collapses.

So we started with research: what should we show early to mislead learners without giving up the deal?

---

## Slide 9 — Research: Three Decoy Personas

### Bullets
- **Gradient:** gradual mismatch, slow transition to truth
- **Full flip:** wrong priorities early, abrupt switch
- **Reverse:** sincere top outcomes first, misdirect later

### Speaker script

We treated this as empirical research, not a guess. Three variants shared the same acceptance logic and opponent modeling — they differed only in what they show early.

Gradient: partially wrong priorities, gradual blend toward truth — hardest to detect, no sudden tell. Full flip: maximally wrong, then jump to a true band. Reverse: open with your actual best outcomes, then shift toward misdirection — the hypothesis that some opponents distrust bids.

We benchmarked all three across competition scenarios, both seats, against learner and deceptive opponents.

---

## Slide 10 — Research: The Middle Path Won

### Bullets
- **Reverse rejected** — concealment collapsed vs learners
- **Full flip rejected** — fragile when opponents adapt mid-game
- **Winner:** sustained **decoy persona**, gradual truth later

### Speaker script

Reverse looked good in some matchups but failed against the learner agents that dominate the field. Full flip didn't beat the middle ground reliably.

The winner: a sustained false early signal with gradual revelation when deal extraction matters more. That's the core of Agent360.

---

## Slide 11 — Agent360: Three Layers

### Bullets
1. **Bidding persona** — what we offer (decoy → transition → closing)
2. **Opponent model** — what we infer from their bids
3. **Deal extraction** — when we accept

### Speaker script

Three separate layers — so improving deal extraction never accidentally breaks the decoy persona.

On each step: partner offer → update model → accept? → else bid from current phase.

---

## Slide 12 — Agent360: Three Phases

### Bullets
- **Decoy (early):** bid outcomes that **misrepresent** true priorities
- **Transition (middle):** mix decoy with gradually widening good outcomes
- **Closing (late):** prioritize deal quality as deadline approaches
- First seat holds decoy **longer** — more bids exposed to the learner

### Speaker script

Three phases — not one abrupt flip. Early: bids that disagree with what we actually care about. Middle: slowly introduce good outcomes while still sprinkling decoys. Late: shift toward closing.

Who opens matters — first seat exposes more bids, so we hold the decoy longer there.

---

## Slide 13 — Agent360: Modeling & Acceptance

### Bullets
- Opponent model: **frequency-based**, refined for deceptive or conceding partners
- Classify partner **behavior** (mirroring, learning, conceding, baiting)
- Accept when offer beats our aspiration — reject obvious **traps** from deceptive opponents

### Speaker script

We model the opponent from their bid stream — same family most league agents use, which is exactly what our decoy tries to fool. Refinements handle partners who also mislead or freeze issues.

Acceptance uses aspiration curves and deadline safety, with guards against bait offers from deceptive opponents. We kept changes only when they helped across opponent types — not just one benchmark.

That wraps Agent360. Next: GunnerAgent and the human setting.

---

## Slide 14 — HAN: What GunnerAgent Must Handle

### Bullets
- **Who:** real humans — every turn = offer **+ message**; they judge trust, not just numbers
- **Scored on:** deal **utility** + human **perception** (post-negotiation questionnaires)
- **Hard part:** ~**10 offers** per side; **no opponent utility** — only bids and messages
- **Job:** get a good deal **and** sound human with almost no partner data

### Speaker script

HAN is not harder math — it's math plus performance. Half the score is whether the human thought you were a person.

ANL gives you opponent utility; HAN does not. GunnerAgent must negotiate and perform at the same time.

---

## Slide 15 — GunnerAgent: Two Layers (Core + LLM)

### Bullets
- **GunnerCore:** accept/reject + every offer — Shochan adapted for hidden opponent utility
- **LLM wrapper:** writes 2–3 sentences **after** the move is fixed — never changes numbers
- **Why split:** LLM glitch → fallback message, **not** a bad offer
- LLM never sees our utility, reservation value, or priorities

### Speaker script

Main design decision: numbers first, words second. Strategy stays deterministic; the LLM only handles presentation.

If the model crashes, canned fallbacks go out. Omer's split is what makes this safe against real humans.

---

## Slide 16 — How GunnerAgent Concedes (Two Phases by Time)

### Bullets
- **One curve fails:** Boulware = robotic repeats; Conceder = gives value early; Linear = human waits
- **Phase 1 — Anchor (t < 0.4):** threshold 1.0 → 0.7 — **movement without giving real value**
- **Phase 2 — Settle (t ≥ 0.4):** hold ~0.7, then **sharp drop** near deadline — time pressure closes
- **Same curve** for accept **and** propose (Pareto filter, rank, no-repeat cap)

### Speaker script

Phases are by **relative time**, not round count — say "first 40% of the clock," not "rounds 1–5."

Phase 1: human sees progress. Phase 2: urgency to agree before time runs out.

---

## Slide 17 — Guessing What the Human Wants (~10 Offers)

### Bullets
- **Hidden utility** — guess from ~10 offers; used only to **rank** our proposals, not accept/reject
- **Frequency models fail:** human opens with preferences, then **concedes** — table fills with wrong values
- **First offer = template:** opening bid is the real preference sketch; later bids are mostly concession
- **≤2 issues:** match to first offer · **≥3 issues:** also weight issues they **keep unchanged**

### Speaker script

Example: human opens demanding high warranty, later concedes on price. Frequency model thinks they don't care about warranty. Template model remembers the opening.

We never estimate their reservation value — too few data points.

---

## Slide 18 — Making It Sound Human (LLM Layer)

### Bullets
- LLM **only talks** — core already decided; presentation is **half the HAN score**
- **Move labels** for us + partner so tone matches the numbers (warm but firm)
- **Modular prompts** — small editable pieces, not one giant block that breaks when you fix one line
- **Fallbacks** on timeout/bad JSON — never silent, never contradicts the offer

### Speaker script

Each turn: label what we did and what they did, then LLM writes to match. Persona is warm and assertive — not robotic, not apologetic.

Utilities never enter the prompt. Close Gunner section here.

---

## Slide 19 — Same Stack, Opposite Strategies

### Bullets

#### Agent360 (ANL)
- **Opponent:** learning agents · many rounds · offers only
- **Optimize:** deal quality + **hide** preferences
- **Early game:** decoy persona → gradual truth
- **Shape:** persona / model / acceptance — kept separate

#### GunnerAgent (HAN)
- **Opponent:** humans · ~10 rounds · message every turn
- **Optimize:** utility + **perceived trust**
- **Early game:** anchor — move without giving value
- **Shape:** numerical core + language layer (text only)

#### Shared
- NegMAS · alternating offers · Shochan lineage · benchmark before shipping

### Speaker script

You've now seen both agents. Same NegMAS foundation — opposite choices wherever the leagues differ.

Agent360 misleads learners with a decoy persona; GunnerAgent anchors early and sounds human while the numerical core holds firm. Both inherited from Shochan and only kept changes that helped across opponent types.

One thesis: match strategy to the scoring rule and the data budget.

---

## Slide 20 — Lessons & Conclusions

### Bullets
1. Scoring rule defines the strategy
2. Opponent modeling must fit the data budget
3. Evaluate across opponent families
4. Separate concerns that fail independently
5. Empirical iteration over intuition

### Speaker script

Five lessons. The scoring rule defines the strategy. Modeling must fit the data budget. No single benchmark tells the whole story. Separate what fails independently — persona from acceptance, numbers from language. Research, benchmark, keep or rollback.

Thank you. Happy to take questions.

---

## Appendix — Timing guide (~20 min)

| Slides (md) | Block | ~Time |
|-------------|-------|-------|
| 1–2 | Title & ANAC | 2:00 |
| 3–5 | ANL & HAN intro | 3:00 |
| 6 | Two agents (brief) | 0:45 |
| 7–13 | Agent360 | 6:30 |
| 14–18 | GunnerAgent | 5:45 |
| 19–20 | Comparison & close | 2:30 |

**v2 deck (25 slides):** adds roadmap, section dividers, thank-you — same content blocks; Gunner = slides 17–22.
