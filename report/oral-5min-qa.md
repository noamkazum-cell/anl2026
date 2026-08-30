# Judge Q&A — ANAC 2026 Oral

**Presenter:** Noam Kazum  
**Team:** Noam Kazum · Omer Shani Steinmetz  
**Agents:** Agent360 (ANL) · GunnerAgent (HAN)  
**Use with:** `report/oral-5min-presentation.md`

---

## How to use this

- Present both agents as **joint work**. Never say who coded which part.
- Learn the **one-sentence answers** first; expand only if the judge digs in.
- Be equally fluent on **GunnerAgent** and **Agent360** — judges will ask about both.
- If you don’t know: “We didn’t measure that directly; what we did measure was …” → pivot to a panel result or a design choice you kept/rejected.
- Prefer concrete numbers and rejected alternatives over vague claims.

---

## Quick triad (memorize cold)

1. **Why reverse lost (Agent360):** Opening sincere trains frequency learners; concealment collapsed vs BOA/MAP/MiCRO-style agents.
2. **Why Core + LLM (Gunner):** LLM failure must never produce a bad offer; numbers first, words second, fallbacks if the model fails.
3. **Why first-offer template (Gunner):** With ~10 turns, humans open near preferences then concede — frequency tables fill with the wrong values.

---

## 1. Big-picture / project

### Why two agents instead of focusing on one?

The leagues ask incompatible questions. ANL rewards hiding preferences from learners over many rounds; HAN rewards sounding human with ~10 turns and a message every move. One strategy can’t optimize both. Comparing them sharpens the research claim: strategy follows scoring rule and data budget.

### What’s the main scientific contribution?

For **Agent360**: an empirically validated **concealment-first** persona (gradient over reverse/full-flip), with seat-aware phasing and mode-aware acceptance, without oracle info.  
For **GunnerAgent**: a **safe Core+LLM split** plus a **two-phase** concession and **first-offer template** model suited to HAN’s short horizon.

### Who is on the team?

**Noam Kazum** and **Omer Shani**, supervised by **Dr. Galit Haim** and **Dr. Raz Lin**, College of Management. We developed both agents together for ANAC 2026.

### What would you do with another semester?

**Agent360** — richer opponent classification and online tuning of decoy length.  
**GunnerAgent** — opponent-type adaptation of the concession exponent; sharper issue-importance from concession order; better handling when the outcome space is tiny and the no-repeat cap runs out.

### What’s the single-sentence thesis?

**Strategy must follow the scoring rule and the data budget — and concerns that fail independently should live in separate layers.**

---

## 2. Agent360 / ANL

### Isn’t deception unethical / against “good AI”?

In ANL 2026, **Concealing is an explicit scoring axis**. The rules incentivize misrepresentation in the bid stream — competitive signaling, not verbal lying. We study how agents respond to that incentive. In cooperative or incentive-compatible settings, honesty can be optimal; here the score pushes the opposite way on concealment.

### Why not just bid randomly to maximize concealment?

Random bids destroy Advantage and often look incoherent. We use **rational** outcomes that **mismatch** true top issues but stay above a utility floor — so we still have a path to good deals in transition and closing.

### Explain Concealing in one sentence.

After the session, if the opponent’s inferred utility of you correlates well with your true utility, your Concealing score is low — so we want their model to stay **wrong**.

### Why did reverse psychology lose?

Opening with sincere high-utility outcomes trains frequency learners correctly. Local gains vs some time-based agents were outweighed by concealment losses vs BOA/MAP/MiCRO-style learners that dominate the field.

### What’s “maximal-mismatch decoy”?

From our rational outcomes, pick ones that disagree with our true preferred values on **at least half the issues**, subject to a utility floor — systematically wrong early signal without garbage bids.

### Why three phases instead of one switch?

Abrupt flips are detectable and fragile. Gradual transition keeps the false early signal long enough to poison the learner, then reveals enough preference late to close.

### Why treat first and second seat differently?

