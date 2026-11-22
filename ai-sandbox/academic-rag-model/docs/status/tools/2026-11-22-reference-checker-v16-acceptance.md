# Reference checker v16 acceptance (2026-11-22)

## Scope and evidence map

| Handoff requirement | Implemented behavior | Evidence |
| --- | --- | --- |
| Venue used as title | Compare parsed title with registered venue, or identify an italic venue before volume/DOI; route titleless. | Recorded Nziguheba and Kihara shapes; copied-ledger sweep. |
| Short title prefix | Whole-word prefix with at least two words counts as strong title agreement. | Recorded Lee shape; no title search. |
| Comparison prose | The "vs" comparison has no cited title. | Recorded Egger shape; no title search. |
| Trailing Markdown in DOI | Strip trailing Markdown and unmatched closers, retaining balanced parentheses. | Recorded DOI shape; copied-ledger sweep. |
| Adjacent links | Keep a DOI inside its link, including links followed by a colon or closing parenthesis. | Recorded slide-shaped links; copied-ledger sweep. |
| Quoted on purpose | Page decision is checked against note, DOI, and exact citation text; ledger suppresses that note only and reopens on changed text. | Recorded ledger tests for defect, second note, changed text, wrong note. |
| No note edits; no gate scope or v14/v15 changes | Only checker, ledger, page, tests and checker README changed. | Git diff review. |

## Copied-ledger sweep

The selection rule in v16 (tracked latest version of every Markdown file under `ai-sandbox/research/` containing a DOI; exclude plans and the unversioned Literature Gap Memo) yields **27 files**. Applying the same rule to the handoff commit `f75c7360` also yields 27, so the handoff's stated 24-file count does not match its selection rule. This run follows the stated rule and records all 27. The main ledger and cache were copied to a temporary directory; all raises wrote to that copy. No review decisions were applied.

**Totals:** 23 defects, 101 open items. No unresolved DOI rows. No title-search-unavailable rows remained in the final pass; the retry set was empty. All nine checker defects named in v16 section 1 are absent. The expected real wrong-link and quoted-review defects remain. The current Correction Log contributes 12 defects, and the manual-download list contributes 43 open items; these are left for human review.

| File under `ai-sandbox/research/` | Defects | Open items |
| --- | ---: | ---: |
| `independent-research/notes/00_overview-and-strategy/02_agenda-strategy-and-reviews/Humanitarian Development Nexus - Research Focus Analysis.md` | 0 | 1 |
| `independent-research/notes/00_overview-and-strategy/02_agenda-strategy-and-reviews/Research Presentation Narrative - Humanitarian Transportability Pipeline.md` | 1 | 1 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Claude Spot Check - v1.md` | 1 | 1 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Context Distance Cases - v1.md` | 2 | 2 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Correction Log - v2.md` | 12 | 6 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Fetch List and Priorities - v1.md` | 0 | 26 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Nexus Evidence Use Adversarial Scan - v1.md` | 1 | 1 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - RQ1 Knowledge Audit - v5.md` | 0 | 0 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - RQ2 Decision Space - v4.md` | 0 | 0 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - RQ3 Transfer - v6.md` | 0 | 0 |
| `independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Summary - v3.md` | 0 | 0 |
| `independent-research/notes/00_overview-and-strategy/04_documentation-probe-and-sources/Documentation Probe - Kenya Data and Replication Sweep - v1.md` | 0 | 1 |
| `independent-research/notes/00_overview-and-strategy/05_slides-and-talk/presentation_slides.marp.md` | 1 | 1 |
| `independent-research/notes/01_compound-shocks-panel/review-gate/Literature Gap Memo - Verification Review.md` | 5 | 1 |
| `independent-research/notes/01_compound-shocks-panel/review-gate/Literature Gap Memo - v2.md` | 0 | 0 |
| `independent-research/notes/02_literature-and-evidence-map/Literature Pipeline - Early Prototype.md` | 0 | 0 |
| `independent-research/notes/02_literature-and-evidence-map/Machine-Readable Literature Sources - Evidence Mapping and Trial Eligibility.md` | 0 | 1 |
| `independent-research/notes/03_rct-transportability/Follow-up - Data Availability and Transportability Critique.md` | 0 | 3 |
| `independent-research/notes/03_rct-transportability/ag-transport-grant-proposal/Feasibility Addendum - Trial Costs and Farming Base - v2.md` | 0 | 1 |
| `independent-research/notes/03_rct-transportability/ag-transport-grant-proposal/Project Summary and References - v1.md` | 0 | 1 |
| `independent-research/notes/03_rct-transportability/ag-transport-grant-proposal/Proposal Draft - v5.md` | 0 | 11 |
| `independent-research/notes/03_rct-transportability/ag-transport-grant-proposal/Reference Log - Four Searches - v4.md` | 0 | 0 |
| `independent-research/projects/compound-shocks/literature_review.md` | 0 | 0 |
| `independent-research/projects/data-fusion-toolkit/literature_review.md` | 0 | 0 |
| `independent-research/projects/systems-dynamics/literature_review.md` | 0 | 0 |
| `independent-research/projects/transferability/literature_review.md` | 0 | 0 |
| `journal-articles/needs_manual_downloads.md` | 0 | 43 |

Claude can seed the review page's `items` collection using the existing flattening of `python -m tools.reference_review list --status open` (the item's `subject_ids` and first `candidates` entry become `note`, `doi`, `mentions`, `registry`, `tier` and `reason`). Seed the new `defects` collection directly from `python -m tools.reference_review list --status defects`; use each card's `item_id` as its document ID. The page records `quoted` only as a decision; applying that decision writes the note-local ledger entry.

## Verification state

- Fixture tests: checker and ledger focused suite passed (141 passed, 1 skipped). The full chunked suite passed in 8 chunks (1165.4 seconds).
- Live copied-ledger sweep: completed as above. This is a one-time observation, not longitudinal evidence.
- Formal landing check: passed nine selected tool test files, reported no overlaps, and found no modified research notes for the citation gate. Landing remains subject to owner approval.
