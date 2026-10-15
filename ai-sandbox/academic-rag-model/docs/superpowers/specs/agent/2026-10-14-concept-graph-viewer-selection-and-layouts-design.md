# Concept graph viewer: sections as the single grouping, multi-select, summaries, connection form, layout presets

Date: 2026-10-14. Extends [the reviewer proposals design](2026-10-14-concept-graph-reviewer-proposals-design.md) and
the viewer in `agent/concept_graph/viewer/`. Fixes the multi-select path of that design, which does not work today.

## Goal

A reader can select several concepts in the ways they expect (Ctrl-click, Shift-click, box-select, whole sections),
move them together, read what is selected in the right panel, collapse parts of the concept list, and propose
connections from a selection. Readers can switch between ready-made layouts.

## One grouping: sections

Today a concept has both a section (when it is taught) and a topic (a vocabulary label, shown as a colour and as the
buttons at the top of the left sidebar). They nearly coincide, and the differences confuse readers. This design makes
the **section the only grouping**:

- Each section declares a `topic` slug and a `short` label (in `data/sections.yaml`). The topic buttons are the
  sections' short labels in course order; the headings in the concept list are the same sections' full titles. Both
  name the same list of concepts.
- A concept's `topic` must equal its section's topic. `validate` reports a mismatch as an error. The topic
  vocabulary in `config/vocab.yaml` becomes the list of section topics. The proposal forms drop the separate topic
  dropdown and derive it from the section.
- **Short labels:** Order theory, Preferences and utility, Revealed preference, Stochastic choice, Consumer demand,
  Duality and Slutsky, Producer theory, Risk and uncertainty.
- **Data fixes** (8 of 104 concepts): `satisficing-procedure` becomes topic `stochastic-choice`; `income-effect`,
  `substitution-effect`, `slutsky-equation`, `slutsky-matrix`, `law-of-compensated-demand` and
  `negative-semidefinite-substitution` become `duality` (section s06); `weak-axiom-of-revealed-preference` stays in
  s02 and becomes `rational-choice`. Colours per concept are unchanged in the other sections.

## Terms

- **Concept**: a node. **Section**: a course section; also the "topic" of its concepts.
- **Section button**: the filter buttons at the top of the left sidebar. **Concept list**: the sections and concepts
  listed below them.
- **Selected**: highlighted on the canvas and listed in the right panel. **Visible**: not hidden by a filter.

## Decisions (made with the owner)

- Section buttons stay filters; they also select and summarise (below). Plain click only, no Ctrl or Shift variants.
- The right panel always groups a selection by section, with collapsible sections, whatever created the selection.
  A summary appears only for a whole section; a partly selected section shows a clickable concept list. No
  on-the-fly generated summaries, and no summary made by joining one-line summaries.
- Box-select is an unordered group, so its connection form asks which concept is the source, with modes.
- Layout presets are a shared pool shipped with the graph; users cannot publish layouts.

## Selection on the canvas

- **Tap** a concept: replaces the selection (as today).
- **Ctrl, Cmd or Shift-tap**: adds to or removes from the selection and does not clear it. The existing tap handler
  calls `select()`, which clears everything first; it must skip that when a modifier key is held. This is the bug that
  stops multi-select working today.
- **Removing one concept**: Ctrl, Cmd or Shift-tap on an already selected concept deselects just that concept and
  keeps the rest, so a group can be built up and trimmed without starting again.
- **Shift-drag on empty canvas** (Cytoscape box selection) selects everything inside; dragging any selected concept
  moves all selected concepts. Neither is disabled in the viewer today.
- **Escape** or **Clear selection** empties the selection. Hiding a section deselects its concepts, so nothing hidden
  is ever selected.

## Selection in the concept list (left sidebar)

- **Click** a concept name: replaces the selection with that concept (and centres it, as today).
- **Ctrl or Cmd-click**: toggles that concept: adds it, or removes it when it is already selected.
- **Shift-click**: selects the range, in the list's displayed order, between the last-clicked concept and this one,
  including both ends. The range crosses section headings and includes concepts inside collapsed sections.
- Clicking a concept name inside the right panel's lists behaves as a plain click in the concept list; Ctrl or
  Cmd-click there toggles it, and each listed concept also has a small remove (x) control.

## Collapsible section headings in the concept list

- Each heading has a chevron that collapses or expands that section's concepts. **Collapse all** and **Expand all**
  controls sit above the list. Everything starts expanded.
- Collapsing only changes the list; it does not hide anything on the canvas, change the filters or change the
  selection. The collapsed state is remembered in the browser (`localStorage`, keyed by graph version).
- The heading's text is not the chevron: clicking the text selects the whole section (below). A search expands any
  section that contains a match.
- A collapsed heading shows a count, `k of n selected` when some of its concepts are selected.

## Section buttons

Plain click only. The filter semantics are unchanged: a highlighted button means that section is visible; with none
highlighted everything is visible; clicking a button from that state shows only that section.

