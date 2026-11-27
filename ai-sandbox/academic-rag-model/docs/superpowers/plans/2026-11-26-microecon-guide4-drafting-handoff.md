# Drafting handoff: Guide 4, Equilibrium and Welfare (Microeconomics Part 2)

Written 2026-11-26, for a Claude or Codex session. Another session will review the draft against the sources, so record where you checked each theorem statement and key formula, and report only checks you actually ran.

Read first, in `ai-sandbox/academic-rag-model/docs/superpowers/specs/`: `2026-11-26-microecon-part2-study-guides-design-v1.md` (intent, source rules, anti-goals) and `2026-11-26-microecon-guide0-topics-v1.md` (the toolkit codes you point back to).

## Hard rule: this year's Problem Set 4
It is open graded work, due 2026-12-04, with no solutions. Teach the tools it needs. Do not solve it, hint at its answers, or build an example or practice question from its economy (its functional forms, three-good production chain, ownership pattern or consumer types), including with changed numbers or names. Use clearly different economies. Skip any prior-year question that closely matches it. You may read it only to know which tools to teach; do not mention it in the guide beyond a line that it is excluded.

## File
`ai-sandbox/academic-hub/academic_notes/microecon/part_2/study_guides/Guide 4 - Equilibrium and Welfare.md`

## Shape
1. Opening: what the guide answers (what an equilibrium is, why it is efficient, which efficient outcomes markets can reach) and a topic table.
2. Short background recap, one or two paragraphs per tool, pointing to the toolkit: demand (B4), endowment income (B8), profit maximization (C5), relative prices and Walras' law (D5), Edgeworth box (D4), convex sets and separating hyperplanes (A3, A10). The guide must still read on its own.
3. Course results, one section per topic below: idea in plain words; exact statement with every assumption; proof worked step by step, saying where each assumption is used; a worked example or counterexample; common mistake.
4. One-page formula and theorem sheet.
5. About six practice questions, answers at the end.
6. Sources list by topic.

Length (planner's call): 7,000–10,000 words. Prefer more steps and shorter sentences over dense qualification. Define each term before using it. Keep processing or transcription remarks out of the guide; put them in your report.

## Topics
| # | Topic | Lecture pages (2026) |
|---|---|---|
| T1 | Private-ownership exchange economy, Walrasian equilibrium, excess demand | L5 p. 8 |
| T2 | Excess demand: continuity, homogeneity, Walras' law, L−1 markets | L5 p. 9 |
| T3 | Computing an equilibrium; Edgeworth box picture | L5 pp. 8–9, Recitation 2 |
| T4 | Blocking coalitions, the core, individual rationality, Pareto optimality | L6 p. 7 |
| T5 | First welfare theorem: equilibrium allocations are in the core | L6 p. 8 |
| T6 | Production: profit shares, budgets, excess demand; where convexity matters | L7 pp. 8–9 |
| T7 | The core with production: who gets the profits | L7 p. 10 |
| T8 | Second welfare theorem and the proof by a fictitious economy | L7 pp. 11–12 |
| T9 | Proof by separating hyperplane | L7 pp. 13–15 |
| T10 | Choosing endowments and shares that decentralize an optimum | L7 pp. 16–17 |
| T11 | What the theorems do not say: distribution, market failures, nonconvexity | L8 p. 2 |

Existence proofs belong to Guide 5 (you may state that existence needs convexity and point there). Gross substitutes, SMD and asset markets belong to Guide 6.

Guides 1–3 are not written yet, so include one recap section on Pareto optimality with production (2026 Lectures 2–4): the planner's problem with welfare weights, the first-order conditions (equal marginal rates of substitution and transformation), and corner solutions. Guide 2 will treat it fully.

Also teach, with your own examples, because exercises lean on them: constant returns and zero profit, including the factor price frontier; decreasing returns and distributing profits; a fixed cost and the shutdown choice; Cobb–Douglas expenditure shares; labor supply with disutility of work and corner choices; homothetic preferences and aggregation of demand.

## Points in the slides to handle with care
Verify each against the page image, then explain it openly in the guide where it affects understanding.
- L6 p. 7 defines blocking with a strict gain for **every** coalition member; the recitations use a weak gain for all with one strict. Say which assumption makes the difference small.
- L6 p. 8 ends with an inequality between consumption sums that does not follow as written; the contradiction is with the value of the coalition's resources. The step before it also needs budgets to bind.
- L7 pp. 13–17: state what delivers nonnegative or positive prices, and what is needed to go from cost minimization to utility maximization (positive wealth). Compare MWG 16.D on quasi-equilibrium.
- L7 p. 14: state the separating hyperplane theorem's conditions precisely.

## Sources
Under `ai-sandbox/academic-hub/`. Lectures and this year's TA material outrank everything else.
- Lectures 5–8: `academic_notes/microecon/part_2/professor_notes/processed_outputs/`.
- Recitations 2 and 3: `academic_notes/microecon/part_2/class_2024/Recitations/processed_outputs/`.
- Practice: 2024 `class_2024/Homeworks/ProblemSet4` and solutions `Homeworks/Solutions/hw4_part2_ols`; 2025 `class_2025/Problem Sets/ProblemSet4` and its solutions. Some solution files are named differently from their headings: match by content.
- Mas-Colell: `academic_notes/microecon/part_1/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/` (`15_`, `16_`, `18_`).
- Jehle and Reny: `academic_notes/microecon/part_2/textbooks/processed_outputs/Jehle_Advanced_Microeconomic_Theory_2011/chapters/05_general_equilibrium.rag.md`.

## Notation
Follow the course. Where goods are indexed inside a consumer or firm vector, use the 2026 Lectures 2–3 order, good first: `x_{li}`, `ω_{li}`, `y_{lj}`; say once that some sources reverse it. Consumers `i`, firms `j`, shares `θ_{ij}`, utility `u_i`.

## Accuracy and ground rules
- Check every theorem statement against the source text, and transcribed course pages against the page image (`pypdfium2` in the shared `.venv`; PDFs under `academic_resources/`). Some prior-year transcriptions were once fabricated.
- Work every example and answer yourself and check the arithmetic with a script in your scratchpad.
- Write in your own words; do not copy textbook passages or exercises at length.
- Create only the guide file. Read `docs/WORKTREE_DATA_AND_RETIRE.md` first (`academic_notes/` is a separate repo). Run no pipeline, indexer or paid API call; do not commit or push; do not spawn subagents.

## Report
Clickable `file://` link (copy the path exactly), word count, verification list with locators, anything unverified, source slips or conflicts found, and a one-line confirmation of how you kept clear of Problem Set 4.
