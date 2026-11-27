# Common rules for microeconomics Part 2 study guides

Used by the Guide 1 and Guide 2 handoffs (2026-11-26). Paths below are under `ai-sandbox/academic-hub/`; guide topics are under `academic_notes/microecon/part_2/`.

## Reader and models
- The reader has little micro background. Level and style follow the finished guides, which are in the main vault (not in your worktree). Read for style and notation, not to copy examples, under `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub\academic_notes\microecon\part_2\study_guides\`:
  - `Guide 0b - Micro Toolkit.md`, `Guide 2 - Pareto Optimality.md`, `Guide 4 - Equilibrium and Welfare.md`
- Keep planning words, such as calling a past problem set "closed", out of the guide.
- Intent and source rules: `ai-sandbox/academic-rag-model/docs/superpowers/specs/2026-11-26-microecon-part2-study-guides-design-v1.md`.

## Shape
Opening and topic table; a short recap of the tools needed, pointing to Guide 0b codes but readable alone; one section per topic (plain idea, exact statement with every assumption, proof or derivation step by step, worked example, common mistake); formula sheet; practice questions with answers at the end; sources by topic. Define each term before using it. Keep processing and transcription remarks out of the guide; report them instead.

## Open graded work: Problem Set 4 (due 2026-12-04)
Do not solve it, hint at its answers, or mention it beyond a line that it is excluded. No example or practice question may use its forms, even renamed or rescaled:
- production `sqrt(max(input - F, 0))`, or the same thing written as a cost with a setup input plus a squared term;
- Cobb–Douglas production in two inputs with returns of degree at most one, `q1^a q2^(v-a)`;
- log utility over two goods minus a disutility of work, quadratic or infinite;
- a three-good chain of labor, an intermediate good and a final good;
- consumers of whom only some can work; one sole owner and a 50/50 firm; redistributing shares to equalize utilities.

Open the problem set only to check your finished draft against it. Report each close match. Course lectures may use an idea in this list (leisure as a good, for instance); teach it, with a clearly different economy.

## Practice questions
At least half adapted from 2024 or 2025 questions, naming year, set and question. Skip any that matches the list above.

## Notation and rendering
- Goods first inside vectors: `x_{li}`, `ω_{li}`, `y_{lj}`; consumers `i`, firms `j`, shares `θ_{ij}`, utility `u_i`. Say once that some sources reverse the order.
- Inside math, never put `<` directly before a letter; write `\lt `.
- In a display equation, no line starts with `-`, `+` or `*` followed by a space.
- Any text diagram: check by script that marked points lie where the text says.

## Accuracy
- Lectures and this year's TA material outrank everything else. Check theorem statements against the source text, and transcribed course pages against the page image (`pypdfium2` in the shared `.venv`; PDFs under `academic_resources/`). Some prior-year transcriptions were once fabricated.
- Slides contain typos: check, and explain openly where it affects understanding.
- Work every example and answer yourself and check the arithmetic with a script in your scratchpad.
- Write in your own words; do not copy textbook passages or exercises at length.
- Textbooks: Mas-Colell under `academic_notes/microecon/part_1/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/`; Jehle and Reny under `academic_notes/microecon/part_2/textbooks/processed_outputs/Jehle_Advanced_Microeconomic_Theory_2011/chapters/`.

## Ground rules
Create only the guide file, in your own worktree of the `academic_notes` repo (read `docs/WORKTREE_DATA_AND_RETIRE.md` first). Run no pipeline, indexer or paid API call; do not commit or push; do not spawn subagents.

## Report
Clickable `file://` link (copy the real path exactly), word count, verification list with locators, anything unverified, source slips or conflicts, and the result of the Problem Set 4 comparison.
