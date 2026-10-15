# Literature taxonomy pipeline: design spec

Date: 2026-10-15. Status: **design, awaiting owner review**. No implementation approved.
Owner: Aaron Scherf. Author: Claude (architecture), from a brainstorm with the owner on 2026-10-15.
Related pitch: `ai-sandbox/research/independent-research/notes/Pitch - Structured Literature Taxonomy and Research Hub Extension.md`
(this spec supersedes its Section 03/05 on *how*; its schema ideas, landscape analysis and project synergies stand).

## 1. Intent

### Outcome

Turn the journal-article corpus into a **queryable, structured body of evidence** and a set of **human-readable literature artifacts**, and eventually use it to answer "has X been tried in context Y, or is this a new contribution?" and to support shaping a research proposal.

### Stated by the owner

- Transcribe academic PDFs; then extract categorical data and metadata; then summarize related articles thematically into a mini literature review / annotated bibliography; then analyze the resulting database; then gap analysis; then research-proposal support.
- Outputs: a human-readable artifact **and** a database of key components per paper (data sources, methodology, country/region, treatment effects studied, primary results, ...).
- Default to **subscription Gemini in Antigravity**; avoid paid API calls wherever possible.
- The **research index** (`research/.index/`) is made valid for external connections to existing classifications (OpenAlex first); the academic-hub index is aligned later.
- Baseline classification: the **3ie** evidence-gap-map dimensions, extended for other domains and for elements 3ie does not cover.
- Concept_graph's task-card tooling must stay usable by its original pipeline after any relocation.
- ORKG / RDF triples are an explicitly **deferred** extension (section 11).

### Assumptions (owner to correct)

- First target domain is the pitch's: compounded disasters, armed conflict, social protection (the "3R Framework"); the schema is built core-plus-module so other domains plug in.
- Corpus scale for the first milestone is the ~75 papers already harvested, growing to hundreds.
- The owner remains the human relay between Claude/the repo and Antigravity (paste prompt, say "done"), as in concept_graph.

## 2. Goals and non-goals

Goals: reuse existing transcription, indexing and discovery code; make every machine-extracted claim traceable to a quote in the source transcript; keep the database rebuildable from files; keep every LLM step runnable on the subscription route.

Non-goals (this spec): a vector database or server; knowledge-graph / triple store (deferred); replacing OpenAlex discovery; automatic file moves in the corpus; automatic proposal writing; unattended scheduling.

## 3. Verified current state

Verified by reading code and docs in this session (main at `c406ce3`). Items marked *(docs only)* were taken from a status doc and not re-verified in code.

| Area | State |
| --- | --- |
| Journal transcription | `pipelines/convert_journal_articles/convert_journal_articles.py` reuses `transcribe_notes.process_pdf()`. `main()` always calls `get_gemini_client()` (line ~131) and passes no driver, so it is **API-only today**. Index root defaults to `research/`. `--max-pages` guard exists. |
| Agent-driver seam | `process_pdf(..., driver, collect_mode)` already exists. `ApiDriver`, `AgentDriver`, `NullDriver` in `pipelines/transcribe_notes/agent_driver.py`/`agent_work.py`; notes CLI exposes `--driver agent --collect` and `--submit RUN_ID`. `route_notes_transcribe.py` gained the same flags at `c406ce3`; `agent_submit.submit_doc` performs the submit write-through. Its design spec records the guardrail "no hidden generative fallback". |
| Defect heuristic | `page_looks_defective()` is tuned to LaTeX math notes; flags 32-43% of paper pages *(docs only)*. In agent mode this inflates task cards to relay. |
| Task-card system (generic) | `agent/concept_graph/{tasks,work,drivers}.py`: `Task`, `render_card`, `extract_result` (one fenced YAML mapping under `## Result`), `Run` manifest (statuses pending/filled/applied/bounced/skipped), per-stage hooks `make_tasks` / `validate_result` / `apply_result`, `collect` / `submit` / `api_run` with a `$` estimate gate and `--approve-cost`. `tasks.py` and `work.py` are almost fully generic; `drivers.py` binds to `GraphStore` and `stages`. Importers are only concept_graph's own modules and 6 test files. |
| Task-card system (transcription) | `pipelines/transcribe_notes/agent_work.py`: image-page cards, pipe-delimited output. A separate, working system; **left alone** by this spec. |
| Index | `core/indexer/index_card.py`: cards keyed by `file_id` (hash of file bytes), embeddings via MiniLM. Journal conversion indexes into `research/.index/`, not the academic-hub index. |
| Discovery | OpenAlex-only candidate discovery; sidecars (`metadata_sidecar.py`), `manifest.py`, snowball. Folder routing uses level-0 Concepts and a single label (known issue, see the 2026-10-14 audit). |
| Pitch schema | `EmpiricalStudyTaxonomy` (countries, scale, methods, datasets, hazards, intervention, outcomes, study type). Assumes an API/Instructor extraction call; this spec replaces that with task cards. |

