# Literature taxonomy: term selection and grain refinement, redesign

Date: 2026-11-03. Status: design for the owner's approval; nothing here is built. Scope: `agent/literature`. Follows the Phase 1 audit
([status](../../../status/literature/2026-11-02-phase1-quality-gate.md), [subproject status](../../../status/literature/2026-11-03-subproject-status.md)) and the
earlier [grain-refinement design](2026-10-25-grain-refinement-design.md), whose rollout this document corrects.

This document names 3ie terms only by their short labels. Definitions and other 3ie text stay in the local, ignored vocabulary directory.

## Why

The Phase 1 audit found that wrong labels in the intervention and outcome facets are mostly not random. The same wrong pick recurs across papers, both
extraction passes make it, and so it reaches tier A. Two-pass agreement therefore did not buy precision (A 0.87, B 0.93). The causes are in how a term is
offered to the model and how the refinement pass was rolled out, not in the model alone. The owner's instruction: fix these causes before any further
extraction or refinement run, and write the failure modes down so a later run on a clean corpus does not repeat them.

## What we found (2026-11-03)

Evidence is from the real database (67 analysed papers) and one real refinement card. Aggregates only.

| # | Finding | Evidence |
|---|---|---|
| F1 | **Leaf terms carry no definition in our vocabulary.** Our 3ie vocabularies came from a saved explorer page that holds group-level definitions only. 3ie defines every leaf; the definitions live on per-term portal pages and in the portal's data file. | 0 of 1,586 intervention leaves and 0 of 3,032 outcome leaves had a definition. Upstream: 1,583 of 1,583 and 3,030 of 3,030 have one. One real card offered 219 intervention terms, 45 with a definition (the groups). |
| F2 | **The refinement listing is a flat list.** Parent and child structure is lost, so a group and its children read as peers. | Same card: one undifferentiated block of 219 lines. |
| F3 | **The instruction pushes toward children and never says a parent is acceptable.** It asks for "the most specific listed term" and says not to "settle for a broad category when a listed child describes the paper's own wording better". Nothing says to keep the group when no child fits, or to prefer a term whose definition fits. | `stage.py` and `refine_grain.py` INSTRUCTIONS. |
| F4 | **The fix for one attractor created another.** Before refinement, 34 of 62 papers sat on the coarse climate-adaptation group. After it, one of that group's two children holds 15 of 88 intervention facts, in 15 papers, 12 of them at tier A. The audit upheld it as wrong in the two papers where it was contested. | `_tiers.json`; audit of 2026-11-03. |
| F5 | **Both passes see the same listing in the same order**, so they err together. | Wrong picks in the audit were mostly tier A with both passes agreeing. |
| F6 | **Refinement was a one-time rollout, not part of the run.** It needs an existing coarse record to scope from, and nothing enforces it. Papers added later, and every re-extraction, skip it. | 110 of 171 record files carry the refinement stamp; the 61 without are the `extract-v3` papers (45) and the 16 `extract-v4` re-extractions. |
| F7 | **Verification is keyed on facet, label and pass, plus the transcript hash.** A record whose facts change, as refinement does, keeps its old verdicts, and `verify` skips it. | Seen on the re-extracted papers; the old spec already says to run `verify --redo` by hand after refinement. |
| F8 | **The same real-world term appears once per sector branch**, each with its own id and, for about 100 outcome terms, a differently worded definition. Counts for one concept split across ids. | Outcome "Resilience": six copies. 3ie's documentation says cross-cutting terms appear in several places in the tree. |

Where the leaf definitions come from. The portal's front-end bundle (a public JavaScript file served by the 3ie Development Evidence Portal) contains the
whole taxonomy as a data array: sector, broad group, group, group definition, leaf term, leaf definition. Our term tree matches it almost exactly:
1,582 of 1,586 intervention leaves and 3,030 of 3,032 outcome leaves match on leaf label plus group label. Where one label and group occur under several
sectors with different definitions, the full path (sector, broad group, group, leaf) disambiguates. No page-by-page scraping is needed.

## Goals

1. Every leaf term shown to the extractor carries 3ie's own definition.
2. The extractor can see a term's place in the tree and chooses a child only when the child's definition fits what the paper itself studies. A group term is
   a legitimate answer.
