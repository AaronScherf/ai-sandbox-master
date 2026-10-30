# Stage 5 gap analysis, slice 1 (offline): status

Date: 2026-10-29. Branch `claude/literature-gap-analysis`. Design: `docs/superpowers/specs/literature_taxonomy/2026-10-29-literature-gap-analysis-design.md`;
plan: `docs/superpowers/plans/literature_taxonomy/2026-10-29-literature-gap-analysis-slice1.md`.

## What shipped

`python -m agent.literature gap run|question` over `literature.sqlite`: stop-and-pick term resolution, direct and adjacent
matching (one relaxed facet, sibling or UN M49 subregion), corpus-only verdicts, coverage and blind spots, a local report
(`research/literature_gap/<run-id>/`, gitignored), and the optional free-text card (submitted with the existing `submit`).
No network, no LLM in the core. `db query` and `cluster define` are unchanged.

## Deviations from the spec

- The subregion table is `agent/literature/gap/country_subregions.yaml` (codes quoted: an unquoted `NO` parses as a
  boolean), not `vocab_data/`, because `load_vocab_dir` reads every YAML there as a vocabulary (TODO-0091). It holds no names.
- No `gap submit`: the card goes through `submit RUN_ID`, which prints the `gap run` command to run next.
- Candidates carry their ancestor path (found on the smoke run below).
- Test files are `test_lit_gap_*.py`; `--report-root` was added so a smoke run does not write into the main checkout.

## Smoke run on the real database (counts only)

Read-only against the main checkout's db and records; reports written to a scratch folder. Database: 87 eligible papers,
15 excluded, 8 eligible without a record, 83 open tier C facts; the db was not stale.

- "Unconditional Cash Transfers (UCTs)" names 7 terms (the same label under 7 branches of the 3ie tree). Only one has papers
  (5). Picking it: verdict `tried_directly`, 5 direct papers (equal to `db query --where intervention=<that id>`), 2 adjacent
  papers via sibling terms, no blind spots, years 2015 to 2026, not thin.
- "cash transfers" resolves to no single term; the candidates are "Labelled cash transfers" and "Conditional Cash Transfers
  (CCTs)" variants, none with corpus papers.

## Findings for the owner

- **Same label, many branches.** Matching by term id (spec 4.2: same-label terms are never merged) means a question about
  "unconditional cash transfers" matches only the branch copy the extraction happened to pick. A paper tagged with another
  branch's copy of the same concept is invisible to a direct match and would not be adjacent. A merge-by-label option, or
  canonical-term grouping in the vocabulary, is a decision for the owner before slice 2.
- Stop-and-pick fires often on this vocabulary. The ancestor path in the candidates makes the choice workable.

## Not built

Slice 2: OpenAlex recall probe, live search and classification, the discovery queue Artifact, the
`found_externally_not_in_corpus` verdict. Precedence of an external direct hit over corpus-adjacent evidence is open.
