# Guide 0 (Toolkit): detailed topic list, v1

Dated 2026-11-26. Companion to `2026-11-26-microecon-part2-study-guides-design-v1.md`.

## Decisions settled 2026-11-26 (fold into design v2)
- Each guide: background, then course results with worked proofs, then a one-page formula sheet.
- A few practice questions per guide, from prior-year sets, answers at the end.
- Output: `academic_notes/microecon/part_2/study_guides/`.
- One drafting session per guide from a handoff. Order: 0 (format trial), 4, 1, 2, 3, 5, 6, 7, 8.

Guide 0 has no course results of its own, so its middle layer is the background with short derivations.

Reader: little or no micro background. Each topic gets a plain-language idea, the definition, one worked example and the common mistake. "G4" means Guide 4 relies on it. "JR" is Jehle and Reny.

## Part A. Math
| # | Topic | Be able to | Source | Used by |
|---|---|---|---|---|
| A1 | Notation, necessary vs. sufficient, proof by contradiction | Read and structure a short proof | JR A1.1–A1.2 | all |
| A2 | Vectors, inner products, value `p·x`, hyperplanes | Read a budget or profit expression geometrically | JR A1.2 | G1, G4 |
| A3 | Convex sets, Minkowski sums | Test convexity; add two sets | JR A1.2.2 | G1, G4, G5 |
| A4 | Concave, convex, quasiconcave functions | Say which assumption a result needs and why | JR A1.4 | G1, G2, G4 |
| A5 | Partial derivatives, chain rule, implicit differentiation | Get the slope of a level curve | JR A2.1 | G2 |
| A6 | Homogeneous functions | Apply homogeneity of degree 0 and 1 | JR A2.1.3 | G1, G4 |
| A7 | Lagrangians and the meaning of multipliers | Solve and interpret an equality-constrained problem | JR A2.3.1–A2.3.3 | all |
| A8 | Kuhn–Tucker, corner solutions | Handle nonnegativity and slack constraints | JR A2.3.5 | G2 |
| A9 | Value functions, envelope theorem | Differentiate a maximized value | JR A2.4 | G4, G6 |
| A10 | Separating hyperplane theorem (statement and picture) | Explain what it separates | JR A2.5 | G4 |

## Part B. Consumers
| # | Topic | Be able to | Source | Used by |
|---|---|---|---|---|
| B1 | Preferences: completeness, transitivity, continuity, monotonicity, local nonsatiation, convexity | State each and what fails without it | JR 1.2 | G4, G8 |
| B2 | Utility representation, ordinal meaning | Show a monotone transform changes nothing | JR 1.2.2 | G2, G8 |
| B3 | Indifference curves and MRS | Compute MRS and fix its sign convention | JR 1.2–1.3 | G2 |
| B4 | Utility maximization, Marshallian demand | Derive demand, interior and corner | JR 1.3 | G4 |
| B5 | Cobb–Douglas, quasilinear, perfect substitutes and complements, CES, homothetic | Recognize each and solve it quickly | JR 1.3, 1.5 | G2, G4, G6 |
| B6 | Indirect utility, expenditure minimization, duality (brief) | Explain why minimizing spending matters | JR 1.4 | G4 |
| B7 | Income and substitution effects, Slutsky, normal and inferior goods, gross substitutes | Decompose a price change | JR 1.5 | G6 |
| B8 | Endowments as income, labor and leisure | Write the budget with endowments; excess demand | JR 5.1 | G1, G4 |

## Part C. Producers
| # | Topic | Be able to | Source | Used by |
|---|---|---|---|---|
| C1 | Production functions, isoquants, MRTS | Compute and draw | JR 3.2 | G1, G2 |
| C2 | Returns to scale, fixed and sunk costs, nonconvexity | Spot when convexity fails | JR 3.2.1 | G1, G5 |
| C3 | Production sets and netputs, transformation function, MRT | Move between `f` and `F(y) ≤ 0` | JR 5.3.1, MWG 5.B | G1, G2 |
| C4 | Cost minimization, marginal and average cost | Derive a cost function | JR 3.3 | G1, G7 |
| C5 | Profit maximization, supply and factor demand | Derive; say when no maximum exists | JR 3.5 | G4 |

## Part D. Markets
| # | Topic | Be able to | Source | Used by |
|---|---|---|---|---|
| D1 | Price taking, supply, demand, equilibrium | Solve a one-good market | JR 4.1 | G4 |
| D2 | Consumer and producer surplus, deadweight loss | Say when surplus measures welfare | JR 4.3 | G2, G7 |
| D3 | Partial vs. general equilibrium | Give an example where they differ | JR ch. 4–5 | G1 |
| D4 | Edgeworth box: endowment, lens, contract curve | Draw and compute all three | JR 5.1; 2024 Recitation 1 | G2, G4 |
| D5 | Relative prices, Walras' law (first pass) | Use one price as numeraire | JR 5.2 | G4 |

## Part E. Risk and time
| # | Topic | Be able to | Source | Used by |
|---|---|---|---|---|
| E1 | States, probabilities, conditional expectation | Compute with a two-stage tree | MWG 6.B (conditional expectation from first principles) | G3 |
| E2 | Expected utility | Say what the Bernoulli function is | JR 2.4.1–2.4.2 | G3, G6 |
| E3 | Risk aversion, certainty equivalent, Arrow–Pratt | Compute both measures | JR 2.4.3 | G3 |
| E4 | CARA and CRRA | Use the functional forms | JR 2.4.3, MWG 6.C | G3 |
| E5 | Discounting, saving, intertemporal budget | Solve a two-period problem | JR 5.4.1 | G3, G6 |

## Running examples
Reuse one two-consumer, two-good Cobb–Douglas economy in B, D and E, and one single-input firm (with and without a fixed cost) in C, so later guides can refer back.

## End matter
- One-page formula sheet.
- About eight practice questions, answers at the end, drawn from the early parts of prior-year sets. Questions that depend on later guides stay out. Problem Set 4 is not used or solved.

## Left to later guides
Correspondences and fixed-point theorems (G5); asset-market matrix algebra (G6); externalities and public goods (G7); preference aggregation (G8). Imperfect competition, game theory, information economics and auctions (JR 4.2, ch. 7–9) are left out of the series.

## Notes for the drafting session
- Follow the course's notation where it has one (goods `l`, consumers `i`, firms `j`, endowment `ω`); note where JR or MWG differ. State each MRS index convention: course sources are not uniform.
- Check key formulas against the page image or source text; do not rely on memory for theorem statements.
- Section numbers above come from the JR chapter headings; confirm each section covers its topic before citing it.