## 4. Architecture

Option **A (file contracts, derived database)** was chosen over database-first and knowledge-graph alternatives (section 11).

```
 discovery            stage 1                stage 2                stage 4
 (OpenAlex)  PDF ──▶ transcribe ──▶ .md ──▶ extract ──▶ study_record.json ──▶ derived SQLite
 sidecar IDs     (subscription)    + card   (task cards)   (source of truth)    │
                                                 │                              ├─▶ stage 3 synthesis (review + bibliography)
                                                 └── review Artifact            ├─▶ stage 5 gap analysis (+ live OpenAlex)
                                                     (exceptions only)          └─▶ stage 6 proposal support
```

Principles:

1. **Files are the source of truth; the database is derived and rebuildable.** `study_record.json` per paper, keyed by `file_id`, under `research/.index/study_records/`.
2. **Every LLM step is a task card** (collect, relay to Antigravity, submit). The paid API is an explicit opt-in behind the existing cost gate and the over-$1 warning. No stage silently falls back to the API.
3. **Code validates; Claude is not in the loop.** Schema, vocabulary membership, quote presence and citation integrity are checked in code on submit; failures bounce back with reasons.
4. **Every extracted facet carries evidence** `{value, quote, locator}`; the quote must be found in the transcript.
5. **Humans review exceptions only**, through an interactive Artifact (repo rule), not hand-edited files.
6. **Absence is reported with coverage**, never as bare "novel".

## 5. Shared task-card layer: `core/agent_tasks/` (prerequisite, stage 0)

Lift the generic parts of concept_graph's task-card system into `core/agent_tasks/` and make concept_graph a consumer.

Contents: `Task` and `Passage` (+ optional `attachments: list[str]` of file paths, e.g. page images); card rendering and `extract_result`; `Run` manifest and worklist; `collect` / `submit` / `api_run` parameterized over a `Stage` protocol (`make_tasks`, `validate_result`, `apply_result`) and an opaque apply target; the cost gate. The `graph_repo` argument becomes `output_repo` with `graph_repo` kept as an alias; the privacy guard (cards hold source text and must stay outside the output repo) is preserved.

Compatibility requirements (binding):

- `agent/concept_graph/tasks.py` and `work.py` remain as thin re-export shims; every existing import path continues to resolve, to the **same objects** (asserted by a test with `is`).
- `agent/concept_graph/drivers.py` remains the graph-bound adapter around the generic loop.
- Card format (`## Result`, `## Bounced`), manifest keys (including `graph_repo`) and status names are **byte-compatible**, so an in-flight run can still be submitted after the move.
- Gate: run the concept_graph suite before the move as a baseline; after it, **no test edits in the same commit**; then add the literature stage as the second consumer.
- `core/` changes need tests for the callers too (academic-rag-model CLAUDE.md).

To confirm during planning: hidden graph-only fields on `provenance()` or `Passage`; docs or CLI help text that name these modules.

## 6. Stages

### Stage 1: transcription (adapt existing)

1. Expose the existing driver on `convert_journal_articles.py`: `--driver {agent,api}` (**default `agent`**), `--collect`, `--submit RUN_ID`, `--run-id`, reusing `AgentDriver` and `agent_submit.submit_doc`. Adopt the "no hidden generative fallback" guardrail. `--driver api` keeps the existing client path and the over-$1 warning.
2. Add a journal-prose profile to `page_looks_defective()`: calibrate against the real papers, with regression fixtures. Target: defective-page rate under ~10% for born-digital PDFs. Acceptance is measured, not asserted.
3. Carry identity into the index card from the discovery sidecar: `openalex_id`, DOI, OpenAlex topic IDs, ISO-3166 country codes.
4. Optionally keep rendered page images for pages with result tables so extraction cards can attach them (section 6.2).

