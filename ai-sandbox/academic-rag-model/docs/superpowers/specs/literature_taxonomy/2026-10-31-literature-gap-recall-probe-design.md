# Literature gap analysis, slice 2: recall probe (design)

Date: 2026-10-31. Builds on `2026-10-29-literature-gap-analysis-design.md` (slice 1, landed). Scope: `agent/literature/gap/` only.

## Intent

A gap run says what the corpus holds. It cannot say whether the corpus is a fair sample of the topic. The recall probe asks
OpenAlex for the most relevant works on the question's topic and counts how many are already in the corpus. A low count
tells the owner an empty or thin verdict reflects how the corpus was assembled, not the literature.

## Goals

- `gap run ... --probe` adds one network step: top-N OpenAlex works for the question, matched to the corpus.
- Report "k of N in the corpus" with a Wilson 95% interval, N always stated. Never a percent complete.
- Default run stays offline; without `--probe` nothing changes.

## Non-goals (decided with the owner, 2026-10-31)

- Returning, listing or classifying the works that are not in the corpus. No discovery queue, no Artifact, no card.
- The `found_externally_not_in_corpus` verdict. The verdict stays corpus-only; the probe never alters it.
- Topic-id mapping (the db holds no OpenAlex topic ids).
- Paid APIs. OpenAlex is free; a `mailto` is sent for its polite pool.

## Behaviour

1. **Query** (my call): the labels of the resolved intervention and outcome terms and the country names, space-joined, via
   the existing `iter_topic_works(keywords, mailto, batch_size)` (OpenAlex `default.search`, relevance order); first N taken.
   A label group contributes its one shared label. Study design, sector, population and data source are left out:
   keyword search handles them poorly and they would shrink N to nothing. Descendant terms are not added.
2. **N**: default 25 (owner confirmed 2026-10-31), `--probe-n`. Fewer returned results means a smaller stated N; zero results gives no interval.
3. **Matching** (against every paper in the db): OpenAlex id (`papers.openalex_id`, new column in `PaperRow`), then bare
   DOI (case-insensitive), then normalized title (`_normalize_title` rule: lowercase, alphanumerics only). A paper
   matches once; the first rule that hits is recorded. A corpus paper counts whether or not it satisfies the constraints
   (the probe measures topic coverage, not the verdict).
4. **Interval**: Wilson score, z = 1.96, on k of n.
5. **Report**: `report["external"]` (null today) becomes
   `{"probe": {"query", "requested", "retrieved", "in_corpus", "interval": [lo, hi] | null, "matched": [{"file_id", "by"}],
   "not_in_corpus": count, "mailto_used": true, "fetched": ISO date}}`. Markdown gets a short section with the fixed line
   "Top {retrieved} OpenAlex results by relevance for this query; {k} are in the corpus ({lo}-{hi}% interval). This
   measures the corpus against OpenAlex's ranking for this wording, not against all the literature." No titles of
   misses are stored (my call: that is the discovery queue, out of scope).
6. **Failure**: a network error or non-200 after the helper's retries is reported as `{"probe": {"error": "..."}}` plus a
   console warning; the offline report is still written and the exit code is unchanged.
7. **CLI**: `--probe`, `--probe-n N`, `--mailto ADDR` (required with `--probe`, or `$OPENALEX_CONTACT_EMAIL` as `backfill-years` does; never read from git config).
   `--probe` with a stopped (unresolved) run does nothing, as the run stops first.

## Tests

No network. A recorded OpenAlex payload of invented works through an injected fetch function. Cover: match by id, by DOI, by
title, and a work matching twice counted once; Wilson interval (known values, k=0, k=n, n=0); fewer than N results; the
error path; report/markdown text; CLI refuses `--probe` without `--mailto`; the default run unchanged.

## Open for the owner

- With N=25 and a small corpus (87 papers) most probes will show a low k. That is the intended signal, but the interval
  is wide (about 0 to 13% for k=0). N up to 100 narrows it at one extra request per 100 works.
