# Concept graph: status as of 2026-10-15

Package: `agent/concept_graph/`. Graph repo (data and published page): `microecon-concept-graph`, live at
https://aaronscherf.github.io/microecon-concept-graph/. This document consolidates the earlier status docs
(`2026-10-09-concept-graph-core-status.md`, `2026-10-10-concept-graph-pipeline-status.md`,
`2026-10-14-concept-graph-proposals-status.md`) and records what was added since.

## What exists

A study-aid graph of graduate microeconomic theory: concepts (nodes), typed conditional claims between them (edges),
and eight course sections, shown as one self-contained HTML page. Drafting is done by an agent over private task
cards (Gemini in Antigravity, on a subscription); every item is validated in code, stays `proposed` until a person
accepts it, and carries its citations and provenance.

| Part | State |
|---|---|
| Data model, validation, build (graph.json and index.html) | shipped |
| Drafting stages `seed`, `fill`, `link`, `critic`, `summary` over task cards | shipped |
| Retrieval over the hub index with a fallback chain (paid key, free key, local keyword search) | shipped |
| Review loop: accept, reject, edit, comment, and propose concepts and connections from the page | shipped, GitHub submission not exercised end to end |
| Viewer: sections as the single grouping, multi-select, collapsible list, grouped panel, summaries, layout presets | shipped |

## The graph today (2026-10-15)

- **104 concepts and 159 linked claims in 8 sections**, all with explanations and citations.
  - s01 to s04: 12 concepts each; s05: 14; s06: 15; s07: 13; s08: 14.
  - Evidence now includes the 2024 and 2025 class slides, homeworks, solutions, proofs and exams (source keys such as
    `slides-2024`, `hw-2025`, `exam-2024`) as well as this year's lecture notes through 2026-10-13, the professor
    slides and the three textbooks.
  - The five classic two-commodity utility families (Cobb-Douglas, CES, linear, Leontief, quasi-linear) and the
    marginal rate of substitution are in s05 with their properties (Walrasian demand, indirect utility, Hicksian
    demand, expenditure function, Slutsky matrix).
- **Critic:** 159 claims judged `supports` and 5 rejected over the project (3 wrong early edges, a functional form
  listed as a component of the general problem, and a positivity claim that holds only with full-support errors).
  All five are tombstoned in `data/rejected.yaml`.
- **Summaries:** one agent-drafted paragraph per section (76 to 91 words), stored on the section and shown when a
  whole section is selected.
- **Validation:** 0 errors, 2 warnings: a conditional logical cycle among `expected-utility-theorem`,
  `rational-preference-relation` and `utility-function` (each edge states its own condition), and one orphan
  (`positivity-condition`).

## Timeline

- 2026-10-09 to 10-10: core (store, validate, build, viewer) and the drafting pipeline; 59 concepts in 8 sections.
- 2026-10-11 to 10-12: fill, link and critic for the five taught sections; layout, LaTeX and meta-commentary fixes;
  published the page.
- 2026-10-14: densified to 104 concepts using all years of course material; retrieval fallback chain; `--orphans`,
  `fill_hints`; printed agent prompts; reviewer proposals (spec, plan, implementation, review).
- 2026-10-14 to 10-15: viewer selection, sections as the single grouping, layouts and summaries (spec, plan,
  implementation, review); polish round (below).

## Pipeline decisions worth keeping

- **Cards generated and validated by code, drafted by a subscription agent.** The agent never touches the graph
  files; `submit` runs the validators (own-words guard, citation grounding, cycle checks, meta-commentary check,
  length and math checks) and applies. Claude's role is design, coordination and review.
- **`collect` prints a ready-to-paste prompt** for each run (and saves `PROMPT.md`), naming the stage and showing a
  card's first instruction line so an agent can tell it was given the wrong run.
- **Retrieval degrades instead of stopping:** paid key, then free key, then local keyword search, only on quota or
  rate-limit errors.
- **The section is the single grouping.** Each section declares `topic` and `short`; a concept's topic must equal its
  section's; the topic buttons are the sections' short labels.
- **Reviewer proposals are light** (names, dropdowns, a one-line note); the pipeline writes the prose. Duplicate
  proposals merge deterministically and are flagged when a choice is tied; near-duplicates of existing concepts
  become edge proposals plus a comment; re-applying a review is a no-op.

## Verification

- `python -m pytest tests/agent/concept_graph`: 331 tests. `node --test agent/concept_graph/viewer/tests/*.test.js`:
  45 tests.
- Browser behaviour is checked with headless Edge against copies of the sample and the real graph, using
  `?debug` (exposes `window.__cg` and turns layout animation off). Each fix in the review rounds has a check that
  failed before the fix.
- Not verified: real mouse and touch gestures (the checks use synthetic events), Cmd-click on a Mac, box-select with
  filtered concepts, the GitHub issue-form submission path with proposals.

## Open items

- **`positivity-condition` is an orphan** (its only edge was rejected). A `collect link --orphans` pass can fix it.
- **The critic is probably lenient** (the drafting model judges its own work). TODO-0075 covers a different model, a
  stricter rubric, seeded bad edges and sample review by Claude or Codex.
- **Evidence clipping:** the seed card shows only part of each source (25 statements per slide deck, 12 per lecture
  note, 40 headings per chapter, about 12,000 characters). TODO-0074 measures how much that matters.
- **The human relay** (paste a prompt, say "done") is the main cost of the Antigravity route. Removing it needs an
  agent bridge (TODO-0075).
- **Summaries are drafted, not reviewed.** A few sentences are looser than the theory (for example, convexity does
  not by itself guarantee an interior solution). Re-draft with `collect summary --redo` or edit in review.
- **Not built:** drag-to-connect, a searchable target picker in forms, an agent stage that rewrites merged proposal
  notes, reviewer-written explanations, proposing sections, shared user-made layouts, aliases in duplicate checks.
- **Known small things:** the round id of a proposal is the date; connection notes in a merged concept are credited
  to the first author (hand-written review JSON only); the page's pre-check does not know the rejected list, so the
  server remains the authority.

## How to run it

See `agent/concept_graph/README.md`: `collect <stage>` writes cards and prints the prompt; the agent fills them;
`submit <run-id>` validates and applies; `validate`, `build`, then commit and push the graph repo. After a review,
`apply-review` merges reviews and proposals, and `collect fill|link|critic --node <id>` drafts what was proposed.

## Lifecycle references

### Specs

- [2026-10-14-concept-graph-reviewer-proposals-design](../../../superpowers/specs/agent/2026-10-14-concept-graph-reviewer-proposals-design.md)
- [2026-10-14-concept-graph-viewer-selection-and-layouts-design](../../../superpowers/specs/agent/2026-10-14-concept-graph-viewer-selection-and-layouts-design.md)

### Implementation plans

- [2026-10-14-concept-graph-reviewer-proposals](../../../superpowers/plans/2026-10-14-concept-graph-reviewer-proposals.md)
- [2026-10-14-concept-graph-viewer-selection-and-layouts](../../../superpowers/plans/2026-10-14-concept-graph-viewer-selection-and-layouts.md)

### Tests

- [test_cg_proposals](../../../../tests/agent/concept_graph/test_cg_proposals.py)
- [test_cg_apply_proposals](../../../../tests/agent/concept_graph/test_cg_apply_proposals.py)
- [test_cg_sections](../../../../tests/agent/concept_graph/test_cg_sections.py)
- [test_cg_layouts](../../../../tests/agent/concept_graph/test_cg_layouts.py)
- [test_cg_stage_summary](../../../../tests/agent/concept_graph/test_cg_stage_summary.py)
