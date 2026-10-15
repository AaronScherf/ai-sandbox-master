# Concept graph viewer: multi-select, topic summaries, connection form and layout presets

Date: 2026-10-14. Extends [the reviewer proposals design](2026-10-14-concept-graph-reviewer-proposals-design.md) and
the viewer in `agent/concept_graph/viewer/`. Fixes the multi-select path of that design, which does not work today.

## Goal

A reader can select several concepts in the ways they expect (Ctrl-click, Shift-click, box-select, whole topics),
move them together, read what is selected in the right panel, and propose connections from a selection. Readers can
switch between ready-made layouts.

## Terms

- **Concept**: a node. **Topic**: a vocabulary topic (`order-theory`, `rational-choice`, ...), shown as a colour and as
  a button in the left sidebar. **Section**: a course section; the headings in the sidebar's concept list are sections.
- **Topic button**: the topic filter buttons in the left sidebar. **Concept list**: the sections-and-concepts list below.
- **Selected**: highlighted on the canvas and listed in the right panel. **Visible**: not hidden by a filter.

## Decisions (made with the owner)

- Topic buttons stay filters; they also select and summarise (below).
- The right panel always groups a selection by topic, with collapsible sections (option c), whatever created the
  selection. Topic summaries only for whole topics; partial topics show a clickable concept list. No on-the-fly
  generated summaries.
- Box-select is an unordered group, so its connection form asks which concept is the source, with modes.
- Layout presets are a shared pool shipped with the graph; users cannot publish layouts.

## Selection on the canvas

- **Tap** a concept: replaces the selection (as today).
- **Ctrl, Cmd or Shift-tap**: adds to or removes from the selection and does not clear it. The existing tap handler
  calls `select()`, which clears everything first; it must skip that when a modifier key is held. This is the bug that
  stops multi-select working today.
- **Shift-drag on empty canvas** (Cytoscape box selection) selects everything inside; dragging any selected concept
  moves all selected concepts. Neither is disabled in the viewer today.
- **Removing one concept**: Ctrl, Cmd or Shift-tap on an already selected concept deselects just that concept and
  keeps the rest, so a group can be built up and trimmed without starting again.
- **Escape** or **Clear selection** empties the selection. Hiding a topic deselects its concepts, so nothing hidden is
  ever selected.

## Selection in the concept list (left sidebar)

- **Click** a concept name: replaces the selection with that concept (and centres it, as today).
- **Ctrl or Cmd-click**: toggles that concept: adds it, or removes it when it is already selected.
- **Shift-click**: selects the range, in the list's displayed order, between the last-clicked concept and this one,
  including both ends. The range crosses section headings: `Total order` then Shift-click `Continuous preference`
  selects every concept listed between them, in list order.
- Clicking a concept name inside the right panel's lists behaves as a plain click in the concept list; Ctrl or
  Cmd-click there toggles it, and each listed concept also has a small remove (x) control.

## Topic buttons

Plain click only: there are no Ctrl or Shift variants on the topic buttons. The filter semantics are unchanged: a highlighted button means that topic is visible; with none highlighted
everything is visible; clicking a button from that state shows only that topic.

| Action | Visible | Selected | Right panel |
|---|---|---|---|
| Click a non-highlighted button | adds the topic (from none highlighted: only that topic) | that topic's visible concepts replace the selection | grouped list; the topic's summary when it is fully selected |
| Click a highlighted button, others still highlighted | hides that topic | its concepts are deselected | whatever is still selected, grouped |
| Click the only highlighted button | whole map back | nothing | plain panel, no summary |

## Right panel for a selection

- **One concept selected**: the existing detail view, unchanged (prerequisites, accept, reject, edit, propose).
- **Two or more selected**: a heading "N concepts selected" with **Clear selection** and **Add connection**, then one
  collapsible section per topic, headed `<topic>, k of n selected`:
  - a topic whose visible concepts are all selected shows its **summary** and then its concept list;
  - a partly selected topic shows only its concept list. Each name is clickable (a plain click selects only it);
  - the most recently added topic is expanded and the others collapsed; the summary of a collapsed fully selected
    topic is still one click away. For a box-select across topics, the expanded topic is the one with the most newly
    selected concepts, ties by button order.
