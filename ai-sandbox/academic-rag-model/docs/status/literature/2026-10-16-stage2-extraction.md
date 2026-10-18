# Literature taxonomy stage 2: extraction (status)

Work in progress; Task 11 completes this file (suite counts, spec amendments, not-done list).

## Pilot 1 (2026-10-18): 12 papers, two independent passes each

- 24 cards filled by Antigravity (subscription). All 24 applied; 2 needed one resubmit after a bounce. No fabricated quotes got through.
- Vocabularies: real 3ie intervention (1,913 terms) and outcome (3,465) taxonomies plus a sector list, built from the saved
  taxonomy explorer pages into an ignored local directory (`research/resources/3ie/vocab`, usage terms unknown, never
  committed). Cards list only the grouping levels of any vocabulary over 150 terms. `study_design`, `population`,
  `data_source` and `hazard_type` are provisional starter lists committed in `vocab_data/`.
- The supplied 3ie material has no appraisal confidence criteria, so `appraisal` uses our own rubric (`extract-v2`).

### Double-pass disagreement

| Stage | Papers with at least one flag | Flagged items |
|---|---|---|
| Id comparison only | 11 of 12 | about 60 |
| Same-label ids merged (3ie lists the same wording under several branches) | 11 of 12 | 50 |
| Plus rules: parent/child agree, contained proposed wording agrees, "general population" ignored | 11 of 12 | 49 |

Cosmetic differences were a small share. What remains is real: different outcomes picked, one pass finding one result
and the other two, geography scale, sector, data sources.

### Decision: rules only for now; revisit

Rule-based closing is in `compare.py` (`_apply_rules`). It barely reduces the flags, so every paper still needs a person.
If the full run shows the same prevalence, expand to more elaborate methods:

1. An adjudication pass: the agent sees only the two disputed candidate facts with their verified quotes and rules which
   the paper supports (never the original extraction); resolved items are marked `auto_resolved`.
2. A third pass with majority vote on set facets, only for disputes adjudication leaves open.
3. Human review for the rest, plus a random audit (about 10%) of auto-resolved items to measure its accuracy.

### Other findings

- The index holds duplicate conversions of one paper under different file_ids (manual downloads); dedupe before a full run.
- Two papers (about 295 KB and 273 KB of text) exceed the one-card size cap and are skipped until chunking exists.
