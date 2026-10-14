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
