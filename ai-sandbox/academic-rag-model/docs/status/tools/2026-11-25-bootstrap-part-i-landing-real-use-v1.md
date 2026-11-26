# Bootstrap Part I PDF transcription landing: real-use check - v1

**Date:** 2026-11-25 (America/New_York; Git log timestamps are UTC)
**Verdict:** **Fast** for this real transcription and its index landing. The monorepo check and land selected no tests, and land did not retest. This is one observed landing, not evidence about later landings or a periodic full-suite run.

## Scope and repository map

- Source: `ai-sandbox/academic-hub/academic_resources/econometrics/part_2/professor_notes/Bootstrap_Part_I.pdf` (31 pages). The PDF was copied into an isolated worktree for the run and was not tracked or landed.
- `pipelines.transcribe_notes` used the API driver and its normal cost router. Dry run found 13 defective pages (42%), above the 10% hybrid threshold, so the pipeline transcribed all 31 pages in three `gemini-3.1-flash-lite` batches. Conversion wall time: **107.362 s**. The pipeline reported 33,825 input and 5,050 output tokens.
- The Markdown and page cache belong to the separate `academic_notes` Git repository. Branch `codex/bootstrap-part-i-transcription`, commit `ae483bf9b89e396880aeb47ebfb03d31c73b220b`, change ID `82daae2cd6c072f8eb6c9888d84a195edf657cca6d6358a04597360d63c5f908`. Paths: `econometrics/part_2/professor_notes/processed_outputs/Bootstrap_Part_I.md` and `Bootstrap_Part_I_pages_cache.json`.
- The generated source-index card and recomputed course entry belong to the monorepo. Branch `codex/transcription-bootstrap-part-i`, commit `fcbb1609dd4ea64e13ffd38587291d559692aecc`, change ID `ec3a21555dbf0345b3b7095b3c562c437a81a6910e20ee67fbdddbabf0fbbea3`. Paths: `ai-sandbox/academic-hub/.index/econometrics.json` and `.index/courses.json`.
- Both repositories' `main` and `origin/main` resolve to the commits above after landing. The owner separately approved the notes landing, including six earlier local-main commits, and then approved the monorepo index landing.

`23-gmm.pdf`, the owner's first choice, was already transcribed and indexed. A new run reproduced its committed Markdown and cache exactly after line-ending normalization, leaving no change to land. It was not used as the measurement. The earlier synthetic fixture branch was also not landed.

## Output and pre-flight verification

- The generated Bootstrap Markdown has 31 page markers, no NUL bytes, and no Unicode replacement characters. `python -m tools.reference_review raise econometrics/part_2/professor_notes/processed_outputs/Bootstrap_Part_I.md` in the notes worktree reported **0 items, 0 defects, 0 incomplete lookups**.
- `python -m tools.active_work` found no overlap involving the monorepo transcription branch. The separate notes branch check also printed `Overlaps: none`.
- Both landing checks printed `Guard: passed`. No PDF or other binary was included in either commit.

## Console evidence

Notes repository check (wall time **5.216 s**):

```text
Branch:      codex/bootstrap-part-i-transcription
Commit SHA:  ae483bf9b89e396880aeb47ebfb03d31c73b220b
Change ID:   82daae2cd6c072f8eb6c9888d84a195edf657cca6d6358a04597360d63c5f908
Checks:      skipped [] (0.0s)
Overlaps:    none
Guard:       passed
```

Notes repository land (wall time **6.541 s**):

```text
Approved check: 2026-11-26T00:48:36.149416+00:00 base a6d8d437 skipped reason outside_project_only
LANDED ae483bf9b89e396880aeb47ebfb03d31c73b220b (1 attempt(s), no re-test)
```

Monorepo index first check took **6.374 s**. The owner requested a fresh check after the notes landed; the selected second check took **4.574 s**:

```text
Branch:      codex/transcription-bootstrap-part-i
Commit SHA:  fcbb1609dd4ea64e13ffd38587291d559692aecc
Change ID:   ec3a21555dbf0345b3b7095b3c562c437a81a6910e20ee67fbdddbabf0fbbea3
Checks:      skipped [] (0.0s)
Overlaps:    none
Guard:       passed
```

Monorepo index land (wall time **8.238 s**):

```text
Approved check: 2026-11-26T00:56:10.856885+00:00 base 431a8eca skipped reason outside_project_only
LANDED fcbb1609dd4ea64e13ffd38587291d559692aecc (1 attempt(s), no re-test)
```

Neither land command printed a `Retesting:` line.

## Append-only log evidence

The notes repository log is `academic_notes/.git/agent-landing-log.jsonl`; the monorepo log is the shared `.git/agent-landing-log.jsonl`. Filtered by the branch and change IDs above:

| Repository | `check` event | `land` event |
| --- | --- | --- |
| Notes | `checks: "skipped"`, `selection_reason: "outside_project_only"`, `check_seconds: 0.0`, `check_targets: []`, `overlaps: []` | `approved_at: "2026-11-26T00:48:36.149416+00:00"`, `approved_reason: "outside_project_only"`, `retested: false`, `retest_chunk_timings: []`, `retest_reason: ""`, `result: "landed"` |
| Monorepo index | Latest check `at: "2026-11-26T00:56:10.856885+00:00"`, `checks: "skipped"`, `selection_reason: "outside_project_only"`, `check_seconds: 0.0`, `check_targets: []`, `overlaps: []` | `approved_at: "2026-11-26T00:56:10.856885+00:00"`, `approved_reason: "outside_project_only"`, `retested: false`, `retest_chunk_timings: []`, `retest_reason: ""`, `result: "landed"` |

The monorepo `approved_at` equals the latest check's `at`, showing that land selected the newer skip. There was no land-time test suite run.

## Timing against baselines

Approval waiting time and the 107.362-second PDF conversion are excluded from landing timing.

| Segment | Measured wall time |
| --- | ---: |
| Notes check + land | 5.216 + 6.541 = **11.757 s** |
| Monorepo first check + recheck + land | 6.374 + 4.574 + 8.238 = **19.186 s** |
| Monorepo selected check + land | 4.574 + 8.238 = **12.812 s** |
| Both repositories, including the extra monorepo recheck | **30.943 s** |

The monorepo's **19.186 s** from its first check through `LANDED`, excluding approval waits, is about **98% shorter** than both reference cases: the **912.8 s** full check on 2026-11-16 and the **1,045.5 s** unexpected land-time retest on 2026-11-22. The observed result meets the expected under-one-minute check-plus-land path. The check log's `check_seconds: 0.0` describes test execution only; the measured check wall times include Git, guard, and bookkeeping work.

## Status and limits

The notes and index are landed and pushed in their respective repositories. This run verifies a successful live PDF conversion and two successful live landings with no test retest. It does not establish transcription accuracy page by page, and it does not replace a full-suite run of `main` or demonstrate behavior across future landings.
