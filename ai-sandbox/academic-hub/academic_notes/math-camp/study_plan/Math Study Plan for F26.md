---
tags: [math-camp-study-plan]
---

# Math Study Plan — Fall 2026

> **Note to any reader, human or LLM agent:** this is a living draft, not an authoritative guide. It reflects one pass at synthesizing two source documents and the Ground Truth research plan as of 2026-08-31, and is expected to be revised frequently as actual course syllabi arrive and the research direction evolves. Treat specifics here — week numbers, topic ordering, direction tie-ins — as provisional; check the source documents (linked below) and the current Ground Truth artifact for what's actually current before relying on this.

Math camp (Aug 10–28) covered the official three-week syllabus at speed. This plan is the semester-long follow-through: one review/deepening block per week, running alongside the micro / macro / econometrics sequence, the environmental science course, and the open-source-conflict-data seminar. It draws its topics and resources directly from two sources already in this folder rather than inventing new ones:

- **`syllabus/processed_outputs/Summer_Maths_Camp_2026.md`** — the official six-topic syllabus (Linear Algebra, Analysis in Euclidean Spaces, Multivariable Calculus, Convexity, Optimization & Correspondences, Probability Theory) and its reading list.
- **`study_plan/processed_outputs/Columbia Math Camp Prep Schedule (15 week).md`** — the day-by-day pre-camp schedule, including the "bonus" material beyond the official syllabus (differential/difference equations, dynamic optimization and optimal control, measure-theoretic probability) that the camp itself may not have had time to cover.

Each week below also names which part of the **Ground Truth** research plan (`research/independent-research/notes/Ground Truth - PhD Research Plan.html`) it's building toward — the point isn't to re-derive theorems for their own sake, but to make sure the mathematical tools are solid *before* they're needed for the evidence map, the climate–conflict–displacement fusion project, or a committee member's first question about identification.

## Priority lens: what each direction actually needs

| Ground Truth direction | Load-bearing math |
|---|---|
| **I — Climate adaptation, migration & cash transfers under conflict** (flagship) | Markov chains & stochastic processes (conflict/displacement as state transitions), contraction mappings & Bellman equations (resilience-investment decisions under shock risk), stability of difference/differential equations (recovery trajectories) |
| **II — Digital credit & insurance in fragile settings** | Quadratic forms & positive definiteness (risk/covariance structure), convex duality (pricing problems), probability & conditional expectation (credit scoring, moral hazard) |
| **III — General toolkit for scaling pilots (causal ML, HTE, meta-analysis)** | Spectral decomposition & SVD (dimension reduction, regularization), convex optimization / QP / SDP (double-ML penalization, the DEA and shape-constrained estimation ideas in `Research Ideas.md`), LLN/CLT and asymptotic theory |
| **IV — Chatbot-elicited survey data** | Probability & inference — the lightest mathematical load of the four; folded into the Module D review rather than given its own block |

The Research Ideas.md note on **ML global approximation vs. causal interpretability** (spectral bias, ergodic sets, Monte Carlo Dropout) is the clearest single bridge between this study plan and the dissertation — it's explicitly a question about uniform convergence, compactness, and measure-theoretic probability, all covered below.

## Standing habits, every week

- **One redone problem.** Pick one problem from the original camp problem sets (posted on the course site) each week and redo it cold, no notes — a faster signal of real retention than rereading.
- **One "theorem I needed" log entry.** Whatever paper you're reading that week for the evidence map (Project 01) or the fusion study (Project 02), note the one piece of math it assumed you already knew. That list *is* next week's syllabus.
- **Keep the video-lecture links.** Both source documents point to the same Arizona Math Camp / Axler / Strang / MIT 18.100B / Stat 110 playlists — reuse those rather than searching for new ones; the whole point of camp was to standardize on one set of references.

---

## Module A — Linear algebra & matrix analysis for ML (Weeks 1–3)

Foundational for direction III: causal forests, double-ML, and any PCA- or embedding-based fusion of remote-sensing covariates all sit on top of this.

### Week 1 — Vector spaces, linear maps, and matrix representations
- **Topics:** vector spaces & subspaces, linear combinations, linear independence and span, basis and dimension, linear maps and their matrix representations.
- **Resources:** Axler 1B–1C, 2A–2C, 3A, 3C; Strang 3.1, 3.4, 8.1 (prep schedule, Weeks 2–3).
- **Why it matters:** this is the vocabulary every regression, every projection, and every "high-dimensional covariate space" claim in the Ground Truth essays is stated in.

