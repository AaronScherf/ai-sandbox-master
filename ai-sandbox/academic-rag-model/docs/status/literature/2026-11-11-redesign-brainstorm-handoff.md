# Literature pipeline redesign: brainstorm handoff (2026-11-11)

Input for a design brainstorm, not a spec and not an implementation task. Claude leads the design discussion with the owner; Codex implements only what the owner later approves, in a dedicated `codex/<task>` worktree; subscription Gemini fills cards. Do not write code, run a card batch, or change the 3ie vocabulary from this document. Write the outcome as a new dated design doc (revisions as new `- vN` files).

## Why this exists

The batch-2 rollout and the refine-v4 recovery trial ([closeout](2026-11-06-term-selection-trials.md#closeout-2026-11-11), [trial audit](2026-11-11-refine-v4-trial-audit-handoff.md)) tried to fix omissions by rewording one prompt. The audit showed the real gaps are upstream of the prompt:

1. The pipeline never decides whether a paper is the kind of evidence the 3ie intervention/outcome facets can describe. A climate-projection model, a conceptual framework, or a qualitative study of lived experience has no 3ie intervention or outcome. Gemini was told to find them anyway: in batch 2 it emptied facets; in v4 it proposed rainfall and temperature projections as "outcomes" (P0176, P0177, P0184, P0185 were proposals, not 3ie terms; the 3ie vocabulary has no climate-variable outcome).
2. `study_design` does not decide this. `simulation_model` labels both the Somalia climate projection (no interventions) and the risk-transfer model (three modelled interventions). Method and applicability are different questions.
3. The test papers were a convenience sample (28 original trial papers; the v4 eight were drawn from the papers that lost all facts). They are fine as a regression check and unfit for pass/fail or precision claims.

Treat all prior trial work as a proof of concept that informs the design.

## Owner requirements (stated 2026-11-11)

- The corpus is just a collection of papers and could be used for anything. A subset will feed 3ie-style evidence maps. Any user with a directory of research papers must be able to run these pipelines, so nothing may depend on the corpus's contents or structure.
- A **classification and categorisation run** is part of the process, not an assumption about the input.
- The directory should be **dynamically categorised into thematic subfolders**, working together with the rest of the frontmatter metadata.
- Build on and improve the pending work to make the journal-article transcription tag index files appropriately.

## Working model to react to (Claude's proposal, not decided)

| Layer | Question | Basis | Applies to |
|---|---|---|---|
| `doc_type` | What kind of document is this (journal article, report, grey literature, textbook, notes)? | Index card, classified at indexing time | Every file |
| General characterisation | How was the work done and what is it about? `study_design`, sector, population, geography, key findings; thematic category | Reading the paper | Every paper |
| 3ie applicability | Does the paper itself evaluate, model, or review a named policy/programme/practice, or measure results of one? Quote required. | Reading the paper | Papers in the evidence-map subset |
| 3ie facet extraction | Intervention and outcome terms under the fit test | Reading the paper | Applicable papers only; `[]` and no forced proposals otherwise |

Two products fall out: a general literature synthesiser for the whole directory, and a taxonomy extractor for the eligible subset. Design and measure them separately.

`study_design` is a prior for applicability, not the test (an RCT/DiD/RD almost always applies; qualitative, narrative review, simulation, ML must be asked). Alternative to evaluate: classify finely first and define an eligible category set. The audit's evidence favours a content check, because the same category appears on both sides.

## What exists (check before designing; these are leads, not verified)

- `core/indexer/index_card.py`: `doc_type` is classified by the LLM at card time against a `known_doc_types` set, with a passthrough used by the journal converter. The hub's own values (`ta_notes`, `problem_set`, `textbook`, `handwritten_notes`, `lecture_notes`, `syllabus`, ...) are course material. Where the research index's `journal_article` cards and their other values come from was not traced.
- `agent/literature/papers.py:eligible_papers` keeps only `doc_type == "journal_article"` with a transcript. This is the only gate today.
- `agent/literature/vocab_data/study_design.yaml` already holds method labels, including `narrative_review` and `simulation_model`.
- Tracker items TODO-0036 (OpenAlex vs indexer tag consolidation and topic clustering; unblocked 2026-10-15) and TODO-0037 (unified discovery-to-index wrapper) in `docs/trackers/academic_hub_to_do.md`. The classification proposal mode (`topic_proposals.py`) in the [2026-10-14 reliability and classification spec](../../superpowers/specs/discover_journal_articles/2026-10-14-reliability-and-classification-design.md) shipped.
- [Journal article transcription status](../convert_journal_articles/2026-09-01-journal-article-transcription-status.md) ("What's next") and the [2026-10-15 literature taxonomy pipeline design](../../superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md).
- Memory-recorded: the reprokit evidence-map work (v0.4.0, 2026-11-07; criteria unconfirmed; tracker section has open items). It may already define what counts as evidence for a map, which is the applicability question. Read it first.

A rough, unfiltered count of `study_design` over the current records (82 records, which does not match the 67 canonical papers, so the filter was off): qualitative 25, cross-sectional regression 11, systematic review 11, simulation/structural 8-11, narrative review 6, the rest single digits. Only about 20-25 look like standard impact evaluations. Recount properly before relying on it.

## Questions the brainstorm should settle

1. What are the exact applicability outcomes, and who defines "evidence" for a map (the reprokit criteria versus the 3ie definitions)? Is "reviews of interventions" one value or several?
2. Does `study_design` stay a separate field or derive from applicability? What is the minimal set of general-characterisation fields for a corpus-agnostic run?
3. How does `doc_type` extend beyond a fixed vocabulary for an arbitrary user's directory (journal article, report, working paper, notes, grey literature)? Fixed set, user-supplied, or proposed-and-reviewed like vocabulary proposals?
4. How are thematic subfolders produced dynamically: from OpenAlex topics, indexer tag mining, an LLM proposal, or a mix? How do folders interact with frontmatter (source of truth, rename and move behaviour, hub_id stability)?
5. Where does each stage run (local, subscription Gemini, paid API), and what does each cost for a typical directory? Warn the owner before anything estimated over $1.
6. What is the smallest first release that delivers value on its own (probably a classification pass plus the applicability gate, before touching facet wording again)?
7. What happens to existing records (35 `refine-v1`, batch-1 and REDDI `refine-v3`) under the new design: rerun all, rerun selectively, or keep as legacy?
8. How are proposals handled for papers outside the 3ie scope, so the ledger is not flooded?

## Test-set principles (carry into the design)

- Stratify by design type and by independent applicability labels, assigned blind **before** any extractor runs, by the owner or a different model from the one tuned.
- Hold out a portion that is never used for prompt or rule changes.
- Use a paper-level answer key (applicable yes/no; main intervention and outcome named); fact-level gold is too expensive.
- Judge term fit with a definition-aware judge; reuse the `trial2` judging scripts and prompts described in `research/.agent_work/term-selection-trials/README.md`.
- Report applicability agreement, recall of main facts on applicable papers, and term-fit precision, per stratum, not pooled.

## Constraints that stand

- Do not change the official 3ie vocabulary or the shared `CHOOSING_RULE`/`FIT_TEST_EXAMPLES` without an explicit owner decision.
- Settled owner decisions: individuals fall under households; adopting adaptation measures is not resilience; commentary and conceptual papers use `narrative_review`; whole-corpus rollout is the goal.
- Live state: 35 `refine-v1` papers, batch-1 and REDDI `refine-v3` accepted, P0172 open, 31 open proposals; derived outputs reflect that state. The `refine-v4` code is on `codex/refine-v4` (`d3a348c8`), unlanded.
- Any step needing a human decision produces an interactive Artifact with decisions in its `db` collection, not a hand-edited file.
- Follow `docs/WORKTREE_WORKFLOW.md`; routing per `docs/AGENT_ROUTING.md`.

## Expected output of the brainstorm

A design doc with: the chosen layer model, the applicability definition with examples, the classification and thematic-folder approach, a test-set plan with who labels, a minimal first release, a redo plan for existing records, and the owner decisions still open.
