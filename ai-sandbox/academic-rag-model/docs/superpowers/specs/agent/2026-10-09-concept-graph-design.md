# Concept Graph: Design

Status: draft for owner review (2026-10-09). Nothing is implemented. This spec consolidates the brainstorm held
on 2026-10-09; each decision below was put to the owner and accepted unless marked *open*.

## Intent

A study aid for the microeconomics course (ECON 6211): a **directed concept graph** whose nodes are the course's
key ideas (binary relation, preorder, partial order, preference relation, utility function, Sen's alpha/beta,
WARP, GARP, Szpilrajn, ... through consumer demand and Walrasian demand) and whose edges say *how* they connect,
including which statements imply or are equivalent to which, **and under what conditions**. Every node and edge
carries a plain-language explanation. It is read by people, not computed on.

Success means: a student can open one link, browse the graph by name, click any concept to read what it is, see
what it needs and what it leads to, and trace the dependency path from the course's first building blocks up to
the current frontier. The data behind it is reproducible from the corpus and reviewable by colleagues.

**Non-goals.** No general-purpose knowledge-graph platform; no graph database; no inference over the graph; no
practice-problem generation (a later extension may link to `agent/problem_gen`); no editing of the master data by
anyone but the maintainer.

**Constraints carried from the owner.**
- The repo is public. Node and edge text is **original wording plus citations**, never source text (enforced, see
  IP guard). Citations point to Rubinstein / Mas-Colell / Ok sections, lecture dates and problem-set questions.
- Cost-aware: subscription IDE agent (Antigravity first, Claude Code also works) is the **default** LLM; metered
  API is the fallback driver. Any API run estimated over $1 needs the owner's go-ahead.
- Built for growth: the course has sections still to come; nothing may assume Walrasian demand is the top.

## Decisions

| # | Decision |
|---|---|
| D1 | Source of truth is **YAML** (LaTeX-friendly), built into one `graph.json`. No graph DB. |
| D2 | Authoring is **curated skeleton + grounded fill-in** (approach 1): a human-reviewed node list, then an LLM drafts explanations/edges from retrieved corpus passages. |
| D3 | Output is a **self-contained interactive HTML viewer** (Cytoscape.js). Obsidian notes are an optional by-product, not the product. |
| D4 | The whole planned syllabus is seeded; untaught sections are `planned` (faded, unfilled). |
| D5 | Review happens **in the viewer** (accept / reject / edit); the maintainer applies review files with a CLI. Reviewers never edit master. |
| D6 | Data + viewer live in a **separate public mini repo**, served by GitHub Pages. |
| D7 | Default reviewer path is **Submit -> prefilled GitHub issue**; download-and-email is the fallback. |
| D8 | Deviation from `academic-rag-model/CLAUDE.md` ("human-decision steps default to a db-backed Artifact"): the portable file/issue flow is first; an Artifact `db` adapter is a later phase behind the same storage interface. |

## Data model

Authored as YAML in the mini repo; validated by Pydantic models in `schema.py` plus a JSON Schema export.

### Sections (`data/sections.yaml`)

```yaml
- id: s00-math-background      # stable slug; never reused
  title: Mathematical background
  order: 0                     # float; insert between neighbours without renumbering
  state: taught                # taught | in_progress | planned
  lectures: []
  syllabus_ref: "Part 1, Ok ch. 1"
- id: s01-binary-relations
  title: Binary relations and orders
  order: 1
  state: taught
  lectures: ["2026-09-07", "2026-09-10"]
```

`state` drives rendering (planned = faded) and which sections `fill`/`link` process by default. Appending a
section extends the layout upward automatically; layout height comes from section `order`.

### Nodes (`data/nodes/<section-id>.yaml`)

```yaml
- id: partial-order                 # stable slug
  name: Partial order
  kind: object                      # open vocabulary, config/vocab.yaml
  section: s01-binary-relations     # where in the course it appears
  topic: order-theory               # thematic area (colour); distinct from section
  introduced_in: "2026-09-10"       # optional lecture date
  gist: A preorder that is also antisymmetric.        # one line, hover label
  explanation: |                    # our own words; LaTeX allowed
    ...
  formal: |                         # optional formal statement
    $\succsim$ is reflexive, transitive and antisymmetric.
  example: |                        # optional example or counterexample
    ...
  citations:
    - {source: rubinstein, ref: "ch. 2, 2.1"}
    - {source: lecture, ref: "2026-09-10"}
  status: proposed                  # proposed | verified
  critic: {verdict: supports, note: ""}     # supports | weak | unsupported
  provenance: {driver: agent, agent: antigravity, run: "2026-10-12T10:02", model: null}
  reviewed_by: null
  reviewed_on: null
```

