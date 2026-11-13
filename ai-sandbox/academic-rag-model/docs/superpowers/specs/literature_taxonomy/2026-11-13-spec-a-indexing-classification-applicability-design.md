# Spec A: indexing, classification and applicability gate (first release)

Date: 2026-11-13. Status: draft for owner review. Parent:
[umbrella design v2](2026-11-11-literature-corpus-redesign-umbrella-design%20-%20v2.md)
(read it first; this spec does not repeat its rationale). Revisions are new `- vN` files.

Marking: **[Owner]** = stated by the owner. **[Call]** = my default, not yet agreed.
**[Unverified]** = a lead from the survey, to confirm in Task 0.

## 1. What this release delivers

A user points the pipeline at a folder of transcribed research documents and gets:

1. A per-document **research profile** on the existing index card: bibliographic fields verified against DOI registries, `report_type`/`subtype`, discipline and subfields, geography, `method_class`, `study_design`, `orientation`, `evidence_role`, and **intervention/outcome tags on the unmodified 3ie tree** with supporting quotes.
2. A mechanically derived **`applicability`** label (both / intervention only / outcome only / not applicable).
3. **Folders** regenerated from the frontmatter `discipline`.
4. A **corpus summary** report (counts per tag and per profile view).
5. An **evaluation harness** with a blind-labelling Artifact and per-stratum reports.

Not in this release: effect estimates, replication links, `outcome_status`, intervention-outcome linking (spec B); synthesis and draft-to-review (specs C, D); changes to the 3ie vocabulary or to `CHOOSING_RULE`/`FIT_TEST_EXAMPLES`. [Owner]

## 2. Task 0: preconditions (do before any other task)

Each is a lead from the survey. Report the answer in the plan; if a premise fails, say what it changes.

1. **`hub_id` path independence for journal-article cards.** `core/indexer/hub_identity.py` stamps `hub_id` into frontmatter for authored notes. Confirm journal articles carry a path-independent identity (`compute_file_id` is a candidate). If not, add one before any folder code. [Unverified]
2. **Extending `core/indexer/index_card.py`.** Find how cards are written and versioned, and the least invasive way to add a research profile with empty or "not applicable" values on course-material cards, without re-indexing `academic_resources` or `academic_notes`. Shared by everything, so callers need tests. [Owner constraint]
3. **Where discipline, tags and the sidecar interact today.** `topic_routing.py:route_to_folder` (uses `concepts[0]`), `topic_proposals.py`, `identity.py`, `papers.py:eligible_papers` (gates on `doc_type == "journal_article"`). List every reader of `doc_type` and of the folder path in `research/`. [Unverified]
4. **Overlap with unlanded branches.** Which of `codex/refine-v4`, `codex/refine-v4-trial-audit`, `codex/term-selection`, `claude/literature-reextract-v4` touch `agent/literature/schema.py` or `index_card.py`. Spec A lands first on `main`; those stay parked. [Call]
5. **3ie vocabulary tree.** Confirm `vocab_data/*.yaml` and `research/resources/3ie/vocab/{intervention,outcome,sector}.yaml` carry `level` and `parent` for every term, and which of the two is the source of truth. The folder also holds the taxonomy explorer pages and the sector taxonomy PDF for cross-checking. [Unverified]

## 3. Record schema (research profile)

Added to the card; versioned (`research_profile_version`); layer 4 fields are absent, not empty. Values below marked "closed" are enums; "open" are starter sets extended through reviewed proposals.

| Field | Value | Source | Notes |
|---|---|---|---|
| `report_type` | open: journal_article, working_paper, report, program_document, grey_literature, thesis, protocol, notes, other | LLM + registry prior | [Owner] starter set + reviewed proposals |
| `subtype` | open, per type (journal: empirical_study, systematic_review, methodology, qualitative_assessment, scientific_experiment, discussion_paper; program: design, procurement, monitoring_report, evaluation_report, supporting_document) | LLM | [Owner] |
| `title`, `authors[]`, `doi`, `publication_year`, `journal`, `openalex_id` | strings | sidecar, then DOI lookup, then LLM only when neither exists | `doi_verified: {date, source, match}` |
| `discipline` | closed: the 26 OpenAlex fields + `other` | OpenAlex topics, else LLM | with `discipline_confidence`, `discipline_source` |
| `discipline_domain` | closed: 4 OpenAlex domains | derived from `discipline` | mechanical |
| `openalex_subfields[]` | closed: the OpenAlex subfield list | OpenAlex topics (scored) where present; otherwise LLM from the list, within the chosen field | each with `source`, `score`; [Owner: include; keep classification cheap] |
| `country` (admin0), `admin1` | ISO-style names | LLM from text, checked against the sidecar | `country` required when the study has a place; list when multi-country |
| `country_income_group` | World Bank group in the year the intervention began | derived from `country` and year | empty if the year is unknown |
| `method_class` | closed: quantitative, qualitative, mixed_methods, other | LLM | [Owner] |
| `study_design` | open: `vocab_data/study_design.yaml` | LLM | disagreement with `method_class` is flagged |
| `orientation` | closed: retrospective, prospective | LLM | [Owner] |
| `evidence_role` | closed: primary_evaluation, synthesis, other | LLM | [Owner] |
| `intervention_tags[]`, `outcome_tags[]` | 3ie term ids (any level) | LLM, staged descent | each: `term_id`, `level`, `quote`, `quote_locator`; leaves imply ancestors at read time |
| `applicability` | closed: both, intervention_only, outcome_only, not_applicable, not_assessed | derived | mechanical from the two tag lists; `not_assessed` = tagging was skipped (non-research document), `not_applicable` = tagging ran and found nothing |
| `intervention_start_year` | integer, optional | LLM from text | `approximate: true` when taken from the study period or `publication_year`; feeds `country_income_group` |

