# Spec A: Research Profile, Classification and Applicability Gate: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every transcribed research document a verified research profile (bibliographic fields, `report_type`, discipline and subfields, geography, method flags, 3ie intervention/outcome tags with quotes, derived `applicability`), regenerate discipline folders from it, and report on the corpus.

**Architecture:** A `research_profile` dict is added to the existing index card (absent on course-material cards, so nothing there is rewritten). LLM steps are task cards on the existing `core/agent_tasks` layer (subscription Gemini via Antigravity by default); code validates and applies them. Everything new lives in `agent/literature/profile/` except the shared data model in `core/indexer/research_profile.py`.

**Tech Stack:** Python 3.13, pytest, PyYAML, the existing `core/agent_tasks` and `core/indexer` modules.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-11-13-spec-a-indexing-classification-applicability-design.md` (parent: `2026-11-11-literature-corpus-redesign-umbrella-design - v2.md`). Executors read both.

**Worktree:** Codex builds in branch `codex/spec-a-research-profile`, path `.worktrees/codex-spec-a-research-profile`, created from `main` per `docs/WORKTREE_WORKFLOW.md`. Stage explicit paths only.

## Global Constraints

- Run code as modules from `ai-sandbox/academic-rag-model/` (`python -m agent.literature.profile.cli ...`); tests with `python -m pytest tests/<path>`; the full suite with `python tools/run_tests_chunked.py`.
- `core/indexer/` is shared: any change there needs tests for its callers (`tests/core/indexer/`, `tests/core/test_index_card_set_fields.py`).
- Do not change the 3ie vocabulary, `CHOOSING_RULE` or `FIT_TEST_EXAMPLES`. 3ie tags use the whole tree; a leaf implies its ancestors at read time; a branch-only tag does not count toward any leaf.
- No tag without a quote that exists verbatim in the transcript (checked in code). No proposals for out-of-scope papers.
- Course-material cards (`academic_resources`, `academic_notes` shards) must come out byte-identical.
- Default run mode: task cards filled by a subscription Gemini agent. A paid API run needs a printed cost estimate and explicit approval; warn the owner before anything estimated over $1.
- Discipline: closed list of the 26 OpenAlex fields plus `other`; confidence threshold 0.8; two Gemini agents with different prompts (variant `a` and `b`).
- Folders: discipline with fewer than 3 papers goes to `other` (configurable); moves only from a reviewed dry-run plan; logged and reversible.
- Human decisions live in a ledger keyed by `file_id`, override model output and survive prompt-version changes.
- Never commit PDFs, `.env`, or copyrighted material (public repo). Preserve each file's line endings when scripting edits (read and write with `newline=''`).
- Anything needing a human decision produces an interactive Artifact with decisions in its `db` collection, not a hand-edited file.

## Review Focus

1. A paper with no DOI and no discovery sidecar: bibliographic fields come from the transcript, `doi_verified` is `unverified`, nothing crashes.
2. Quote checking against real transcripts: line-break hyphenation, ligatures, curly quotes and extra whitespace must not reject a genuine quote; an invented quote must be rejected.
3. Multi-country and no-country papers: `country` is a list or empty, `country_income_group` is empty rather than guessed.
4. A transcript longer than `MAX_CARD_CHARS` (300,000): skipped with reason `too_long`, never silently truncated.
5. Folder moves: two papers with the same filename in the target folder, an interrupted apply, and a card whose `file_id` survives the move.

---

### Task 0: Preconditions report

**Files:**
- Create: `docs/status/literature/2026-11-13-spec-a-task0-findings.md`

**Interfaces:**
- Produces: written answers the later tasks cite. No code.

- [ ] **Step 1:** Answer each of the spec's five Task 0 items in the findings doc, with file and line evidence:
  (1) does a journal-article card's identity survive a folder move (`compute_file_id` in `core/indexer/index_card.py:66`; `move_card` at `:524` rewrites `course`/`path`), and is `hub_id` stamped on transcripts; (2) how a card is written, versioned and read, and whether adding a nested `research_profile` key breaks `reconcile_and_write` or the content hash; (3) every reader of `doc_type == "journal_article"` and of `research/` folder paths (`agent/literature/papers.py:24`, `discovery/.../topic_routing.py`, `topic_proposals.py`, study records); (4) which unlanded branches touch `agent/literature/schema.py` or `core/indexer/index_card.py` (`git diff main...<branch> --stat`); (5) whether `Vocabulary` in `agent/literature/vocab.py` exposes parent links and where the built 3ie intervention/outcome/sector vocabularies live (`research/resources/3ie/vocab/*.yaml` vs `agent/literature/vocab_data/`).
- [ ] **Step 2:** For each answer that contradicts a spec premise, add a "Changes the plan" line naming the task affected. Also record whether transcripts carry YAML frontmatter and whether editing it changes `compute_content_hash`.
- [ ] **Step 3:** Commit the findings doc. Stop and report if (1) or (2) fails: a path-independent identity or a different card extension point must be settled with the owner before Task 2.

### Task 1: Vocabulary data and tree helpers

**Files:**
- Create: `agent/literature/vocab_data/build_openalex.py`, `agent/literature/vocab_data/openalex_taxonomy.yaml`, `agent/literature/profile/__init__.py`, `agent/literature/profile/taxonomy.py`
- Test: `tests/agent/literature/profile/test_taxonomy.py`

**Interfaces:**
- Produces: `load_openalex() -> OpenAlexTaxonomy` with `.domains: dict[str, str]`, `.fields: dict[str, str]`, `.subfields: dict[str, str]`, `.field_domain(field_id: str) -> str`, `.subfield_field(subfield_id: str) -> str`; `ancestors(vocab: Vocabulary, term_id: str) -> list[str]` (parent chain, nearest first, excluding the term); `rollup(vocab, term_ids: list[str]) -> set[str]` (terms plus all ancestors).

- [ ] **Step 1:** Write tests: `test_openalex_has_26_fields_and_4_domains`, `test_every_field_maps_to_one_domain`, `test_every_subfield_maps_to_a_field`, `test_ancestors_of_leaf_is_branch_then_sector`, `test_rollup_includes_ancestors_but_branch_does_not_imply_leaf` (a branch id yields itself and its ancestors only).
- [ ] **Step 2:** Run `python -m pytest tests/agent/literature/profile/test_taxonomy.py -v`; expect FAIL (module missing).
- [ ] **Step 3:** Implement `build_openalex.py` (fetch `/domains`, `/fields`, `/subfields` from `api.openalex.org` once, write `openalex_taxonomy.yaml` with a `retrieved` date; the YAML is committed, tests never hit the network) and `taxonomy.py`.
- [ ] **Step 4:** Run the tests; expect PASS.
- [ ] **Step 5:** Commit explicit paths.

### Task 2: Research profile data model and card setter

**Files:**
- Create: `core/indexer/research_profile.py`
- Test: `tests/core/indexer/test_research_profile.py`

**Interfaces:**
- Produces: `RESEARCH_PROFILE_VERSION = 1`; frozensets `REPORT_TYPES` (journal_article, working_paper, report, program_document, grey_literature, thesis, protocol, notes, other), `RESEARCH_REPORT_TYPES` (all but notes and other), `METHOD_CLASSES`, `ORIENTATIONS`, `EVIDENCE_ROLES`, `APPLICABILITY` (both, intervention_only, outcome_only, not_applicable, not_assessed), `PROFILE_FIELDS` (the spec section 3 table's keys); `derive_applicability(intervention_tags: list[dict] | None, outcome_tags: list[dict] | None, assessed: bool) -> str`; `validate_profile(profile: dict) -> list[str]` (problems; empty = valid); `set_research_profile(academic_hub_root: str, file_id: str, fields: dict) -> bool` (merges into `card["research_profile"]`, stamps `research_profile_version`, False when no card, ValueError on unknown keys, never touches other card keys).
- Consumes: `find_card_by_file_id`, `load_shard`, `save_shard`, `_replace_card` from `core/indexer/index_card.py`.

- [ ] **Step 1:** Write tests: `test_applicability_table` (parametrised: both / intervention_only / outcome_only / not_applicable when `assessed=True`; `not_assessed` when `assessed=False` regardless of tags), `test_validate_rejects_unknown_report_type_and_bad_enums`, `test_validate_accepts_open_report_type_when_marked_proposed`, `test_set_profile_merges_without_touching_other_keys`, `test_set_profile_unknown_key_raises`, `test_set_profile_missing_card_returns_false`, `test_course_shard_without_profile_is_byte_identical_after_other_card_updated`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement the module. Use the nested key approach decided in Task 0; if Task 0 finds it unsafe, stop and report.
- [ ] **Step 4:** Run these tests plus `tests/core/test_index_card_set_fields.py` and `tests/core/indexer`; expect PASS.
- [ ] **Step 5:** Commit.

### Task 3: Bibliographic metadata and DOI verification

**Files:**
- Create: `agent/literature/profile/metadata.py`
- Test: `tests/agent/literature/profile/test_metadata.py`

**Interfaces:**
- Produces: `Lookup = Callable[[str], dict | None]`; `crossref_lookup(doi: str) -> dict | None` and `openalex_lookup(doi: str) -> dict | None` (network, return `{"title","authors","year","journal","doi"}`); `verify_bibliography(card: dict, lookup: Lookup) -> dict` returning `{"fields": {...}, "doi_verified": {"date","source","match": "match|mismatch|unverified"}, "mismatches": [str]}`; `title_match(a: str, b: str) -> bool` (case, punctuation and whitespace-insensitive; true at ratio >= 0.9).

- [ ] **Step 1:** Write tests with an injected fake lookup: `test_matching_record_marks_match`, `test_title_mismatch_is_flagged_not_overwritten` (card title kept, mismatch listed), `test_no_doi_gives_unverified_without_calling_lookup`, `test_lookup_returning_none_gives_unverified`, `test_author_list_and_year_filled_from_lookup_only_when_card_lacks_them`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement. Reuse `fetch_dois`/reference-checker helpers if Task 0 shows they fit; otherwise a small `urllib` client with timeout and polite User-Agent that carries no personal data.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 4: Classification task cards and discipline resolution

**Files:**
- Create: `agent/literature/profile/classify.py`, `agent/literature/profile/discipline.py`
- Test: `tests/agent/literature/profile/test_classify.py`, `tests/agent/literature/profile/test_discipline.py`

**Interfaces:**
- Consumes: `Task`/`Passage` (`core/agent_tasks/tasks.py`), `collect_run`/`submit_run` (`core/agent_tasks/loop.py`), `OpenAlexTaxonomy`, `set_research_profile`, `validate_profile`.
- Produces: in `classify.py`: `STAGE = "classify"`, `@dataclass Target(index_root: str)`, `make_tasks(target: Target, docs: list[dict], *, variant: str = "a") -> list[Task]` (`docs` are cards; the card text is title, abstract and the first pages, never above `MAX_CARD_CHARS`; over-length documents are skipped with reason `too_long`), `validate_result(entry, result, target) -> list[str]`, `apply_result(target, entry, result, provenance) -> str | None`. Variant `a` writes the profile fields; variant `b` is a differently worded prompt that returns discipline and subfields only and writes `discipline_check`. In `discipline.py`: `field_from_topics(topics: list[dict] | None) -> tuple[str | None, float]` (highest summed topic score, normalised to 0..1); `resolve_discipline(primary: dict, check: dict | None, topics: list[dict] | None, *, threshold: float = 0.8) -> dict` returning `{"discipline","discipline_confidence","discipline_source","needs_review": bool, "reason": str}`.

- [ ] **Step 1:** Write tests: `test_stage_contract_validate_rejects_field_not_in_openalex_list`, `test_validate_rejects_subfield_outside_chosen_field`, `test_non_research_report_type_sets_not_assessed`, `test_over_length_transcript_is_skipped_with_reason`, `test_variant_b_never_overwrites_primary_discipline`, and for `resolve_discipline`: `test_agreement_above_threshold_no_review`, `test_below_threshold_needs_review`, `test_different_field_same_domain_needs_review_with_mild_reason`, `test_different_domain_needs_review_with_strong_reason`, `test_topics_used_when_present_else_llm`, `test_no_check_result_needs_review`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement; prompts are module constants with `PROMPT_VERSION`; record model/prompt version in provenance. Subfields are chosen in two steps inside one card (field, then subfields of that field only).
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 5: 3ie tagging with staged tree descent

**Files:**
- Create: `agent/literature/profile/tagging.py`, `agent/literature/profile/quotes.py`
- Test: `tests/agent/literature/profile/test_tagging.py`, `tests/agent/literature/profile/test_quotes.py`

**Interfaces:**
- Consumes: `rollup`, `ancestors`, `Vocabulary`, `derive_applicability`, `set_research_profile`.
- Produces: in `quotes.py`: `normalize(text: str) -> str` (NFKC, ligatures, curly to straight quotes, de-hyphenate line breaks, collapse whitespace, casefold) and `quote_in_text(quote: str, text: str) -> bool`. In `tagging.py`: `STAGE = "tag"`, `make_round_tasks(target, docs: list[dict], kind: str, level: int, prior: dict[str, list[str]]) -> list[Task]` (`kind` is `"intervention"` or `"outcome"`; `level` 1 sector, 2 branch, 3 leaf; `prior` maps `file_id` to the term ids chosen at the previous level, whose children are listed with definitions); `validate_result` (every tag: id in the vocabulary at that level and under a prior-level term, non-empty `quote` for which `quote_in_text` is true against the transcript, empty tag list allowed); `apply_result` (appends to `intervention_tags`/`outcome_tags` with `term_id, level, quote, quote_locator`, and after the last level sets `applicability` through `derive_applicability(..., assessed=True)`).

- [ ] **Step 1:** Write tests: `test_quote_survives_hyphenation_ligature_and_curly_quotes`, `test_invented_quote_rejected`, `test_tag_without_quote_rejected`, `test_term_not_under_prior_level_rejected`, `test_empty_result_is_valid_and_gives_not_applicable`, `test_branch_only_tag_kept_at_branch_and_not_expanded_to_leaves`, `test_leaf_tag_rolls_up_to_ancestors_in_summary_helper`, `test_non_research_report_type_gets_no_tagging_task`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement. Measure, do not assume, whether one prompt can carry the whole tree: leave a module constant `MAX_LISTED_TERMS` and log the listed-term count per card; the default is the staged descent.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 6: Geography derivations

**Files:**
- Create: `agent/literature/profile/derive.py`, `agent/literature/profile/reference_data/wb_income_groups.csv`
- Test: `tests/agent/literature/profile/test_derive.py`

**Interfaces:**
- Produces: `country_income_group(country: str | list[str] | None, year: int | None) -> str | None` (World Bank group in that year; None for unknown country/year or a multi-country list that spans groups); `resolve_start_year(llm_year: int | None, study_period: tuple[int, int] | None, publication_year: int | None) -> tuple[int | None, bool]` (year and an `approximate` flag).

- [ ] **Step 1:** Write tests: `test_known_country_and_year`, `test_year_changes_group` (a country that moved groups, from the CSV), `test_unknown_country_returns_none`, `test_multi_country_spanning_groups_returns_none`, `test_start_year_prefers_llm_then_period_start_then_publication_year_with_approximate_flag`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement; the CSV is built from the World Bank classification history with a retrieval date column and committed.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 7: Review ledger and queue

**Files:**
- Create: `agent/literature/profile/review.py`
- Test: `tests/agent/literature/profile/test_review.py`

**Interfaces:**
- Produces: ledger at `<index_root>/research_profile_decisions.json`; `record_decision(index_root: str, file_id: str, field: str, value, who: str) -> None`; `decision_for(index_root: str, file_id: str, field: str)`; `effective_value(index_root: str, card: dict, field: str)` (human decision if present, else the card's value); `review_queue(index_root: str) -> list[dict]` (cards with `needs_review`, `study_design`/`method_class` disagreement, or a failed DOI match, plus unresolved tag disagreements); `resolve_item(index_root: str, file_id: str, field: str, value, who: str) -> None`.

- [ ] **Step 1:** Write tests: `test_decision_overrides_model_value`, `test_decision_survives_prompt_version_change`, `test_queue_lists_low_confidence_and_disagreeing_cards`, `test_resolved_item_leaves_queue`, `test_ledger_write_is_atomic_on_interruption` (simulated failure mid-write leaves the old file).
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement with temp-file plus `os.replace`.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit. Then build the review Artifact page following `core/indexer/offering_links.py` and its review artifact (decisions in the `db` collection, applied through `resolve_item`); add a short task note in the findings doc for the artifact URL.

### Task 8: Folder plan and apply

**Files:**
- Create: `agent/literature/profile/folders.py`
- Test: `tests/agent/literature/profile/test_folders.py`

**Interfaces:**
- Consumes: `effective_value`, `move_card` (`core/indexer/index_card.py:524`), `update_card_paths`.
- Produces: `@dataclass Move(file_id: str, from_folder: str, to_folder: str, reason: str)`; `plan_moves(cards: list[dict], decisions_root: str, *, min_papers: int = 3) -> list[Move]` (folder name = effective discipline slug; disciplines under `min_papers` go to `other`; non-research documents go to `other`; unchanged papers produce no move); `render_plan_page(moves: list[Move]) -> str` (dry-run listing for the review Artifact); `apply_moves(index_root: str, moves: list[Move], approved: set[str]) -> list[dict]` (moves the card, the transcript and the source PDF together, only for `approved` file ids; refuses a target filename collision; writes a log entry per move with the inverse); `undo_moves(index_root: str, log: list[dict]) -> None`.

- [ ] **Step 1:** Write tests with a temporary index root: `test_small_discipline_goes_to_other`, `test_plan_has_no_move_for_unchanged_papers`, `test_apply_moves_card_transcript_and_pdf_together`, `test_apply_skips_unapproved`, `test_filename_collision_refused_and_nothing_moved`, `test_interrupted_apply_is_resumable_and_idempotent`, `test_undo_restores_original_layout`, `test_file_id_unchanged_after_move`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement. After the first apply, update the path references Task 0 listed (study records, `papers.py` readers) through their own APIs, not by editing generated JSON by hand.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 9: Inclusion profiles and corpus summary

**Files:**
- Create: `agent/literature/profile/profiles.py`, `agent/literature/profile/profiles/3ie_strict.yaml`, `agent/literature/profile/profiles/broad.yaml`, `agent/literature/profile/summary.py`
- Test: `tests/agent/literature/profile/test_profiles.py`, `tests/agent/literature/profile/test_summary.py`

**Interfaces:**
- Produces: `@dataclass InclusionProfile(name, framework, evidence_roles, study_designs, method_classes, income_groups, min_year, include_unclear)`; `load_profile(path: str) -> InclusionProfile`; `matches(profile: InclusionProfile, record: dict) -> tuple[bool, str]` (decision and reason; "unclear" when income group or year is missing and `include_unclear`); `summarize(cards: list[dict], profile: InclusionProfile | None = None) -> dict` (counts per `report_type`, `subtype`, `discipline`, `discipline_domain`, `method_class`, `orientation`, `evidence_role`, `applicability`, 3ie sector and branch with leaf-to-ancestor rollup, plus a list of flagged papers); `render_summary(summary: dict) -> str`.

- [ ] **Step 1:** Write tests: `test_strict_includes_impact_evaluation_in_lmic_after_min_year`, `test_strict_excludes_high_income_country`, `test_missing_income_group_is_unclear_and_included`, `test_broad_includes_any_tagged_paper`, `test_min_year_is_a_profile_parameter_not_a_constant`, `test_summary_counts_equal_direct_counts_over_cards`, `test_summary_rolls_leaf_tags_up_to_branch_and_sector`, `test_summary_ignores_course_material_cards`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement; `3ie_strict.yaml` follows the public PICOS criteria in spec section 5 (the 2000 start year lives only in the YAML).
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 10: Evaluation harness

**Files:**
- Create: `agent/literature/profile/evaluate.py`
- Test: `tests/agent/literature/profile/test_evaluate.py`

**Interfaces:**
- Produces: `load_3ie_csv(path: str) -> list[dict]` (columns Title, Author_Names, Abstract, Publication_Of_Type, DOI, Journal_Name; "No DOI"/"no doi"/blank become None; a mojibake-tolerant reader); `map_publication_type(value: str) -> str | None` (Journal article to journal_article; Published working paper to working_paper; Published report, 3ie series report, 3ie grantee final report to report; Thesis/thesis to thesis; Published protocol to protocol; Ongoing study and 3ie-funded ongoing study to None, unscored; case-insensitive); `score_records(predicted: list[dict], answer_key: list[dict], stratum_of: Callable[[dict], str]) -> dict[str, dict]` (per stratum: bibliographic accuracy, `report_type` agreement, discipline agreement, applicability agreement, tag recall on main facts; never pooled); `blind_label_page(papers: list[dict]) -> str` (labelling Artifact HTML; decisions go to its `db` collection).

- [ ] **Step 1:** Write tests: `test_map_publication_type_cases_incl_capitalisation`, `test_ongoing_study_unscored`, `test_no_doi_variants_become_none`, `test_score_is_per_stratum_not_pooled`, `test_blind_label_page_hides_model_predictions`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement. The CSVs live in `research/resources/3ie/` and are test inputs only, never copied into the repo.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit.

### Task 11: CLI, idempotence and regression run

**Files:**
- Create: `agent/literature/profile/cli.py`, `agent/literature/profile/__main__.py`, `agent/literature/profile/README.md`
- Modify: `agent/literature/README.md` (link), `docs/trackers/academic_hub_to_do.md` (TODO-0036 status, via grep of headings only)
- Test: `tests/agent/literature/profile/test_cli.py`

**Interfaces:**
- Consumes: every module above.
- Produces: `python -m agent.literature.profile.cli <command>`: `metadata`, `classify collect|submit [--variant a|b]`, `tag collect|submit --kind intervention|outcome --level 1|2|3`, `folders plan|apply|undo`, `summary [--profile PATH]`, `queue`, `eval`. All take `--index-root`; `collect`/`submit` take the standard run options; an API mode takes `--approve-cost`.

- [ ] **Step 1:** Write tests on a small temporary index root with fake agent answers: `test_full_pipeline_end_to_end_on_three_fake_papers`, `test_rerun_with_same_prompt_version_is_idempotent` (card shards byte-identical on the second run), `test_course_shards_untouched`, `test_summary_command_matches_direct_counts`, `test_api_mode_without_approval_refuses_and_prints_estimate`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement the CLI; `README.md` documents the stages, run order and the two-Gemini discipline check.
- [ ] **Step 4:** Run `python -m pytest tests/agent/literature/profile tests/core/indexer -v`, then `python tools/run_tests_chunked.py`; expect PASS.
- [ ] **Step 5:** Run the real regression on the 67 trial papers in `research/` with subscription Gemini cards (no paid API): `metadata`, `classify collect`, hand the run to the agent, `classify submit`, same for variant `b`, `tag` rounds 1 to 3, then `summary`. Record the agreement rate, review-queue size and any quote rejections in `docs/status/literature/2026-11-13-spec-a-regression-run.md`. Do not apply `folders apply` until the owner approves the dry-run plan in the review Artifact.
- [ ] **Step 6:** Commit.

---

## Self-review

- **Spec coverage:** schema (Task 2), bibliographic and DOI (3), classification, discipline, subfields (4), 3ie tagging and quotes (5), income group and start year (6), human-decision ledger (7), folders and reversibility (8), profiles and corpus summary (9), harness and 3ie CSV gold (10), run, idempotence and regression (11), Task 0 items (0, 1, 2). Frontmatter mirroring is not planned; Task 0 decides whether transcripts carry frontmatter and whether editing it affects the content hash, and a mirror task is added only if both answers allow it.
- **Spec items deferred to the builder:** module layout beyond the names above, prompt wording, Artifact layout.
- **Not in this plan (spec section 1):** estimates, replication links, `outcome_status`, intervention-outcome linking, synthesis.
