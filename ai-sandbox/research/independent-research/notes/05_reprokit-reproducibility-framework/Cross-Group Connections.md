# Cross-Group Connections: Reprokit Reproducibility Framework

*Group F. See `Reprokit Project Summary.md` in this folder for the framework itself. Written 2026-11-05. "(inference)" marks my own reading.*

## Compound shocks panel (B)
- This is the pilot. Every `reprokit` goal was tested on `compound-shocks-panel`, and the Pipeline Review is about both. The gate documents (Pilot Scope Realignment, Data Audit Review, Gemini Brief) decide what the pilot may do next; reprokit decides how safely it does it.
- The Literature Gap Memo (Gemini, on branch `gemini/compound-shocks-lit-memo`) calls `reprokit` a "substantial workflow and reproducibility contribution" because ACLED's terms stop anyone publishing the fused panel; the pipeline lets others rebuild it with their own ACLED key. Its Open Question 3 asks whether to keep that route or swap ACLED for UCDP GED (CC BY 4.0). That is a decision about reprokit's restricted-data approach as much as about the research.
- The ACLED Terms note is the source for reprokit's "restricted data stays restricted" rule: raw rows private, aggregates and figures published with attribution, credentials from environment variables, replicators use their own accounts.
- Open licence work (five unverified descriptor fields) sits in this folder's summary and in the tracker.

## RCT replication and transportability (D)
- The RCT brainstorm's Step 1 is "replicate the study to confirm it works". Reprokit is the machinery for that: pinned data hashes, role-based adapters, manifests, byte-for-byte reruns, and a harmonization record when a new source differs in kind. The Phase A result that a new measurement type needs new adapter code (Sudan's displacement stock) applies directly: each RCT's data will differ in kind (inference).
- The brainstorm's Steps 2 and 3 add covariates and proxies from other sources. Under the framework each added source needs a descriptor and a harmonization decision, and the verification states keep proxy-based results labelled as such.
- Multi-RCT synthesis (hierarchical model across trials) is the framework's "compare" goal at a larger scale. Whether it needs a library repo (Project 04) or a study repo is undecided (inference).

## Literature pipeline and evidence map (C)
- Spec phase 12 hooks the project charter's 3ie taxonomy tags to the literature pipeline. It is blocked until the taxonomy is final. The Pitch's `EmpiricalStudyTaxonomy` is a candidate shape for that taxonomy (inference).
- The framework's evidence/desk repo kind is the home for Projects 01 and 03: no PDFs, a citation manifest (DOI or OpenAlex ID) and a shared Zotero group library.
- The Pilot Scope Realignment lists the literature pipeline as a source for the gate; reprokit's cost-transparency goal covers the same pipeline's paid-AI use.

## Overview and strategy (A)
- Project 04 in the 3R plan (open-source analytics toolkit) is the framework's library-repo kind. Spec phase 10 splits it out after the pilot shows what it needs.
- The 3R plan names software rigour (pytest, CI, modular design) as a reason for the Academic Hub and CTL work. Reprokit is a research-side instance of the same standard.
- The 3R plan's Project 06 (math thesis as an agent-orchestrated lab) is a candidate for the framework's study-repo kind and its agent-instructions standard (`AGENTS.md`, `agents.yaml`) (inference).

## Exploratory methods (E)
- The agent-based modeling idea would be a new project kind. The spec's phase 16 (future-kind check) is where such a case would be tested against the core (inference).

## Cross-project items outside `notes/`
- `academic-rag-model/docs/trackers/academic_hub_to_do.md` holds the open tracker items listed in the summary.
- `ai-sandbox/research/independent-research/projects/repositories.json` is the registry the spec calls for (URL, pinned commit). Right now it lists only two older gitlink repos; reprokit and compound-shocks-panel are not in it. A repo-hygiene handoff in `academic-rag-model` proposes adding them (inference: not done yet).
- The former Project 02 scaffold was retired on 2026-11-06; its literature review is temporarily in `projects/compound-shocks/`.
