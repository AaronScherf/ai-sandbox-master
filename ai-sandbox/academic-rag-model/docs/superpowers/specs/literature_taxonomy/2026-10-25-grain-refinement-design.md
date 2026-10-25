# Literature taxonomy: grain-refinement pass (TODO-0085)

## Problem

`stage.py`'s `_vocab_listing` collapses any vocabulary over `LISTING_LIMIT =
150` terms to "grouping levels only" (terms that are themselves some other
term's parent). The real `intervention` vocabulary has 1,917 terms (331
grouping-level, 1,586 leaves); `outcome` has 3,466 (435 grouping-level, 3,031
leaves). Both collapse under the limit, so the extraction prompt shows the
model only the mid-level category nodes, not the specific leaf terms beneath
them.

Checked against the real 62-paper corpus (`literature_db/literature.sqlite`):
every paper's intervention/outcome facts are read at floor B (agreed or
checker-confirmed). Of 34 papers landing on the single bucket "Climate
adaption & mitigation strategies," only 3 were a comparison-pipeline bug
(already fixed separately: `agreed_facts` now prefers a descendant term when
one pass finds it and the other doesn't). The other papers reflect the
listing truncation itself: a stricter check -- a paper where *every* current
fact in a facet is a non-leaf (grouping) term, i.e. it has no specific
fallback at all -- still catches 46 of 56 papers with any intervention fact,
and 47 of 58 with any outcome fact (56 of 62 papers overall, across either
facet). This is not a narrow edge case; it is close to the whole corpus.

## Goal

A correction pass that re-extracts only `core.intervention` and
`core.outcome` for all 62 papers, showing each paper a vocabulary listing
specific enough that the model can pick a real leaf term instead of
defaulting to the coarse bucket it structurally could not see past before.
Every other field in every record (`study_design`, `population`, `sector`,
`data_sources`, `results`, `geography`, `appraisal`, `identity`,
`transcript_sha`) is untouched. Double-pass rigor (pass a + pass b, 124 cards
total) is kept, so the existing confidence-tiering machinery
(`agreed_facts`/`single_pass_facts`/`tiered_facts`) continues to work
unchanged on the refreshed facts.

## Why scoping by `sector` was rejected

The 13 top-level roots of both the `intervention` and `outcome`
vocabularies are literally the same 13 terms as the `sector` vocabulary
(confirmed by direct comparison of the YAML files), which made "scope the
listing by the paper's own `sector` fact" an obvious first idea (`sector`
itself is a 13-term vocabulary, never truncated, and spot-checking 12 random
papers' sector tags against their titles/quotes found no clear mistags).

But a full-corpus check falsified it as the scoping signal: 41 of 62 papers
have at least one current intervention or outcome fact whose root branch is
*outside* the paper's own tagged sector(s) -- e.g. `670e9034b3a6ec4d` is
tagged sector "Conflict, Security, & Fragility" but its intervention fact
roots to "Agriculture & Forestry" and its outcome fact to "Energy &
Extractives." This corpus is heavily agriculture/climate-focused, so a
paper's institutional/thematic `sector` tag often differs from the branch its
actual intervention/outcome content falls under. Scoping strictly by
`sector` would have hidden the correct branch for two-thirds of the corpus.

## Scoping rule actually used

For each paper and each of the two facets (`intervention`, `outcome`)
independently, pick the branch(es) to expand in full by this fallback chain:

1. **Root(s) of the paper's own current vocab-anchored facts in that
   facet.** Checked: zero papers are "proposed-only" in either facet --
   every paper that has any fact in a facet has at least one fact anchored
   to a real vocabulary term, so this tier always has something to work
   from whenever the facet has any current fact (56 of 62 papers for
   intervention, 58 of 62 for outcome).
2. **If the paper currently has zero facts in that facet** (6 papers for
   intervention, 4 for outcome -- the TODO-0087 cohort), fall back to the
   root(s) implied by the paper's `sector` fact(s) (always present, 62 of
   62).
3. **If neither exists** (should not occur in practice, since every paper
   has a sector fact), fall back to today's grouping-levels-only listing --
   no regression, just no improvement for that one case.

Once the branch(es) are picked, the listing shows the full subtree under
them -- every id, label and definition, no `LISTING_LIMIT` collapse within
that scope. A branch is typically ~1,917 / 13 ≈ 150 intervention terms or
~3,466 / 13 ≈ 270 outcome terms; both are well within a normal prompt. A
paper whose current facts span two root branches (multi-sector papers exist)
gets both branches' subtrees concatenated.

This is computed per pass, from that pass's own current record -- if pass a
and pass b currently disagree even on the coarse root, each pass's new card
is scoped independently from its own prior answer, not a union across both.

## New module: `agent/literature/refine_grain.py`

A new module parallel to `stage.py`, not added into it, so the narrower flow
stays isolated from the main extraction path. It exposes the same shape the
rest of the pipeline expects from a stage module (`STAGE`, `make_tasks`,
`apply_result`), matching `verify.py`'s and `contribute.py`'s pattern so
`cmd_submit`'s existing dispatch picks it up by adding one entry to its
lookup dict.

### Result shape

```yaml
## Result
intervention: [{value: "...", vocab_id: "...", quote: "...", locator: N}]
outcome: [{value: "...", vocab_id: "...", quote: "...", locator: N}]
```

Same fact shape as the main extraction (`value` plus exactly one of
`vocab_id` or `proposed: true`, `quote`, `locator`) -- reuses
`validate.py`'s per-fact checks (`_fact`), just scoped to these two keys
instead of the full `core` mapping.

### Instructions

Re-identify this paper's intervention and outcome facts from the same
transcript pages as the original extraction, using the vocabulary listing
below (which is specific to this paper, not the generic grouping-only
listing), picking the most specific term that fits. Explicitly: do not
settle for a broad category when a listed child describes the paper's own
wording better.

Neither pass is shown the other pass's answer, and neither is shown the
*old* coarse fact either -- each re-extracts independently against the
transcript, same as the original double-pass design, to avoid anchoring
bias toward the existing (possibly wrong) answer.

### `make_tasks(target, papers, *, pass_label="a", redo=False)`

For each paper: reads that pass's current record (if `pass_label="b"` and no
current record exists yet, falls back to pass a's record for scoping only --
the scoping rule needs *some* existing record to anchor on, even on a first
run where pass b has never been written). Builds the scoped listing per the
rule above, builds a `Task` with the same transcript passages as the
original extraction, and the narrower instructions/context. Skips a paper
with the same reasons `stage.make_tasks` already skips one (no readable
transcript, no page markers, over `MAX_CARD_CHARS`), plus a new skip reason
if the paper has no record at all yet for any pass (nothing to refine).

### `apply_result(target, entry, result, provenance)`

Unlike `stage.apply_result`, which replaces the entire record, this:

1. Reads the existing record for `entry["subject"]["pass"]`.
2. Replaces only `record["core"]["intervention"]` and
   `record["core"]["outcome"]` with the new result's values.
3. Sets `record["extractor"]["grain_refine_version"] = "refine-v1"` -- a new
   key, distinct from `prompt_version`, so a record that went through this
   correction is identifiable without implying the *whole* record was
   re-extracted under a new prompt version.
4. Updates only the `intervention` and `outcome` entries of
   `record["extractor"]["vocab_versions"]` to the vocabulary's current
   version; every other facet's recorded vocab version is untouched (those
   facets were not touched this round, so their recorded version must keep
   describing what was actually used for them).
5. Writes the record back.
6. Files any new `proposed: true` fact with `target.proposals.add`, the same
   way `stage.apply_result` does today, scoped to just these two facets.
7. After both passes are written, calls the existing
   `compare.reconcile(target.records, file_id, target.vocabs)` unchanged --
   it already re-diffs the whole record, so it correctly re-evaluates review
   status without any change on its side.

## CLI surface

No new verb beyond the existing `collect`/`submit` pattern:

- New subcommand `refine-grain`, mirroring `cmd_verify`'s structure: builds
  double-pass cards via `refine_grain.make_tasks`, writes them with the
  existing `collect_run`. Supports `--file-id` (repeatable) for a targeted or
  partial run -- useful for trying a handful of cards before committing to
  the full 124.
- `cmd_submit` already dispatches by `run.stage` to the right module via
  `{verify.STAGE: verify, contribute.STAGE: contribute, synth.STAGE:
  synth}.get(run.stage, stage)`; add `refine_grain.STAGE: refine_grain` to
  that lookup and `submit` picks up the new stage for free. No changes to
  `cmd_submit` itself.

## Testing

- Scoping function: given a record's current intervention/outcome facts,
  returns the full listing for the right branch(es); covers both fallback
  tiers (no vocab-anchored fact -> use `sector`; no sector either -> today's
  grouping-only, as a defensive case even though it should not occur in
  practice); covers a paper with facts spanning two root branches.
- `make_tasks`: correct task/skip counts and skip reasons, same style as
  `tests/agent/literature/test_lit_stage.py`'s coverage of
  `stage.make_tasks`.
- `apply_result`: every field outside `core.intervention`/`core.outcome` is
  byte-for-byte unchanged after merging; `grain_refine_version` and the two
  `vocab_versions` entries update; a new `proposed` fact is filed via
  `Proposals.add`; `reconcile` is called afterward.
- CLI: `refine-grain` produces the expected card count/content; `submit`
  correctly routes a `refine_grain`-stage run to the new module's
  `apply_result`.

## Rollout

Run `refine-grain` (double pass) for all 62 papers -- 124 cards relayed
through subscription Gemini/Antigravity, the same manual-relay workflow used
for the original extraction. No special-casing of which papers to include:
the scoping rule above produces a useful, narrower listing for every paper
regardless of whether it currently shows the coarse-bucket symptom, so there
is no cheaper meaningful subset to run first (checked: a mechanical "has a
non-leaf term" filter catches 60 of 62 papers; the stricter "every current
fact in the facet is non-leaf" filter still catches 56 of 62 -- effectively
the whole corpus either way).

After `submit`, each record's `verification` block still carries its
pre-refinement `transcript_sha`/support, so `verify.make_tasks` would skip
every paper as "already verified" and leave any new single-pass
intervention/outcome fact stuck "open" in the confidence tiers. Run
`verify --redo` and then `verify --full-paper --redo` before rebuilding the
database, so the refreshed facts actually get re-verified.

After that, rebuild `literature_db/literature.sqlite` and recheck the
intervention/outcome label distributions against today's baseline (34 papers
on "Climate adaption & mitigation strategies," "Agriculture & Forestry"
appearing as an intervention) to confirm the fix actually reduced the
coarse-bucket concentration before considering this done.
