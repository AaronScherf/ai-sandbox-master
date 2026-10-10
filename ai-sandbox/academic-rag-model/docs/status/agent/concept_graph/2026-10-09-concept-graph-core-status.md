# Concept graph core: status (2026-10-09)

Implements Plan A of the concept graph: `docs/superpowers/plans/2026-10-09-concept-graph-core.md`, from the spec
`docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md`. Branch `claude/concept-graph-core`, not merged.
The LLM drafting stages (Plan B) and publishing the public repo are **not done**.

## What was built (`agent/concept_graph/`)

- `schema.py`: pydantic models for sections, nodes, edges, vocab; the nine edge types; `edge_id`, `field_hash`.
- `store.py`: `GraphStore`, a round-trip (ruamel.yaml) reader/writer that keeps comments and formatting.
- `validate.py`: build-time checks (errors block a build, warnings are reported).
- `build.py`: `graph.json` plus one self-contained `index.html` (Cytoscape.js and KaTeX inlined, MathML output).
- `viewer/`: `logic.js` (pure, Node-tested), `app.js`, `style.css`, `template.html`, vendored libraries.
- `reviews.py`, `gh_issues.py`: review files, conflict-safe merge, GitHub issue intake through `gh`.
- `scaffold.py`: skeleton for the public graph repo (README, NOTICE, CC BY-NC-SA 4.0 + MIT licenses, issue form).
- `cli.py`: `validate`, `build`, `apply-review`, `scaffold`. `sample_data/`: a hand-written 17-node graph.

## Verification

- `python -m pytest tests/agent/concept_graph -q`: 68 passed (Node logic tests: 15 of 15, run through pytest).
- Rest of the repo's suite (run with the main checkout's full venv, `--ignore=tests/agent/concept_graph`, because the
  worktree venv only carries this package's dependencies): see "Rest-of-repo suite" below.
- The page was checked in headless Chrome (screenshots plus injected probe scripts, because no interactive browser was
  available to the implementer): title and 17 nodes, section bands with later sections higher, planned section faded,
  proposed items dashed, node and edge panels with sentences, "show what this needs" fading, accept/reject/edit/comment
  decisions, persistence across reloads, review JSON shape, search and topic/status filters, the three Submit/Download
  messages, no console errors, no horizontal overflow at 511 px.
- Not verified: an actual file save from Download review, Submit opening a GitHub tab, Safari and Firefox rendering.

## Decisions that differ from, or add to, the spec

- Edge types are a code constant (spec decision D9); `component_of` added so a conjunction ("Sen's alpha and beta
  together") can take part in an `iff`; cycles among definitional edges are errors, among `implies`/`hypothesis_of`/
  `yields` only warnings (spec amended the same day).
- A "Fit graph to window" button and refit-on-resize were added (the spec asks for a fit button; the plan omitted it).
- The first draft of the layout was illegible at fit zoom and produced a page-level scrollbar; both were fixed after
  the browser check (font 16, five nodes per row, `minmax(0, 1fr)` grid column, no body overflow).

## Known limits

- A price such as `$5` renders as text only when no closing `$` follows on the same line; otherwise it is read as math.
- MathML output needs a current browser (Chrome/Edge 109+, Firefox, Safari).
- A review too long for a link (over 6000 characters) is copied to the clipboard and the reviewer pastes it.
- Cytoscape 3.30 logs a deprecation notice for `width: "label"` (boxes still size correctly).
- The vendored `cytoscape.min.js` may be rewritten to CRLF by git on some checkouts, so its bytes can differ from the
  SHA-256 in `viewer/vendor.lock.json`; the build does not re-verify it.

## What's next

1. Plan B: `seed`, `fill`, `link`, `critic`, agent and API drivers, IP guard (tracked in the to-do tracker).
2. Owner-gated: create the public repo, push, enable Pages, create the `review` label (plan Task 11).
3. Later: Artifact review adapter, Obsidian by-product.

## Rest-of-repo suite

(filled in when the run finishes)
