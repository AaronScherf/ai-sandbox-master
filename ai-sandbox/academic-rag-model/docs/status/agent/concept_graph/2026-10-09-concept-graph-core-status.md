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

- `python -m pytest tests/agent/concept_graph -q`: 74 passed (Node logic tests: 17 of 17, run through pytest).
- Rest of the repo's suite (run with the main checkout's full venv, `--ignore=tests/agent/concept_graph`, because the
  worktree venv only carries this package's dependencies): 2972 passed, 34 subtests passed, exit 0.
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

## Final review and fix pass

A fresh reviewer read the whole branch after Task 10. Findings and what was done:

- **Fixed (each with a test that failed first):** a reject for an item someone else had since verified deleted it silently;
  it is now a conflict entry. Rejecting a theorem node left dangling `via` references that broke the next build; `via` is
  now cleared on those edges. Rejecting a node now lists the edges it removed. `gist` could not be edited in the page
  (backend supported it); it now can (checked in the built page, no automated DOM test). Two prices in one passage
  rendered as broken math; inline math must now hug its dollar signs and not be followed by a digit. `config/site.yaml`
  was the one unvalidated file shipped to the public page; it is now a validated model. `scaffold --with-sample` could copy
  stale build output from `sample_data/`; it no longer does.
- **Deferred minors:** `data-etype` in `app.js` is inserted without `esc()` (safe today because edge types are a
  validated 9-value enum, but the Task 5 ruling overstated "every dynamic string"); `scaffold --contact` does not warn
  about an email address; `gh issue list --limit 100` silently truncates; vendored JS can be rewritten to CRLF by git
  (hash not re-verified at build); Cytoscape `width: "label"` deprecation notice.
