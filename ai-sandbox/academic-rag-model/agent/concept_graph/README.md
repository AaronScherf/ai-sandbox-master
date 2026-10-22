# concept_graph

A study aid for a course (first built for microeconomics): a directed **concept graph** whose nodes are the course's
key ideas (binary relation, preorder, WARP, Szpilrajn extension, ... up through demand) and whose edges say how they
connect and **under what conditions** one implies another. It is read by people, in a single self-contained
HTML page, and reviewed by colleagues through that page. Design: [`docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md`](../../docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md).

This package has two halves: the **core** (data, validation, viewer, review loop, repo scaffolding) and the
**drafting stages** (`seed`, `fill`, `link`, `critic`) that propose nodes, explanations and edges from the
corpus for people to review. Nothing a stage writes is ever `verified`.

All commands run from `ai-sandbox/academic-rag-model/` as modules:

```
python -m agent.concept_graph.cli --graph-repo <path> <command> ...
```

## The graph repo

Data lives in a separate checkout, never in this monorepo. Microecon's graph repo is public and serves its own page;
econometrics keeps its graph repo private and publishes only the built page from a public site repo (see
"Publishing").

```
config/vocab.yaml        kinds and topics (open vocabularies); a kind may be {name, help}, help shown on the seed card
config/site.yaml         page title, the course subject (named on fill and seed cards), and the GitHub repo
                         reviews are submitted to
data/sections.yaml       the course outline, in order
data/nodes/<section>.yaml    concepts, one file per course section
data/edges/<section>.yaml    connections
data/rejected.yaml       tombstones, so a rejected item is not re-proposed
build/graph.json, index.html    built output (served by GitHub Pages)
reviews/applied/         review files that have been merged
review-comments.md, review-conflicts.md    reviewer notes and unapplied edits
```

`agent/concept_graph/sample_data/` is a hand-written 17-node graph used by the tests and by `scaffold --with-sample`.

## Commands

| Command | What it does |
|---|---|
| `validate` | Checks the graph; prints errors and warnings; exits 1 on errors. |
| `build` | Validates, then writes `build/graph.json` and a single `index.html` (libraries inlined, works offline). |
| `apply-review FILE... [--from-issues OWNER/REPO] [--commit] [--close-applied]` | Merges review files (or open GitHub issues labelled `review`) into the YAML. |
| `scaffold --repo OWNER/NAME --holder "Name" [--title T] [--subject S] [--hub-root H --course C] [--with-sample] [--contact TEXT]` | Creates a new graph repo skeleton with README, NOTICE, licenses, issue form, titled and described for the course; with `--hub-root/--course` the `seed.yaml` template lists the course's textbook keys. Needs network once, for the Creative Commons legal text. |

Examples against the sample:

```
python -m agent.concept_graph.cli --graph-repo agent/concept_graph/sample_data validate
python -m agent.concept_graph.cli --graph-repo agent/concept_graph/sample_data build
```

(`build` writes `index.html` and `build/` into the directory it is given; delete them from `sample_data/` afterwards.)

## Data model

- **Nodes**: `id` (stable slug), `name`, `kind`, `section` (where in the course), `topic` (thematic area, colours the
  graph), `gist`, `explanation`, optional `formal` and `example`, `citations`, and review fields.
- **Edge types** (code constant `EDGE_TYPES`): `is_a` (A is a B that also ...), `has_property`, `defined_on`,
  `component_of` (A is one of the conditions making up bundle B), `implies` and `iff` (both need a `condition`;
  optional `via` names a theorem), `hypothesis_of` and `yields` (wire a named theorem node), `counterexample_to`,
  `uses` (essential input), `applies_to` (nonexclusive application), `estimates` (sample rule to population target),
  `computed_from` (formula dependency), `variant_of` (method lineage without strict subtype identity),
  `defined_via` (A's definition is stated in terms of B; definitional, cycle-checked), and `assumption_of` (A is a
  condition imposed by model, estimator or procedure B; theorem premises stay `hypothesis_of`).
  A nonempty `condition` appears in the graph sentence for every type; for `is_a` it describes what the subtype adds.
  Edge id is always `<source>--<type>--<target>`.
