# Concept graph: reviewers propose concepts and connections

Date: 2026-10-14. Closes TODO-0070 (`docs/trackers/academic_hub_to_do.md`). Extends
[the concept graph design](2026-10-09-concept-graph-design.md); package `agent/concept_graph/`.

## Goal

A reviewer using the public page can say "this concept is missing" or "these two concepts are connected" without
writing prose. The proposal travels in the same review file as accept, reject, edit and comment, and `apply-review`
turns it into a `proposed` item that the existing fill, link and critic stages then draft and check.

Success means: a reviewer can make a proposal in under a minute; nothing invalid or duplicate reaches the graph
silently; two reviewers proposing the same thing add to one item instead of fighting over it; and the maintainer sees
every proposed item before it is accepted.

## Decisions made with the owner

- **Light proposals.** The reviewer supplies a name, dropdown choices and at most a one-line note. The pipeline
  writes the explanation and citations. A "write it myself" form is out of scope.
- **Dropdowns** for kind, section, topic and edge type (the graph's own vocabulary), and pickers that list real
  concepts only, so an endpoint cannot be invented.
- **A concept may list connections** (optional); a connection stands alone or comes from a selection.
- **Duplicates are merged, not dropped,** and the first proposal checked is not treated as the best.
- **Selection, not drag,** is the way to connect concepts on the canvas (drag-to-connect can be added later).

## Interaction

1. **Toolbar "Propose" menu:** "New concept" and "New connection" open an empty form.
2. **From a concept's sidebar:** "Propose a connection from this concept" pre-fills the source. The target is chosen
   by clicking another node on the canvas or from a searchable dropdown.
3. **From a selection:** Shift-click or Ctrl-click two or more concepts; a floating "Add connection" button opens a
   form with the first selected as source, the others as targets, one row per target (own type dropdown and note),
   and a swap-direction button.
4. **New concept form:** name, kind, section, topic (dropdowns), a one-line note (200 characters), and an optional
   list of connections (concept picker, type dropdown, direction, condition when required, note). While the reviewer
   types a name the form lists similar existing concepts ("Did you mean ...?") with links.
5. **After submitting a form** the proposal appears in a "Your proposals" list (withdraw button) and as a dashed
   ghost node or edge on the canvas. Proposals are part of the review that Download or Send already produces.

The reviewer-name gate that guards Accept and Reject also guards Propose.

## Review file (schema version 2)

`schema_version` becomes 1 or 2; the viewer emits 2. `apply-review` accepts both, and proposals are valid only in 2.
`Decision.target` becomes optional for the two new actions.

```json
{"action": "add_node",
 "proposal": {"name": "Quasi-concave utility", "kind": "property", "section": "s05-consumer-demand",
              "topic": "demand", "note": "Upper contour sets are convex.",
              "connections": [{"other": "utility-function", "type": "has_property", "direction": "in",
                               "condition": null, "note": ""}]}}
{"action": "add_edge",
 "proposal": {"source": "a", "type": "implies", "target": "b", "condition": "for single-valued demand", "note": ""}}
```

The node id is computed from the name (slug), never typed. `direction` is `out` (new concept is the source) or `in`.
A proposal's identity inside the page is `proposal|node|<slug>` or `proposal|edge|<id>`, so it can be replaced or
withdrawn like any other decision.

## Validation (server is the authority)

`proposals.py` (new) holds the rules; `reviews.py` calls it. The page runs the same checks as pure functions in
`logic.js` for instant feedback, with node tests that mirror the Python tests.

Concept:
- slug id valid, not an existing node, not in `rejected.yaml`
- `kind`, `topic` in the vocabulary; `section` exists
- name not empty, at most 120 characters; note at most 200 characters and free of source commentary (`check_meta`)

Connection (standalone, or a concept's connection once the concept exists):
- both endpoints are existing nodes or the proposed concept; no self-edge; edge type in `EDGE_TYPES`
- id (`source--type--target`) not existing, not rejected
- `condition` required for `implies` and `iff` (`CONDITION_REQUIRED`); `via` is not offered in this version
- a definitional cycle is an error, a logical cycle only a warning (the existing `validate` rules)
- not redundant: an `iff` already covers an `implies`; `has_property` against an existing reverse `component_of`

The own-words IP guard compares against retrieved passages and so is not applied; the fill and link stages rewrite
the prose from sources, and the maintainer sees each proposed item. Invalid proposals are written to
`review-conflicts.md` with the reason, as stale edits are today. Nothing is dropped silently.

## Duplicates and merging

A **similarity check** (no embeddings, deterministic) compares a proposed concept with every existing node and every
other proposal in the round, on normalized names (case, punctuation, apostrophes) and aliases:

- exact match after normalization
- one name's tokens contained in the other's with at least two tokens ("Walrasian demand" and "Walrasian demand
  correspondence")
- token-set overlap of at least 0.75
- edit distance of at most 10% of the longer name (typos)

Proposals that match each other form a **cluster**. Handling:

1. **Several proposals in the same round (one file or many).** `apply-review` reads all review files first, then
   clusters. A cluster becomes one `proposed` node. The first one read is not preferred; the merge rule is:
   - `name`: the most frequent normalized form; a tie goes to the longer, more specific one
   - `kind`, `section`, `topic`: majority. A tie is broken by a fixed rule that does not depend on read order (the
     option whose reviewer name sorts first alphabetically) and is always written to `review-conflicts.md` as
     "needs a decision", listing each reviewer's choice, so the maintainer makes the real call
   - `connections`: the union, de-duplicated by (other, type, direction); conditions for the same edge are joined
   - `gist` (the notes): each distinct note joined with the reviewer's name, trimmed to 200 characters, so no one's
     information is lost; the fill stage then writes the real explanation
   - provenance: `agent` lists every contributing reviewer; `run` is the round id; the merge is recorded in
     `review-conflicts.md` as an informational line ("merged 3 proposals for X")
2. **A proposal similar to an existing node.** The concept is not created. Its connections become edge proposals
   against the existing node (validated as above), its note is recorded as a comment on that node in
   `review-comments.md`, and a conflicts line says "treated as proposals about X: confirm or re-propose". A false
   positive therefore costs a maintainer one confirmation, not a lost idea.
3. **Duplicate edges** in or across files collapse to one by id; their notes are joined the same way.

Synthesis is deterministic and traceable in this version. An agent "reconcile" stage that rewrites merged notes is
possible later; the fill stage already rewrites the prose from sources, so it is not needed to avoid information loss.

## What gets written

- Nodes: `status: proposed`, `gist` = merged note, empty `explanation` (so `collect fill` selects it),
  `provenance: {driver: reviewer, agent: "<names>", run: "<round id>"}`.
- Edges: `status: proposed`, `explanation` = merged note, no citations until the critic and link stages run;
  `provenance` as above. The rebuilt page shows them as dashed (unreviewed) items, as proposed items are shown today.
- The review file is archived with the existing `archive_review`.

## Limits

- A proposal is about 300 characters, so 10 to 15 fit in the 6000-character issue URL. A longer review uses the
  clipboard path that already exists; no new mechanism.
- No accounts and no backend: a proposal is only a line in a review file until a maintainer applies it.

## Testing

Python (`tests/agent/concept_graph/test_cg_proposals.py`, plus fixtures in `cg_helpers`):
- each validation rule and each bounce reason, with the exact message
- exact, token-containment, overlap and typo duplicates; a non-duplicate with a shared word ("Utility function" and
  "Indirect utility function") is not merged
- a cluster inside one file, across two files, and with a tie on kind or section
- a proposal similar to an existing node becomes edge proposals and a comment, not a node
- redundant edges, a version 1 review still applying, and a full round trip through `build`

Node (`viewer/tests/proposals.test.js`): slug, similar-node search, proposal checks that mirror the Python rules,
recording, replacing and withdrawing, and `buildReview` emitting version 2. A headless Edge screenshot confirms the
form, the dropdowns and the ghost items render.

## Out of scope

Drag-to-connect on the canvas, a reviewer-written explanation, editing citations, proposing a `via` theorem, proposing
a new section, and any backend or login.
