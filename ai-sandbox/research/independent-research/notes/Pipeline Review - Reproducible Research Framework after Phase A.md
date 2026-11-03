# Pipeline review: did the reproducible research framework meet its objectives? (Phase A, 2026-11-03)

Reviewer: Claude. Subject: `reprokit` v0.2.0 (template, schemas, validators) and `compound-shocks-panel` v0.1.2, against the 15 goals in `2026-10-31-reproducible-research-framework-design.md` section 2. Primary question: is it a good process wrapper for future projects? Secondary: did it serve this project's research subject?

**Evidence used:** this session's work (fresh-clone checks, both country reruns, the audit review), CI history, `reprokit` source and schemas, the Phase A commit history, and Gemini's 2026-11-02 structure audit (`.agent-reports/reviews/20261102-133500-reprokit-structure-audit/review.md`).

**Evidence limits:** I did not test the `pip` fallback, read the copier template file by file, or have anyone but me and the same machine reproduce a run. Goals 10 to 15 were not attempted in Phase A, so they are marked untested, not failed.

## Verdict

**Strong on mechanical reproducibility and on keeping the method honest. Weaker on three things a wrapper for future projects most needs: checking that what the documents say is true, handing a newcomer a map, and proving a clean run cheaply.** The core did port to a second country, but not by configuration alone.

## Goal-by-goal

| # | Goal | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Reproduce | **Met, with limits** | Fresh clones reproduced `panel.csv` and `publishable_aggregates.csv` byte for byte for both countries (13m13s, 17m23s). CI passes on Windows and Linux. Limits: same machine; raw files copied, not re-downloaded; no outside reproducer. |
| 2 | Adapt | **Partly** | Sudan took one new adapter (`iom_dtm.py`, 65 lines), one mapping, descriptors and a harmonization record. It also changed core files (`panel.py`, `schema.py`, `pipeline.py`, `eda.py`, `audit_memo.py`, `cli.py`, `fetch/hdx.py`), about 200 changed lines in `src/`, because a stock is not a flow. The core is country-neutral but not source-neutral. |
| 3 | Compare | **Partly** | Core versus extension columns and the harmonization gate worked: the gate forced an explicit written decision that the Somalia flow and Sudan stock must not share a column. Pooled and nested tests were deferred to Phase B. |
| 4 | Standalone | **Met** | Own repo, own tests, no monorepo coupling. The suite takes about 3 minutes. |
| 5 | Libraries | Untested | |
| 6 | Restricted data stays restricted | **Met, one gap** | Raw ACLED uncommitted, fixtures synthetic, gitleaks in CI, history clean, only totals published. Gap: the ACLED API fetch has never run against the live service. |
| 7 | Agent-accessible | **Partly** | `AGENTS.md` and descriptors help, but `AGENTS.md` still points to `data/raw/` and `outputs/`, which do not exist at the root of this repo (they are under `instances/<name>/`). |
| 8 | Cost-transparent | **Weak** | `compute.yaml` declares 8 GB and no GPU but no measured runtime or memory. The README said "about 3 minutes" until the clean-room found 13 to 17. An earlier Sudan run was killed for low memory. |
| 9 | Rights-safe | **Partly** | Secrets and raw rows: fine. Licences: the Somalia population file was recorded as CC BY-IGO, then found to be "restricted for use only in HRP and Humanitarian Operations". `reprokit validate` accepted the placeholder "confirm before reuse". |
| 10 | Fits a meta-structure | Not attempted | `project.yaml` has `taxonomy.tags`, `sources` and `siblings` empty (blocked on the 3ie taxonomy). |
| 11 | Knows what it is for | **Partly** | Charter exists but is mostly placeholders; `purpose: side_project` is a workaround because there is no exploratory category. |
| 12 | Plans end products | **Partly** | Panel and audit memo are built by `reproduce`; paper and slides are Phase B. |
| 13 to 15 | Communicate, derive, future kinds | Not attempted | `comms/` is empty. |

## What worked and should be kept

