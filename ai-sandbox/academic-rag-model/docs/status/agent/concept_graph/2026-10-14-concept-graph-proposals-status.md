# Concept graph: reviewer proposals (2026-10-14)

Closes TODO-0070. Spec: `docs/superpowers/specs/agent/2026-10-14-concept-graph-reviewer-proposals-design.md`.
Plan: `docs/superpowers/plans/2026-10-14-concept-graph-reviewer-proposals.md`.

## What shipped

- Review file `schema_version` 2 with `add_node` and `add_edge` decisions; version 1 files still apply.
- `proposals.py`: name normalization and slug, similarity (token containment with generic suffix words, token
  overlap of at least 0.75, edit distance of at most 10%), validation, clustering and merging.
- `reviews.apply_proposals`, run once per round by `apply-review`: merged duplicates, near-duplicates of existing
  concepts turned into edge proposals plus a comment, conflicts to `review-conflicts.md`.
- The page: Propose menu, concept and connection forms with dropdowns, multi-select "Add connection", a "Your
  proposals" list with withdraw, and dotted ghost items. The rules are mirrored in `logic.js`.

## Verified

- `python -m pytest tests/agent/concept_graph -q`; `node --test agent/concept_graph/viewer/tests/*.test.js`.
- A headless Edge run on the sample graph: saving a concept with a connection, the "similar existing" hint, a
  duplicate name bounced with the reason, and the ghost node drawn next to its connection.

## Open

- An agent "reconcile" stage that rewrites merged proposal notes (the fill stage rewrites prose from sources today).
- Drag-to-connect on the canvas; proposing a new section; proposing a `via` theorem; reviewer-written explanations.
- Similarity thresholds (0.75 overlap, 10% edit distance) are untuned against real proposals.

## Viewer selection, sections and layouts (2026-10-14)

Spec: `docs/superpowers/specs/agent/2026-10-14-concept-graph-viewer-selection-and-layouts-design.md`; plan:
`docs/superpowers/plans/2026-10-14-concept-graph-viewer-selection-and-layouts.md`.

- The section became the single grouping (`topic`, `short`, `summary`, `summary_hash` on sections; `topic-mismatch`
  error; `missing-summary` and `stale-summary` warnings for sections that declare a topic).
- Additive selection on the canvas (the old tap handler cleared the selection, so multi-select never worked),
  concept-list Ctrl and Shift selection, collapsible headings, section buttons that select and summarise, a grouped
  right panel.
- Connection form: modes for groups, sentence rows, per-row reverse. Concept form: no topic dropdown.
- Layout presets (computed and `config/layouts/*.json`), Download layout, per-browser positions with Reset.
- `summary` stage (8 cards).

Verified: pytest tests/agent/concept_graph (320), node viewer tests (45), and headless Edge runs with `?debug` for
selection, ranges across a collapsed section, section buttons on the real graph copy, the connection form and the
timeline layout.

Open: the 8 section summaries are not drafted yet (run `collect summary`, then `submit`); the migration of the
graph repo's section fields and 8 concept topics is scripted in the plan (Task 7) and waits for this branch to land;
section summaries are not shown anywhere until then.