Open `kind` vocabulary (extend in `config/vocab.yaml` with one line): object, structure, property, axiom,
definition, theorem, lemma, model, function, correspondence, identity, technique, example.

### Edges (`data/edges/<section-id>.yaml`; an edge lives in the file of its higher-`order` endpoint)

```yaml
- id: total-order--is_a--partial-order
  source: total-order
  type: is_a
  target: partial-order
  condition: "also complete: every pair is comparable"
  via: null                         # optional theorem node id
  explanation: |
    ...
  citations: [...]
  status: proposed
  critic: {...}
  provenance: {...}
```

| Type | Reads as | Direction / notes |
|---|---|---|
| `is_a` | "A is a B, that also ..." | A -> B; `condition` = what A adds. Taxonomy only (total order is_a partial order). |
| `has_property` | "A has property P" | object -> property node (reflexivity, antisymmetry, transitivity). |
| `defined_on` | "A is defined on B" | object -> the set/relation it lives on. |
| `implies` | "A implies B, when ..." | A -> B; `condition` required; optional `via` theorem. |
| `iff` | "A holds exactly when B, when ..." | one double-headed edge, never two edges; `condition` required. |
| `hypothesis_of` | "A is an input to theorem T" | premise -> theorem node. |
| `yields` | "T yields B" | theorem node -> conclusion. |
| `counterexample_to` | "A shows the converse of E fails" | example node -> edge or node; use sparingly. |

