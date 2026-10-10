# concept_graph

A study aid for the microeconomics course: a directed **concept graph** whose nodes are the course's key ideas
(binary relation, preorder, WARP, Szpilrajn extension, ... up through demand) and whose edges say how they
connect and **under what conditions** one implies another. It is read by people, in a single self-contained
HTML page, and reviewed by colleagues through that page. Design: [`docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md`](../../docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md).

This package is the **core** (data, validation, viewer, review loop, repo scaffolding). The LLM stages that
draft nodes and edges from the corpus (`seed`, `fill`, `link`, `critic`, agent/API drivers, IP guard) are a
separate follow-up plan and are **not built yet**.

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

`seed`, `fill`, `link`, `critic`, the agent and API drivers, the IP guard, and the Artifact review adapter.
