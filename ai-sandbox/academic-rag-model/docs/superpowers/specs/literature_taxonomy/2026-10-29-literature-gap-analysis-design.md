# Literature taxonomy: stage 5 gap analysis, design

Date: 2026-10-29. Status: draft for owner approval. Scope: `agent/literature` only (the journal-article pipeline). Refines
section 6 "Stage 5" of [the umbrella spec](2026-10-15-literature-taxonomy-pipeline-design.md); where they differ, this
document wins for stage 5. Does not touch the concept graph, notes or econ-new.

## 1. Intent

The owner will ask research questions of the form "has anyone studied *intervention X* on *outcome Y* in *country Z*?"
and needs an answer that is honest about what the corpus can and cannot say. Stages 2 to 4 give a database of 64 papers
and 521 tier A/B facts (`research/literature_db/literature.sqlite`, local only). Stage 5 turns a question into facet
constraints, finds the papers that match, and reports one of a fixed set of verdicts with the coverage numbers and the
evidence behind it. Stage 6 (proposal support) later consumes the report.

The point is a defensible "tried / not tried / unknown", not a recommendation. A confident wrong "no evidence" on a
corpus this small is the failure to design against.

## 2. Goals, non-goals, anti-goals

Goals
- Deterministic, reproducible verdicts over the db: same db and same constraints give the same report.
- Hierarchy-aware matching, with an explicit, rule-based notion of "adjacent context".
- A free-text front door (a task card) that yields the same constraints a user could type.
- Every report states what it did not measure.

Non-goals (slice 1)
- Any network call. OpenAlex coverage, live search, classification of external papers and the discovery queue (slice 2).
- OR or NOT constraints ("vouchers or cash"); a constraint set is an AND, like `db query`.
- Changing `db query` / `cluster define` behaviour.
- Proposal text, ranking of gaps by importance, or any score that merges direct and adjacent evidence.

Anti-goals (a failure even if it technically works)
- A percent-complete claim for a topic.
- A term chosen silently when the phrase did not resolve to exactly one term.
- A verdict that reads "no evidence found" without saying it covers the corpus only (slice 1).
- Paper quotes or 3ie term text leaving the machine (no Artifact in slice 1, no committed report).

## 3. Slices

| Slice | Contents | Network | LLM |
| --- | --- | --- | --- |
| 1 | constraints, resolution, direct and adjacent matching, corpus coverage, verdict, report; optional free-text card | none | none in the core; the card is optional |
| 2 | OpenAlex recall probe, live search with classification, `found externally` verdict, discovery queue Artifact | OpenAlex | classification card |

Slice 1 is specified fully here. Slice 2 is specified at the level needed to keep slice 1's interfaces compatible
(section 8) and gets its own plan.

## 4. Slice 1 design

### 4.1 Entry points

