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

## Verification and silver set (2026-10-19)

Instead of hand-reading every paper, facts were split three ways (`python -m agent.literature silver`):
88 facts both passes found (auto-accepted), 59 found by one pass only and sent to an independent checker pass
(`verify`, stage `verify`, 11 cards): 52 confirmed with a verified quote, 7 not confirmed.

Owner review (interactive Artifact): the 7 open facts and a random audit of 12 accepted facts.
- Audit: 11 of 12 correct, 0 wrong, 1 unsure ("administrative records" for county-level statistics). The automatic
  acceptance looks reliable on this sample, but the sample is small and one model family did both passes and the check.
- Open facts: the checker was right more often than not (2 wrong, 4 unsure, 1 correct on the owner's guess only; not
  accepted into the silver set).
- Recurring weak term: `data_source.administrative_records` appeared in 5 of the 19 reviewed items and is too vague
  (government statistics vs true administrative records vs sampling frames). Split or redefine it before the full run.

`gold/gold_set.yaml` is this silver set (12 papers, 138 expected values), not a hand-built gold set. Scores against it
are optimistic: facets from `eval` (pass a vs silver) were precision 0.96, recall 0.88, proposal rate 0.92 per record,
bounce rate 0.08, strict double-pass agreement 0.08 (1 of 12 papers fully agree). Recall of facts both passes missed is
unmeasured; only a small hand-built gold set would measure it.

## Verification summary (2026-10-19)

Full suite run per directory from `ai-sandbox/academic-rag-model/` with the shared venv, after the last code change:

| Directory | Result |
|---|---|
| `tests/agent` (includes 129 in `tests/agent/literature`) | 1770 passed |
| `tests/audio_generator` | 89 passed |
| `tests/core` | 570 passed |
| `tests/discovery` | 202 passed |
| `tests/pipelines` | 757 passed |
| `tests/resume_manager` | 271 passed |
| `tests/tools` | 230 passed |

No existing code or test files were edited except one assertion pinning the prompt version (`extract-v1` to `extract-v2`).
A first full run found a real clash: a bare `tests/agent/literature/test_store.py` collided with
`tests/agent/problem_corpus/test_store.py` when the whole agent tree ran. The literature test files now carry a
`test_lit_` prefix. Mutation checks for the quote matcher, validator and diff are recorded in the plan ledger.

## Not done

- Hand-built gold set (the committed gold file is a silver set); recall of facts both passes missed is unmeasured.
- The Warsame et al. check (paper not converted) and dedupe of duplicate conversions before a full run.
- A full run over all converted papers, and accepting or rejecting the 11 open vocabulary proposals.
- Stage 2b: interactive review page for proposed vocabulary terms.
- Chunked extraction for papers over the one-card size cap; table-image attachments.
- Adjudication or a third pass for real disagreements, if the full run shows the same prevalence.
- `api` subcommand handles extraction cards only, not verification cards.