3. The two passes are less likely to make the same mistake for the same reason.
4. Refinement is a standard, enforced step of every run, so a clean corpus is processed uniformly. A record that skipped it, or whose facts changed since
   it was verified, is visible and cannot enter analyses silently.
5. These failure modes and the correct run order are written where a future operator will read them.

## Non-goals and anti-goals

- No new vocabulary terms and no change to 3ie's tree or wording. We add 3ie's own definitions to terms; we do not invent definitions.
- Not a model change and not a paid-API change. Runs stay on subscription Gemini in Antigravity.
- Do not re-extract papers wholesale. Only the intervention and outcome facets are re-run, through the existing refinement pass.
- Anti-goal: replacing one attractor with another. A change that lowers the climate-group concentration but concentrates facts on a different term has failed.
- Anti-goal: committing 3ie text. The enrichment output stays in the ignored vocabulary directory.

## Design

### D1. Leaf definitions from 3ie's portal data

Extend `agent/literature/vocab_data/build_3ie.py` (or add a sibling module next to it) with an enrichment step.

- Input: the portal's current front-end bundle. The script reads the portal's HTML to find the current main script (its filename contains a content hash and
  changes), downloads it once, and extracts the intervention and outcome data arrays. The arrays are JavaScript object literals with unquoted keys and a few
  non-JSON escapes (`\x` sequences and stray backslashes); a tolerant extraction is required. A local copy of the bundle must also be accepted, so tests
  and offline runs need no network.
- Match each upstream row to our term by the full path (sector, broad group, group, leaf label), falling back to leaf plus group label. Write the leaf
  `definition`. Leave existing group definitions untouched unless upstream differs; report any such difference rather than overwriting it.
- Report counts: matched, unmatched, ambiguous, group definitions that differ. The four and two unmatched leaves are expected; the report lists them by id.
- Provenance: record the fetch date and the bundle's content hash in the vocabulary's `source` field. Bump the vocabulary `version`. A version bump only
  affects cards already staged (`stage.py` rejects a result whose vocabulary moved); it does not invalidate existing records.
- The script contains no 3ie text. Tests use a tiny synthetic fixture shaped like the real arrays.
- Courtesy and terms: one request for the page and one for the bundle, with a descriptive user agent. Before the script is committed, the owner checks the
  portal's terms of use for automated retrieval of its public files. The output stays local either way.

Owner decision recorded here: **definitions are added as 3ie states them**, with no paraphrase.

### D2. Listing format

Render the vocabulary branch as an indented tree, parent above children, each line `id: label - definition`, instead of a flat list. Definitions appear on
every term that has one (after D1, all of them). Keep the existing grouping-only view of the first extraction card for vocabularies over `LISTING_LIMIT`
(150 terms), but add each grouping term's definition, which it already prints when present. Estimated size: the largest scoped branch is a few hundred
terms with a sentence each, well inside the card limit; the implementer measures the largest real card and reports it.

### D3. Instruction wording (Claude writes the final text; the implementer only wires it in)

Replace "most specific listed term" and "do not settle for a broad category" in both `stage.py` and `refine_grain.py` with a fit test:

- Read each candidate's definition. Choose a child only if its definition describes something this paper itself does, studies or measures.
- If the paper discusses the topic of the group in general terms, or no listed child matches, choose the group term itself. A group is a valid answer.
- Do not choose a child merely because its label shares a theme with the paper (for example, a paper on adaptation in general is not an "agrobiodiversity"
  paper).
- `value` is the paper's own wording for the thing, so a mismatch between `value` and the chosen term is visible to the checker and to a reviewer.
- Keep `proposed: true` for a term that is missing from the vocabulary; it is separate from choosing a group.

Add one short worked example of each kind (a child fits; no child fits so the group is kept). Bump `PROMPT_VERSION` for both stages, since the card
instructions change.

### D4. Reduce correlated errors between passes (my call, to be tested)

Render the listing for pass b in a different, seeded order from pass a (siblings permuted within their parent; the tree shape is unchanged). This removes
a shared positional bias without changing what is offered. It is cheap and reversible. The trial (D7) compares precision with and without it; keep it only if
it helps or is neutral.

### D5. Make refinement part of the standard run, and guard against skipping it

Standard order for any paper: `collect --double`, `submit`, `refine-grain --double`, `submit`, `verify`, `verify --full-paper` if needed, `tiers`, `db build`.

