# Literature corpus redesign: umbrella design (v2)

**v2 (2026-11-12) changes from v1:** adds the two map views, "3ie-strict" and "broad" (section 5a); makes reproducing a published 3ie map the primary external check (section 10); adds `discipline_domain`, `openalex_subfields` and derived country income group to the record (section 4); replaces the "prior art" placeholder with findings (section 13); new open decisions in section 14. Everything else is v1 unchanged. v1 was approved on 2026-11-12; v2 additions await review.

Date: 2026-11-11 (v1), 2026-11-12 (v2). Status: draft for owner review. Supersedes the layer model in
the [2026-10-15 literature taxonomy pipeline design](2026-10-15-literature-taxonomy-pipeline-design.md);
that doc's file-is-truth architecture and task-card rule stand. Input:
[brainstorm handoff](../../../status/literature/2026-11-11-redesign-brainstorm-handoff.md).
Revisions are new `- vN` files.

Marking: **[Owner]** = stated by the owner in the 2026-11-11 brainstorm.
**[Call]** = my default, not yet agreed. **[Unverified]** = from a survey I have not confirmed in code.

## 1. Intent

Anyone with a disorganised directory of research PDFs (journal articles first;
program documents and grey literature later) can run the pipeline and get a
queryable, citation-grounded corpus. Nothing may depend on this corpus's
contents or structure. [Owner]

Why a redesign: the term-selection trials and the refine-v4 recovery tried to
fix omissions by rewording one prompt. The audit showed the gaps are upstream.
The pipeline never decides whether a paper can be described by 3ie intervention
and outcome terms, so Gemini was forced to invent them; discipline folders came
from a lossy OpenAlex step; and the test papers were a convenience sample. All
prior trial work is a proof of concept that informs this design.

Products, in build order:

1. **Indexing and classification** (spec A, first release).
2. **Corpus summary**: counts per tag; input to the completeness checker.
3. **Evidence-map extraction** (spec B): intervention/outcome tags, parameters, effect estimates.
4. **Topic synthesis** (spec C): question to relevant papers (with category counts) to a cited report, RAG over the corpus only.
5. **Draft-to-review** (spec D): a notes file or draft is tagged, matched to the corpus, then synthesised as in 4.

This doc fixes what they share. Each product gets its own spec; the only
contract between A and B is the per-paper record (section 4).

## 2. Goals, non-goals, anti-goals

Goals
- A per-paper record that is correct on verifiable facts (title, authors, DOI, year, journal) and checked mechanically against DOI registries.
- An applicability decision made from the paper's content before any facet extraction.
- Evidence-map-ready tags on the unmodified 3ie taxonomy, usable at any level of the tree.
- Folders that follow the metadata, not the reverse.
- A test set whose labels are fixed blind and whose results are reported per stratum.

Non-goals (now)
- Extending the 3ie vocabulary. [Owner] Term gaps are logged, not fixed; revisit only after sufficient evidence of gaps, to avoid overfitting to one outcome set.
- Linking specific interventions to specific outcomes (open question, section 11).
- Gap-analysis strength of evidence (separate design).
- Corpus-clustered or custom disciplines and sub-disciplines.
- Re-indexing `academic_resources` or `academic_notes`. [Owner]

Anti-goals (a failure even if it technically runs)
- Wrong bibliographic metadata; a missed obvious 3ie tag; a missed clearly labelled treatment effect; a missed replication link. [Owner, the four ways an output is judged wrong]
- Forced intervention or outcome terms on papers that have none.
- A vocabulary that grows to fit whatever the pipeline meets.

## 3. Current state (leads; verify before building)