Rule of thumb: a named result with its own proof or story is a **theorem node** wired with `hypothesis_of` /
`yields` (Szpilrajn: partial order -> theorem -> total order, an existence/extension result, not an implication).
A plain entailment stays a direct `implies` / `iff` (Sen's alpha + beta <=> WARP), optionally with `via`.

IDs are stable slugs; renaming a display `name` never changes an `id`. A rejected item is recorded in
`data/rejected.yaml` (a tombstone of `{kind, id|source+type+target}`) so later `link` runs do not re-propose it.

## Pipeline (`agent/concept_graph/`, run as `python -m agent.concept_graph.cli <stage>`)

Code lives in the monorepo; data lives in a configured checkout of the mini repo (`--graph-repo`). Exactly one
writer per checkout (child-repo rule in `docs/WORKTREE_WORKFLOW.md`). Every stage is idempotent: it only creates
or updates `proposed` items, never touches `verified` items, and only `--redo <id>` regenerates a proposed one.

1. **`seed`** drafts `sections.yaml` and the node skeleton (`id`, `name`, `kind`, `section`, `topic`,
   `state: planned`) from the syllabus, professor notes, lecture notes, and chapter headings of Rubinstein,
   Mas-Colell and Ok. Output is a file to edit; the owner approves the skeleton before `fill`. Re-run per new
   section. It runs without the 2024/2025 prior-year material but is better with it (it shows this professor's
   sequencing); that material is a separate transcription task.
2. **`fill`** (per node, only `taught`/`in_progress` sections unless `--include-planned`) retrieves passages and
   drafts `gist`, `explanation`, `formal`, `example`, `citations`.
3. **`link`** proposes edges among **existing ids only**, with type, condition, explanation, citations.
4. **`critic`** is a separate, blind pass: re-reads each edge's cited passages and returns
   `supports | weak | unsupported`. Failures are flagged, not dropped.
5. **`build`** validates and writes `build/graph.json` and the viewer `index.html`; optionally Obsidian notes.

### Retrieval

`core.indexer.index_search` / `agent.rag.rag_agent.retrieve_passages` over the `microecon` course. Current-offering
material ranks first; passages whose card carries a prior-offering label (`.notes_subset.json`, e.g. 2024, 2025)
are corroboration, cited as such. The only network call in agent mode is the Gemini query embedding the tutor
already makes. The cross-offering linkage (`core/indexer/offering_links.py`) is used as is, to mark prior-year
duplicates; it is per-file, not per-passage.

### Drivers

One task contract, two transports. A **task** is `{id, stage, node/edge ids, retrieved passages, schema, rules}`.

- **agent driver (default).** `collect` writes `work/<stage>/<task-id>.md` task cards (passages, target schema,
  rules including own-words and existing-ids-only) and an index `work/<stage>/worklist.md`. The IDE agent writes
  `results/<task-id>.yaml`. `submit` validates every result (schema, ids exist, citations resolve to real chunks,
  IP guard) and bounces bad files with the reason, as `agent/tutor` `prep-submit` does. `critic` task cards omit
  the original drafting reasoning (blind pass).
- **api driver (`--driver api`).** Same task cards sent through `core/env/gemini_utils`. Prints an estimated token
  and dollar cost first and refuses to proceed above $1 without `--approve-cost <usd>`. Default model is
  configurable, defaulting to the repo's current default in `agent/study_guide/revise/cost.py`.

*Open:* the generic collect/submit/validate helper is also wanted by the agent-driven transcription mode (a
separate spec, started elsewhere; see `docs/status/transcribe_notes/`). This package defines its own thin
version behind a `Driver` interface now and adopts a shared helper if one lands first.

### IP guard

Prose fields (`gist`, `explanation`, `example`, comments) are rejected if they share a run of 8 or more
consecutive normalized words with any retrieved passage; the task is bounced with the offending span for
rewording. `formal` (LaTeX) is exempt because a formal statement legitimately matches. The threshold is a config
value to tune on real output; it is a tripwire, not a legal guarantee.

### Build-time validation

JSON Schema + Pydantic; no dangling `source`/`target`/`via`; no duplicate ids; every edge type used is in the
vocabulary; `implies`/`iff` have `condition`; `via` references a `theorem`/`lemma` node; cycles detected in the
subgraph of `is_a`, `implies`, `hypothesis_of`, `yields` (an `iff` pair is allowed, anything else is an error
listing the cycle); orphan nodes warned; section ids exist. NetworkX does the graph checks.

## Viewer (`agent/concept_graph/viewer/`, built to a single `index.html`)

Stack: Cytoscape.js with a layered layout (dagre or ELK, to be chosen on the real graph), KaTeX for LaTeX. JS/CSS are
inlined so the file works offline; size budget is 5 MB.

- Layered by section `order` (bottom = earliest), colour by `topic`. `planned` sections faded; `proposed` items
  dashed, `verified` solid; `critic` flags shown as a small marker.
- Left: searchable name list; filters by topic, section, kind, edge type, status.
- Click a node: side panel with gist, explanation, formal, example, citations, and every in/out edge written as a
  sentence ("Needs completeness and transitivity => ..."). Click an edge: type, condition, explanation, `via`.
- **Dependency-path mode:** highlight everything a node transitively needs (reverse closure over `is_a`,
  `defined_on`, `has_property`, `hypothesis_of`, `implies`).
- Any current browser (Chrome, Edge, Firefox, Safari), desktop or phone. Readable at a glance: node names are
  never truncated; zoom/pan and a "fit" button.

### Review layer

Behind a storage adapter interface `{load(), record(decision), export(), submit()}`:
- **LocalFile adapter (built first).** Decisions persist in `localStorage` (guarded; the page works without it).
  **Submit** copies the review JSON to the clipboard and opens the repo's prefilled GitHub issue form; **Download**
  saves `review-<name>-<date>.json` as the no-account fallback.
- **ArtifactDb adapter (later phase).** Same UI published as an artifact whose `db` holds decisions; `apply-review`
  reads them with `ArtifactData`. Master -> artifact is a one-way republish; the artifact is never the master.

Controls on every proposed node/edge: Accept, Reject, Edit (text box over the explanation or condition), Comment.

## Review files and `apply-review`

```json
{
  "schema_version": 1,
  "graph_version": "<git sha or content hash of the graph the reviewer opened>",
  "reviewer": {"name": "..."},
  "created": "2026-10-20T14:03:00Z",
  "decisions": [
    {"target": {"kind": "edge", "id": "..."}, "action": "accept"},
    {"target": {"kind": "node", "id": "..."}, "action": "edit", "field": "explanation",
     "base_hash": "<hash of the field when opened>", "new_value": "..."},
    {"target": {"kind": "node", "id": "..."}, "action": "comment", "comment": "..."}
  ]
}
```

`apply-review <file...>` or `apply-review --from-issues` (uses the `gh` CLI to read issues labelled `review`):
- `accept` -> `status: verified`, `reviewed_by`, `reviewed_on`. `edit` -> new value, `verified`. `reject` -> item
  removed and tombstoned. `comment` -> appended to `review-comments.md`, no data change.
- **Conflicts are never auto-resolved.** If the target field's current hash differs from `base_hash`, or two
  reviewers made different edits to the same field, the decision is written to `review-conflicts.md` and left
  unapplied for the maintainer.
- Uses `ruamel.yaml` round-trip so formatting and comments survive. One commit per reviewer
  (`review: apply <name>`), so `git diff` shows exactly what changed. Applied files are archived under
  `reviews/applied/`.

Because reviewers only ever produce new files or issues, there are no git merge conflicts by construction.

## Mini repo and publishing

```
microecon-concept-graph/         (public)
  data/{sections.yaml, nodes/, edges/, rejected.yaml}
  config/vocab.yaml
  build/graph.json
  index.html                     (built viewer; served by GitHub Pages)
  reviews/applied/
  .github/ISSUE_TEMPLATE/review.yml   (form with one textarea for the pasted review)
  README.md  LICENSE (CC BY-NC-SA 4.0, content)  LICENSE-CODE (MIT, viewer)  NOTICE.md
```

Colleagues clone nothing: they use the Pages link, review, press Submit, paste into the issue form, and send.
A static page cannot write to the repo without a secret or backend, so the paste step is the floor. The issue
form is prefilled from the page where the URL length allows; otherwise the clipboard carries it. *Open:* confirm
the prefill-by-field-id behaviour of issue forms and the practical URL limit when building the template.

### Licensing and notice

A fair-use statement does not create fair use. What protects the repo is that the content is original wording
plus citations, enforced by the IP guard. The license expresses intent: CC BY-NC-SA 4.0 for data and text (others
can be held to non-commercial terms), MIT for viewer code. `NOTICE.md` states: independent, educational,
non-commercial student project; not affiliated with or endorsed by any author, publisher or university; sources
are cited for orientation and none of their text is reproduced; contact address for takedown requests. No lecture
slides or solution text is copied in; the professor is not named. This is not legal advice.

## Cost control

Agent driver costs subscription quota, not API dollars. API driver: estimate first, hard stop above $1 without
`--approve-cost`. A full pass over roughly 150 nodes is several calls per node, so expect it to cross $1 on the
API; that is why the agent driver is the default. No stage runs automatically.

## Testing

- Unit: schema validation and vocabulary; IP guard (overlap, normalization, `formal` exemption); build-time
  validation (dangling ids, bad `via`, cycle detection, `iff` allowed); `apply-review` (accept, edit, reject,
  stale `base_hash`, two-reviewer conflict, round-trip formatting).
- Fixture: a hand-written ~12-node graph (binary relation -> preorder -> partial order -> total order via
  Szpilrajn; choice structure -> Sen alpha/beta <=> WARP <=> rational preference; one planned section) used for
  `build`, the viewer, and an end-to-end run with a fake driver (no network).
- Viewer: pure functions (dependency closure, edge-to-sentence rendering) unit-tested under Node if available;
  otherwise verified manually in a browser from the fixture build. The first real graph is reviewed by eye.
- All Gemini calls mocked in tests; no paid call in CI.

## Rollout phases (each its own plan task)

1. Mini repo created; `schema`, `build`, validation, and the viewer on the hand-written fixture.
2. `apply-review` and the LocalFile review adapter, plus the issue template; dry-run with one real colleague.
3. `seed` for the whole syllabus; owner edits the skeleton.
4. `fill` / `link` / `critic` with the agent driver on `taught` sections; owner review; then the API driver.
5. Publish via Pages with license and notice; share the link.
6. Later: ArtifactDb adapter, Obsidian by-product, per-section incremental runs as lectures arrive, practice-problem
   links, GitHub Actions validation of incoming review issues.

## Dependencies and risks

- **Prior-year transcription** (`2024_class/`, `2025_class/`, 86 PDFs): optional input to `seed`, run separately;
  markers added 2026-10-09, nothing transcribed yet.
- **Agent-driven transcription mode**: separate spec; this package does not wait for it.
- **Edge accuracy** is the main quality risk (a wrong implication in a study guide is worse than a missing one).
  Mitigations: existing-ids-only, blind critic pass, `proposed`/`verified` marking, human review before `verified`.
- **Granularity drift** (too many or too few nodes): controlled by the human-approved skeleton.
- **Pages / issue-form behaviour** and **layout engine choice** are verified at build time, not assumed here.
