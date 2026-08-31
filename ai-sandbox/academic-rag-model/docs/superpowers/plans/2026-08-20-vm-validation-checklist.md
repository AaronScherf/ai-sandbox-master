# VM Validation Checklist: Chapter-Aware Chunking

Companion to `docs/superpowers/specs/2026-08-19-textbook-chunking-and-page-tracking-design.md`
and `docs/superpowers/plans/2026-08-20-chapter-aware-chunking.md`. Everything
here needs a real GCP VM run to confirm -- none of it is testable from a
machine without CUDA. Update this file's checkboxes and "Findings" sections
as each item is actually run; this is meant to accumulate across sessions
and across different textbooks, not be re-derived from scratch each time.

## Before running

- [ ] Pull the latest `marker-conversion` branch onto the VM.
- [ ] Confirm `marker_setup.sh` completes cleanly (no changes to it in this
      plan, but worth confirming the VM environment is healthy before
      attributing any issue to the new chunking code).

## Round 1: a book with a real embedded outline (Axler-like)

**Status (2026-08-22): TWO full batch runs complete for Axler, Hammack, and
Rudin; output inspected directly both times, not just logs.**

**Run 1 findings:** confirmed anchor-uniqueness and page-tag coverage both
solid; folio tags were 0/0/0 across all three books, for what turned out to
be three *different* root causes (see below).

**Run 2 findings (after the front_matter_end and multi-anchor-bootstrap
fixes):**
- ✅ `<span id="page-N-M">` anchor uniqueness: zero duplicates in any of the
  three books, both runs -- the Critical boundary-overlap fix from the
  final whole-branch review continues to hold in production.
- ✅ `<!-- page N -->` tag coverage: Axler 404/404, Hammack 380/380 exact;
  Rudin 591/594 both runs (3 short -- the already-known,
  already-deferred consecutive-blank-page-marker gap in `page_markers.py`).
- ✅ **Axler: 404/404 folio tags.** Fully fixed by the front_matter_end scan
  range fix (`9d77b79`).
- ✅ **Rudin: 591/591 folio tags** (matches its page-tag count exactly).
  Fully fixed by the multi-anchor bootstrap fix (`901c2ac`).
- ❌→✅ **Hammack: still 0/380 folio tags after run 2** -- a third, distinct
  root cause, unrelated to either fix above: Hammack's PDF outline is
  organized at the *Part* level (6 top-level entries: Preface,
  Introduction, Parts I-IV), with the real 14 chapters nested one level
  underneath. `get_outline_chapters` only ever read top-level entries, so
  title-matching against the printed TOC's chapter titles ("Sets",
  "Logic", "Counting"...) found zero overlap -- confirmed directly by
  pulling Hammack's real outline locally (it's `textbook.pdf` in the input
  folder, identified by matching page count: 380). This also meant
  Hammack only ever got *Part*-level chunk alignment, not chapter-level --
  a chunking-safety gap, not just a folio-tagging one. **Fixed (`a99135a`,
  same day):** outline extraction now flattens every depth and lets the
  printed TOC's own chapter titles arbitrate which entries are real
  chapters via fuzzy matching, falling back to the bootstrap path when
  matching doesn't find enough. **Not yet re-run against the real Hammack
  PDF** -- confirm `<!-- folio ` count > 0 for Hammack specifically before
  checking this off for real.
- Not yet confirmed either way: `run_config.json` contents, resume
  behavior (interrupt + rerun).
- Minor, not chased down: `parse_printed_toc` extracts one spurious entry
  from Hammack's front matter (`folio=2, title='='`) -- harmless (fails to
  fuzzy-match any real outline title, gets silently dropped), but a real
  parser bug worth a proper fix sometime.

Use a small/cheap book first if possible -- the goal here is confirming
mechanics work, not doing a full production run.

- [ ] Run with default flags. Confirm in the logs that chapter discovery
      found entries (no "falling back to no chapter awareness" warning).
- [ ] Confirm output markdown contains `<!-- page N -->` tags, and that N
      increases monotonically across the whole merged file (no resets at
      old chunk-boundary points -- this is the concrete bug found in the
      real Axler_Linear_Algebra_Done_Right_2026 output during design).
- [ ] Confirm `<span id="page-N-M">` ids are unique across the whole file
      (`grep -o 'id="page-[0-9]*-[0-9]*"' output.md | sort | uniq -d`
      should print nothing).