- One indexer exists: `core/indexer/index_card.py`. The journal converter imports it, writes cards under its own `.index/` in `research/`, and stamps `openalex_id`, `doi`, `publication_year`, `openalex_topics` from the discovery sidecar (`pipelines/convert_journal_articles/identity.py`). [Unverified beyond imports]
- Not frontmatter today: authors, journal, geography, replication links. Study-level fields live in `research/.index/study_records/*.json` (schema `agent/literature/schema.py`). [Unverified]
- Discipline bug: `route_to_folder` (`discovery/discover_journal_articles/topic_routing.py`) files by `work.concepts[0]` and discards scores. Documented in `docs/trackers/pending_updates/2026-10-14-journal-discovery-audit.md`. `topic_proposals.py` exists. [Unverified]
- `doc_type` on research cards is mixed (`journal_article`, `personal_essay`, `business`, `journal-articles`), i.e. type and folder are conflated. `KNOWN_DOC_TYPES` in `index_card.py` is a course-material set. [Unverified]
- `agent/literature/papers.py:eligible_papers` gates on `doc_type == "journal_article"`: the only gate today.
- 3ie vocabulary YAML carries `level` and `parent`, so the tree is available (`vocab_data/build_3ie.py`).
- Reuse: `agent/literature/synth.py` (mechanically checked `P<n>` citations), `agent/rag/rag_agent.py`, `fetch_dois.py`, reference-checker work.
- Corpus: about 156 PDFs in `research/journal-articles/`, about 93 study records, 67 in analyses. Roughly 46 sit in a "novelty-check" folder. Counts are approximate.
- Unlanded: `codex/refine-v4`, `codex/refine-v4-trial-audit`, `codex/term-selection`, `claude/literature-reextract-v4`.

## 4. Layer model and the per-paper record

| Layer | Question | Basis | Applies to |
|---|---|---|---|
| 1. Document identity | What is it? `report_type` + `subtype` | Card time, then confirmed | Every file |
| 2. Bibliographic and descriptive | Title, authors, DOI, year, journal, discipline, geography, method class, study design | Reading + DOI lookup | Every paper |
| 3. Applicability | Which 3ie intervention and outcome tags does it contain? | Reading, quote required | Every paper |
| 4. Evidence-map extraction | Parameters, outcome status, effect estimates, replication links | Reading | Papers with at least one tag |

**Record fields** (frontmatter in the card; study-level detail may stay in a linked study record, one record per paper so there is a single join key):

- Identity: `report_type`, `subtype`.
- Bibliographic: `title`, `authors`, `doi`, `publication_year`, `journal`, `openalex_id`; `doi_verified` (date + source).
- `discipline` (section 7), `geography`: `country` (admin0, required when relevant), `admin1` (optional).
- `discipline_domain`: the OpenAlex domain (4 values) derived mechanically from `discipline`; no extra classification step. [Call]
- `openalex_subfields[]`: OpenAlex subfields (about 254) with scores, copied from the stored topics, recorded as candidates with `source: openalex`. Not used for folders, not LLM-verified; used for filtering and for matching in synthesis (spec C, D). Empty for papers with no OpenAlex record. [Call]
- `country_income_group`: World Bank group for the study country in the year the intervention began, derived from `country` and year; needed by the 3ie-strict view (section 5a). Left empty when the year cannot be determined. [Call]
- `method_class`: quantitative, qualitative, mixed methods, other. [Owner] Separate from `study_design`, which stays as the finer label from `vocab_data/study_design.yaml`. [Call] Disagreements between the two are flagged for review.
- `orientation`: retrospective or prospective. [Owner] The main way to tell designs from evaluations.
- `evidence_role`: primary evaluation, synthesis (flagged "not primary evaluation"), other. [Owner]
- `intervention_tags[]`, `outcome_tags[]`, from the 3ie tree, each with a supporting quote. `outcome_status` per outcome tag: intended, modelled, observed. [Owner]
- `applicability`: derived mechanically (section 5).
- `has_causal_estimate` (bool, with the identification approach named), `estimates[]` (point estimate, CI, SE, p-value, units, outcome and intervention it refers to), `replication` (links to replication files/repositories, with the quote).

Estimates and replication links are extracted at indexing time; meta-analysis use comes later. [Owner]

## 5. Applicability

Mechanical from the tags. A paper is a candidate for the map when it contains any 3ie intervention or outcome term.

