# Notes Reorganization Report

*Prepared 2026-11-05 by Claude. Scope: the 14 files sitting directly in `ai-sandbox/research/independent-research/notes/` (13 `.md`, `Research Ideas.docx`, plus the `Ground Truth - PhD Research Plan.html` duplicate). `application_essays/` and `processed_outputs/` were not read. Nothing was moved or renamed; this report and the five `Cross-Group Connections.md` files are the only additions.*

Contents: **1.** file summaries in edit order, **2.** grouping, **3.** proposed folder structure, **4.** pointers to the per-group connection documents, **5.** things to know before moving anything.

---

## 1. Summary of each file, oldest edit first

"Last edit" is the filesystem modification time in the main checkout. Three pairs share an identical timestamp, which suggests a bulk touch (sync or script) rather than independent edits, so treat order within a pair as arbitrary: Ground Truth `.md`/`.html` and Somalia (09-27 22:05), Ground Truth 3R and Pitch (10-09 21:46), ACLED Terms and Sudan Data Sources (10-31 16:54).

| # | Last edit | File | Author / origin |
|---|---|---|---|
| 1 | 2026-08-30 14:04 | `Research Ideas.docx` | Aaron |
| 2 | 2026-09-07 18:15 | `lit_review.md` | Gemini chat transcript |
| 3 | 2026-09-27 22:05 | `Ground Truth - PhD Research Plan.md` (+ `.html` copy) | Claude/Aaron synthesis |
| 4 | 2026-09-27 22:05 | `Somalia Three-Shock Case Study.md` | Aaron, converted pitch |
| 5 | 2026-10-05 12:21 | `Data Sources - Climate Displacement Cash Conflict.md` | Gemini |
| 6 | 2026-10-09 21:46 | `Ground Truth - PhD Research Plan - 3R Revision.md` | Aaron + Gemini |
| 7 | 2026-10-09 21:46 | `Pitch - Structured Literature Taxonomy and Research Hub Extension.md` | Aaron + Gemini |
| 8 | 2026-10-31 16:54 | `ACLED Terms - Redistribution Findings.md` | Gemini |
| 9 | 2026-10-31 16:54 | `Sudan Data Sources - Portability Check.md` | Gemini |
| 10 | 2026-10-31 18:23 | `Pilot Scope Realignment - Exploratory Review Gate.md` | Gemini |
| 11 | 2026-11-03 01:07 | `Review Gate - Data Audit Review.md` | Claude |
| 12 | 2026-11-03 14:13 | `Review Gate - Gemini Brief for Literature Gap Memo.md` | Claude |
| 13 | 2026-11-03 14:39 | `Pipeline Review - Reproducible Research Framework after Phase A.md` | Claude |
| 14 | 2026-11-05 20:40 | `RCT_replication_gemini_brainstorm.md` | Aaron + Gemini |
| (+1) | 2026-10-20 (branch commit) | `Brainstorming Transcript - Transferability of Crisis Interventions.md` | Aaron + Gemini; added 2026-11-06, see below |

### 1. `Research Ideas.docx` (2026-08-30)
**Purpose:** Free-form personal notebook of research identity and methods ideas, from before the plan was narrowed.
**Main ideas:**
- A heterodox, data-first development economics: local context over global assumptions, distributional effects over averages, an equity and working-class focus, and mixed methods that use NLP/LLMs.
- Multidimensional welfare as vector optimization, instead of a single welfare index.
- Agent-based models for climate and conflict shocks: mitigation vs adaptation, preparedness vs response, cost vs lives saved.
- Deep-network global solution methods lose causal interpretability and are prone to spectral bias. They smooth over sharp ecological tipping points, so the open question is hybrid architectures that respect thresholds.
- Non-parametric alternatives to analytic optimization: DEA and shape-constrained estimation, weighed against structural estimation.