The opener’s bid stream is longer and more exposed to the opponent’s learner. We extend the decoy window and tighten early gates when we open — no oracle routing, just seat + time.

### How do you model the opponent?

Smith-style frequency models with recency / time / issue weighting, plus trajectory features (concession slope, non-monotonicity). We classify **behavior** — mirror, learner, deceptive, conceding, unknown — not agent class names we don’t have.

### How do you detect bait?

Deceptive mode + concealment tactics + late offer whose Smith utility jumps far above the trajectory prediction → reject even if aspiration would accept, until near the catastrophe/deadline window.

### Did you overfit to local benchmarks?

Risk we managed with panels: learners, time-based stress, and in-house deceptive sparring. We **removed** changes that helped one cell but hurt the panel — escape accept, reverse persona, some stricter gates.

### Do you use the opponent’s true utility?

No. Only observed offers, relative time, and seat. We publish an estimated opponent utility for league Advantage scoring, built from blended Smith estimates.

### What’s your local score roughly?

Development snapshot panel mean around **Advantage ~0.55, Concealing ~0.79, Score ~1.34** (learners ~1.27, stress ~1.43, deceptive sparring ~1.19). Emphasize it’s a **proxy**, not official tournament rank unless you have official numbers.

### Connection to signaling / mechanism design?

Offers are signals. Strategy-proof mechanisms can make honesty dominant; ANL’s Concealing axis does the opposite for preference revelation. We operate in competitive signaling, not incentive-compatible reporting.

---

## 3. GunnerAgent / HAN

*Own this section as fully as Agent360 — same “we,” same confidence.*

### Why can’t the LLM choose the offer?

Stochastic errors, timeouts, and bad JSON must not produce bad deals. Half the score is perception, but a bad offer destroys utility. Numbers first, words second; fallbacks if the LLM fails.

### Which LLM?

League-fixed local model via Ollama — **qwen3:4b-instruct**. We engineer prompts and sampling, not the model choice.

### Does the LLM see your utilities?

No. It gets verbal labels, offer terms, partner message/history — never utility, reservation, or priorities — so it can’t leak strategy or invent numbers.

### Walk me through one turn end to end.

1. Partner offer arrives (with their message).  
2. **GunnerCore** decides accept or reject using the current threshold on **our** utility only.  
3. If reject: build candidates above threshold → Pareto filter on (our util, estimated opp util) → sort by predicted partner utility → pick one under the no-repeat cap.  
4. **LLM wrapper** gets the fixed move + labels → writes 2–3 sentences.  
5. If LLM fails → send a **fallback** message that still matches the numerical move.  
Emit (decision + message). The LLM never changes the numbers.

### Why two concession phases? (be concrete)

Classical aspiration:  
`aspiration(t) = (M − rv)(1 − t^e) + rv`.

With ~10 turns, one curve fails:
- **Boulware** (e > 1) → near-identical repeats → reads robotic  
- **Conceder** (e < 1) → gives value away early  
- **Linear** (e = 1) → partner waits until the end  

Our split at **t = 0.4**:
- **Phase 1 — Anchor:** linear from **1.0 → 0.7** (fixed floor, not scaled by rv — so movement is visible without giving real value)  
- **Phase 2 — Settle:** Shochan-style curve from 0.7 down to `max(1.5·rv, 0.3)` with **e = 2.5** — hold near 0.7, then sharp drop near the deadline  

Same threshold for **accept** and **propose**.

### Why not Smith/frequency modeling like Agent360?

In HAN the partner quickly leaves preferred outcomes and concedes; frequency tables fill with non-preferred values. In our tests, frequency models collapsed toward a zero-sum proxy. The **first offer** is the best preference sketch; later bids are mostly concession.

### How does opponent modeling work exactly?

Estimate `û_opp` **only to rank** proposals (Pareto + sort) — **not** for accept/reject.

