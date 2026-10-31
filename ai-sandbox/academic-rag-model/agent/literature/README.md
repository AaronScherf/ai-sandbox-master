# agent/literature

Stage 2 of the literature taxonomy: extract one structured, quote-verified study record per converted journal paper.
Design: `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md` (section 6, with
the 2026-10-18 amendment). Status and pilot results: `docs/status/literature/2026-10-16-stage2-extraction.md`.

The default route uses a subscription agent (Antigravity) and no paid API: this package writes task cards, the agent
fills them, this package validates the answers and writes records. Run everything from `ai-sandbox/academic-rag-model/`.

## Commands

Global options come before the subcommand: `--index-root` (default `research/`), `--vocab-dir` (a directory of
vocabulary YAML files layered over the committed ones in `vocab_data/`), `--work-root`.

```powershell
python -m agent.literature collect --run-id r1 [--double] [--file-id ID] [--redo]   # extraction cards, no API calls
python -m agent.literature bootstrap r1                    # the contract to give the agent
python -m agent.literature submit r1                       # validate filled cards, write records; bounced cards say why
python -m agent.literature verify --run-id v1              # cards that ask a checker about facts only one pass found
python -m agent.literature silver                          # per paper: agreed / confirmed / open fact counts
python -m agent.literature tiers                           # facts by confidence tier A/B/C; writes _tiers.json
python -m agent.literature remap                           # point facts at terms whose proposal was accepted or merged
python -m agent.literature cluster define NAME --where sector=<term> --where countries=SO   # papers of a review (tier A/B facts)
python -m agent.literature annotate NAME --run-id a1 [--limit 11]   # cards: contribution + limitation note per paper (--limit = a batch)
python -m agent.literature synthesize NAME --run-id s1     # cards: the review (chunks of up to 20 papers; --merge joins them)
python -m agent.literature render NAME                     # review.md + bibliography.md under research/literature_reviews/NAME/
python -m agent.literature db build [--floor B]            # rebuild research/literature_db/literature.sqlite from records, tiers, annotations, clusters
python -m agent.literature db matrix                       # papers per intervention x outcome x study design
python -m agent.literature db dist <facet>                 # papers per label for one facet (countries, data_sources, ...)
python -m agent.literature db cooccur                      # pairs of data sources used in the same paper
python -m agent.literature db query --where facet=value    # papers matching every constraint (same rules as cluster define)
python -m agent.literature db export [--out PATH]          # Markdown evidence matrix
python -m agent.literature gap run --run-id g1 --where intervention="cash transfers" --where countries=SO [--pick facet=term_id] [--quotes]   # gap analysis, offline
python -m agent.literature gap question "free text" --run-id g1   # optional: a card that turns a question into constraints (then `submit g1`, then `gap run --run-id g1`)
python -m agent.literature exclude FILE_ID [FILE_ID ...] [--undo]   # set off-topic papers aside (_excluded.json); records stay on disk
python -m agent.literature status
python -m agent.literature backfill-years [--mailto you@example.com]  # fill publication_year from OpenAlex, no LLM
python -m agent.literature refine-grain [--file-id ID] [--redo]       # re-extract only intervention/outcome, scoped per paper (TODO-0085)
python -m agent.literature proposals list                  # terms the agent proposed that no vocabulary term covered
python -m agent.literature eval [--gold PATH]              # aggregates against gold/gold_set.yaml
python -m agent.literature api r1 --approve-cost 1.0       # explicit paid-API opt-in for extraction cards (cost-gated)
```

`submit` picks the right stage from the run. Cards live in `<index-root>/.agent_work/<run>/` (gitignored). A pending or
bounced card stays pending; nothing is sent to the API unless `api` is invoked.

## Record

One JSON file per paper, `<file_id>.json` (pass b: `<file_id>.b.json`; proposals: `_proposals.json`):
`identity`, `core` (intervention, outcome, study_design, sector, population, data_sources, geography, results),
`appraisal`, optional `modules`, `extractor` (driver, agent, run, schema and prompt versions, vocabulary versions),
`review` (`unreviewed`, `needs_review`, `accepted`, `corrected`) and, after `verify`, `verification`. Every fact is
`{value, vocab_id | proposed: true, quote, locator}`; the quote is checked against the exact page text offered on the card
and the locator is a page number that was offered. Records are **not committed**: they hold verbatim quotes.

## Vocabularies

