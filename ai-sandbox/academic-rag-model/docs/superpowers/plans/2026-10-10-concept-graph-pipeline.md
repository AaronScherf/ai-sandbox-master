# Concept Graph Pipeline (Plan B) Implementation Plan

> **Format note:** Plan A listed full code for every step because it was written for any executor. This plan is
> executed natively by its author, so it fixes interfaces, behaviours and the exact test cases (names and what
> they assert) and leaves the code to be written test-first. Tasks are still TDD: write the named tests, watch
> them fail, implement, run the suite, commit.

**Goal:** Add the LLM drafting stages to `agent/concept_graph/`: `seed`, `fill`, `link`, `critic`, driven by task
cards a subscription IDE agent fills in (default), or by the metered Gemini API behind a cost gate (fallback),
with an IP guard and citation checks on everything that comes back.

**Architecture:** Each stage has three pure parts: `make_tasks` (retrieve passages, build task cards),
`validate_result` (schema, ids, IP guard, citations), `apply_result` (write `proposed` items into the graph repo
through `GraphStore`). Two transports share them: **agent** (`collect` writes cards and a manifest into a private
work directory; the agent fills each card's `## Result` block; `submit` validates and applies; bad cards are
bounced with reasons) and **api** (`api <stage>` sends the same card text to Gemini, then runs the same
validate/apply). Nothing the pipeline writes is ever `verified`, and verified items are never overwritten.

**Tech Stack:** as Plan A (Python 3.13, pydantic 2, ruamel.yaml, PyYAML, pytest), plus the repo's existing
`core.indexer.index_search` / `agent.rag.rag_agent.retrieve_passages` for retrieval and `core.env.gemini_utils`
for the API driver (both injected, so tests make no network or paid calls).

**Spec:** `docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md` (Pipeline, Retrieval, Drivers, IP guard,
Cost control sections). **Builds on:** Plan A (`docs/superpowers/plans/2026-10-09-concept-graph-core.md`, branch
`claude/concept-graph-core`).

## Global Constraints

- Branch `claude/concept-graph-pipeline`, worktree `.worktrees/claude-concept-graph-pipeline`, created from
  `claude/concept-graph-core`. Stage explicit paths; never `git add -A`.
