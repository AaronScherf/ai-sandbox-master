# concept_graph

A study aid for the microeconomics course: a directed **concept graph** whose nodes are the course's key ideas
(binary relation, preorder, WARP, Szpilrajn extension, ... up through demand) and whose edges say how they
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

Data lives in a separate checkout (the public mini repo), never in this monorepo:

```
config/vocab.yaml        kinds and topics (open vocabularies)
config/site.yaml         page title and the GitHub repo reviews are submitted to
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
| `scaffold --repo OWNER/NAME --holder "Name" [--with-sample] [--contact TEXT]` | Creates a new graph repo skeleton with README, NOTICE, licenses, issue form. Needs network once, for the Creative Commons legal text. |

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
  optional `via` names a theorem), `hypothesis_of` and `yields` (wire a named theorem node), `counterexample_to`.
  Edge id is always `<source>--<type>--<target>`.
- **Status**: `proposed` (dashed in the viewer) or `verified`. Only a person's accept or edit sets `verified`.
- **Sections** have a `state`: `taught`, `in_progress` or `planned` (faded; skipped by the unfilled/orphan checks).
- Validation errors: dangling endpoints, duplicate ids, unknown kind/topic/section/edge type, missing `condition`,
  bad `via`, self-loops, and cycles among definitional edges. Cycles among `implies`/`hypothesis_of`/`yields`
  are warnings (mutually implying results with different conditions are legitimate).

## Drafting stages

Each stage turns corpus passages into **proposed** items that a person then reviews in the page.

| Stage | What it proposes |
|---|---|
| `seed` | The course outline (sections) and a skeleton of concept nodes, from the hub's syllabus, textbook chapter titles, lecture dates and slide titles. For starting a graph. |
| `fill` | `gist`, `explanation`, optional `formal`/`example`, and citations for each unfilled node in a taught section. |
| `link` | Typed edges between existing nodes (with conditions and `via`), each citing evidence. |
| `critic` | A blind second look at each proposed edge: `supports`, `weak` or `unsupported`, with a note. |

**Agent workflow (default; costs subscription quota, not API dollars):**

```
python -m agent.concept_graph.cli --graph-repo G collect fill --hub-root H --course microecon   # writes task cards
python -m agent.concept_graph.cli --graph-repo G --work-dir W bootstrap <run-id>                 # the agent's contract
# the agent fills the yaml block under "## Result" in each card
python -m agent.concept_graph.cli --graph-repo G --work-dir W submit <run-id> --agent-name NAME  # validate + apply
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

Retrieval uses the repo's passage search (`agent.rag.rag_agent.retrieve_passages`); its only network call is the
query embedding. Source keys: `rubinstein`, `mwg`, `ok`, `lecture`, `slides`, `hw`, `other`.

## Reviewing

In the page, a reviewer types a name and accepts, rejects, edits or comments on items. **Submit review** opens a
prefilled GitHub issue form (or copies the review to the clipboard when it is too long for a link);
**Download review** saves a `review-<name>-<date>.json` for people without a GitHub account.

`apply-review` never silently overwrites: each edit records the hash of the field the reviewer saw, and if the
field has changed since (or two reviewers edited it differently) the edit goes to `review-conflicts.md` for the
maintainer. Rejecting a node also removes and tombstones its edges. Accepting sets `status: verified` with the
reviewer's name and date. Use `--commit` for one `review: apply <name>` commit per reviewer.

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

The Artifact review adapter and an Obsidian export.