### 2. `lit_review.md` (2026-09-07)
**Purpose:** Saved AI answer on building an automated literature-ingestion pipeline for the Columbia agenda.
**Main ideas:**
- Architecture: OpenAlex and Semantic Scholar for discovery, Unpaywall and EZProxy for full text, Zotero for references, and Obsidian or a local vector store for the knowledge hub.
- Draft scripts: `lit_harvester.py`, `lit_vector_indexer.py` and `lit_rag_memo.py`.
- Seeded with the Tier 1 and Tier 2 Columbia faculty.
- Looks like the early prototype of what is now `academic-rag-model/agent/literature` (my inference; worth confirming).

### 3. `Ground Truth - PhD Research Plan.md` (2026-09-27; the `.html` is a rendered copy)
**Purpose:** The original master plan, a synthesis of 18 application essays into dissertation directions, a faculty outreach list, a month-by-month calendar and six year-one projects.
**Main ideas:**
- Six recurring themes (climate-adaptive agriculture, remote sensing, digital credit, causal ML for scaling pilots, displacement, practitioner tools) plus a heterodox strand that doesn't fit.
- Four directions. I is the flagship (climate adaptation, migration and cash transfers under conflict). II is digital credit and insurance. III is a toolkit for scaling pilots. IV is chatbot-elicited surveys.
- Projects: 01 evidence map, 02 fused climate-conflict-displacement panel, 03 chatbot pilot, 04 open-source toolkit, 05 heterodox note, 06 math thesis.
- Later revisions: Ukraine agribusiness RCT dropped, NECR5250 dropped (09-27).
- Superseded in framing by the 3R Revision (#6).

### 4. `Somalia Three-Shock Case Study.md` (2026-09-27)
**Purpose:** Design for the first Project 02 case study. It was converted from a course pitch and the course framing was stripped.
**Main ideas:**
- Separates three simultaneous 2021-2023 shocks in Somalia: the Ukraine-war import price shock, the drought and al-Shabaab conflict.
- Three layers: data (what happened), narratives (what was claimed, from news and press) and verification (what holds up).
- The verification layer uses claim-lineage tracing and an LLM coding pass checked against hand-coding. It is flagged as a reusable Project 04 component.
- Lists verification risks (ACLED under-reporting, the famine declaration status, the wheat-import-share figure) and fallback scopes (drop Ukraine, switch to Sudan, or centre on Odesa).
- Partly overtaken by the data audit, which found the price panel thin before 2023-07 and the narrative layer not yet built.

### 5. `Data Sources - Climate Displacement Cash Conflict.md` (2026-10-05)
**Purpose:** Survey of datasets and published precedents for the whole research program.
**Main ideas:**
- Frames the flagship question: does climate-adaptive resilience reduce the chance a shock becomes displacement, and does that break down under conflict?
- Maps each project to its data needs.
- Lists the fusion pitfalls: spatiotemporal misalignment (MAUP), reporting bias in insurgent-held areas, and endogeneity.
- Deep dives on PRMN, ACLED, CHIRPS/ERA5, WFP/FSNAU prices, cash-transfer datasets, World Bank surveys and 3ie.
- Covers published precedents, a cross-dataset matrix, a fusion pipeline sketch with a Project 06 residual hook, and next steps for Oct-Dec.

### 6. `Ground Truth - PhD Research Plan - 3R Revision.md` (2026-10-09)
**Purpose:** Supersedes the original plan with a sharper identity: Resilience, Response and Recovery under compounded disasters and armed conflict, with data scarcity as an advantage.
**Main ideas:**
- Three pillars: data scarcity as an advantage, transferring mechanisms from disaster response to conflict, and rebuilding and capital replacement.
- New directions: I 3R economics (flagship), II anticipatory action and disaster-to-conflict transferability, III data fusion under conflict, IV Ukraine reconstruction.
- Drops the chatbot pilot. Adds Project 03 (a transferability working paper) and Ukraine as a Spring 2027 testbed.
- Names DML (EconML) and spatiotemporal graph models as its technical identity.
- Reframes Academic Hub and the CTL partnership as engineering foundation, and Project 06 as an agent-orchestrated statistics sandbox.

### 7. `Pitch - Structured Literature Taxonomy and Research Hub Extension.md` (2026-10-09)
**Purpose:** Pitch for an LLM extraction layer that tags papers by method, dataset, geography, hazard, intervention and outcome.
**Main ideas:**
- Flat keyword search fails here: country tags reflect author affiliation, and datasets are invisible.
- Compared against ORKG, 3ie, Papers with Code and OpenAlex.
- A four-stage architecture (harvest, Pydantic extraction, DuckDB/YAML storage, evidence-matrix output) with a draft `EmpiricalStudyTaxonomy` schema.
- Positioned as feeding Project 01 (the gap memo from empty matrix cells), Project 04 (schemas from observed practice) and the CTL fellowship.
- Milestones Oct-Dec 2026.

### 8. `ACLED Terms - Redistribution Findings.md` (2026-10-31)
**Purpose:** Compliance reading of ACLED's terms for an open-source repository.
**Main ideas:**
- Quotes the EULA and attribution rules, then gives a plain-language reading.
- Raw event rows cannot be published. Aggregated counts, attributed maps and figures, synthetic fixtures and API-calling code can be.
- Replicators must hold their own `myACLED` accounts, and credentials come from environment variables.
- The research tier has a rolling 12-month lag.
- Open questions and a draft consultation email to ACLED.
- Ends with an action matrix for Project 02. It is not legal advice, and ACLED was not contacted.

### 9. `Sudan Data Sources - Portability Check.md` (2026-10-31)
**Purpose:** Tests whether the Somalia panel design ports to Sudan, role by role.
**Main ideas:**
- Conflict, rainfall and boundaries port directly.
- Displacement is only partly portable: IOM DTM gives stocks with state-level origin, where PRMN gives flows with reasons.
- Prices are partly portable: WFP Sudan has no wages or livestock and covers few markets.
- Column-by-column discrepancy matrix.
- Recommended adaptations: a state-level or host-locality model, interaction modeling instead of reason tags, and NDVI or night lights in place of terms of trade.

### 10. `Pilot Scope Realignment - Exploratory Review Gate.md` (2026-10-31)
**Purpose:** Owner decision, written up by Gemini, to split the pilot into gated phases.
**Main ideas:**
- Phase A (data intake, fusion and descriptive audit) proceeds.
- Formal econometrics, price decomposition, cross-country regressions and the LaTeX paper are held.
- A mandatory gate before Phase B: Part A data audit, Part B literature gap memo, Part C owner approval.
- Prior plans are preserved with commit SHAs.
- Specifies edits to the plan's Tasks 11, 12 and 15.

### 11. `Review Gate - Data Audit Review.md` (2026-11-03)
**Purpose:** Gate Part A, Claude's review of the two audit memos.
**Main ideas:**
- Neither panel is ready for a conflict-by-price design.
- Somalia's price coverage jumps around 2023-07, which looks like WFP network expansion and not conflict.
- Displacement and good price coverage barely overlap in either country.
- Sudan prices cover only 18 of 189 localities.
- Missing prices look programme-driven in Somalia and conflict-linked in Sudan.
- Only `events`, `fatalities` and `precip_mm` are dense in both.
- Also lists memo defects (fixed in v0.1.2).

### 12. `Review Gate - Gemini Brief for Literature Gap Memo.md` (2026-11-03)
**Purpose:** Task brief for Gemini to produce `Literature Gap Memo.md` (gate Part B).
**Main ideas:**
- Four questions: what is already published, what is the contribution, which identification strategy is credible, and what additional data would help.
- Tasks: search the offline corpus, search outside it, then write the memo.
- Rules: no fabricated citations, no raw ACLED rows, no modelling, a $1 cost ceiling, and Gemini works in its own branch.
- **The memo it asks for does not exist in `notes/` yet.**

### 13. `Pipeline Review - Reproducible Research Framework after Phase A.md` (2026-11-03)
**Purpose:** Claude's review of whether `reprokit` v0.2.0 and `compound-shocks-panel` met the 15 framework goals.
**Main ideas:**
- Strong on byte-for-byte reproducibility, hash-pinned downloads, the harmonization gate and verification-state labels.
- Weaker on four points. `validate` checks structure, not truth. Hand-copied numbers drift between documents. There is no cheap smoke test. A newcomer gets no map.
- Adding a second source type needed core edits.
- Ten recommendations for `reprokit` v0.3, three open questions, and a short note on fit for Phase B.

### 14. `RCT_replication_gemini_brainstorm.md` (2026-11-05)
**Purpose:** Brainstorm on replicating geocoded RCTs and extending them with satellite proxies, then transporting the results.
**Main ideas:**
- Four steps: replicate; add covariates and proxy outcomes (night lights, NDVI); test whether proxies can detect the effect without panel survey data; project impacts to new locations.
- Related ideas: a Bayesian hierarchical model across several RCTs with a leave-one-site-out check, and ACLED/displacement as a forecast target.
- Gemini's first response ties these to:
  - DML and surrogate indices;
  - LIML or Fuller for many weak proxy instruments;
  - causal transportability;
  - Meager-style hierarchical shrinkage;
  - JIVE vs leave-one-site-out;
  - Bai-Ng targeted-predictor factor models and FAVAR.
- Aaron then asked for a frank critique: do the ideas fit together, is there enough RCT panel data, and how well does it map to transfer learning for conflict and disaster settings.
- **The transcript ends there. Those three follow-up questions have no answer yet.** The final "Response" block only repeats the questions.
- Every citation and claim in it is unverified Gemini output.

### (+1) `Brainstorming Transcript - Transferability of Crisis Interventions.md` (branch `gemini/transferability-brainstorm`, Oct 14-20; added to this report 2026-11-06)
**Purpose:** A 65 KB, multi-round Gemini dialogue that turns a rambling theme (can crisis-response lessons and methods transfer from disasters to conflict?) into three research questions, then into three small empirical sprints. It is the direct precursor of the RCT brainstorm (#14) and the source of Project 03's structure.
**Main ideas:**
- Your framing, in your words: judge transfer by same sign and similar magnitude, not exact effect size; the audience is development and humanitarian practitioners, not econometric theorists; hold the intervention fixed (cash, index insurance) and treat the crisis context as the thing being matched.
- Three research questions: (1) welfare, market and survival effects of safety nets in disaster vs conflict, mediated by supply bottlenecks and expected conflict duration; (2) delivery rails across the state-capacity spectrum (Colombia vs Haiti/Venezuela); (3) whether satellite and conflict covariates can serve as a similarity index to predict out-of-sample transfer.
- A literature audit and a synthesis with the Ground Truth plans, listing what is new ("inverse matching", a geospatial evaluation matcher, market inelasticity as a failure mode) and what is pruned (agronomy, chatbot, heterodox strand, firm recovery, math thesis).
- A methods section: Bayesian hierarchical models that relax exchangeability with a context-divergence variance penalty, situational-proximity CAR priors, and dynamic or fuzzy Bayesian networks.
- A practical pivot to three 2-4 week sprints: (1) Somalia fused panel (the origin of the compound-shocks pilot), (2) geospatial evaluation matcher (geocode 15-20 cash and insurance trials, attach satellite and ACLED covariates, check common support), (3) price transmission under checkpoint blockades.
- Companion files on the same branch: `projects/empirical_sprints/` (overview plus three sprint plans) and an `academic-rag-model` doc of meta-reflections on brainstorming. Those are outside `notes/` and I did not read them in full.
- The status line still says "In Progress", but the file ends with "operational handoff complete".

---

## 2. Grouping by project

Six groups: two are cross-cutting overviews or idea pools (A, E), and four are project clusters (B, C, D, F). A file's *primary* group is where I propose it lives; "also touches" is what the Cross-Group Connections documents track.

| Group | Files (primary) | Also touches |
|---|---|---|
| **A. Program overview & strategy** (multi-project) | Ground Truth (`.md`, `.html`), Ground Truth 3R Revision | Every other group |
| **B. Compound shocks panel** (Project 02) | Somalia Three-Shock, Data Sources, Sudan Data Sources, ACLED Terms, Pilot Scope Realignment, Data Audit Review, Gemini Brief | Data Sources: Projects 01/03/06. Somalia: Project 04 verification layer. Brief: group C |
| **F. Reprokit reproducibility framework** (added after your request; Project 04 and the replication goal) | Pipeline Review (moved here from B), plus the new `Reprokit Project Summary.md` covering the spec, plan, v0.3 handoff, CHANGELOG and tracker items | Group B (the pilot), group D (replication), group C (taxonomy hooks) |
| **C. Literature pipeline & evidence map** (Project 01) | Pitch, `lit_review.md` | Pitch: Project 04 and CTL. `lit_review.md`: the Gemini Brief runs this pipeline |
| **D. RCT replication & transportability** (new; Direction III, Project 03) | RCT brainstorm, Transferability brainstorm transcript | Group B (ACLED/displacement forecasting, satellite proxies), group C (which RCTs have geocoded panel data), group A |
| **E. Exploratory methods & heterodox ideas** | Research Ideas.docx | Group A (heterodox open question), group B (agent-based models), group D (spectral bias vs DML) |

Why the borderline calls:
- **Data Sources** is a program-wide survey, but its detailed content is Somalia-first, so it sits in B.
- **Pitch** serves Projects 01 and 04 equally. It sits in C because its main product is the literature pipeline.
- **Research Ideas** is left on its own, because most of it matches no active project. It is closest to Project 05 and the "heterodox strand" in the Ground Truth plan.

---

## 3. Proposed folder structure

Numbered prefixes keep the order stable. Everything under `notes/` stays within the same repo path, so only relative paths change.

```
notes/
├── 00_overview-and-strategy/
│   ├── Ground Truth - PhD Research Plan.md          (+ .html)
│   ├── Ground Truth - PhD Research Plan - 3R Revision.md
│   └── Cross-Group Connections.md                    ← new
├── 01_compound-shocks-panel/                         (Projects 02 + 04)
│   ├── case-study/
│   │   └── Somalia Three-Shock Case Study.md
│   ├── data-sources/
│   │   ├── Data Sources - Climate Displacement Cash Conflict.md
│   │   ├── Sudan Data Sources - Portability Check.md
│   │   └── ACLED Terms - Redistribution Findings.md
│   ├── review-gate/
│   │   ├── Pilot Scope Realignment - Exploratory Review Gate.md
│   │   ├── Review Gate - Data Audit Review.md
│   │   ├── Review Gate - Gemini Brief for Literature Gap Memo.md
│   │   └── Literature Gap Memo.md                    (to be produced by Gemini)
│   └── Cross-Group Connections.md                    ← new
├── 02_literature-and-evidence-map/                   (Project 01)
│   ├── Pitch - Structured Literature Taxonomy and Research Hub Extension.md
│   ├── lit_review.md                                 (consider renaming: "Literature Pipeline - Early Prototype.md")
│   └── Cross-Group Connections.md                    ← new
├── 03_rct-transportability/                          (Direction III, Project 03)
│   ├── Brainstorming Transcript - Transferability of Crisis Interventions.md
│   ├── RCT_replication_gemini_brainstorm.md
│   └── Cross-Group Connections.md                    ← new
├── 04_methods-and-exploratory-ideas/
│   ├── Research Ideas.docx
│   └── Cross-Group Connections.md                    ← new
├── 05_reprokit-reproducibility-framework/            (spec, plan and status live in ../docs/superpowers)
│   ├── Pipeline Review - Reproducible Research Framework after Phase A.md
│   ├── Reprokit Project Summary.md                   ← new
│   └── Cross-Group Connections.md                    ← new
├── application_essays/                               (unchanged)
├── processed_outputs/                                (unchanged)
└── _Notes Reorganization Report.md                   (this file; can be deleted once the move is done)
```

The six `Cross-Group Connections.md` files (A to F) are already written in these folders on the `claude/research-notes-reorg` branch. The originals have not been moved.

Naming suggestions, all optional:
- `RCT_replication_gemini_brainstorm.md` is the only underscore-style name. A matching name would be `RCT Replication and Transportability - Gemini Brainstorm.md`.
- Where a file's name implies a stage ("Review Gate - ..."), the subfolder already says it, so you could shorten the names later.
- If `Research Ideas.docx` is converted to Markdown, it becomes searchable.

---

## 4. Per-group connection documents

Each group has one `Cross-Group Connections.md` that pulls the relevant ideas out of files that belong to several groups, so you don't have to reopen the big shared documents.

- [`00_overview-and-strategy/Cross-Group Connections.md`](00_overview-and-strategy/Cross-Group%20Connections.md)
- [`01_compound-shocks-panel/Cross-Group Connections.md`](01_compound-shocks-panel/Cross-Group%20Connections.md)
- [`02_literature-and-evidence-map/Cross-Group Connections.md`](02_literature-and-evidence-map/Cross-Group%20Connections.md)
- [`03_rct-transportability/Cross-Group Connections.md`](03_rct-transportability/Cross-Group%20Connections.md)
- [`04_methods-and-exploratory-ideas/Cross-Group Connections.md`](04_methods-and-exploratory-ideas/Cross-Group%20Connections.md)
- [`05_reprokit-reproducibility-framework/Cross-Group Connections.md`](05_reprokit-reproducibility-framework/Cross-Group%20Connections.md) and [`Reprokit Project Summary.md`](05_reprokit-reproducibility-framework/Reprokit%20Project%20Summary.md)

---

## 5. Things to know before moving files

1. **Path references will break.** Several files point at each other by name or by "in this folder": the Gemini Brief says to read `Review Gate - Data Audit Review.md` "in this folder", the 3R Revision's source context and the Data Sources header link to `Ground Truth - PhD Research Plan.md` and `Somalia Three-Shock Case Study.md`, and the Ground Truth plan says "kept as ... in this folder". Pilot Scope Realignment links the `docs/superpowers` specs by absolute path.
2. **Gemini's output path is fixed to `notes/`.** The brief tells Gemini to write `notes/Literature Gap Memo.md`. The memo now exists, committed as `d6915e4f` on branch `gemini/compound-shocks-lit-memo`, but it is not on `main` yet. It was not among the 14 files summarized above. See the chat answer or read it on that branch. If you reorganize first, update the brief, or move the memo afterward.
3. **Other branches write into `notes/`.** The worktree list shows live branches for this area (for example `claude/compound-shocks-*`, `gemini/*-lit-memo`, `codex/acled-source-documentation`). Moving files on main while those are open means merge conflicts for rename vs edit. Better to do the move after they land.
4. **Landing status (2026-11-06):** the RCT brainstorm is on `main` (`2d75cba4`). The Literature Gap Memo, the transferability transcript and this report are being landed through `docs/WORKTREE_LANDING.md`.
5. **Several files are Gemini-generated and unverified**: the RCT brainstorm's citations, `lit_review.md`, and the dataset claims in Data Sources and Sudan Data Sources (the Sudan note says it was verified against live repositories, but I did not re-check it).
6. **Staleness to resolve rather than move blindly:**
   - Ground Truth (original) still lists the chatbot pilot as Project 03 and Direction IV. The 3R Revision drops both.
   - Somalia's timeline (Late Sep to December) predates the Phase A/B gate.
   - Pilot Scope Realignment says the Somalia panel runs to 2023-08. The audit shows 2021-01 to 2025-10.
   - Data Sources lists "Run the preliminary regression model" as a November next step, which the gate has put on hold.
   Consider adding a one-line "superseded by" note rather than deleting any of these.