### Stage 2: extraction (new: `agent/literature/`)

Input: transcript Markdown plus the index card. Output: `study_record.json`.

Record (sketch; versioned with `schema_version`):

```yaml
identity:    {file_id, openalex_id, doi, title, year}
core:                                   # 3ie-derived baseline
  intervention:   [{value, vocab_id, quote, locator}]
  outcome:        [...]                 # outcome domain
  study_design:   [...]                 # RCT, DiD, RDD, IV, PSM, panel, qualitative, SR...
  sector:         [...]
  geography:      {countries: [ISO], regions: [...], scale, quote, locator}
  population:     [...]
  data_sources:   [{name, vocab_id, resolution, quote, locator}]
  results:        [{claim, effect_direction, magnitude, quote, locator}]
appraisal:       {confidence: low|medium|high, rationale, quote?}   # 3ie-style critical appraisal
modules:
  disaster_conflict: {hazard_types: [...], conflict_setting, social_protection_modality}
extractor:  {driver, agent_name, run_id, schema_version, prompt_version}
review:     {status: unreviewed|accepted|corrected, items_flagged: [...]}
```

Vocabularies: countries use ISO-3166; subject areas use OpenAlex topic IDs (joinable externally). Interventions, outcomes, methods and data sources use a local list **seeded from 3ie's classification** and versioned; the agent may *propose* new terms, which go to review rather than into the list. The owner may supply the 3ie codebook to pin category lists; until then the seed list is drafted from general knowledge and flagged as provisional.

Task cards: one per paper (small batches allowed), carrying the relevant sections (abstract, methods, results, data), the schema and the vocab; optional image attachments for key tables. Validation on submit: schema; vocab membership or `proposed` flag; every quote present in the transcript (whitespace/hyphenation normalized); locators resolvable; at least one result with a quote. Bounce on failure with the reason, as concept_graph does.

Review Artifact: only flagged items (low appraisal confidence, proposed terms, quote mismatches, disagreement between two extractions if double-extraction is enabled for the gold set).

### Stage 3: synthesis (text artifact)

- **Grouping**: candidate clusters from OpenAlex topic IDs, MiniLM similarity and 3ie facet overlap; or a facet query supplied by the owner. Proposals are reviewed through an Artifact.
- **Per-paper annotation**: rendered **deterministically** from the record (study, setting, design, data, findings with quotes); a task card adds only a short "contribution and limitations" note.
- **Per-cluster synthesis**: a task card receives annotations for ~15-20 papers (hierarchical for larger clusters). Validation: every claim cites papers within the cluster, every number traces to a record result quote.
- **Outputs**: Markdown literature review and annotated bibliography under `research/literature_reviews/<topic>/` with vault-friendly frontmatter. The bibliography never depends on the LLM.

### Stage 4: analysis (derived database)

SQLite built from the records (DuckDB export optional); no LLM. Views: 3ie-style evidence matrix (intervention × outcome × design) with counts; distributions by method, country, dataset; dataset co-occurrence (input to Project 04). CLI query (illustrative; final name set in the plan: `python -m agent.literature.cli query --dataset ACLED --method DiD`); static HTML/Markdown matrix export for Project 01. Built before stage 3 because it is cheap and exposes extraction errors early.

### Stage 5: gap analysis

1. Parse the question into facet constraints (task card, validated against vocab).
2. Query the database for matching cells.
3. **Coverage report**: papers found, designs, countries, and corpus completeness for the topic (corpus size vs OpenAlex works for the same topic filter).
4. Live OpenAlex search with the constraints; near-matches not in the corpus are classified by a task card.
5. Verdict from fixed categories: *tried directly*, *tried in an adjacent context*, *found externally, not in corpus*, *no evidence found*. Always with the coverage numbers and the evidence list.

Unseen external hits can be queued into discovery (propose/confirm as in snowball).

### Stage 6: proposal support (specified last)

A thin conversational layer in the style of `agent/tutor`'s bootstrap contract. Inputs: a gap report, nearest studies, identification strategies and data sources (with resolution) drawn from records. Output: a proposal skeleton (question, contribution claim against the 3-5 closest papers, design options, threats). **Deliberately not designed in detail until stages 2-5 exist.**

## 7. Index and OpenAlex alignment