- **Status**: `proposed` (dashed in the viewer) or `verified`. Only a person's accept or edit sets `verified`.
- **Sections** have a `state`: `taught`, `in_progress` or `planned` (faded; skipped by the unfilled/orphan checks).
- Validation errors: dangling endpoints, duplicate ids, unknown kind/topic/section/edge type, missing `condition`,
  bad `via`, self-loops, and cycles among definitional edges. Cycles among `implies`/`hypothesis_of`/`yields`
  are warnings (mutually implying results with different conditions are legitimate).

## Drafting stages

Each stage turns corpus passages into **proposed** items that a person then reviews in the page.

The task cards, run manifests and the collect/submit/api loop behind these stages now live in [`core/agent_tasks/`](../../core/agent_tasks/README.md), shared with other pipelines. `tasks.py` and `work.py` here are compatibility shims that re-export from core, and `drivers.py` is the thin adapter that binds the generic loop to the graph store and the stage registry. Existing import paths, the card format and the manifest keys are unchanged, so runs already on disk can still be submitted.

| Stage | What it proposes |
|---|---|
| `seed` | The course outline (sections) and a skeleton of concept nodes, from the hub's syllabus, textbook chapter titles, lecture dates and slide titles. For starting a graph. |
| `fill` | `gist`, `explanation`, optional `formal`/`example`, and citations for each unfilled node in a taught section. |
| `link` | Typed edges between existing nodes (with conditions and `via`), each citing evidence. |
| `critic` | A blind second look at each proposed edge: `supports`, `weak` or `unsupported`, with a note. |

**Seed config (optional, per course).** `config/seed.yaml` in the graph repo carries what the files cannot say:

```yaml
scope: "Choice theory only: consumer behaviour, producer theory, risk, time. No game theory or general equilibrium."
must_include:                 # each must end up as a node (a name, or a list of alternative names)
  - Preorder
  - [GARP, Generalized axiom of revealed preference]
textbook_chapters:            # chapters whose section headings the seed card shows (book key or textbook folder name -> numbers)
  mwg: [1, 2, 3]
min_nodes_per_section: 6   # every section must end with at least this many nodes (default 1)
```