### Week 2 — Eigenvalues, diagonalization, and the spectral theorem
- **Topics:** eigenvectors/eigenvalues, diagonalizability, self-adjoint and normal operators, spectral decomposition of symmetric matrices, singular value decomposition.
- **Resources:** Axler 5A, 5D, 7A–7B, 7E; Strang 6.1, 6.2, 6.4, 7.2 (prep schedule, Week 5).
- **Ground Truth tie-in:** SVD and spectral decomposition are the mechanics behind MOSAIKS-style satellite embeddings (the data source for Project 02 and the toolkit in Project 04) — this is the week to actually understand what those embeddings *are*, not just call an API for them.

### Week 3 — Quadratic forms and positive definiteness
- **Topics:** quadratic forms, positive/negative (semi)definiteness, determinant conditions for definiteness.
- **Resources:** Simon & Blume Ch. 16; Strang 6.5 (prep schedule, Weeks 5, 9–10).
- **Ground Truth tie-in:** direction II — insurance pricing and risk-covariance structure are quadratic-form problems; this is also the linear-algebra prerequisite for the concavity/second-order conditions used constantly in Module B.

## Module B — Real analysis & convex optimization (Weeks 4–6)

Supports the micro-theory sequence directly, and is the math underneath the open tension flagged in Ground Truth between structural (assumed functional form) and non-parametric/shape-constrained estimation.

### Week 4 — Sequences, completeness, and continuity
- **Topics:** sequences and convergence, Cauchy sequences and completeness, contraction mappings, continuity, compactness and uniform continuity.
- **Resources:** Rudin Ch. 2–4; Ok C.1–C.6, D.1, D.3 (prep schedule, Weeks 6–8).
- **Ground Truth tie-in:** contraction mappings are the existence proof behind every Bellman-equation model of household investment under risk (direction I). Keep this week's notes handy for Module C.

### Week 5 — Convexity, concavity, and quasi-concavity
- **Topics:** convex sets, convex/concave functions, quasi-convex/quasi-concave functions, homogeneous functions.
- **Resources:** Ok G.1, A.4.5–A.4.6; Sundaram Ch. 8; Simon & Blume Ch. 20–21 (prep schedule, Weeks 6, 9).
- **Ground Truth tie-in:** this is the mathematical language of the DEA note in `Research Ideas.md` — DEA's efficiency frontier is a convex hull of observed input–output vectors, and its "monotonicity and convexity" axioms are exactly this week's definitions applied as constraints.

### Week 6 — Constrained optimization: KKT, duality, and shape constraints
- **Topics:** unconstrained optimization, Kuhn–Tucker conditions, Lagrange duality, envelope theorem and comparative statics.
- **Resources:** Sundaram Ch. 4–6; Simon & Blume Ch. 17–19, 22; Corbae/Stinchcombe/Zápal Ch. 5 (prep schedule, Weeks 11–12).
- **Ground Truth tie-in:** direction III's shape-constrained kernel estimation (`Research Ideas.md`) is a QP problem solved via KKT/active-set methods — this week is the theory behind why that estimator is guaranteed concave rather than just empirically well-behaved. Also the direct prerequisite for reading any structural-estimation (MPEC) paper in the evidence map.

## Module C — Correspondences, fixed points, and dynamic optimization (Weeks 7–9)

The macro-theory sequence's territory, and the most direct mathematical machinery for direction I — modeling how a household's resilience investment responds to climate and conflict shocks over time.

### Week 7 — Correspondences and the maximum theorem
- **Topics:** upper/lower hemicontinuity, Berge's maximum theorem, Brouwer and Kakutani fixed-point theorems.
- **Resources:** Ok Section E.3, E.5.1, D.8.3; Sundaram Ch. 9 (prep schedule, Weeks 13).
- **Why it matters:** this is the existence machinery behind general-equilibrium and Nash-equilibrium arguments, and it's the formal footing for the multi-dimensional welfare / vector-optimization idea in `Research Ideas.md` (choice correspondences over a Pareto frontier are literally built from this week's objects).

### Week 8 — Difference and differential equations
- **Topics:** eigenvalues and dynamics, scalar and systems of ODEs, stability of steady states, difference equations.
- **Resources:** Simon & Blume Ch. 23–25; Sydsæter Ch. 5–7, 11 (prep schedule, Week 12 "bonus" material — flagged in the official syllabus as content that may not be covered live, so this is likely new rather than review).
- **Ground Truth tie-in:** direction I's core empirical claim — that resilience investment changes whether a shock becomes a displacement event — is a statement about the stability of a recovery trajectory. This week gives the formal vocabulary (steady states, saddle paths) for that claim.