- **The work directory is private.** Task cards and manifests contain retrieved textbook and lecture text. They must
  never be written inside a graph repo or anywhere a `.gitignore` does not cover. Default work root:
  `<hub-root>/.agent_work/concept_graph/<run-id>/` (the hub's `.agent_work/` is already gitignored on `main`).
  The CLI refuses a work directory that is inside the `--graph-repo`.
- **Own words only.** Prose fields (`gist`, `explanation`, `example`, edge `explanation`, comments) are rejected if
  they share a run of 8 or more consecutive normalized words with any passage offered on that card. `formal`
  (LaTeX) is exempt. The threshold is a constant `IP_RUN_WORDS = 8`.
- **Citations are bound to retrieval.** A citation is accepted only if its exact `(source, ref)` pair was offered on
  that card. Source keys: `rubinstein`, `mwg`, `ok`, `lecture`, `slides`, `hw`, `other`. No instructor or student
  names, no email addresses in anything written to the graph repo.
- Everything written by a stage has `status: proposed` and `provenance` (`driver`, `agent` name, `run` id). A node or
  edge whose status is `verified` is never modified by a stage. `--redo <id>` regenerates a `proposed` item.
- Edge ids are computed by code (`edge_id`), never written by the agent. Edges may only connect existing node ids.
  Tombstoned (rejected) ids and edges are never re-proposed.
- **Spend:** the agent driver costs subscription quota, not API dollars. The API driver prints an estimate first and
  refuses to run above $1 without `--approve-cost <usd>`; estimates use the repo's `gemini-3.8-flash` ceiling price
  ($0.75/M input, $3.75/M output tokens) unless a price for the chosen model is known. No test makes a real
  Gemini call. The only network call in `collect` is the query embedding inside the existing retrieval.
- Do not run any stage against the real corpus or write into the public graph repo without the owner's go-ahead.

## Review Focus

1. A card is filled with text copied from an offered passage: it must be bounced, not applied (IP guard), including
   when the copied run straddles a markdown or punctuation difference.
2. A card cites something that was not offered (invented section, wrong source key): bounce.
3. The agent invents a node id, links to an id that does not exist, or re-proposes an edge that already exists or
   was rejected: bounce or skip with a reason; never write a dangling edge.
4. `submit` run twice, or a card edited after being applied: the second run must not duplicate or overwrite.
5. Work-dir hygiene: a work directory inside the graph repo is refused; manifests with passage text never land in
   the graph repo.
6. The agent returns malformed YAML, a fenced block with extra prose, or leaves the Result block empty: bounce
   with a readable reason; one bad card must not stop the others.
7. API driver over budget: refuses before any call; under budget, one failed call does not lose the others' results.

## File Structure (all under `agent/concept_graph/`; tests mirror in `tests/agent/concept_graph/`)

```
sources.py      Passage dataclass, classify_passage(path, citation) -> (source, ref)            Task B1
ipguard.py      longest_shared_run(), check_prose()                                            Task B1
store.py        + add_nodes(), add_edges(), add_vocab()  (modified)                            Task B2
tasks.py        Task model, card rendering/parsing, result-block extraction                    Task B3
work.py         Run manifest + worklist: create_run(), load_run(), set_status(), bounce notes   Task B3
stages/__init__.py  stage registry
stages/fill.py  stages/link.py  stages/critic.py  stages/seed.py                               Tasks B4-B7
retrieval.py    Retriever protocol, IndexRetriever (wraps the repo's index search)             Task B8
drivers.py      collect(), submit(), status(), api_run() + cost estimate/gate                   Task B8
cli.py          + collect, submit, status, bootstrap, api  (modified)                          Task B8
README.md, docs/status/agent/concept_graph/... (modified/new)                                  Task B9
```

## Shared formats

**Task card** (`<work>/<run-id>/cards/<task-id>.md`; rewritten by `collect`, filled by the agent):

```
# Task <task-id>   (stage: <stage>)
## Instructions      <stage rules, own-words rule, result shape, how to cite>
## Subject           <ids/names/gist of what to produce, existing neighbours, constraints>
## Offered passages
### P1  [source: rubinstein | ref: ch. 2, §Preference relations, p. 12]
<passage text>
### P2 ...
## Result
```yaml
```
```

The agent writes only inside the yaml fence under `## Result`. `submit` reads that block; everything else on the
card is ignored (the manifest, not the card, is the source of truth for ids, offered citations and passage text).

**Manifest** (`<work>/<run-id>/manifest.json`): `{run_id, stage, created, graph_repo, tasks: [{id, subject, status,
offered: [[source, ref], ...], passages: [{id, source, ref, text}], attempts, reasons}]}`; status goes
`pending -> filled -> applied | bounced`. `status` (CLI) renders it as a table.

**Result shapes** (YAML under `## Result`):
- fill: `{gist, explanation, formal?, example?, citations: [{source, ref}]}`
- link: `{edges: [{source, type, target, condition?, via?, explanation, citations: [...]}]}` (may be empty)
- critic: `{verdict: supports|weak|unsupported, note}`
- seed: `{topics?: [...], sections: [{id, title, order, state, lectures?, syllabus_ref?}], nodes: [{id, name, kind, section, topic, gist?}]}`

---

### Task B1: Passages, source classification, IP guard

**Files:** create `sources.py`, `ipguard.py`; tests `test_cg_sources.py`, `test_cg_ipguard.py`.

**Produces:**
- `Passage(id, source, ref, text, path)` dataclass; `Passage.offered -> (source, ref)`.
- `classify_passage(path: str, citation: str) -> tuple[str, str]`: Rubinstein folder (note the corpus spells it
  `Rubenstein`) -> `("rubinstein", "ch. N" + ", " + citation if citation)`, with N from the `chapters/NN_` file name;
  `Press_Microeconomic_Theory` -> `mwg`; `Ok_Real_Analysis` -> `ok`; `lecture_notes` with an ISO date in the name ->
  `("lecture", "<date>")`; `professor_notes` -> `("slides", <stem without leading number/underscores>)`; `problem_sets`
  -> `("hw", <stem>)`; anything else -> `("other", <stem>)`. Never returns an empty ref.
- `longest_shared_run(text: str, passages: list[str]) -> tuple[int, str]`: longest run of consecutive normalized words
  (lower-cased, punctuation and markdown stripped, math delimiters kept as tokens-free) common to `text` and any
  passage, with the offending words.
- `check_prose(fields: dict[str, str], passages: list[str], limit: int = IP_RUN_WORDS) -> list[str]`: one readable
  message per field whose shared run is >= `limit`; skips empty fields.

**Tests (names are the spec):** `test_rubinstein_chapter_file_maps_to_source_and_chapter`,
`test_mwg_ok_lecture_slides_hw_and_other_sources`, `test_ref_is_never_empty`, `test_copied_run_of_eight_words_is_caught`,
`test_seven_shared_words_is_allowed`, `test_punctuation_and_case_differences_do_not_hide_a_copy`,
`test_a_paraphrase_with_the_same_vocabulary_passes`, `test_formal_field_is_not_checked` (the exemption lives in the
stage, so this asserts `check_prose` is only given prose fields by `fill`; see B4), `test_empty_fields_are_skipped`.

### Task B2: Store additions

**Files:** modify `store.py`; tests extend `test_cg_store.py`.

**Produces:** `GraphStore.add_nodes(section_id, nodes: list[dict])` (appends to `data/nodes/<section_id>.yaml`,
creating it if absent, refusing an existing id), `add_edges(edges: list[dict])` (each edge goes to the file of its
higher-`order` endpoint's section, creating it; refuses an existing id), `add_vocab(kinds=(), topics=())` (appends
unseen entries to `config/vocab.yaml`, keeping order and comments), `add_sections(sections: list[dict])` (appends to
`data/sections.yaml`, refusing an existing id). All keep round-trip formatting and comments.

**Tests:** `test_add_nodes_creates_the_section_file_and_round_trips`, `test_add_nodes_refuses_an_existing_id`,
`test_add_edges_goes_to_the_higher_order_sections_file`, `test_add_edges_refuses_a_duplicate_id`,
`test_add_vocab_appends_only_new_entries_and_keeps_comments`, `test_add_sections_appends_in_order`,
`test_added_items_validate_cleanly` (sample + one new node/edge passes `validate`).

### Task B3: Tasks, cards and the work directory

**Files:** create `tasks.py`, `work.py`; tests `test_cg_tasks.py`, `test_cg_work.py`.

**Produces:**
- `Task(id, stage, subject: dict, instructions: str, passages: list[Passage], context: str)`;
  `render_card(task) -> str`; `extract_result(card_text) -> dict | list | None` (parses the yaml fence under
  `## Result`; returns `None` when empty; raises `ResultError(reason)` on malformed YAML, a non-mapping, a missing
  fence, or more than one fence).
- `work.create_run(work_root, graph_repo, stage, tasks) -> Run` (refuses a `work_root` inside `graph_repo`; writes
  cards and `manifest.json`); `load_run(work_root, run_id)`; `Run.set_status(task_id, status, reasons=None)` (atomic
  write); `Run.card_path(task_id)`; `Run.bounce(task_id, reasons)` (also appends a `## Bounced` section to the card
  listing reasons and clears nothing the agent wrote); `render_worklist(run) -> str`.

**Tests:** `test_card_round_trips_the_agents_yaml`, `test_empty_result_block_is_none`,
`test_malformed_yaml_gives_a_readable_reason`, `test_extra_prose_outside_the_fence_is_ignored`,
`test_two_fences_is_an_error`, `test_work_dir_inside_the_graph_repo_is_refused`,
`test_manifest_records_offered_citations_and_passage_text`, `test_set_status_persists_and_is_atomic`,
`test_bounce_appends_reasons_and_keeps_the_agents_work`, `test_worklist_lists_status_per_task`.

### Task B4: Stage `fill`

**Files:** create `stages/__init__.py`, `stages/fill.py`; tests `test_cg_stage_fill.py`.

**Produces:**
- `make_tasks(store, retriever, *, section=None, nodes=None, redo=False, top_k=6) -> list[Task]`: one task per
  `proposed` node in a `taught`/`in_progress` section with an empty explanation (all of them with `redo`; never
  `verified`; `planned` sections skipped unless named in `nodes`). Query = `f"{name} {gist or ''} {kind}"`. The card
  subject carries id, name, kind, topic, section title, existing gist, and the node's direct neighbours (names and
  edge sentences) so the explanation can mention how it connects.