Rules for tags [Owner]: unmodified 3ie tree; assign at the most specific node the text supports; branch-only support stays at the branch; no tag without a quote that exists verbatim in the transcript (checked mechanically); no tag, no proposal when nothing fits (a capped gap-note log records genuine in-scope misfits; it is not a vocabulary proposal). [Call on the gap-note log]

Vendor the OpenAlex field and subfield lists once into `agent/literature/vocab_data/` (fetched from the OpenAlex API, versioned with the retrieval date). The 3ie vocabulary stays where it is.

## 4. Pipeline

All LLM steps are task cards (the umbrella's rule): collect, run by an agent, submit, validate. [Owner: default driver is a subscription Gemini model through Antigravity; API and local models are selectable alternatives.] Reuse the `AgentDriver` collect/submit pattern already in `pipelines/convert_journal_articles/`. Every card and result records `prompt_version` and model.

1. **Mechanical metadata.** From the discovery sidecar and transcript front matter; DOI lookup (Crossref, then OpenAlex) confirms DOI, title, authors, year, journal; mismatches are flagged, never silently overwritten. Reuse the reference-checker and `fetch_dois` work. Papers with no DOI are marked unverified.
2. **Classification card (one per document, cheap).** Input: title, abstract and the first pages of the transcript, plus sidecar topics when present. Output: `report_type`, `subtype`, `discipline` (+confidence), `openalex_subfields` (two-step: field, then subfields within it), `country`/`admin1`, `method_class`, `study_design`, `orientation`, `evidence_role`. A document classified as notes/essay/other non-research stops here.
3. **Tagging cards (research documents only).** Interventions and outcomes tagged separately by **staged descent** of the 3ie tree (sector, then branch, then leaves), each stage showing definitions, each tag requiring a verbatim quote. Whether one prompt can carry the full tree is measured, not assumed. [Call: staged descent is the likelier fit]
4. **Verification.** Discipline: confidence at least 0.8 [Owner], a second agent re-classifies independently, and only substantive disagreement goes to a human sample. 3ie tags, `report_type`, `method_class`, applicability: thresholds and the verification process are set empirically on the test set (section 6); until then every tag carries its quote and a second-agent agreement flag, and disagreements queue for review in an Artifact. [Owner]
5. **Folders.** `discipline` drives the folder; a discipline with fewer than 3 papers (configurable) goes to `other`. A dry-run plan (moves, reasons) is reviewed in an Artifact, then applied by the pipeline's resolve function; moves are logged and reversible. The first run is a one-time reorganisation of `research/`; the plan owns updating every path reference found in Task 0. No clustering, no sub-disciplines. [Owner]
6. **Corpus summary.** `python -m ...` command (module path decided in the plan) prints and writes counts per `report_type`, `subtype`, `discipline`, `discipline_domain`, `method_class`, `orientation`, `evidence_role`, `applicability`, per 3ie sector and branch, and per inclusion profile (3ie-strict vs broad, section 5), with the list of unverified or flagged papers. Feeds the completeness checker.

## 5. Inclusion profiles (umbrella section 5a)

A profile is a small config file (YAML) naming: the vocabulary/framework, allowed `evidence_role` and `study_design`/`method_class`, income-group and date filters, and whether "unclear" papers are included. Spec A ships the profile loader, a **3ie-strict** default profile written from the public 3ie PICOS criteria (impact evaluations and systematic reviews, L&MIC by income group in the year the intervention began, listed interventions, "unclear" included), and a **broad** profile (any tag). The summary command applies a profile; producing a full map artifact is later work. Map protocols differ in dates and frameworks, so thresholds such as the 2000 start year are per-profile parameters, never constants.

## 6. Evaluation harness and test set

Build regardless of whether labels exist yet; gate the release only once pass bars are set (to be set per stratum after the first measurements). [Owner]

Components: (a) a blind-labelling Artifact (owner or a different model labels each test paper's `report_type`, applicability, main intervention and outcome **before** any extractor runs, decisions in its `db` collection); (b) a scoring script reporting per stratum: bibliographic accuracy vs DOI, `report_type` agreement, discipline agreement, applicability agreement, tag recall on main facts, and term-fit precision using the `trial2` judging scripts; (c) a held-out portion never used for prompt or rule changes; (d) the 67 existing trial papers as a regression set only.

**What the owner's 3ie folder provides (checked 2026-11-13)**
- Six `all_study_record*.csv` exports (111 to 3,214 rows) with columns Title, Author_Names, Abstract, Publication_Of_Type, DOI, Journal_Name, volume, pages, Url. The Agriculture-led Growth map's file has 1,668 studies. These give **inclusion positives and bibliographic gold** (title, authors, DOI, journal, and a 3ie `Publication_Of_Type`: journal article, working paper, report, thesis, protocol, ongoing study) for free. Many rows have no DOI, which is itself a test of the no-DOI path.
- They do **not** contain per-study intervention or outcome codes, and the saved map pages are an empty React shell with no matrix data. The coded cells need another source (the map's report PDF such as `egm_download.pdf`, or an export from the 3ie map site). Until then the reproduction check can test inclusion and `report_type`/bibliographic extraction but not tags. Which maps use the standard sector taxonomy rather than a map-specific framework is unverified. [Unverified]
- Negatives (papers not in the map) must come from outside the exports, e.g. the existing corpus.
- PDFs of the listed studies are not in the folder, and the repo is public: PDFs are never committed.

Target list for the owner to size and source: see umbrella v2 section 10; add 3ie-listed studies by `Publication_Of_Type` as a free stratum for `report_type`.

## 7. Cost and run modes

Per document: one classification card and the tagging cards (several short calls for the descent). On the subscription Gemini default this is quota, not dollars; on the paid API the plan must give a per-document estimate and the owner is warned before any run estimated over $1. [Owner standing rule] A local-only mode is supported if cheap to add, not required. [Owner]

## 8. Redo of existing records [Call]

Re-run steps 1 to 4 and 6 for all `research/` records (no extraction). The 35 `refine-v1`, batch-1 and REDDI `refine-v3` study records are kept as legacy; re-extraction (spec B) targets only papers this gate marks applicable. P0172 and the 31 open proposals are untouched.

## 9. Acceptance criteria for the plan

- No course-material card is rewritten except to add empty research-profile fields.
- Every tag has a quote that exists verbatim in the transcript.
- Re-running the pipeline on the same inputs and prompt version is idempotent.
- Folder regeneration never moves a file without a reviewed dry-run plan, and a `hub_id` survives a move.
- The corpus summary's counts equal direct counts over the cards.
- The evaluation harness runs end to end on the 67-paper regression set and on any labelled set provided.

## 9a. Calls made after an independent read (mine; correct any)

- **Research document.** `report_type` in journal_article, working_paper, report, program_document, grey_literature, thesis, protocol goes on to tagging. `notes`, `other` and essays stop after the classification card. Program documents are tagged: design and procurement documents carry interventions and intended outcomes (owner's tiers). The cost per document follows.
- **Applicability states.** `not_assessed` and `not_applicable` are different (schema above). The gap-note log is separate from applicability: it flags in-scope papers with no fitting term.
- **Folder scope.** Regeneration moves only the transcribed documents under `research/journal-articles/` (and equivalents the user configures). It does not touch `research/resources/` (the 3ie material), study records, the proposals ledger or P0172; those are re-keyed by `hub_id`, not moved. Non-research documents go to `other`.
- **Discipline verification.** A second agent classifies discipline for every research document (a small card, so the cost is minor and is estimated in the plan). Confidence below 0.8, or a different OpenAlex *field* between the two agents, goes to the review queue; a different field in the same domain is a milder disagreement, a different domain a strong one. Review queue = Artifact.
- **Idempotence and human decisions.** Human decisions (folder plan, disagreement queue) live in a ledger keyed by `hub_id`, separate from the cards, and override model output. A prompt-version change invalidates model output only, never recorded human decisions.
- **Second-agent independence [Owner, 2026-11-13].** Two Gemini agents with different prompts, to avoid cross-tool handoffs in this step. If the disagreement review shows too many false agreements, bring in a different agent type. The plan records the agreement rate and the review outcomes so that decision can be made from data.
- **`study_design` vs `method_class`.** Disagreement flags the paper; it blocks nothing.

## 10. Left to the builder

Module layout and names; the exact prompt text; how the descent stages are chunked; the `other`-folder threshold implementation; Artifact layout; the `research_profile_version` migration mechanism.

## 11. Open decisions for the owner

1. Per-study intervention and outcome codes for a reference map (the report PDF, or an export from the map site), and which 3ie map uses the standard taxonomy.
2. Pass bars per stratum, after first measurements.
3. Gap-note log for in-scope papers with no fitting 3ie term: keep (capped) or drop.
4. Whether to add a third `evidence_role` value for ongoing/protocol records that 3ie lists separately (protocols, ongoing studies).
