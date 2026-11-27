# Drafting handoff for Gemini (Antigravity): Guide 0a, Math Toolkit

Written 2026-11-27. This is a trial draft: Claude will review it against the sources, and a fresh Codex draft may be run later for comparison. This file replaces the 0a part of `2026-11-26-microecon-guide0-drafting-handoff.md`.

## Set up first
Work in your own worktree of the `academic_notes` repo, branch `gemini/microecon-guide0a`, path `C:\Users\theaa\ai-sandbox-master\.worktrees\gemini-microecon-guide0a` (read `docs/WORKTREE_DATA_AND_RETIRE.md` first). Create one file there:
`microecon/part_2/study_guides/Guide 0a - Math Toolkit.md`

Do not touch any other file. Do not commit, push, run a pipeline or indexer, make a paid API call, or spawn other agents.

## Read, in this order
Under `C:\Users\theaa\ai-sandbox-master\ai-sandbox\`:
1. `academic-rag-model/docs/superpowers/specs/2026-11-26-microecon-guide0-topics-v1.md`, **Part A only** (A1–A10). The topics are settled.
2. `academic-rag-model/docs/superpowers/plans/2026-11-26-microecon-guide-common-rules.md`. Where it differs from this file, this file wins.
3. For style and notation only: `Guide 0b - Micro Toolkit.md` and `Guide 5 - Existence of Equilibrium.md` in `academic-hub/academic_notes/microecon/part_2/study_guides/`. Do not copy their examples.

## The guide
- Reader: little or no recent math or micro. Define every symbol before using it.
- Length 4,000–6,000 words. Do not pad.
- Opening and a table of topics, naming which guides use each.
- One section per topic, headed with its code (`## A1. ...`): plain idea; exact definition or theorem with every assumption; short derivation as **numbered steps**; one worked example with numbers; common mistake; "used in" line.
- Formula sheet, then about four practice questions with worked answers, then sources by topic.
- Where Guide 0b, 2 or 5 already teaches something (simplex, fixed points, correspondences, demand), point to it and do not repeat it.

## Diagrams (text diagrams in `~~~text` blocks, each also described in words)
1. A2: a budget line as a hyperplane, with the price vector at right angles to it.
2. A3: a convex set beside a nonconvex one, and the sum of two small sets.
3. A4: a concave function with its chord below the curve.
4. A8: an interior solution beside a corner solution.
5. A10: two convex sets with a separating line.
Generate or check each with a script, so marked points are where the text says.

## Rendering
- Math is `$…$` and `$$…$$`.
- Inside math, never put `<` directly before a letter; write `\lt `.
- No line inside a display equation starts with `-`, `+` or `*` followed by a space.

## Accuracy: the part that matters most
- Sources: Jehle and Reny, `academic-hub/academic_notes/microecon/part_2/textbooks/processed_outputs/Jehle_Advanced_Microeconomic_Theory_2011/chapters/`, files `10_appendix_a1_sets_and_mappings.rag.md` and `11_appendix_a2_calculus_and_optimisation.rag.md`. Search for headings and read ranges.
- Open the source text for every definition and theorem before writing it. **Do not state anything, or cite a section, theorem or page number, from memory.** If you cannot find support, say so in the report and mark nothing as checked.
- Take particular care with: necessary versus sufficient conditions in Kuhn–Tucker (including the constraint qualification and the sign convention of multipliers); quasiconcave versus concave; the hypotheses of the envelope theorem and of the separating hyperplane theorem.
- Compute every example and answer with a script in your scratchpad.
- Write in your own words. Do not copy textbook passages or exercises.

## Open graded work: Problem Set 4
Follow the list of forbidden forms in the common rules. The Lagrangian and Kuhn–Tucker examples are the likely place to slip: do not use log utility over two goods with a disutility of work, or a production function with a setup input. Practice questions may be your own if prior-year sets have no pure math question; say which are adapted and from where.

## Report
1. Clickable `file://` link and the real word count.
2. For each of A1–A10, the source file and line you checked it against.
3. Which scripts you actually ran and what they checked.
4. Anything unverified or unsupported.
5. The result of the Problem Set 4 comparison.
Report only checks you performed.
