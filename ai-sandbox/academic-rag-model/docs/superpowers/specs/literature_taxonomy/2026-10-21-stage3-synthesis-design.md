# Stage 3: literature synthesis (design)

Status: draft for owner review, 2026-10-21. Umbrella spec: [pipeline design](2026-10-15-literature-taxonomy-pipeline-design.md) section 6, stage 3.
Owner decisions so far: output stays **local only** under `research/literature_reviews/<topic>/` (gitignored, like the records and 3ie files); first runs are a small cluster, then a large one; subscription Gemini via task cards, no paid API.

## 1. Intent

Turn the stage 2 records into a readable literature review and an annotated bibliography for a chosen group of papers, where every sentence can be traced back to a paper in the group and every number to a quote the extraction already verified. Success: a person can open the review, click any citation to the annotation, and from there reach the page-level quote; nothing in the output is uncheckable.

Assumptions (owner to correct): v1 groups by an explicit facet query, not by embeddings or OpenAlex; the review is for the owner's reading and later proposal writing, not for publication; only facts in confidence tiers A and B are used.

## 2. Pipeline

1. **Define a cluster** (`cluster define`): a name plus facet constraints (for example sector, intervention, outcome, country). A paper joins when each constraint matches one of its tier A/B facts, counting a term's descendants. Output `research/literature_reviews/<topic>/cluster.yaml` holds the query, the tier floor and the sorted `file_id` list. Deterministic; no model.
2. **Annotate** (`annotate` stage, one card per paper): the card shows the paper's deterministic annotation (study, setting, design, data, results with quotes, tier A/B facts) and the cited pages. The agent adds only `contribution` and `limitations`, each one sentence with a quote and page that pass the existing quote check. Result stored on the record side as `annotations/<file_id>.json`.
3. **Synthesize** (`synthesize` stage): a card per cluster (about 15 to 20 papers). Larger clusters are split by a facet (country or intervention) into chunk cards, then one merge card sees only the chunk sections. The input lists papers as `P1..Pn` and each result as `Pk.Rj` with its claim and magnitude. The agent returns sections of paragraphs, each paragraph `{text, cites: [...]}`.
4. **Validate** (mechanical, a failing card bounces with reasons):
   - every cite is a paper or result of this cluster;
   - every paragraph has at least one cite;
   - every number in a paragraph appears in the claim or magnitude of a result it cites;
   - no paper outside the cluster is named.
5. **Render** (`render`, deterministic): `review.md` (sections with citation keys) and `bibliography.md` (one entry per paper from the index card and record: title, authors, year, DOI when known, design, countries, tier counts, the contribution and limitations note). The bibliography never depends on the model.

All stages reuse `core/agent_tasks` (manifest `stage` routes `submit`), the worklists and the Antigravity hand-off used for extraction and verification.

## 3. Trust and safety

- Tier C facts and facts of papers still flagged `needs_review` are excluded; a paper with no tier A/B results is listed in the bibliography but not synthesized.
- Quotes appear only in the local annotations and review, never in a committed file. Tests use synthetic fixtures.
- The synthesis card can only cite what it is shown, so a hallucinated citation or number is rejected rather than reviewed by hand.

## 4. Testing

Deterministic rendering from a fixture record; membership by descendant terms; citation closure; number tracing (a number only in the prose, or only in an uncited paper, fails); chunk split and merge; a bounced card names the reason; end-to-end collect, fill, submit, render on synthetic papers.

## 5. Out of scope for v1

Embedding or OpenAlex clustering, cluster proposals through an Artifact, vault export, the derived SQLite database (stage 4 of the umbrella spec; this stage uses only a small facet query), gap analysis.

## 6. Open decisions

1. Citation key format in the review: title-based short key, or authors and year when the index card has them?
2. Should the annotate note be required for every paper before synthesis, or optional (synthesis runs on deterministic annotations alone)? Recommended: required, it is cheap and it adds the limitations.