**Course materials.** What each file in the course is (syllabus, instructor slides or notes, recitation, problem
set, exam, textbook, the student's own notes) comes from the shared catalog in
[`core/course_materials/`](../../core/course_materials/README.md), not from folder names. `collect` loads it once per
run (rebuilding it when the course's files changed); `collect seed` stops while files are flagged for review and names
them (decide them with `python -m core.course_materials.cli ... decide`, or pass `--allow-unreviewed`).

`seed` builds its evidence from that catalog, class material first: the syllabus (contact details stripped); the
labelled statements (definitions, assumptions, theorems ..., numbered or not) and section headings of the
instructor's slides and notes; recitation headings; earlier offerings' slides; textbook chapter titles and the
section headings of the chapters listed above; and last, the student's lecture notes, which the card says may contain
mistakes (class material wins where they disagree; the fill card says the same). The card explains each vocabulary kind, shows a format example, and ends with a
self-check. The required list is only a floor (an agent tends to deliver exactly what is required), so `submit` also
bounces any section that would end with fewer than `min_nodes_per_section` nodes, as well as a result that omits a required concept, repeats an existing name (compared ignoring case
and punctuation), or uses a kind, topic or section that does not exist. With `--redo`, `seed` is additive: the card
lists what is already in the graph and asks only for what is missing. To use it for another course: classify the
course and review its flagged files (`core/course_materials`), `scaffold --title --subject --hub-root --course`, fill
in `config/seed.yaml` and the `vocab.yaml` kinds, and `collect seed --course <name>`. Folder names do not matter.

**Agent workflow (default; costs subscription quota, not API dollars):**

```
python -m agent.concept_graph.cli --graph-repo G collect fill --hub-root H --course microecon   # writes task cards
python -m agent.concept_graph.cli --graph-repo G bootstrap <run-id> --work-dir W                 # the agent's contract
# collect also prints (and saves as PROMPT.md in the run folder) a ready-to-paste prompt for the agent:
# it names the stage, the run folder and card count, shows a card's first instruction line so the agent can
# confirm it has the right run, lists the stage's rules and says not to submit
# the agent fills the yaml block under "## Result" in each card
python -m agent.concept_graph.cli --graph-repo G submit <run-id> --work-dir W --agent-name NAME  # validate + apply
```

Cards that fail validation are bounced with the reasons written onto the card; fix only those and submit again.
`status` shows the worklist.

**What `submit` enforces:** the result must match the stage's shape; prose must be in the drafter's own words
(8 or more consecutive words shared with an offered passage is rejected, LaTeX `formal` text excepted); every
citation must be a `(source, ref)` pair that was offered on that card; edges may only connect existing node ids,
need a `condition` when they are `implies`/`iff`, and must not repeat an existing or rejected edge or create a
definitional cycle. Verified items are never overwritten, and `submit` twice does nothing the second time.

**Private work directory.** Cards and the manifest contain retrieved source text. The work directory defaults to
`<hub-root>/.agent_work/concept_graph/` and the tool refuses one inside the graph repo.

**API fallback:** `api <stage> --approve-cost USD` sends the same cards to Gemini (paid key), prints an estimate
first and refuses above $1 without `--approve-cost`; replies go through the same validation.

**Order for a new course** (learned on econometrics, the second course; details and reasons in
[`docs/status/agent/concept_graph/2026-10-21-econometrics-second-course-status.md`](../../docs/status/agent/concept_graph/2026-10-21-econometrics-second-course-status.md)):

1. `seed`, then `fill` and `link`, then `critic` from a different agent than the drafter.
2. Check the edge vocabulary: if `applies_to`/`uses` carry about a third of the edges, the course needs more types.
3. After any relink, remove and tombstone edges that a new edge supersedes (link only adds edges).
4. `seed --redo`, then a **syllabus gap check**: compare the syllabus's assigned readings with the node list and enter
   the gaps as reviewer proposals (a schema-version-2 review file through `apply-review`). On econometrics the gap
   check found 21 missing concepts after the corpus seed found 7.
5. Draft the new items (`fill --node`, `link --node --redo`), then `collect critic` **without** `--redo`: it picks up
   only edges with no verdict, while `--redo` overwrites every edge's single critic slot. A retype clears a verdict,
   so critique again after retyping.
6. `build` and publish after each landing round.

Retrieval uses the repo's passage search (`agent.rag.rag_agent.retrieve_passages`); its only network call is the
query embedding. Source keys come from the catalog: each textbook's book key (`mwg`, `hansen`, ...), `slides`
(instructor slides), `notes` (instructor's handwritten notes), `lecture` (the student's notes), `recitation`, `hw`,
`exam`, `syllabus`, `other`; an earlier offering adds its label (`slides-2024`). A retrieved file missing from the
catalog is classified from its path alone, and `collect` lists such files at the end.

## Reviewing

In the page, a reviewer types a name and accepts, rejects, edits or comments on items. **Submit review** opens a
prefilled GitHub issue form (or copies the review to the clipboard when it is too long for a link);
**Download review** saves a `review-<name>-<date>.json` for people without a GitHub account.

`apply-review` never silently overwrites: each edit records the hash of the field the reviewer saw, and if the
field has changed since (or two reviewers edited it differently) the edit goes to `review-conflicts.md` for the
maintainer. Rejecting a node also removes and tombstones its edges. Accepting sets `status: verified` with the
reviewer's name and date. Use `--commit` for one `review: apply <name>` commit per reviewer.

### Publishing

`build` output is not refreshed by landing graph commits, so rebuild after each round. With a public graph repo
(microecon), Pages serves `index.html` from the repo itself. With a private graph repo (econometrics), copy the built
`index.html` into the public site repo (`AaronScherf/econometrics-concept-graph-site`), commit and push. In that setup
`config/site.yaml` `repo:` must name the **site** repo, since reviewers cannot open issues on a private repo, and
`apply-review --from-issues` then reads the site repo too.

### Proposing concepts and connections

The **Propose** menu adds two kinds of decision to a review (review file `schema_version` 2; version 1 files still
apply): a **new concept** (name, kind, section and topic dropdowns, an optional 200-character note and optional
connections) and a **new connection** (source, type dropdown, one or more targets, a condition for `implies` and
`iff`). Selecting two or more concepts with Shift or Ctrl-click shows **Add connection**; the first one selected is the
source. Proposals sit in "Your proposals" and as dotted ghost items until the review is sent, and can be withdrawn.

`apply-review` handles all proposals of a round in one pass after the per-review loop (`reviews.apply_proposals`,
rules in `proposals.py`, mirrored in `viewer/logic.js`). Concepts with similar names are clustered and merged
(majority kind/section/topic, union of connections, every reviewer's note kept with their name); a tie is written to
`review-conflicts.md` as "needs a decision". A proposal similar to an existing concept is not created again: its
connections become edge proposals against the existing concept and its note goes to `review-comments.md`. Invalid
proposals go to `review-conflicts.md` with the reason. Accepted proposals are written as `status: proposed` with
`provenance.driver: reviewer`. Then draft them like any other node: `collect fill --node <id>`,
`collect link --node <id> --redo`, `collect critic`. The similar-name check can merge different concepts whose
names share most words ("Distributed lag model" was merged into "Autoregressive distributed lag model"), so read
`review-conflicts.md` after each round and re-propose under a distinct name if needed.

### Sections, selection and layouts

The **section** is the single grouping: each section in `data/sections.yaml` declares a `topic` slug and a `short`
label, and `validate` errors when a concept's `topic` differs from its section's. The buttons at the top of the left
sidebar are the sections' short labels (they filter, and a click also selects that section's concepts and shows its
summary); the headings in the concept list are the same sections' full titles, with a chevron to collapse them.

Selection: Ctrl, Cmd or Shift-click toggles a concept on the canvas, in the concept list and in the right panel; a plain
click replaces the selection; Shift-click in the list selects the range in list order (collapsed sections included);
Shift-drag on empty canvas box-selects and a selected group drags together. The right panel groups a selection by
section; a fully selected section shows its `summary`. Add connection from a selection: clicks and Ctrl-clicks make the
first concept the source; a group (box, range, section) opens a mode chooser (one to many, many to one, chain, all
pairs). Rows read as sentences and each row has its own reverse button.

Layouts: the Layout dropdown offers Spread, Section rows, By section and Course timeline, plus any
`config/layouts/<name>.json` (`{"name": ..., "positions": {id: {"x": n, "y": n}}}`), which `build` validates and
embeds. "Download layout" saves the current positions in that format; dragged positions are kept per browser.

Summaries: `collect summary` writes one card per section (8 today); `submit` stores the paragraph as the section's
`summary` with a hash of its members, and `validate` warns when a summary is missing or stale. The page never shows
composed summaries.

Debugging: open the page with `?debug` to expose `window.__cg` (the Cytoscape instance and selection helpers) and to
turn layout animation off, which headless browsers need.

### Options added with the later rounds

- **Retrieval fallback:** `collect` tries the paid key, then the free key, then local keyword search, moving on only
  for quota or rate-limit errors (a notice is printed; keyword matches are weaker, so check those cards).
- **`collect link --orphans`** asks again, with a wider retrieval, for explained concepts that have no edges.
- **`fill_hints`** in `config/seed.yaml` (`{node-id: what the explanation should also cover}`) shows an owner's request
  on that node's fill card.
- **`min_nodes_per_section`** in `config/seed.yaml` is a floor for the additive seed (`collect seed --redo`), not a cap.
- **Summaries** (`collect summary`) and **layout presets** (`config/layouts/*.json`) are described under "Sections,
  selection and layouts".

## Vendored libraries

`viewer/vendor/` holds Cytoscape.js and KaTeX (MIT; licenses alongside), fetched once by
`python -m agent.concept_graph.vendor_fetch` and committed, with their SHA-256 in `viewer/vendor.lock.json`. KaTeX
renders to MathML, so no font files are needed.

## Tests

```
python -m pytest tests/agent/concept_graph -q
```

The viewer's pure logic is tested with Node (`node --test agent/concept_graph/viewer/tests/logic.test.js`); that
test is skipped if Node is not installed. The page itself was checked by hand in a browser.

## Not built yet

The Artifact review adapter and an Obsidian export; drag-to-connect on the canvas and an agent stage that
rewrites merged proposal notes.