Guards (code, with tests):

- `status`, `tiers` and `db build` report records whose `extractor` has no refinement stamp for the current refinement prompt version, and name them. `db build`
  refuses to load them unless an explicit override is given. This makes F6 impossible to miss.
- Verification verdicts are matched on a content key (facet, label, and a hash of the fact's quote), not on facet, label and pass alone. A fact whose
  content changed has no verdict until verified again, and `verify` no longer skips a paper only because its transcript hash is unchanged. (This is the
  stale-verification fix already on the list; it belongs here because refinement changes facts.)
- The refinement spec's "run `verify --redo` by hand afterwards" step becomes automatic through the content key.

### D6. Duplicate terms across sector branches

Not changed in this work. Document it (F8) and add a reporting view that groups term ids by their shared label for counts and the gap report, so "Resilience"
is counted once. Changing ids would invalidate every record; that is out of scope.

### D7. Trial, success criteria and rollout

Trial set: the 15 papers whose intervention facts currently use the over-picked term, the 8 re-extracted papers (which have no refinement yet), and 5 control
papers whose current labels were judged correct, so a regression shows. About 28 papers, double pass, subscription Gemini.

Judged the way Phase 1 was finally judged: Gemini reads the whole paper and each intervention and outcome label, blind to the old label; the owner audits
the contested labels in an Artifact that shows the paper's pages. Quote-only judging is not used.

Success (proposed; the owner sets the final numbers):

- Paper-level precision of intervention and outcome facts on the trial set at least 0.85, and not lower than before on the controls.
- No single leaf term holds more than 10% of a facet's facts across the corpus after the rollout (today's worst: 17% of intervention facts).
- The share of intervention and outcome facts on a group term rather than a leaf is reported and reviewed; a rise is expected and acceptable, a collapse onto
  group terms for papers that clearly study a specific intervention is not.

Rollout if the trial passes, in this order: the 8 re-extracted papers, the `extract-v3` papers (about 22), then every already-refined paper (110 record
files) once more under the new wording, because their tier A facts include the old attractor. Each batch is followed by `verify`, `tiers`, `db build`, and a
re-check of the term distribution. Rerun the paper-level precision sample at the end and record it in the Phase 1 doc.

### D8. Documentation deliverables

- This document is the failure-mode record (F1 to F8) and the reason for each guard.
- The package `README.md` gains a short "Run order and known failure modes" section: the standard order from D5, what each guard means, and a pointer
  here. Written by the implementer from this text.
- The subproject status doc is updated as each step lands.

### D9. Vocabulary text decisions already taken by the owner (2026-11-03)

These are definition edits to our own local vocabularies (`vocab_data/`), made together with D1 and committed as ordinary vocabulary text (none is 3ie text):

- `population.households` and `data_source.household_survey`: state that they include surveys of individuals, as survey reporting commonly says
  "household" for either.
- `study_design.narrative_review`: widen to include commentary, conceptual and policy-discussion papers; state that `study_design.qualitative` excludes reviews.
- Resilience: follow 3ie's framework. 3ie's outcome "Resilience" concerns a household's ability to weather shocks, and 3ie files climate adaptation under
  interventions, not outcomes. A paper's adoption of adaptation measures is therefore an intervention or an adoption outcome, not resilience. The extraction
  instruction gets a one-line pointer to this rule (part of D3).

## Work and owners

| Step | Owner | Why |
|---|---|---|
| Final wording of D3 and D9 text | Claude | Prompt design |
| D1 enrichment script and tests | Codex, from this spec | Well specified; owner checks the portal terms first |
| D2 listing, D3 wiring, D4 pass-b ordering, D5 guards, D6 view, tests | Codex, from this spec | Mechanical once the wording exists; any design question comes back to Claude |
| Branch review | Claude | Review remit |
| D7 trial runs | Gemini, relayed through Antigravity | Existing pipeline, subscription |
| D7 audit and success numbers | Owner | Only the owner judges correctness |
| Landing | Owner | After `land_branch check --full` |

## Open questions for the owner

1. The success numbers in D7 (0.85 precision, 10% concentration cap).
2. Whether the portal's terms allow the fetch in D1 (a read of their terms page, not a code question).
3. Whether to refine the 110 already-refined records again after the trial passes (my recommendation: yes, one batch after the first two).
