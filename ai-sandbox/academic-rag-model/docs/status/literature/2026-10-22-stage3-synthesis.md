# Literature taxonomy stage 3: synthesis (status)

Built on branch `claude/literature-synthesis`; design in `docs/superpowers/specs/literature_taxonomy/2026-10-21-stage3-synthesis-design.md`,
plan in `docs/superpowers/plans/literature_taxonomy/2026-10-21-stage3-synthesis.md`.

## What is built

| Piece | Where | What it does |
|---|---|---|
| Cluster | `agent/literature/cluster.py` | Papers whose tier A/B facts match every `facet=value` constraint; written to `research/literature_reviews/<topic>/cluster.yaml`. An unknown facet or term fails loudly. |
| Annotation | `annotation.py` | Deterministic per-paper summary of the record (facts with tiers, numbered results) and unique citation keys. |
| `annotate` stage | `contribute.py` | One card per paper: a contribution and a limitation, each one sentence with a quote the checker verifies against the offered pages. |
| `synthesize` stage | `synth.py` | Cards of up to 20 papers (grouped by first country), plus an optional merge card; the validator described below. |
| Render | `review.py` | `review.md` (citation keys linking to the bibliography) and `bibliography.md`, deterministic. Refuses until `synth-final` exists and every paper is annotated. |
| CLI | `cli.py` | `cluster define|show`, `annotate`, `synthesize [--merge]`, `render`; `submit` routes by the run's stage. |

## Validator rules (checked at `submit`)

- Every paragraph has at least one citation, and each citation is a paper or result id that is on the card.
- No raw `P3` or `P3.R2` in the sentence text.
- Every number in a paragraph appears in the claim, magnitude or quote of a cited result (a paper-level cite covers all of its results) or equals a cited paper's year. Counts of studies must be written as words.
- Every paper on the card is cited at least once.

## Plan for the first runs

1. Small social-protection cluster first (`cluster define`, then `annotate` and `synthesize` through Antigravity, one run per stage and a fresh chat per run, each ending in `submit`).
2. Then the agriculture cluster, which is expected to need chunk cards and a `--merge` card.

## Known limits

- Clusters are by facet only, no embeddings or OpenAlex neighbours.
- Numbers are traced to result text, not to the underlying table.
- The bibliography has title words and year as the key because the index cards carry no author names.
- The validator checks digits, not direction or sign: a paragraph could reverse a finding's direction while quoting the right magnitude, and a number written as a word is not checked. Read the review against the bibliography before relying on a direction.
- Numbers are compared as text, so `1,200` vs `1200` or `12.5` vs `12.50` bounce; the bounce message names the number so the agent can copy the cited form.
- Only facts in tiers A and B are used; tier C facts never reach an annotation or a card.

## Not done

Embedding or OpenAlex clustering, vault export of the review, the stage 4 derived database, chunked extraction for the three oversize papers.