1. **Fingerprinting plus hashes plus hash-pinned downloads.** This is why the clean-room matched exactly. Keep as the template default.
2. **The harmonization gate.** It turned "Sudan has a different displacement source" into a reviewed written decision, and the later review upheld it.
3. **Verification-state labels.** The old Somalia window's clean-room was correctly marked void when the window changed, instead of being quietly reused.
4. **Descriptors with `find_in_other_geography`.** This is what made the Sudan walkthrough writable.
5. **Review loops with owner sign-off.** Harmonization record, tag and licence reading each had a named human decision.

## What did not work (ranked by importance for future projects)

1. **Validation is structural, not truthful.** `reprokit validate .` returns 0 silently. It checks schemas and that `period.start` is not after `period.end`. It does not check that `reuse_terms` was actually verified, that a descriptor's coverage matches the config period, or that `verification_status: run on acquired data` has a current verification note. The licence error and every stale-period error got through it.
2. **The same facts are hand-copied into many documents, so they drift.** This session found: the README's window and "planned portability test" wording; run times (3 minutes versus 13 and 17); `AGENTS.md` paths; the memo's "2021-01 to 2023-08" and event counts out of date with the descriptor; Sudan memo text about PRMN; the plan's stale checkboxes. None of these is a data error. All came from numbers or claims typed by hand into prose.
3. **No cheap proof that a fresh clone works.** The plan assumed a fixture instance runnable from the CLI. There isn't one, and `pytest` takes 3 minutes. Every future project will hit this: a newcomer's first question is "does it work on my machine?"
4. **Orientation for a newcomer.** I agree with Gemini that the root has too many meta files (about 11) and that docs point to paths that do not exist. I disagree with its "Exceptional" ratings on provenance and transparency, which did not account for the licence and stale-descriptor defects. I did not test the `pip` fallback, so I take no side on that finding.
5. **Core edits to add a second source type.** Not a defect, but the framework should say so: a new measurement type means core changes plus a harmonization record, and the design doc's "change config only" claim holds only for same-kind sources.

## Recommendations for `reprokit` v0.3 and the next project

Ordered by value for effort. None is built.

1. **Make `validate` check claims, not just shape.** Fail on `reuse_terms` or `access` fields containing "confirm", "unverified" or empty; require each descriptor's coverage dates to fall inside or be explained against the config period; require a verification note for any `run on acquired data` claim, matching the current commit.
2. **Generate numbers; do not type them.** Have `reproduce` write a short run card (row counts, hashes, timings, window, peak memory) from `manifest.json` and `run_report.json`, and have the README and verification notes quote or link it. This removes most of the drift above.
3. **Ship a `smoke` command in the template** that runs the synthetic fixture instance end to end in under 60 seconds and is what CI and a newcomer run first.
4. **Fix path drift once, in the template.** Pick single-instance or multi-instance as a template option and generate `AGENTS.md` and README paths from it. Add a researcher's orientation table at the top of the README (Gemini's Proposal A is right).
5. **Record measured cost.** Add runtime and peak memory per step to the run card and compare against `compute.yaml`, so cost claims come from runs.
6. **Add a "second source type" section to the framework doc** and a template stub for a harmonization record, so the cost of a new measurement type is expected.
7. **Add an exploratory purpose** to the charter schema.

## Secondary: did it serve the research subject?

- **Yes for the descriptive audit.** It produced a balanced district-month panel for two countries, with documented joins, and its audit memos made the price-gap and displacement-gap questions answerable.
- **Gaps that mattered:** the memos had no per-month count of districts with a price, so the Somalia 2023-07 coverage step change had to be found by an ad hoc check; the price-versus-conflict table pools across years, which hides the year effects; sorghum is the only price column compared; and there is no unit-area column. Adding the per-month coverage series and by-year splits to the template memo would have surfaced the step earlier.
- **Fit for Phase B:** the pipeline is a sound base for conflict and rainfall panels. Price and displacement work should wait on the data decisions in the literature gap memo.

## Open questions for you

1. Which of recommendations 1 to 3 do you want first for a `reprokit` v0.3? My order of value: 1, then 2, then 3.
2. Should the framework design doc be amended with the second-source-type note (item 5) and the Phase A evidence, or kept as the original intent?
3. Do you want an outside reproduction attempt (phase 11) before the next project, since everything here was verified on one machine?
