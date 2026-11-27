# Drafting handoff: Guide 5, Existence of Equilibrium (Microeconomics Part 2)

Written 2026-11-27, for a fresh Claude or Codex session. Another session will review the draft against the sources, so record where you checked each theorem statement and proof step, and report only checks you actually ran.

Read first: `2026-11-26-microecon-guide-common-rules.md` (same folder). It binds this draft.

## File
`ai-sandbox/academic-hub/academic_notes/microecon/part_2/study_guides/Guide 5 - Existence of Equilibrium.md`

Length: 7,000–10,000 words. About six practice questions. This is the most mathematical guide and Guide 0a (math) is not written, so teach the math here from the start: pictures and one-dimensional cases before general statements.

## What the guide answers
When prices that clear every market are guaranteed to exist, how that is proved, and what goes wrong when an assumption fails.

## Topics
| # | Topic | Lecture pages (2026, PDF pages) |
|---|---|---|
| T1 | The problem: excess demand, homogeneity, Walras' law, counting equations and unknowns; why counting does not prove existence | L6 p. 3 |
| T2 | Math toolkit: simplex, interior and boundary; continuity, compactness, convexity; fixed points; intermediate value theorem and Brouwer | L6 pp. 9, 11 |
| T3 | Two goods: boundary behavior and the first existence theorem; possible multiplicity | L6 pp. 4–5 |
| T4 | Where the first welfare theorem fits (pointer to Guide 4 only) | L6 p. 6 |
| T5 | Many goods with bounded demand: the map g, why its fixed points are equilibria | L6 pp. 9–11 |
| T6 | Why unbounded demand breaks the argument | L6 p. 11; L7 p. 2 |
| T7 | Correspondences, closed graph and upper hemicontinuity, Kakutani | L7 p. 3 |
| T8 | The correspondence f and the full proof | L7 pp. 3–5 |
| T9 | The case L = 2, worked completely (the slide leaves it as an exercise) | L7 p. 6 |
| T10 | What has been shown; failures of existence (nonconvex preferences, discontinuous demand, a zero-endowment case); role of convexity with production | L7 pp. 7, 9 |

Core and welfare results belong to Guide 4; gross substitutes, uniqueness and Sonnenschein–Mantel–Debreu belong to Guide 6.

## Points in the slides to handle with care
Verify each against the page image, then state the correct version openly.
- L6 pp. 4–5: say which preference assumption gives the boundary behavior; check whether the theorem as stated includes it, and whether the endowment condition is on totals or on each consumer.
- L6 p. 10: the fixed-point argument gives excess demand at most zero. Say exactly what is needed to conclude equality, and what happens for a free good.
- L7 pp. 3–5: state every property Kakutani needs, including nonempty values. The upper hemicontinuity argument at boundary points relies on how excess demand behaves as prices approach zero: state that condition and use it.
- Check that "bounded" and "unbounded" demand cases are not silently mixed.

## Sources
- Lectures 6–7: `professor_notes/processed_outputs/`.
- 2024 Recitation 3: `class_2024/Recitations/processed_outputs/recitation_3.md` (its two-good slide has a sign slip).
- Prior years: look for existence questions in `class_2024/Homeworks/` and `class_2025/Problem Sets/` and their solutions. If too few exist for half the practice questions, write your own and say so in the report.
- Textbooks: Mas-Colell §§17.B–C and the Mathematical Appendix; Jehle and Reny §5.2.1 and Appendix A1.