- [ ] Confirm `<!-- folio N -->` tags appear and look plausible (spot-check
      a few against the book's own printed page numbers).
- [ ] Check `run_config.json` in the checkpoint dir: confirm it has
      `boundaries`, `folio_offset`, `folio_start_page` keys.
- [ ] Kill the run partway through (or just interrupt it), rerun, confirm
      it resumes and the log shows boundaries were loaded from
      `run_config.json`, not recomputed.

**Findings:**
(fill in after running)

## Round 2: a book with no embedded outline but a parseable TOC (Hammack-like)

- [ ] Confirm the log shows the outline-absent path: front matter converted
      up front, `bootstrap_chapter_index_from_front_matter` invoked.
- [ ] Confirm chunk boundaries in the log/checkpoint land at real chapter
      starts, not arbitrary fixed intervals.
- [ ] Confirm folio tags are present and correct, or absent with a clear
      WARNING logged explaining why (no anchor found, offset disagreement,
      etc.) -- either outcome is fine, silent wrongness is not.

**Findings:**
(fill in after running)

## Round 3: a scanned book with no anchors/links/outline at all (Rudin-like)

- [x] Confirm the pipeline still completes successfully end to end. --
      **yes**, 594-page book, no crash.
- [x] Confirm `<!-- page N -->` tags are present (paginate_output doesn't
      depend on the book having real structure) but no `<!-- folio -->`
      tags or anchor-remapping activity (nothing to remap). -- **yes**,
      591/594 page tags (see Round 1's note on the known blank-page-marker
      gap), zero folio tags, zero anchor spans (confirmed: Rudin's scanned
      PDF has no embedded links/anchors for Marker to emit in the first
      place, so there's nothing for `page_markers.py` to remap -- expected).
- [ ] Confirm chunking either found a bootstrapped chapter index (if the
      scanned TOC parsed) or cleanly fell back to fixed-interval chunking
      with the safety probe active -- check the log either way. Not yet
      confirmed (would need the run's log output, not just the final .md).

**Findings (2026-08-22):** Root-caused the missing folio tags directly by
reading Rudin's own converted text: Chapter 1 ("The Real and Complex
Number Systems") starts on physical page 11, and that specific page prints
no folio number at all -- a standard typesetting convention (chapter-opening
pages often suppress their header/footer page number). `chapter_index.py`'s
`bootstrap_chapter_index_from_front_matter` only ever tried to anchor on
the *first* TOC chapter's page specifically (`detect_printed_folio` had to
find "1" on exactly that page) -- when that one page doesn't print its
folio, as here, the whole bootstrap failed, even though every other page
in the book almost certainly prints its folio normally.

**Fixed (`901c2ac`, same day):** the bootstrap now scans every page in the
front matter once and tries every TOC chapter's folio against it, not just
the first, requiring the same >=2-sample majority consensus
`compute_folio_offset` already used elsewhere before trusting an offset --
so a single suppressed chapter-opener page no longer sinks the whole
bootstrap, as long as at least two *other* chapters print normally.
Locally unit-tested against a fixture that directly reproduces Rudin's
failure shape (chapter 1's page silent, chapters 2 and 3 print normally) --
confirmed the derived offset still correctly resolves chapter 1's physical
page even though its own page never contributed a sample. **Not yet
re-run against the real Rudin PDF** -- confirm `<!-- folio ` count > 0 on
the next run before checking this off for real. Deliberately not
addressed: a book where literally *every* chapter-opening page suppresses
its folio (we have no evidence this happens; the current fix already
covers the case actually observed).

## The one piece needing the closest look: `probe_and_shift_boundary`

This is the single component the design spec explicitly flagged as
unverified from outside the VM (the exact Marker rendered-block attribute
path for detecting "this page ends mid-Table/mid-Equation").

- [ ] Find or construct a test case where a table or formula visibly spans
      what would have been a fixed-interval chunk boundary under the old
      `--chunk-size 150` behavior, and confirm the probe actually shifts
      the boundary away from it (log line: "boundary at page N looks
      unsafe... shifting forward").
- [ ] If the structured block-type check in `_page_looks_unterminated`
      throws or never fires (check for the absence of any "looks unsafe"
      log lines across a full run that should have triggered at least
      once), that's a signal the attribute path assumed in Task 10 doesn't
      match the installed Marker version -- note the actual attribute
      shape found and update `_page_looks_unterminated` accordingly.
- [ ] Check the opposite failure mode too, flagged by the final whole-branch
      review: does the probe fire **too often**? The primary signal is "the
      page's last block is a Table/Equation" -- on a math-heavy textbook a
      large fraction of pages legitimately end with an equation, so if this
      check works as designed it may shift most fallback boundaries, many
      all the way to the `--max-boundary-shift` cap. Count how many
      "shifting forward" log lines appear per book and sanity-check that
      against how many actually looked risky by eye.
- [ ] Sanity-check output integrity directly: `grep -c '<!-- page ' output.md`
      should equal `total_pages_processed` from the run's metadata JSON
      (catches both a too-low count -- the page-break regex not matching
      Marker's real format at all -- and a too-high count -- overlapping
      chunk boundaries duplicating pages).
- [ ] Confirm `run_config.json`'s `boundaries` are contiguous and cover
      `[0, total_pages)` with no gaps or overlaps (the final whole-branch
      review found and fixed a bug here pre-VM-validation; this is the
      regression check for it on a real run).

**Findings:**
(fill in after running)

## Cost/performance sanity check

- [ ] Compare total processing time against a baseline run of the same
      book on the pre-chunking-change code (or against `processing_time_seconds`
      in an existing `academic-hub/processed_outputs/*/**_metadata.json`
      for the same book, if one exists) -- chapter-aware chunking should
      add at most a handful of extra single-page Marker calls (front-matter
      bootstrap + any boundary probes), not a meaningfully different
      runtime.

**Findings:**
(fill in after running)

## Known deferred items from implementation review (not bugs, just worth having in view)

These were found and deliberately deferred (not fixed) during the
implementation plan's task reviews -- listed here so a VM run has a chance
to reveal whether any of them actually matter in practice, not just in
theory:

- `probe_and_shift_boundary`'s structured block-type check may never match
  if Marker's real attribute renders as e.g. `"BlockTypes.Table"` rather
  than the bare `"Table"` the code checks for -- self-acknowledged as
  unverified from day one; see the checklist item above.
- The outline-absent branch's full-bootstrap-failure fallback
  (`front_matter_end = min(20, total_pages)`) is never run through the
  boundary safety probe, unlike every other non-chapter-aligned cut in the
  function -- only matters for a book with neither an embedded outline nor
  a parseable TOC.
- ~~Resuming against a `run_config.json` written before this feature existed
  (old format: `chunk_size` only, no `boundaries` key) silently recomputes
  fresh boundaries rather than erroring~~ -- **fixed** in the final
  whole-branch review's fix wave: an old-format `run_config.json` now
  triggers a warning and clears the stale (incompatible-scheme) chunk files
  before recomputing, so nothing old gets merged with the new boundary
  scheme. Worth a VM-run spot-check if an old in-flight checkpoint from
  before this branch ever gets resumed.
- The raw-PyPDF last-resort fallback tier's page tag changed from
  1-indexed (`Page N+1`) to 0-indexed (`<!-- page N -->`, matching every
  other tier) as an intentional side effect of unifying the tag format --
  worth being aware of if diffing fallback-tier output against pre-change
  runs.

Additional items surfaced by the final whole-branch review (after all 13
tasks landed), deferred as Minor rather than fixed immediately:

- The boundary-probe shift loop permits `max_boundary_shift + 1` shifts due
  to an off-by-one in the loop condition (`while shifted <= max_shift`) --
  one extra page of shift beyond the configured cap, not a correctness
  break.
- `_boundary_bootstrap_images` (used only for the front-matter/TOC
  bootstrap conversion inside `compute_chunk_boundaries`) is never cleaned
  up -- per-book cleanup only removes the main `checkpoint_dir`. Front-matter
  images from every book in a batch accumulate on the VM disk indefinitely.
  Worth a periodic manual `rm -rf` check on long-running VMs, or a follow-up
  fix to clean it up at the end of `compute_chunk_boundaries` or fold it
  into the per-book checkpoint dir instead of a shared path.
- The two `process_page_range` calls inside `compute_chunk_boundaries` (for
  front-matter/TOC bootstrap conversion) use hardcoded
  `chunk_timeout_s=1800, page_timeout_s=240` rather than
  `args.chunk_timeout`/`args.page_timeout` -- a user who overrides those
  flags (the commented example in Step 3.3 above does exactly this) won't
  have the override respected during the bootstrap conversion specifically.
- ~~If an embedded outline's first entry is physical page 0,
  `compute_chunk_boundaries` attempts a zero-page front-matter conversion~~
  -- **confirmed on a real VM run** (2026-08-22) and **fixed in two
  passes**. First pass: this turned out to be worse than "alarming but
  harmless" log noise -- the same zero-page call was also used to
  re-read the TOC for folio-offset computation, so it silently disabled
  folio tagging for the *entire book* (chunking itself was unaffected).
  Guarded with `front_matter_end > 0` to stop the crash-adjacent
  cascade. Second pass, same day: that guard was itself too blunt.
  Pulled Axler's actual PDF outline locally (`get_outline_chapters`,
  runnable off the VM) and found `front_matter_end == 0` isn't a rare
  case at all -- PDF outlines commonly bookmark the *title page* as
  their first top-level entry (Axler: page 0 = "Linear Algebra Done
  Right", page 14 = the real "Vector Spaces" chapter, seven entries
  later). The guard was silently disabling folio tagging for exactly
  this common, unremarkable case. Fixed by scanning
  `max(front_matter_end, max_front_matter_pages)` instead of
  `front_matter_end` alone for the TOC re-read -- works whether the
  outline's first entry is a title-page bookmark or the real chapter 1.
  Believed fixed for Axler and (same PDF-outline pattern, not yet
  independently confirmed) Hammack; confirm folio tags actually appear
  on the next run of either book.
- `README.md` and `convert_textbook.py`'s own module docstring still
  describe fixed-interval chunking and don't mention the `<!-- page N -->`
  / `<!-- folio N -->` tag output -- the most user-visible change in this
  whole feature. Worth a documentation pass once VM validation confirms
  the feature works as designed.

Further items surfaced by the final whole-branch review's fix-wave
re-review (all Minor, none blocking, all left deliberately unfixed since
the re-review found no new Critical/Important breakage):

- The old-format-`run_config.json` cleanup (the fix for the resume hazard
  above) clears stale chunk `.md` files but not the book's `metadata.json`
  or `images_dir` -- a resumed pre-feature run can end up with the OLD
  run's `table_of_contents`/`page_stats` in the delivered
  `{folder}_metadata.json`, and orphaned old-scheme images get shipped
  alongside the new output. Not a correctness break (no content collision),
  just leftover/stale metadata and unreferenced image files.
- That same cleanup runs inside a `try` block whose `except (json.JSONDecodeError, OSError): pass`
  would silently swallow an `OSError` from the cleanup itself, letting the
  run proceed with stale chunk files still present -- low probability
  (`rmtree`/`makedirs` are both already defensive), but the failure mode
  would be invisible if it ever happened.
- A **corrupt or truncated** `run_config.json` (possible since the write
  isn't atomic -- a kill mid-write reproduces this) hits the same
  `except json.JSONDecodeError: pass` as a missing-`boundaries`-key file,
  but does NOT get the new stale-chunk-clearing treatment: Fix 4 only clears
  chunks for the old-format case, not the corrupt-file case. Since the
  boundary probe is explicitly documented as potentially nondeterministic,
  a recompute here could produce different chunk tags than what's already
  on disk, reproducing the same duplicate-content merge Fix 4 was written
  to prevent. Worth closing before this comes up on a real interrupted run
  -- either clear chunks on both exception paths, or write `run_config.json`
  atomically (temp file + `os.replace`).
- The front-matter-chunk-0 size cap (also from the fix wave) only bounds
  the main conversion loop's chunk 0 -- the *separate* TOC re-read inside
  `compute_chunk_boundaries` (used to compute the folio offset when an
  embedded outline exists) still makes one unbounded
  `process_page_range(0, front_matter_end)` call over the same page range,
  before the subdivision logic runs. For a book whose outline's first
  chapter sits very deep, this specific call could still be the
  large/slow one the fix was meant to eliminate.
- `page_markers.py`'s page-break regex, even after the braced-format fix,
  still can't tag two page-break markers that sit back-to-back with no
  content between them (a genuinely blank page) -- the first match
  consumes the shared `\n\n`, leaving the second marker unmatched. Very
  rare in practice (blank pages are usually still numbered but empty), and
  pre-existing (not introduced by this branch's changes).

## Open questions for next session

(running list -- add to this as issues turn up; don't just fix and forget,
note *why* so future books don't hit the same surprise)