Package `agent/literature/gap/` (module split is the builder's call). New subcommands on the existing CLI, run from
`ai-sandbox/academic-rag-model/` (names are a proposal):

```
python -m agent.literature gap run --run-id g1 --where intervention="cash transfers" --where countries=SO [--pick intervention=<term_id>]
python -m agent.literature gap question "free text" --run-id g1     # writes the constraint card
python -m agent.literature submit g1                                # validates the filled card, writes constraints.json
python -m agent.literature gap run --run-id g1                      # no --where: reads that run's constraints.json
```

Amended during planning: there is no `gap submit`. The existing `submit RUN_ID` dispatches by run stage, so the card
goes through it like every other card and prints `next: python -m agent.literature gap run --run-id g1` when it is
applied. Constraints come from `--where` or from the card's `constraints.json`, and both feed one pipeline. Global options (`--index-root`, `--vocab-dir`)
behave as for the other subcommands.

### 4.2 Constraints and resolution

A constraint is `{facet, value}` with a facet from `cluster.FACETS` (the six record facets plus `countries`), the same
shape `cluster.parse_constraint` produces. Repeated constraints on one facet must all match (a paper needs both), as in
`cluster define`.

Resolution of `value` for vocabulary facets:
1. Exact term id, label or alias (the lookup `cluster._matcher` already does through `Vocabulary.find`) resolves to one term.
2. Anything else does not resolve. The run **stops** and writes `candidates.json` in the run directory: up to 8 ranked
   candidates per unresolved constraint, from normalized token overlap against label, aliases and definition. Each
   candidate shows term id, label, level (depth in the tree), child count, and how many corpus papers it would match as
   a direct constraint. Ranking is lexical; no model.
3. The user re-runs with `--pick facet=term_id`, or the card supplies the term. The report records each resolution as
   `resolved from '<phrase>' by user|card`.

Country values are ISO-3166 alpha-2 codes and validated with `vocab.is_country`; a name that is not a code goes through
the same stop-and-pick, with candidates from a country-name lookup.

A term with the same label in two tree positions is a candidate for each position, never merged.

### 4.3 Direct matches

A paper is a **direct** match when every constraint matches one of its tier A/B facts. A fact matches a vocabulary
constraint when its term id is the resolved term or a descendant of it (`_ancestors`, as in `cluster._matcher`). The gap
code matches **by term id only**, so that two terms with the same label in different tree positions stay distinct
(4.2), and so that the "would match N papers" count on a candidate equals what the run then finds. `cluster._matcher`
also accepts a fact whose normalized label equals the term's label; the gap matcher keeps that label clause only for
facts with no vocabulary id (`proposed:` values, see 4.5). It reuses the term lookup and ancestor helpers, not the
label clause, and `db query` / `cluster define` are left unchanged. On the manual smoke run the builder compares direct
counts from the two matchers and records any difference in the status doc. Tier C facts, excluded papers
(`RecordStore.ids()` omits them) and papers with no record never appear.

Caveat stated in every report: facets are per paper. A direct hit means the paper has all the facts; it does not prove
the paper links, for example, that intervention to that outcome, since they may come from different arms or results.
The evidence list prints each paper's results (claim and direction) so the owner can check.

### 4.4 Adjacent matches

Relaxable constraints are those on `intervention`, `outcome` and `countries`. Sector, population, study design and data
source constraints are never widened.

A paper is **adjacent** when it is not direct and there is exactly one relaxable constraint `c` such that the paper
matches every other constraint exactly (descendants included) and matches the widening of `c`:
- `intervention` or `outcome` term T: the other children of T's parent, each with its descendants. T's own subtree is
  already direct. A term with no parent, or whose parent is a top-level grouping (the groupings are the sector-like
  roots, which the vocabulary refuses as facts), cannot be widened: its siblings would span a whole bucket. Grandparent-
  level matches are not adjacent. The label states the sibling count so a wide widening is visible.
- `countries` code: any other country in the same UN M49 subregion, from a committed table
  `vocab_data/country_subregions.yaml` (ISO alpha-2 to subregion name; public UN standard, provenance noted in
  `vocab_data/README.md`). A country absent from the table cannot be widened, and the report lists it.

Each adjacent hit carries one label per qualifying relaxation, for example
`different outcome (sibling: <label> <- <label>)` or `different country (same subregion: <subregion>)`. A paper adjacent
through two different single relaxations carries both labels. A single-constraint question may be relaxed (its sibling
terms are then the adjacent set).

Papers that are neither direct nor adjacent but match at least one constraint exactly are **partial matches**: reported
with how many constraints they match exactly (a widened match does not count), capped at 10 by that count then year,
under a heading that says no verdict applies. A paper matching none is omitted. There is no merged score. With a single
constraint the partial list is empty by construction.

`different method`: if the question constrains `study_design`, a paper that matches every other constraint exactly and
fails only the design constraint is listed as `different method`. It is not adjacent, and it is not also listed as
partial. A paper that is adjacent on one constraint and also fails the design constraint is a partial match.

### 4.5 Coverage section (offline)

From the db and sidecar files only:
- Eligible paper count in the db, excluded count (`_excluded.json`), eligible-without-record count, open tier C fact
  count. The builder finds where each already lives (the `status` and `tiers` commands report them) and reuses it.
- For direct plus adjacent papers: distribution by study design, by country, year range, and a tally of result
  directions.
- Thin flag: fewer than 3 direct papers.
- **Blind spots that make a "no evidence" less certain**, each a count with the paper ids, never folded into the verdict:
  - Papers with a `proposed:` (non-vocabulary) fact in a constrained facet. They match only on exact normalized label,
    and the report lists "N papers have proposed values in <facet>; they may cover this question under wording the
    vocabulary lacks".
  - When a `countries` constraint is present: eligible papers with no country fact, and papers whose geographic scale is
    `multi_country` or `global` (scale is in the record; the builder checks whether the db carries it and, if not, reports
    only the no-country-fact count and notes the missing scale). Such papers are never counted as direct for a country.
- A fixed line: `Corpus completeness: not measured (needs OpenAlex, slice 2). The corpus was assembled by discovery, not
  sampled; absence here is not absence in the literature.`
- The db path, its modification time and paper count, so a stale db is visible. Matching always reads the db. If any
  record is newer than the db, the run still completes, with a warning at the top of the report and in the terminal that
  verdict and counts come from the db snapshot while the sidecar counts (excluded, no-record, open tier C) are current;
  exit code 0 either way.

### 4.6 Verdict (slice 1)

Fixed categories, decided only from the counts:
- `tried_directly`: at least one direct paper.
- `tried_adjacent`: no direct paper, at least one adjacent paper.
- `no_evidence_in_corpus`: neither.

`found_externally_not_in_corpus` is reserved in the enum and the report schema and is produced only in slice 2. The
report always prints the rule that fired, the counts, and the coverage section above.

### 4.7 Report

`research/literature_gap/<run-id>/report.json` and `report.md`, plus `candidates.json` while stopped. Local only and
gitignored (it holds quotes and 3ie term text); add the ignore entry with the code. `report.md` is rendered
deterministically from `report.json`; no model writes any of its text. Contents:
1. The question as asked and the resolved constraints (phrase, term id, label, level, resolved by).
2. Verdict, rule, counts, caveats (including the per-paper facet caveat).
3. Coverage (4.5).
4. Evidence: per paper, `direct` or `adjacent` with label(s), title, year, the matching facts with tier, and results with
   direction. Quotes appear only if the owner passes `--quotes`; the default prints claim and direction only.
5. Partial matches and different-method papers.

`report.json` carries a `schema_version`, and the same fields slice 2 will extend (an `external` section, null in slice 1).

### 4.8 Free-text card (optional front door)

`gap question` writes one task card using the shared card layer, following the pattern of `annotate`/`synthesize`. The card
holds the question, the vocabulary listing (grouping levels for lists over 150 terms, as other cards do) and a lexical
candidate shortlist per facet computed from the question text. The agent returns constraints:
`{facet, term_id | country code, phrase}` plus a list of phrases it could not map. `submit` bounces a gap card with a term
that is not in the named facet's vocabulary, a facet outside the list, a country that is not a valid code, or no
constraint at all. It does not need quotes. Unmapped phrases are shown to the owner and the run proceeds only with the
mapped constraints, with the unmapped phrases printed at the top of the report. The card route needs no API calls;
`--driver api` is not offered for this stage in slice 1.

## 5. Testing

Everything uses an invented corpus; no paper text, no 3ie text, no network. Tests build, in a temp directory, a db (or the
records it is built from) with ids like `paper-a`, titles like "Study A", placeholder quotes, a ~20-term synthetic
vocabulary tree with aliases, and a four-country toy subregion table. Files: `tests/agent/literature/test_gap_*.py`.

Known-answer cases: a leaf matching a parent constraint is direct; one adjacent case each for intervention, outcome and
country; two relaxations needed gives partial, not adjacent; a root term cannot be widened; a country missing from the
table is reported unwidenable; an unresolved phrase stops with ranked candidates and the right counts, and `--pick`
completes the run; an unconstrained facet matches anything; tier C facts, excluded papers and papers with no record are
absent; thin flagging at 2 vs 3 papers; each of the three verdicts; the completeness line is always present in the
rendered report; the stale-db warning; two same-label terms in different positions stay distinct; a depth-1 term is not widened; a proposed-value
paper and a no-country paper appear as blind spots and not in the verdict; `different method` vs partial. Properties: an adjacent paper is never direct; the verdict depends only on the
counts. Card tests: bounces for unknown term, wrong-facet term, invalid country, empty constraint list. Existing
`db query` and `cluster define` tests must pass unchanged.

A manual run against the real db is a smoke check, not a test; its counts (never text) go in a status doc,
`docs/status/literature/`.

## 6. Guardrails

- No API calls in slice 1. Slice 2 follows the umbrella spec: warn and get a go-ahead before any paid call over $1; default
  to the subscription route (the owner relays cards to Antigravity).
- No Artifact in slice 1. This is a deliberate exception to the academic-rag-model default (an Artifact for every human
  decision): the only decision is one term pick per ambiguous phrase, and the candidates would publish 3ie term text,
  whose reuse terms are unknown, and the evidence would publish quotes, to a hosted page.
- Nothing from `research/` is committed; the builder commits code, the synthetic fixtures and the committed subregion table.
- Worktree workflow throughout; only the owner lands on `main` after `land_branch check --full`.

## 7. Calls made without the owner (check these)

1. Subcommand and flag names (`gap run|question|submit`, `--pick`, `--quotes`) and the package name `agent/literature/gap/`.
2. Candidate list size of 8, partial-match cap of 10, and the thin-cell threshold of 3.
3. `different method` papers listed separately rather than as adjacent.
4. Evidence prints claim and direction only by default; quotes are opt-in with `--quotes`.
5. Report location `research/literature_gap/<run-id>/`.
6. A single-constraint question may be relaxed to its siblings.
7. UN M49 subregions as the country adjacency, from a committed table, over a non-geographic notion (such as income group).
8. The free-text card proceeds with the mapped constraints and prints the unmapped phrases; it does not stop on them.
9. Matching is by term id (labels only for `proposed:` facts), not the label clause `cluster._matcher` also uses.
10. `proposed:` facts and papers with no country fact or multi-country/global scale are reported as blind spots, never
    counted toward the verdict.
11. Terms whose parent is a top-level grouping are not widened.
12. Partial matches count exact matches only, need at least one, and exclude `different method` papers.
13. A stale db warns and still runs (exit 0).

## 8. Slice 2 (outline only; own plan)

- **Recall probe.** Search OpenAlex with a keyword query built from the resolved terms' labels (the db has no OpenAlex
  topic ids; a topic-id mapping is a later improvement that needs an extraction change). Take the top N by relevance
  (default 25, always stated). Match each to the corpus by OpenAlex id, then DOI, then normalized title, reusing the
  helpers in `agent/discovery/discover_journal_articles` and `agent/literature/backfill_years.py`
  (`resolve_work_by_doi`, by id, by title). Report "k of N in the corpus" with a Wilson 95% interval. Never a percent complete.
- **Classification.** Misses go on a task card that classifies each against the same constraints (direct, adjacent,
  neither), from OpenAlex title and abstract only. Prompt and validation follow the other cards.
- **Verdict.** The fixed set gains `found_externally_not_in_corpus`. Precedence when the corpus has adjacent evidence but
  an external paper is direct is to be settled in the slice 2 brainstorm; the report carries both until then.
- **Discovery queue.** Unseen hits go to an Artifact (checkbox, link, dismiss; decisions in its `db`), applied with
  discovery's own accept and reject functions. The queue holds only OpenAlex bibliographic metadata.
- **Tests.** Recorded OpenAlex fixtures with invented works; no network in tests. Cover dedupe by id, DOI and title, the
  Wilson interval, and an empty search.

## 9. Left to the builder

Module layout; how candidate ranking weighs label against alias against definition (lexical only); the exact JSON field
names; how sidecar counts (excluded, no-record, open tier C) are read; the ignore entry for `research/literature_gap/`;
how the shared matching functions are extracted from `cluster.py`/`db.py` without behaviour change; the committed subregion
table's contents (from the public UN M49 standard).