| Action | Visible | Selected | Right panel |
|---|---|---|---|
| Click a non-highlighted button | adds the section (from none highlighted: only that section) | that section's visible concepts replace the selection | grouped list, with the section's summary when it is fully selected |
| Click a highlighted button, others still highlighted | hides that section | its concepts are deselected | whatever is still selected, grouped |
| Click the only highlighted button | whole map back | nothing | plain panel, no summary |

Clicking a section heading in the concept list selects every visible concept of that section and shows its summary,
without changing the filters.

## Right panel for a selection

- **One concept selected**: the existing detail view, unchanged (prerequisites, accept, reject, edit, propose).
- **Two or more selected**: a heading "N concepts selected" with **Clear selection** and **Add connection**, then one
  collapsible group per section, headed `<section short label>, k of n selected`:
  - a section whose visible concepts are all selected shows its **summary** and then its concept list;
  - a partly selected section shows only its concept list. Each name is clickable (a plain click selects only it);
  - the most recently added section is expanded and the others collapsed; a collapsed fully selected section's
    summary is still one click away. For a box-select across sections, the expanded one is the section with the most
    newly selected concepts, ties by course order.
- "All visible concepts of a section" is measured after the current filters (kind, status, search), and the heading
  says "(filtered)" when some are hidden, so a filter cannot make a summary unreachable.
- **Summary text is always agent-drafted** (see *Summary stage*). The page never shows concatenated one-line
  summaries: when a section has no summary yet, the panel shows the concept list only, and `validate` warns about the
  missing summary. A composed placeholder exists only behind `?debug`, for development.

## Summary stage

A small agent stage (`summary`, same card, validate and submit flow as `fill`) drafts one summary per section: 8
cards today. Each card shows the section's concepts (names, one-line summaries, explanations) and the relevant
retrieved passages, and asks for one cohesive paragraph of at most about 90 words in the agent's own words, with the
same meta-commentary and own-words checks as `fill`. Results are stored as a `summary` field on each section in
`data/sections.yaml`; `build` embeds them in `graph.json`. Because a section's membership changes as concepts are
added, `validate` warns when a summary is older than its membership (a hash of the member ids is stored with it).

## Connection proposals from a selection

- **Ordered pick** (clicks, Ctrl-clicks): the first concept picked is the source, the rest are targets, one row each.
- **Group** (box-select, section button, range): there is no natural source, so the form shows a **mode** chooser and
  a concept dropdown for the chosen concept, defaulting to the earliest in the course (lowest section, then name):
  - **One to many**: the chosen concept is the From; every other selected concept is a To.
  - **Many to one**: the chosen concept is the To; every other selected concept is a From.
  - **Chain in course order**: each concept to the next, earliest first.
  - **All pairs**: capped at four concepts (six rows); direction earlier section to later, reversible per row.
- Add connection is disabled above 12 selected concepts, with the reason in a tooltip.
- **Row layout** reads as a sentence: `[From concept (text)] [type dropdown] [To concept dropdown] [reverse] [remove]`.
- **Reverse** is per row: it swaps that row's From and To (the text becomes the other concept, the dropdown takes the
  old one). A **Reverse all rows** button is also offered. Conditions are asked per row for `implies` and `iff`.
- Everything else is as in the reviewer proposals design (validation, merging, version 2 review files), except that
  the concept form has no topic dropdown.

## Layout presets

- A **Layout** dropdown at the top of the left sidebar switches the arrangement with a short animation.
- **Computed presets** (in the browser): *Spread* (today's default), *Section rows*, *By section* (clusters, ordered by
  course), *Course timeline* (sections left to right).
- **Authored presets**: `config/layouts/<name>.json` in the graph repo, `{ "name": ..., "positions": {id: {x, y}} }`.
  `build` validates them (unknown ids are an error, missing ids are placed by Spread) and embeds them in
  `graph.json` as `layouts`.
- **Authoring**: a **Download layout as preset** button saves the current positions as a file in that format. The
  maintainer drops it into `config/layouts/`, so shared layouts come from the maintainer, not from users.
- **Per-browser moves**: dragged positions are kept in the browser's `localStorage` keyed by graph version and layout,
  with a **Reset layout** button. They are not sent anywhere.

## Testing

- **Pure logic** (`logic.js`, Node tests): range selection in list order across sections and collapsed sections,
  group modes (rows and directions), "fully selected" with filters, section-button state transitions (the table
  above), toggle and deselect, `layouts` parsing.
- **Python**: `validate` errors on a topic that differs from its section's; `build` accepts and rejects layout files
  and embeds layouts and summaries; the summary stage's validation (length, own words, meta commentary).
- **Headless Edge** with a debug-only hook (`?debug` exposes the Cytoscape instance): Ctrl-click two concepts and see
  the button and the form's source; Ctrl-click one again and see it leave the selection; box-select and see the mode
  chooser; drag a selected group and check all positions moved; click a section button and check filter, selection
  and summary; collapse a heading; switch layout presets.

## Out of scope

Live or on-the-fly generated summaries, summaries for arbitrary combinations of concepts, shared user-made layouts,
proposing sections, drag-to-connect on the canvas, and Ctrl or Shift variants on the section buttons.

## Open items

- Wording of the summary stage's card (how long, how technical) is settled when the stage is written.