- `validate_result(task, result, store) -> list[str]`: requires `gist` (<= 160 chars, single line) and
  `explanation`; optional `formal`, `example`; `citations` non-empty and each in `task.offered`; runs `check_prose`
  on `gist`, `explanation`, `example` only; rejects unknown keys.
- `apply_result(store, task, result, provenance)`: `update_item("node", id, {...citations, provenance, status:
  "proposed"})`; refuses (returns skip reason) if the node became `verified` since collect.

**Tests:** `test_makes_one_task_per_unfilled_node_in_taught_sections_only`, `test_verified_and_planned_nodes_are_skipped`,
`test_redo_regenerates_a_proposed_node`, `test_card_carries_neighbours`, `test_valid_result_is_accepted`,
`test_copied_explanation_is_bounced_with_the_shared_words`, `test_formal_may_match_a_passage`,
`test_invented_citation_is_bounced`, `test_missing_citations_is_bounced`, `test_unknown_key_is_bounced`,
`test_apply_writes_proposed_with_provenance`, `test_apply_never_overwrites_a_node_verified_since_collect`.

### Task B5: Stage `link`

**Files:** create `stages/link.py`; tests `test_cg_stage_link.py`.

**Produces:** `make_tasks` (one task per filled node, i.e. non-empty explanation, in taught/in_progress sections;
card lists every other node as `id | name | kind | section | gist` so the agent can only pick real ids, plus the
node's existing and rejected edges; query = name + gist + "implies equivalent necessary sufficient"),
`validate_result` (each edge: both ids exist and one is the task's node; `type` in `EDGE_TYPES`; `implies`/`iff`
need `condition`; `via` only on implies/iff and must be a theorem/lemma node; not a duplicate of an existing,
tombstoned, or earlier-in-this-result edge; no self-loop; `explanation` IP-checked; citations offered; empty `edges`
list is valid), `apply_result` (computes ids with `edge_id`, `add_edges`, `proposed` + provenance). Applying a result
that would create a definitional cycle is bounced (validate the would-be graph with `validate`).

**Tests:** `test_task_per_filled_node_and_card_lists_all_candidate_ids`, `test_unknown_endpoint_is_bounced`,
`test_edge_not_touching_the_task_node_is_bounced`, `test_implies_without_condition_is_bounced`,
`test_via_must_be_a_theorem`, `test_duplicate_existing_edge_is_skipped_with_a_reason`,
`test_tombstoned_edge_is_not_reproposed`, `test_two_identical_edges_in_one_result_is_bounced`,
`test_copied_explanation_is_bounced`, `test_empty_edges_is_valid_and_applies_nothing`,
`test_apply_computes_canonical_ids_and_writes_proposed`, `test_edge_that_would_create_a_definitional_cycle_is_bounced`.

### Task B6: Stage `critic`

**Files:** create `stages/critic.py`; tests `test_cg_stage_critic.py`.

**Produces:** `make_tasks` (one task per `proposed` edge with no `critic`, or all with `redo`; **blind**: the card
shows the claim only (`source type target`, condition, and the two nodes' names and gists) and never the drafting
explanation or its citations; passages are retrieved fresh with a query built from the two names),
`validate_result` (`verdict` in `supports|weak|unsupported`, `note` non-empty for weak/unsupported and IP-checked),
`apply_result` (`update_item("edge", id, {"critic": {...}})`, status unchanged).

**Tests:** `test_card_never_contains_the_edges_explanation_or_drafting_citations`, `test_skips_edges_that_already_have_a_critic`,
`test_redo_includes_them`, `test_verdict_must_be_one_of_three`, `test_weak_needs_a_note`, `test_copied_note_is_bounced`,
`test_apply_sets_critic_and_leaves_status`.

### Task B7: Stage `seed`

**Files:** create `stages/seed.py`; tests `test_cg_stage_seed.py`.

**Produces:**
- `outline_context(hub_root, course, *, max_chars=12000) -> tuple[str, list[Passage]]`: builds the card context from
  files on disk only (no embedding call): processed syllabus markdown (trimmed), the chapter titles of each textbook
  under `academic_notes/<course>/textbooks/processed_outputs/*/chapters/NN_title.rag.md` (as offered passages with
  `source`/`ref` from `classify_passage`, text = the title list), lecture-note dates, professor-note titles.
- `make_tasks(store, hub_root, course) -> list[Task]` (one task; refuses when `sections.yaml` already has taught
  sections unless `--redo`), `validate_result` (ids are slugs and not already used; sections referenced exist;
  `kind` in vocab; `topic` in vocab or listed in `topics`; `order` unique floats; `state` valid; `gist` IP-checked),
  `apply_result` (`add_vocab` for new topics, `add_sections`, `add_nodes` per section; existing ids never changed).

**Tests:** `test_outline_context_lists_chapters_and_dates_from_a_tmp_hub`, `test_seed_refuses_when_the_graph_already_has_taught_sections`,
`test_duplicate_or_reused_ids_are_bounced`, `test_node_in_unknown_section_is_bounced`, `test_unknown_kind_is_bounced`,
`test_new_topics_are_added_to_vocab`, `test_apply_adds_sections_and_skeleton_nodes_as_proposed`,
`test_seeded_graph_validates_apart_from_unfilled_warnings`.

### Task B8: Retrieval, drivers and CLI

**Files:** create `retrieval.py`, `drivers.py`; modify `cli.py`; tests `test_cg_retrieval.py`, `test_cg_drivers.py`,
extend `test_cg_cli.py`.

**Produces:**
- `Retriever` protocol: `retrieve(query: str, top_k: int) -> list[Passage]`. `IndexRetriever(hub_root, course, client)`
  wraps `agent.rag.rag_agent.retrieve_passages` and `classify_passage` (the only part not unit-tested; covered by one
  guarded smoke test that is skipped without the hub and a key). `FakeRetriever` lives in the test helpers.
- `drivers.collect(stage, store, retriever, work_root, **opts) -> Run`; `drivers.submit(run, store, agent_name) ->
  Report` (for each `filled` or `pending-with-nonempty-result` task: extract, validate, apply or bounce; idempotent:
  `applied` tasks are skipped; one bad card never stops the rest; prints a per-card line); `drivers.status(run)`;
  `drivers.estimate_cost(tasks, price_in=0.75, price_out=3.75, out_tokens=900) -> float`;
  `drivers.api_run(stage_name, run, store, complete, approve_cost, agent_name)` where `complete(prompt: str) -> str` is
  injected (default wraps Gemini with `PAID_GEMINI_KEY` + `call_with_retries`): refuses before any call when
  `estimate > approve_cost` (or `approve_cost` is missing and `estimate > 1.0`), isolates per-task failures, and feeds
  each response through the same extract/validate/apply path.
- CLI: `collect <stage> [--section S] [--node ID ...] [--redo] --hub-root H --course C [--work-dir W]`,
  `submit <run-id> [--agent-name NAME]`, `status [<run-id>]`, `bootstrap`, `api <stage> ... --approve-cost USD
  [--model M]`. `bootstrap` prints the agent contract: read `worklist.md`; for each pending card fill only the yaml
  block under `## Result`; own words; cite only offered passages; never edit other files; run `submit`; re-read
  bounced cards and fix only them.

**Tests:** `test_collect_writes_cards_and_manifest_and_never_touches_the_graph_repo`,
`test_submit_applies_valid_cards_and_bounces_bad_ones_independently`, `test_submit_twice_does_not_duplicate`,
`test_submit_skips_cards_the_agent_has_not_filled`, `test_card_edited_after_apply_is_not_applied_again`,
`test_bounced_card_can_be_fixed_and_resubmitted`, `test_estimate_scales_with_task_text`,
`test_api_run_refuses_over_budget_before_any_call`, `test_api_run_requires_approval_above_one_dollar`,
`test_api_run_survives_one_failing_task`, `test_api_results_go_through_the_same_validation`,
`test_cli_collect_submit_status_round_trip_with_a_fake_retriever`, `test_cli_refuses_work_dir_inside_graph_repo`,
`test_bootstrap_prints_the_contract_with_paths`.

### Task B9: Docs and final review

Update `agent/concept_graph/README.md` (commands, the agent workflow in five lines, the private work-dir rule, the
cost gate), add `docs/status/agent/concept_graph/2026-10-10-concept-graph-pipeline-status.md`, run the full
concept_graph suite and the repo suite (main venv, ignoring this package), then one fresh whole-branch review with
the Review Focus above; fix Critical/Important with tests that fail first; record rulings and deferred minors.

**Out of scope:** running any stage on the real corpus or into the public repo (owner-gated, after the
transcription of the remaining documents and `offering_links`); the Artifact review adapter; Obsidian export.

## Lifecycle references

### Specs

- [2026-10-09-concept-graph-design](../specs/agent/2026-10-09-concept-graph-design.md)

### Tests

- [test_cg_cli_stages](../../../tests/agent/concept_graph/test_cg_cli_stages.py)