- "All visible concepts of a topic" is measured after the current filters (kind, status, search), and the heading says
  "(filtered)" when some are hidden, so a filter cannot make a summary unreachable.
- **Summary text is always agent-drafted.** A topic's summary is its `description`, a cohesive short paragraph in
  the owner's review flow (see *Summary stage*). The page never shows concatenated one-line summaries: when a topic or
  section has no description yet, the panel shows the concept list only, and `validate` warns about the missing
  description. A composed placeholder exists only behind `?debug` for development.
- **Section selection**: clicking a section heading in the concept list selects every visible concept of that section
  and shows that section's summary above the grouped list. Topic summaries still appear for any topic that is fully
  selected.

## Summary stage

A small agent stage (`summary`, same card, validate and submit flow as `fill`) drafts one summary per topic and per
section: 8 + 8 cards today. Each card shows the member concepts (names, one-line summaries, explanations) and the
relevant retrieved passages, and asks for one cohesive paragraph of at most about 90 words in the agent's own
words, with the same meta-commentary and own-words checks as `fill`. Results are stored in
`config/topics.yaml` (`{topic-id: {description}}`) and as a `summary` field on each section in
`data/sections.yaml`; `build` embeds them in `graph.json`. Because a topic's membership changes as concepts are
added, `validate` also warns when a description is older than its membership (hash of the member ids).

## Connection proposals from a selection

- **Ordered pick** (clicks, Ctrl-clicks): the first concept picked is the source, the rest are targets, one row each.
- **Group** (box-select, topic button, range): there is no natural source, so the form shows a **mode** chooser and
  a concept dropdown for the chosen concept, defaulting to the earliest in the course (lowest section, then name):
  - **One to many**: the chosen concept is the From; every other selected concept is a To.
  - **Many to one**: the chosen concept is the To; every other selected concept is a From.
  - **Chain in course order**: each concept to the next, earliest first.
  - **All pairs**: capped at four concepts (six rows); direction earlier section to later, reversible per row.
- Add connection is disabled above 12 selected concepts, with the reason in a tooltip.
- **Row layout** reads as a sentence: `[From concept (text)] [type dropdown] [To concept dropdown] [reverse] [remove]`.
- **Reverse** is per row: it swaps that row's From and To (the text becomes the other concept, the dropdown takes the
  old one). A **Reverse all rows** button is also offered. Conditions are asked per row for `implies` and `iff`.
- Everything else is as in the reviewer proposals design (validation, merging, version 2 review files).

## Layout presets

- A **Layout** dropdown at the top of the left sidebar switches the arrangement with a short animation.
- **Computed presets** (in the browser): *Spread* (today's default), *Section rows*, *By topic* (clusters by topic,
  ordered by section within a cluster), *Course timeline* (sections left to right).
- **Authored presets**: `config/layouts/<name>.json` in the graph repo, `{ "name": ..., "positions": {id: {x, y}} }`.
  `build` validates them (unknown ids are an error, missing ids are placed by Spread) and embeds them in
  `graph.json` as `layouts`.
- **Authoring**: a **Download layout as preset** button saves the current positions as a file in that format. The
  maintainer drops it into `config/layouts/`, so shared layouts come from the maintainer, not from users.
- **Per-browser moves**: dragged positions are kept in the browser's `localStorage` keyed by graph version and layout,
  with a **Reset layout** button. They are not sent anywhere.

## Testing

- **Pure logic** (`logic.js`, Node tests): range selection in list order across sections, group modes (rows and
  directions), "fully selected" with filters, topic-button state transitions (the table above), `layouts` parsing.
- **Python**: `build` accepts and rejects layout files, embeds them, and the page data includes them.
- **Headless Edge** with a debug-only hook (`?debug` exposes the Cytoscape instance): Ctrl-click two concepts and see
  the button and the form's source; box-select and see the mode chooser; drag a selected group and check all positions
  moved; click a topic button and check filter, selection and summary; switch layout presets.

## Out of scope

Live or on-the-fly generated summaries, shared user-made layouts, proposing topics, drag-to-connect on the canvas, and
summaries for arbitrary combinations of concepts (only whole topics and whole sections have summaries).

## Open items

- Wording of the summary stage's card (how long, how technical) is settled when the stage is written.