- The research index is the primary target. Cards and records carry `openalex_id`, DOI, OpenAlex topic IDs, ISO country codes, so they join to external classifications.
- Journal conversion continues to index into `research/.index/`; cross-vault queries must keep that distinction explicit until the academic-hub index is aligned (later, separate work).
- Known issue to respect: discovery's folder routing (level-0 Concepts, single label) is **not** a reliable subject classification; the extraction pipeline uses OpenAlex Topics and record facets, not folder names.

## 8. Cost, safety and operational guardrails

- Subscription route default; `--driver api` opt-in with the cost estimate gate; warn and get a go-ahead before any call or run estimated over $1.
- No paid fallback when agent work is pending; pending is a reported status.
- Cards hold source text: run directories live under a gitignored `.agent_work/` outside any published repo.
- Repository is public: never commit PDFs or transcripts of copyrighted papers; records and quotes stay in ignored index locations unless the owner decides otherwise. (To confirm: whether short quotes in `study_record.json` are acceptable to commit; default is to keep `research/.index/` uncommitted as today.)
- One writer per corpus/index root; coordinate with the corpus writer-lock work and Obsidian sync before any bulk write.

## 9. Testing and evaluation

- Stage 0: baseline and post-move concept_graph suite; shim identity test; card/manifest golden files.
- Stage 1: dry-run and collect/submit tests with fixtures (no live API); defect-rate regression on a small fixture set.
- Stage 2: unit tests for validators (quote missing, vocab miss, bad locator); **gold set of ~10 hand-checked papers** including the pitch's check (a Warsame et al. record must yield Somalia / ACLED / FSNAU / panel). Metrics: facet accuracy, quote-verification rate, vocab-proposal rate, bounce rate.
- Stages 3-5: deterministic rendering and SQL tests; citation-integrity validation tests; gap-analysis verdict tests against a fixture corpus with known answers.

## 10. Build order and milestones

| # | Work | Depends on | Notes |
| --- | --- | --- | --- |
| 0 | `core/agent_tasks/` extraction, concept_graph as consumer | none | Safety gates in section 5 |
| 1 | Journal converter driver wiring, heuristic profile, card identity fields | 0 not required, but coordinate | Matches pitch Step 1 prerequisites |
| 2 | Schema, vocab, extraction stage, gold set pilot on harvested papers | 0, 1 | Pitch Step 1 (October) |
| 3 | Derived database, evidence matrix, CLI | 2 | Pitch Steps 2-3 (Nov-Dec) |
| 4 | Synthesis | 2, 3 | |
| 5 | Gap analysis | 2, 3 | Needs coverage estimate from discovery |
| 6 | Proposal support | 5 | Design after 2-5 exist |

Each numbered item gets its own implementation plan; this spec is the umbrella.

## 11. Deferred and rejected

- **Deferred: ORKG / RDF triples (knowledge-graph store).** Explicitly postponed as a potential future extension. Entity-valued facets (dataset, method, intervention, outcome) are stored as normalized vocab IDs so that a later records-to-triples export (Paper -> Problem -> Method -> Dataset -> Result) is mechanical. Revisit when the corpus is large enough that relational queries become limiting or external linking to ORKG matters.
- Rejected: database-first source of truth (harder to review and version, breaks the file-keyed rebuildable convention).
- Deferred: aligning the academic-hub index to OpenAlex-style classification; merging `transcribe_notes/agent_work.py` into `core/agent_tasks/`; multi-provider discovery and backward citation expansion (see the 2026-10-14 discovery audit).

## 12. Open decisions for the owner

1. Is the 3ie codebook worth supplying now, or should the seed vocabulary start provisional and be aligned during the pilot?
2. May short evidence quotes live in committed files, or does `research/.index/` stay uncommitted (default)?
3. Double-extraction (two agent passes, diff flagged) for the gold set only, or for every paper?
4. Which Obsidian/vault location, if any, should receive the rendered review and bibliography?

## 13. Overlapping work (as of this commit)

Open worktrees touching nearby code: `claude/notes-pipeline-consolidation` and `codex/notes-subscription-investigation` (transcribe_notes agent driver, router flags), `claude/excalidraw-agent-driver`, `claude/journal-discovery-minors` and `codex/journal-discovery-audit` (discovery fixes, metadata sidecar). Stage 1 must start from their landed results; stage 0 touches `core/` and `agent/concept_graph/` and needs `tools.active_work` clear before landing.