- **≤2 issues** (buyer–seller-like): template-match against the **first offer**  
- **≥3 issues** (resource-like): template-match **weighted** by issues the partner keeps **unchanged** across rounds (stability ≈ importance)

We do **not** estimate partner reservation value — too few offers; a wrong rv hurts more than none.

### What if the first offer is “I want everything”?

That’s exactly why the ≥3-issue branch exists: first offer alone is uninformative, so we weight issues by **stability** across consecutive offers.

### What if you run out of distinct offers?

Small outcome spaces + high Phase-2 threshold + no-repeat cap (don’t repeat the same offer more than ~3 times) can exhaust candidates. The propose loop may re-offer; the message layer softens deadlock. Known limitation.

### How do modular prompts work?

Small model + one giant prompt = instructions interfere. We assemble from separate pieces: global rules, move brief, partner last action, offer line, output format. Each can be edited without breaking the rest. Recency matters — put exact offer terms and critical instructions **last**. We give a ready-made “You get …” line to copy literally so the model doesn’t paraphrase items wrong. Temperature **0.7**; raise token limit to avoid truncation.

### How do you avoid sounding robotic?

Move labels drive tone: opening, large concession, small adjustment, holding firm, repeating, re-raising, accepting. Separate lighter labels for the partner’s last action. Persona: warm and assertive — not apologetic, not machine-like. Fallbacks still match the numerical move.

### Why inherit from Shochan then change so much?

Shochan won ANAC 2024 ANL with opponent **ufun** available. HAN **hides** partner utility and adds messages + a short clock. We kept the aspiration/propose skeleton, replaced every `opponent_ufun` call with our estimator, and added the two-phase curve, no-repeat cap, and LLM presentation layer.

---

## 4. Comparison / methods

### Both use Shochan lineage — how are they different?

Shared inheritance for aspiration/propose ideas, then diverged: Agent360 rebuilt for **concealment** and long learner games; GunnerAgent rebuilt for **hidden partner utility**, short horizon, and a language layer Shochan never needed.

### How did you evaluate?

Repeatable local tournaments / panels before submission; iterate; keep only changes that help across opponent families.  
**Agent360:** learners + stress + deceptive sparring.  
**GunnerAgent:** curve/model ablations under HAN constraints (league flow: LLM round → humans).

### Same stack, opposite strategies — one table

| | Agent360 | GunnerAgent |
|---|---|---|
| Opponent | Learning agents | Humans |
| Extra goal | Hide preferences | Sound human / trusted |
| Early game | Decoy persona | Anchor without giving value |
| Architecture | Persona / model / accept | Numbers core + language layer |

### Five lessons (closing fallback)

1. Scoring rule defines the strategy  
2. Opponent modeling must fit the data budget  
3. Evaluate across opponent families  
4. Separate layers that fail independently  
5. Empirical iteration over intuition  

---

## 5. Soft / process questions

### What was hardest?

On Agent360: balancing Advantage and Concealing — strengthening acceptance without collapsing the decoy.  
On Gunner: designing for ~10 offers and unknown partner utility without sounding robotic. Across both: knowing when to **roll back** a change that looked good in one cell.

### What did you reject that you’re glad you rejected?

Reverse-psychology persona; mid-game escape acceptance; treating HAN like long ANL frequency learning; letting the LLM touch numerical decisions.

### What are you most proud of?

Clear experimental path on Agent360 personas, and the Core/LLM separation on Gunner so presentation can’t corrupt strategy — plus the shared lesson that **scoring rule + data budget** drive design.

### Where is Omer?

He’s part of the team; I’m presenting today. Happy to take any question on either agent — we built both together.

---

## 6. If stuck — recovery lines

- “The short answer is X; the reason we chose it over Y is Z.”
- “We didn’t optimize for that metric; we optimized for Advantage + Concealing / utility + perception.”
- “Local panel evidence suggested …, so we kept / rolled back …”
- “Happy to point to the poster section on … for the diagram.”
- Never: “That was Omer’s part” / “I mainly did Agent360.”
