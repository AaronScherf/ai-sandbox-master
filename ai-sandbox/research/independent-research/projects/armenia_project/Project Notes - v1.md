# Armenia evidence map: project notes (v1)

*2026-11-24. Working notes behind the [Call Brief - v1](Call%20Brief%20-%20v1.md). Nothing here is a verified finding. Items marked **(verify)** are from memory or inference and need a source check before they go in a proposal. No literature is cited in this note on purpose; add citations only after a registry lookup (see the repository's citing rule). This repository is public: keep client names, fees and any client data out.*

## 1. The idea in one paragraph

A former colleague runs a nonprofit foundation in Armenia working on education and health. She wants an evidence map and an evidence gap map: what development interventions have been tried in Armenia, what they achieved, and which approaches look promising but lack evidence. Phase 1 builds that with the existing discovery and literature pipelines, adds a context dataset and dashboard, and ends with an outline for Phase 2. Phase 2 would test the evidence-transport approach (using evidence from other settings to design new Armenian programs). Phase 1 should be useful even if Phase 2 never happens.

## 2. Parts and sequence

| Part | Purpose | Weeks | Depends on |
|---|---|---|---|
| 1a Scoping sprint | Settle the question and rules, prove the chain on one sector slice, measure recall | 1 to 4 | Her answers to the call questions |
| 1b Full map | Both sectors, grey literature, interactive maps, promising-approaches memo | 5 to 10 | Checkpoint after 1a |
| 1c Context dashboard | Fused dataset of background data, interactive map and dashboard | 3 to 10 (parallel) | Geography and years agreed in 1a |
| Transport preview | Outline of a Phase 2 transport assessment for 2 or 3 interventions | 9 to 10 | Promising list from 1b, context data from 1c |

Feedback: end of week 4, mid week 8, and a final walkthrough. The two-to-three-month window is tight but plausible only if 1a stays to one sector slice and her review turnaround is days, not weeks.

## 3. What the maps are

- **Evidence map.** A matrix of interventions (rows) against outcomes (columns). Each cell shows which studies exist, and optionally their design and a confidence rating.
- **Evidence gap map.** The same matrix read for emptiness: cells with no or only weak evidence are the gaps.
- **Two layers.** Layer A holds Armenian studies. Layer B holds studies from comparable countries. The comparison is the main analytic idea:

| Evidence elsewhere | Evidence in Armenia | Reading |
|---|---|---|
| Strong | None | Candidate for transport assessment or a new trial (Phase 2 material) |
| Strong | Some | Check consistency; likely safe to build on |
| None or weak | None | True gap; not necessarily a priority |
| None or weak | Some | Local innovation worth documenting |

"Comparable" needs a defined rule (section 5.3), not a hand-picked list.

## 4. What exists, and how ready it is

Based on the status docs read on 2026-11-24. Re-check before quoting any of this to her.

| Component | State | What Armenia needs from it |
|---|---|---|
| Journal discovery (OpenAlex, Unpaywall, arXiv, manual-download list) | Shipped, validated on real runs | Works for papers. Paywalled items need manual download. Never run on grey literature. |
| Transcription to Markdown | Shipped | PDFs from agencies and ministries are untested. Armenian or Russian text is untested. |
| Literature extraction (two passes, checker, confidence tiers) | Landed. Precision about 0.88 (A+B) on a 67-paper corpus. Recall unmeasured. | Core of the coding step. Recall must be measured here. |
| Term selection / 3ie facet refinement | Paused 2026-11-11 after a failed trial; redesign not started | Do not wait for it. Use the existing vocabulary with owner review (see 5.5). |
| Applicability gate (is this paper evidence a 3ie facet can describe?) | Not designed | Needed, because only about 20 to 25 of 67 papers in the existing corpus were impact evaluations. Build a minimal version for this project. |
| Gap analysis with recall probe | Slices 1 and 2 landed | Useful for "no evidence in corpus" verdicts, with the recall caveat. |
| `evidence-map` repo (reprokit evidence kind) | Created, empty, protocol proposed | Provides manifest, `[@id]` claim checks, add or remove sensitivity. No per-source taxonomy field, so an export interface is needed. |
| Discovery loop for external works | Not built | Not needed for Phase 1 if search is run by the discovery tool directly. |

Honest framing: this would be the first end-to-end run of the whole chain on a real client question. That is a strength for learning and a risk for promises.

## 5. Draft methodology

### 5.1 Question and scope
- Population and setting: Armenia. Whether to include displaced populations or specific regions is a question for her.
- Sectors: education, health. Slice for 1a chosen after the call.
- Question types: what interventions, what outcomes, what design, what strength, what context.

### 5.2 Definition of evidence (decide with her)
Tiers to propose, since "evidence" varies in what it can claim:
1. Causal evaluations (randomised or quasi-experimental).
2. Other quantitative evaluations (before-after, cross-sectional with a comparison).
3. Systematic reviews and meta-analyses touching Armenia.
4. Qualitative studies and process evaluations.
5. Grey literature and program reports, marked by whether they report outcomes.

Keep the tiers visible on the map, and never present tier 4 or 5 as effect estimates.

### 5.3 "Comparable countries" rule
Define by stated criteria rather than a list. Candidate criteria: income group, region, health or education system features, and conflict or displacement exposure. Likely candidates for review: neighbouring and former-Soviet countries **(verify list)**. Record the rule in the protocol so it can be changed and the map re-cut.

### 5.4 Search
- Registries and repositories of evaluations and reviews (3ie, J-PAL, World Bank, others) **(verify which cover Armenia)**.
- OpenAlex for bibliographic search and citation expansion.
- Grey literature from international agencies, the government and NGOs. Manual curation is likely needed, since the discovery tool targets journals.
- Her own documents.
- Log every search: provider, exact query, date, result count.
- Languages: English first. Armenian and Russian sources are a pilot item, not a promise.

### 5.5 Screening, classification, extraction
- Deduplicate by DOI, then OpenAlex ID, then normalised title and year.
- Screen in two steps: title and abstract, then full text. The model proposes, I review, with exclusion reasons recorded.
- Minimal applicability gate for this project: study design is a prior, then a content check on whether the work evaluates or measures a named intervention. Ambiguous cases go to review.
- Code each included study to intervention and outcome terms (3ie vocabulary, already seeded locally), plus population, setting, design, and a confidence rating.
- Add context descriptors now, since they cost little and Phase 2 needs them: delivery channel, scale, setting (urban or rural, region), timing, and whether outcome data or microdata are available. Distinguish "not reported" from "not checked".
- Each coded fact keeps a source locator. No full text or bulk quotation goes into any shared output.

### 5.6 Quality and recall
- Precision: sample-based paper-level check against the paper (the method used in the Phase 1 quality gate of the literature work).
- Recall: seed a known set of relevant studies (from her list and any existing reviews **(verify they exist)**), then test whether search and screening found them. Report the figure, and say so on the gap map where recall is low.
- Gap verdicts read "none found in the searched sources", not "none exist".

### 5.7 Outputs
- Evidence map and gap map in two layers, filterable by sector, intervention, outcome, design and confidence.
- Interactive version plus a static report version.
- Memo on promising approaches, each with: what the evidence shows, how strong, where, and what is missing.

## 6. 1c: context dataset and dashboard

**Purpose.** Ground the evidence in Armenian conditions, and build the data base a later transportability analysis would need.

**Design.** One linked dataset at the finest reliable geography (probably province, with the capital separate **(verify)**) by year, with a data dictionary and a source and licence for every column. Interactive map and dashboard on top. Evidence records link to places where studies report one.

**Candidate sources, all to verify for access, coverage, years and licence:**

| Domain | Candidates |
|---|---|
| Population and living conditions | National statistics office tables; household living-conditions survey |
| Health | National health survey (a DHS-type survey exists **(verify years)**); WHO country data; ministry of health statistics; burden-of-disease estimates |
| Education | Ministry of education statistics; international learning assessments Armenia took part in **(verify which and when)**; UNESCO institute data |
| Economy and poverty | World Bank indicators; national poverty statistics |
| Attitudes and services | Regional social surveys **(verify)** |
| Geography and environment | Administrative boundaries; population grids; rainfall and vegetation indices; nighttime lights |
| Displacement and conflict | UN and humanitarian datasets. Conflict-event data carries licence limits: never commit aggregates, and check terms before showing any |

**Rules.** Provenance column on every field. Missing data shown as missing. Nothing client-private goes in a public repository. Dashboard hosting and who maintains it afterwards are open items.

**Risks.** Sub-national data may be sparse or suppressed. Series may break across survey rounds. A fused dataset can look more precise than the sources allow, so show source and year on every value.

## 7. Transport preview (outline only)

**What it is.** For 2 or 3 interventions chosen from the "strong elsewhere, none in Armenia" cells, a short document that sets out what a Phase 2 assessment would need. It makes no effect predictions.

**Selection criteria (proposed).** Strong or consistent evidence elsewhere. Plausible fit with the foundation's activities. Outcome measured in a way that can be compared. Context data available from 1c.

**Per intervention, the outline covers:**
- The intervention as actually delivered in the source studies.
- Outcome definitions and scales that would have to be harmonised.
- Source and target context differences that might change the effect (an explicit list of suspected effect modifiers, with the data to check each).
- What Armenian data exist and what would have to be collected.
- Study designs that could test transfer (for example a small local pilot or replication).
- What result would count as the approach not transferring.

The methodology gets built out separately before Phase 2. Until it has been tested on real cases, describe it as a method in development.

## 8. Risks and how to handle them

| Risk | Handling |
|---|---|
| Recall unknown, so the gap map overstates gaps | Measure recall in 1a, report it, label gaps "none found in searched sources" |
| Little Armenian impact evidence, so the map is mostly empty | Say so early; the two-layer design still gives a useful "borrow from elsewhere" view |
| Grey literature outside what the pipeline was built for | Pilot in 1a; budget manual curation in 1b |
| Armenian or Russian sources mishandled | Pilot a small set; state coverage openly |
| Paywalled full text | Manual-download list; ask her organisation about library access |
| Scope grows across two sectors and 1c | Gate 1b on the week-4 checkpoint; one sector slice in 1a |
| Pipeline defects found on first real use | Reserve time; note anything changed in the repository's status docs |
| Paid model use exceeds budget | Subscription runs by default; get approval before any step estimated over $1 |
| Public repository leaks client details | Keep names, fees and client data out; review before any push |

## 9. Open decisions for me (not for her)

1. Fixed-scope proposal, or 1a first with 1b contingent. The brief assumes the second.
2. How much of 1c to build if budget is tight (data inventory only, or the full dashboard).
3. Where Armenia project code and data live (this folder, or a private repository), given the public monorepo.
4. Whether `evidence-map` (public) is reused as the manifest, or a private copy is made for client material.
5. Who reviews classification: me alone, or a second reviewer (she, her staff, a colleague).

## 10. To verify before the proposal is sent

- Which evidence registries cover Armenia, and whether any existing reviews can seed the recall test.
- Years, coverage and licences of every source in section 6.
- That the 3ie vocabulary covers education and health outcomes at the grain needed.
- Whether the discovery tool can retrieve the grey-literature sources she cares about.
- Any pre-existing 3ie or other evidence map covering Armenia or the region, so the work builds on it.
- The status of the literature redesign and the `evidence-map` manifest interface at the time of the proposal.