YAML files in `vocab_data/` (format and provenance rules in `vocab_data/README.md`). The real 3ie intervention, outcome
and sector lists are generated locally from saved 3ie taxonomy-explorer pages by `vocab_data/build_3ie.py` into
`research/resources/3ie/vocab/` (gitignored: 3ie's reuse terms are unknown) and used with `--vocab-dir`. Vocabularies
over 150 terms are listed on a card by their grouping levels only. The study design, population, data source and hazard
type lists are committed starter lists marked `provisional`.

## Double extraction and verification

`collect --double` stages an independent second pass. The two records are compared by fact (ids with the same label,
parent and child terms, and contained proposed wording count as one fact); real disagreements set
`review.status: needs_review`. `verify` sends the facts only one pass found to a checker pass, which answers supported
(with a verified quote), not_supported or unclear. `silver` then splits facts into agreed, confirmed and open; people
review only the open facts and a random audit sample.

`tiers` names the same split as confidence tiers and writes `_tiers.json` for the later stages: **A** both passes found the fact,
**B** one pass found it and the checker found support in the paper, **C** one pass found it and the checker did not support it
(or has not looked). Analyses should start from A and B (`tiers.at_least(items, "B")`) and treat C as excluded.
After a proposed term is accepted or merged (`Proposals.accept` / `Proposals.merge`), `remap` re-points the facts that proposed it.

## Synthesis (stage 3)

Order: `cluster define`, `annotate` (submit), `synthesize` (submit; with `--merge` after chunk cards, then submit again),
`render`. Output is local only: `research/literature_reviews/<name>/` is gitignored because it quotes paper text.
Papers join a cluster when every `--where facet=value` matches one of their tier A/B facts (a term id, label or a
country code). `annotate` asks for a one-sentence contribution and limitation per paper, each with a verified quote.
`synthesize` cards cite papers by short ids (`P3`, `P3.R2`); `submit` bounces a paragraph that has no citation, cites an
id that is not on the card, names a raw id in prose, or states a number that is not in a cited result (or that paper's
year; compared by value, and a figure spelled as a word must be written in digits), uses evaluative wording (improved, harmful, ...) that no cited result's direction supports, and bounces a card that leaves a paper uncited. `render` writes the review with citation keys (title words and
year) and the bibliography, which comes only from the index card, the record and the annotations, never from model prose.

## Database (stage 4)

`db build` recreates `research/literature_db/literature.sqlite` (gitignored: it holds quotes) from the records, so build
again after any change; nothing is edited in the database. Tables: `papers`, `facts` (tier A/B by default, with quote and
page), `results`, `annotations`, `cluster_members`. Matrix, distribution, co-occurrence and query read only those tables
and use no LLM. A paper with several terms in a facet counts under each, so matrix rows can sum to more than the paper count.

## Gap analysis (stage 5, slice 1)

Design: `docs/superpowers/specs/literature_taxonomy/2026-10-29-literature-gap-analysis-design.md`. Reads only
`literature.sqlite`: no network, no LLM (the `gap question` card is optional and goes through `submit` like any other).
Each `--where facet=value` is resolved to one vocabulary term (or an ISO country code). A phrase that is not exactly one
term **stops** the run and writes `candidates.json` with ranked candidates (level, children, ancestor path, how many papers
each would match); re-run with `--pick facet=term_id`. Matching is by term id, descendants included (a label is compared
only for `proposed:` facts), so a label that 3ie lists under several branches is several distinct terms.
When a phrase names several terms with one label, the stop-and-pick list starts with `group:<term_id>` ("all N terms labelled X"):
picking it matches the union of those terms and their descendants (`resolved_by: label_group`), widens to the siblings of every member,
and adds a `breakdown` of direct papers per branch. Reports show each term's full path (`Education > Access > Term`).

- **direct**: a paper whose tier A/B facts match every constraint.
- **adjacent**: all but one relaxable constraint (intervention, outcome, country) match, and that one matches a sibling
  term (other children of its parent; a term under a top-level grouping is not widened) or a country in the same UN M49
  subregion (`gap/country_subregions.yaml`). Each hit is labelled with the facet relaxed. Two relaxations is a partial match.
- **verdict**: `tried_directly`, `tried_adjacent` or `no_evidence_in_corpus` (corpus only). `found_externally_not_in_corpus`
  is reserved for slice 2 (OpenAlex), which is not built.
- The report (`report.json`, `report.md` under `<index-root>/literature_gap/<run-id>/`, gitignored) carries coverage
  counts, thin-cell flag, blind spots (papers with `proposed:` values, no country fact, multi-country or global scale),
  a stale-database warning and the evidence list. It never claims a percent complete.

## Not built

Gap analysis slice 2: OpenAlex recall probe, live search and classification, the discovery queue Artifact.

Chunked extraction for papers over about 60k tokens of transcript (they are skipped with a reason); table-image
attachments (text only for v1); the interactive review page for proposed vocabulary terms (stage 2b); adjudication or a
third pass for real disagreements (see the status doc); the Warsame check, since that paper is not converted.