### Week 9 — Dynamic optimization, control theory, and Bellman equations
- **Topics:** calculus of variations, optimal control, discrete-time dynamic programming, the Euler equation, contraction mappings revisited.
- **Resources:** Sydsæter Ch. 8–10, 12; Ok Section E.4 (prep schedule, Weeks 12–13 "bonus" material).
- **Ground Truth tie-in:** the natural formal model for "a household decides how much to invest in adaptation given climate and conflict shock probabilities" is a stochastic dynamic program — this week is the toolkit for writing that model down rigorously rather than only estimating its reduced form.

## Module D — Probability, stochastic processes & measure theory (Weeks 10–13)

Directly under the econometrics sequence, and the formal treatment of "conflict and climate shocks as a stochastic process" that direction I needs.

### Week 10 — Probability foundations, expectation, and inequalities
- **Topics:** axioms of probability, conditional probability and independence, random variables, expectation and conditional expectation, LLN and CLT.
- **Resources:** Ross Ch. 1–7; Blitzstein Ch. 1–7 / Stat 110 (prep schedule, Weeks 14–15).
- **Why it matters:** the baseline every econometrics course assumes on day one, and the statistical foundation for direction IV's manipulation-robustness checks.

### Week 11 — Markov chains and stochastic processes
- **Topics:** transition matrices, stationary distributions, irreducibility and reversibility.
- **Resources:** Blitzstein Ch. 11–13; Stat 110 lectures 30–33 (prep schedule, Week 15).
- **Ground Truth tie-in:** the most direct formalism for direction I's core question — model conflict intensity and displacement status as a Markov chain over subnational units, with climate shocks and cash-transfer presence as covariates shifting the transition probabilities. This is the week to sketch that model, even roughly, before Project 02's data work begins.

### Week 12 — Measure-theoretic probability
- **Topics:** σ-algebras, Borel sets, Lebesgue measure and integration, Lᵖ spaces.
- **Resources:** Corbae/Stinchcombe/Zápal Ch. 6, 8–9; Rudin Ch. 11 (prep schedule, Week 15 — explicitly beyond the official syllabus, self-study only).
- **Ground Truth tie-in:** this is what actually formalizes the "ergodic set" and "spectral bias" language in the `Research Ideas.md` note on DNN global approximation — a deep-learning model trained by stochastic sampling is, underneath, sampling from a measure, and understanding *where* that measure concentrates mass is what separates a rigorous statement about ecological-tipping-point failure from a hand-wavy one.

### Week 13 — Asymptotics and high-dimensional statistics primer
- **Topics:** review LLN/CLT with an eye toward the high-dimensional case; skim ahead into double-machine-learning and causal-forest mechanics (Semenova, Chernozhukov references from your Ground Truth faculty-alignment notes) to see which of Weeks 1–12 they lean on hardest.
- **Resources:** none from the camp packet — this week is deliberately a bridge into the econometrics-sequence and Project 04 (toolkit) material, using Weeks 1–12 as the reference set.
- **Ground Truth tie-in:** direction III end-to-end. This is the week the whole plan has been pointed at.

## Weeks 14–15 — Consolidation (December, finals period)

Light by design — this is exam period for the actual coursework.

- Redo the two original camp problem sets (Assignment 1 and Assignment 2) cold, timed.
- One synthesis pass: write a single page connecting Weeks 7, 8, 9, and 11 (correspondences, difference equations, dynamic optimization, Markov chains) into a short, informal sketch of the direction I model — the resilience-investment/displacement problem as a stochastic dynamic program on a Markov state. It doesn't need to be rigorous or complete; it needs to exist as a draft you can bring into a February faculty meeting (see the Timeline in Ground Truth) instead of describing the idea from scratch out loud.

---

## Quick reference: topic → direction map

| Week | Topic | Direction |
|---|---|---|
| 1–3 | Linear algebra & spectral methods | III |
| 4 | Sequences, completeness, contraction mappings | I (existence proofs), III |
| 5 | Convexity & quasi-concavity | III (DEA/shape-constraints) |
| 6 | KKT, duality, envelope theorem | II, III |
| 7 | Correspondences & fixed points | I, III (welfare/Pareto notes) |
| 8 | Difference/differential equations | I |
| 9 | Dynamic optimization & Bellman equations | I |
| 10 | Probability foundations | II, IV |
| 11 | Markov chains | I |
| 12 | Measure-theoretic probability | III (spectral bias / ergodic sets) |
| 13 | High-dimensional asymptotics | III |
| 14–15 | Consolidation | I (synthesis draft) |