| Interventions | Outcomes | `applicability` |
|---|---|---|
| yes | yes | both |
| yes | no | intervention only |
| no | yes | outcome only |
| no | no | not applicable |

Examples (owner's rules)
- Evaluates a named program with measured results: both, primary evaluation, retrospective, outcomes observed.
- Review covering several interventions: both, `evidence_role = synthesis`; in the map, flagged as not primary.
- Reports an observational outcome without a managed intervention: outcome only. Marginal eligibility.
- Simulates a policy without outcomes in the 3ie sense: intervention only (replaces the earlier "modelled policy" label).
- Program design or procurement document with planned outcomes: both or intervention only, prospective, outcomes intended.
- Climate or weather modelling with no listed intervention or outcome; pure methodology; commentary with neither: not applicable. No forced proposals, no facet extraction.

`study_design` is a prior, not the test: an RCT, DiD or RD almost always applies; qualitative, narrative review, simulation and ML must be asked. The audit showed the same design appears on both sides (the Somalia climate projection vs the risk-transfer model are both `simulation_model`).

Known limitation, stated not solved: attribution is at paper level. A paper evaluating A and B with outcomes X and Y fills all four cells of the intervention-outcome matrix, even if A affected only X. A map built on this can understate gaps; it cannot invent them. For now an empty cell is a gap. [Owner]

## 5a. Two map views [Owner]

The record supports two views of the same corpus.

- **3ie-strict.** Built to match 3ie's own inclusion rules so that, given the same papers, the pipeline could produce the same map. Public 3ie protocols (for example the resilience evidence gap map) use PICOS criteria: the study must evaluate at least one listed intervention, be an impact evaluation (experimental or quasi-experimental) or a systematic review, concern a low- or middle-income country (World Bank income group in the year the intervention began), and fall within the map's date range (that map: 2000 onwards). Borderline ("unclear") studies are included. The strict view is a configurable **inclusion profile** per map, with those criteria as parameters, not hard-coded constants. It reads `evidence_role`, `study_design`, `method_class`, `orientation`, `country_income_group`, `publication_year` and the intervention tags.
- **Broad.** Every paper with any tag, with the applicability, orientation, evidence role and outcome status shown as flags (section 5). Includes observational outcomes, intervention-only papers and prospective designs.

The 3ie-strict profile is also the pipeline's external check (section 10). 3ie's protocols are map-specific: the resilience map, for example, uses its own list of 40 interventions in 7 domains, not the global taxonomy. A profile therefore names the framework it uses, and a reproduction check can only target a map whose framework we can load. Which of the maps in the owner's 3ie folder use the standard sector taxonomy is still to be checked.

## 6. 3ie tree classification [Owner]

- Use the taxonomy exactly as published. No new terms.
- Classify against the whole tree, not just leaf definitions. Assign each tag at the most specific node the text supports; a leaf counts for every ancestor (mechanical rollup, so sparse leaves can be analysed at the branch).
- A paper that supports only a branch-level claim is recorded at the branch and does not count toward any leaf under it.
- A paper that fits no term gets no tag. Out-of-scope papers generate no proposals. For in-scope papers with a genuine gap, a gap note is logged in a capped ledger, not a proposal against the vocabulary. [Call]
- Do not change `CHOOSING_RULE`, `FIT_TEST_EXAMPLES` or the vocabulary without an explicit owner decision.
- Settled earlier: individuals fall under households; adopting adaptation measures is not resilience; commentary and conceptual papers use `narrative_review`.

## 7. Classification, discipline and folders

**`report_type` and `subtype`.** [Owner for the example subtypes]
- Journal article: systematic review, methodology, empirical study, qualitative assessment, scientific experiment, discussion paper, others as needed.
- Program documentation: design, procurement, monitoring report, evaluation report, supporting document.
- Other types: grey literature report, working paper, notes, other.

[Call] A starter vocabulary like the above, plus proposals for new values reviewed through an Artifact (same pattern as vocabulary proposals), so an arbitrary user's directory is not forced into a fixed list. Classification is by an LLM reading the first pages and checked against the DOI record (a DOI that resolves to a journal article supports the label). Distinct from the course-material `doc_type` values, which are untouched.

**Indexer extension.** Add a research profile to the existing card schema in `core/indexer`. Course-material cards receive empty or "not applicable" values for the new fields and are not re-indexed. [Owner] The new fields live in the existing cards; no second indexer. Only `research/` is re-indexed. TODO-0036 (OpenAlex vs indexer tag consolidation) is settled here: OpenAlex supplies discipline and bibliographic candidates; the indexer's tags remain free-form topic tags.

**`discipline`.** The 26 OpenAlex "fields" (the standard list). [Owner approved the list; scoring rule is my call] Choose the field with the highest weighted topic score from the stored OpenAlex topics; if the top score is weak or two fields are close, the paper's own text decides. This replaces `concepts[0]`.

**Folders** [Owner, except where marked]
- The frontmatter is the source of truth; folders are generated from it. The default key is `discipline`. Other keys (year, project) are possible later.
- Re-categorising a paper moves it at the next regeneration. [Owner] Moves are automatic, logged and reversible. [Call: this replaces the earlier "never auto-move" rule.]
- A discipline with fewer than N papers (default 3, configurable) is held in `other` until it reaches N.
- A paper's `hub_id` must not depend on its path. [Unverified for journal articles: `hub_identity.py` stamps `hub_id` into frontmatter for authored notes.]
- No clustering, no sub-disciplines in this release.

## 8. Verification

DOI lookup against Crossref (and OpenAlex) confirms DOI, title, authors, year and journal. Mismatches are flagged, not silently overwritten. Every identifier is checked mechanically, never from LLM output alone. Where a paper has no DOI, the fields are marked unverified. Reuse the reference-checker and `fetch_dois` work.

## 9. Spec split

| Spec | Scope | Measured by |
|---|---|---|
| A (first release) | Fields in section 4 layers 1-2, applicability tags (gate), folders, DOI verification, corpus summary | Metadata accuracy vs DOI; classification agreement per `report_type`; applicability agreement per stratum |
| B | Parameters, outcome status, estimates, replication links; term-fit | Recall of main facts on applicable papers; term-fit precision (definition-aware judge); estimate extraction accuracy |
| C | Topic synthesis | Citation checks; coverage of relevant papers |
| D | Draft to review | As C, plus matching quality |

Stages run locally or on the subscription Gemini agent. Anything estimated above $1 in paid API cost needs a warning and a go-ahead first.

## 10. Test-set plan

Principles (from the handoff, carried forward)
- Stratify by `report_type`, method class and applicability, with labels assigned **blind before any extractor runs**, by the owner or a model other than the one tuned.
- Hold out a portion that is never used for prompt or rule changes.
- Paper-level answer key: applicability tier, main intervention, main outcome. Fact-level gold is too expensive.
- Reuse the `trial2` judging scripts and prompts for term fit (`research/.agent_work/term-selection-trials/README.md`).
- Report per stratum, not pooled.

External check: reproduce a published 3ie map [Owner]
- Take a published 3ie evidence gap map whose framework we can load, obtain the PDFs of its included studies, and run the pipeline from raw PDFs under the matching 3ie-strict profile. Compare (a) which papers are included and (b) which interventions and outcomes each is tagged with against 3ie's own double-coded results. This gives independent gold labels that neither we nor the model tuned, and so lessens the labelling burden for the intervention and outcome strata.
- Constraints: the repo is public, so PDFs are never committed (existing IP rule); the map's coding may have been done at a different grain than our tags, so agreement is reported at the branch level as well as at the leaf level; maps that use their own framework (as the resilience map does) need that framework loaded as a vocabulary, which is a separate task from the global taxonomy.
- It checks the strict view only. The broad view's extra categories have no 3ie gold and rely on the blind-labelled set below.

Existing corpus
- The 67 papers in the trial analyses were used to tune prompts. They serve as a regression check only, not for pass/fail or precision claims. [Call]
- New papers, not yet seen by any extractor, form the labelled and held-out sets.

Target list (to prepare; the owner decides what is worth the effort, especially manual downloads) [Call on counts]

| Stratum | Why | Suggested count | Source |
|---|---|---|---|
| Impact evaluations (RCT, DiD, RD, IV) | Should be `both`, causal estimates | ~15 | automated (OpenAlex, 3ie repository) |
| Systematic and narrative reviews | Synthesis role | ~8 | automated |
| Observational empirical studies | Outcome only | ~8 | automated |
| Qualitative studies | Mostly not applicable or marginal | ~8 | automated |
| Simulation and modelling | Intervention only / not applicable | ~8 | automated |
| Methodology and discussion papers | Not applicable | ~6 | automated |
| Program design / procurement documents | Prospective, intended outcomes | ~6 | manual (agency sites) |
| Monitoring and evaluation reports | Retrospective, mixed estimates | ~6 | manual / 3ie |
| Grey literature, working papers | Type classification | ~6 | partly automated |
| Papers with replication files | Replication detection (AEA, Dataverse) | ~8 | automated |
| Non-research documents (notes, essays) | `report_type` negatives | ~4 | already in corpus |

Disciplines do not need coverage beyond a handful to test the folder logic.

## 11. First release

Spec A only: the extended card schema, classification and applicability gate, DOI verification, discipline from OpenAlex fields, regenerated folders, corpus summary report, and the blind-labelled test set with an evaluation script. No change to facet wording, no synthesis. It delivers a correctly typed, correctly foldered, verified corpus and an honest eligible subset on its own.

## 12. Redo plan for existing records [Call]

- Re-run classification, applicability and metadata verification for all `research/` records (cheap, no extraction).
- Keep the 35 `refine-v1`, batch-1 and REDDI `refine-v3` records as legacy until the gate runs; re-extract only papers the gate marks applicable and whose records disagree with a fresh extraction.
- The unlanded refine-v4 code is not landed. Specs A and B decide what, if anything, of it to reuse.
- P0172 and the 31 open proposals remain as they are until spec B decides how gap notes replace proposals.

## 13. Prior art (web search 2026-11-12; search snippets and one protocol PDF, not full reads)

- **OpenAlex.** Topics sit in a four-level hierarchy: 4 domains, 26 fields, about 254 subfields (docs say 252 in one place), about 4,500 topics, aligned with Scopus subject categories. Supports the 26-field discipline list. Type values come from Crossref with some extensions (for example reviews); the exact lists were not retrieved.
- **Semantic Scholar.** `publicationTypes` includes JournalArticle, Review, MetaAnalysis, Study, CaseReport, ClinicalTrial, Editorial, Conference, Book, Dataset. A cheap prior for `report_type`; no social-science study design.
- **3ie.** Taxonomy of about 13 sectors, 300 intervention types and 290 outcome categories. Its evidence gap maps cover impact evaluations and systematic reviews, with PICOS inclusion criteria, double coding and "unclear" studies included. The resilience map protocol uses its own 40-intervention framework. No single consolidated 3ie methods handbook found; detail comes from individual protocols.
- **Replication links.** The AEA Data and Code Repository at openICPSR gives each package a DOI; the article link is added by the author after publication. No central registry found. Crossref can carry an `is-supplemented-by` relation to a dataset DOI, and DataCite has the reciprocal `IsSupplementTo`. Plan: DOI-relation lookup first, paper text as fallback. Query parameters need checking.
- **Automation.** ADVISE (3ie/USAID, active-learning screening for map design); a UNDP supervised classifier of impact-evaluation abstracts (high precision, uneven recall); a UNICEF human-in-the-loop mapping of 631 evaluations; LLM extraction studies find study design and outcomes the least reliable fields. Nothing found that combines document type, map eligibility, causal estimates and reproducibility in one pipeline. This is not an exhaustive search and supports no novelty claim.
- **Not covered:** EPPI-Reviewer and RobotReviewer documentation; Crossref and OpenAlex `type` value lists; Campbell Collaboration coding schemes.

## 13a. Builder-check calls (mine, added after an independent read; correct any)

- **Discipline without OpenAlex data.** `discipline` applies to every `report_type`. With no OpenAlex record (no DOI, grey literature, program documents), an LLM reads the document and picks from the same 26 fields; OpenAlex scores are the primary path only when they exist. The `other` folder rule is unchanged.
- **Weak/close scores.** Defaults are configurable: "weak" = top field below 0.5 of total topic score; "close" = runner-up within 0.1 of the top. If the sidecar holds only the old `concepts`, topics are re-fetched by DOI/`openalex_id`.
- **First folder regeneration** is a one-time reorganisation. It runs as a dry-run plan reviewed in an Artifact, then applied. Spec A's plan owns updating every path reference (study records, analyses, `papers.py`, cards). Verifying that `hub_id` is path-independent for journal-article cards is task 0 of spec A; if it fails, a path-independent identity comes before any folder code.
- **Record schema.** Spec A creates only layers 1-3 fields. Layer 4 fields (`estimates[]`, `replication`, `has_causal_estimate`, `outcome_status`) are added by spec B. The card schema carries a version number so B can migrate it.
- **Merge order.** Spec A lands first on `main`. `codex/refine-v4`, `codex/refine-v4-trial-audit`, `codex/term-selection` and `claude/literature-reextract-v4` stay unlanded; before A's plan, check which of them touch `agent/literature/schema.py` and `core/indexer/index_card.py` and rebase or abandon accordingly.
- **Applicability prompting.** Whether the 3ie tree fits in one prompt or needs a staged descent (branch first, then leaves) is a spec A task to settle by measurement; the staged descent is the likelier fit for whole-tree classification.
- **Release gating.** If labels do not exist at build time, the evaluation script and a blind-labelling Artifact are still built; the release is gated only once thresholds are set (see decisions below).

## 14. Open decisions for the owner

1. Intervention-outcome linking: feasible at paper level only? Revisit once the corpus is larger.
2. `report_type` vocabulary: starter set plus reviewed proposals, or fixed? (my default: reviewed proposals)
3. Threshold N for the `other` folder (default 3).
4. Which test-set rows to source and who labels them.
5. Redo scope for legacy records (section 12).
6. Whether synthesis papers and "outcome only" papers appear on the map by default or behind a filter.
7. Gap notes: a capped ledger, or log-only, for in-scope papers with no fitting term.
8a. (v2) Which published 3ie maps use the standard taxonomy and are therefore usable for the reproduction check, and which to use first. The owner has a folder of 3ie reports and example maps.
8b. (v2) Whether `openalex_subfields` and `discipline_domain` are wanted as filter fields in the first release or deferred.
8. Thresholds for the 3ie tagging, applicability, `report_type` and other non-discipline classifications, and the process that keeps them accurate and scalable. These need more work (see "Decided 2026-11-12").

## 15. Decided 2026-11-12 [Owner]

- **Discipline threshold.** Disciplines should be fairly clear. Initial confidence threshold 0.8 (replaces the 0.5 "weak" default in 13a). A second agent checks the result; a human reviews a sample only if the two substantively disagree.
- **Other classifications** (3ie tags, applicability, `report_type`, `method_class`) are harder. Their thresholds and verification process are worked out empirically in specs A and B against the blind test set; no numbers are fixed here.
- **Run modes.** Local model and API are both options. The default is a subscription Gemini model through Antigravity (the cheapest, most powerful route most users have). A local-only mode is supported, not required for the first release to pass.
- **`report_type`.** Starter set plus reviewed proposals through an Artifact. Confirmed.
- Pass/fail bars for the test set follow the same rule: set per stratum once the first labelled measurements exist.

Status: owner approved v1 on 2026-11-12 ("looks good"). v2 additions (section 5a, the reproduction check, the new fields) are awaiting review.
