# Cross-Group Connections: Literature Pipeline & Evidence Map

*Group C (Project 01). Files: Pitch (taxonomy extension) and `lit_review.md`. Written 2026-11-05. "(inference)" marks my own reading.*

## Relationship between the two files
`lit_review.md` (Sep 7) is a saved AI answer with draft scripts for harvesting, indexing and summarizing papers. The Pitch (Oct 9) adds a structured-extraction layer on top: a Pydantic schema for method, dataset, geography, hazard, intervention and outcome. The Gemini Brief (Nov 3) refers to `python -m agent.literature` in `academic-rag-model`, which looks like where this work went (inference; I did not check the code). The Pilot Scope Realignment still names `notes/02_literature-and-evidence-map/Literature Pipeline - Early Prototype.md` as an input to gate Part B.

## What other groups need from this one

### Compound shocks panel (B)
- The Gemini Brief asks for a literature gap memo built from this pipeline: corpus queries by country, intervention, outcome and data source, `db cooccur`, `db dist data_sources`. The Pitch's `datasets_used`, `hazard_types` and `study_countries` fields are the facets those queries rely on.
- The brief's question 4 (additional data) wants "what the closest papers use that we lack". That is a query over `datasets_used` and `spatial_resolution`, so extraction quality directly limits the answer.
- The Pitch's motivating failure case, that "Somalia" matches author affiliation and not study geography, is the same risk the brief handles by requiring DOI-verified citations.

### RCT replication and transportability (D)
- The RCT brainstorm's key empirical worry is whether enough RCTs have geocoded or panel data, especially in conflict and disaster settings. An evidence map is the instrument that would answer it, if one added a facet for *data availability*: geocoded sites, panel waves, public microdata (inference; the Pitch's schema doesn't have it).
- The Pitch's evidence-matrix output (method × dataset × country) would also show where hierarchical multi-RCT synthesis is feasible: several trials, same intervention, comparable outcomes.
- `study_type` in the schema separates impact evaluations from observational panels, which is the split the brainstorm needs.

### Overview and strategy (A)
- Project 01 in the original plan is a registry-based evidence map (3ie, J-PAL, WFP). The 3R plan splits it into disaster vs conflict bins. The Pitch proposes automating the coding instead of doing it by hand, and says the "literature gap memo" becomes a query over empty matrix cells.
- The Pitch claims it supplies Project 04's schema by auditing 100+ papers for standard spatial units and frequencies, and presents a working tool for the CTL fellowship (application due in November).

### Exploratory methods (E)
- `Research Ideas.docx` notes a wish for mixed methods using NLP/LLMs on top of quantitative data. The extraction pipeline is one concrete instance. The Somalia note's claim-coding layer is another.

## What this group provides to others
- A way to turn "has this been done?" into a query. The gate asks exactly that.
- A candidate schema for describing the Phase A panels themselves, so the toolkit can say which published studies used the same dataset combinations (inference).

## Open items
1. The Pitch's Step 1 (test the schema on the 75 harvested papers) was scheduled for October. Its status is not recorded in these notes.
2. Whether `lit_review.md` is now redundant. If so, keeping it as "early prototype" with a pointer to the current pipeline is cheaper than deleting it.
3. The Pitch rates OpenAlex, 3ie and ORKG from general knowledge. The Gemini Brief will test the actual corpus; compare the two when the memo arrives.
