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

Use a small/cheap book first if possible -- the goal here is confirming
mechanics work, not doing a full production run.

- [ ] Run with default flags. Confirm in the logs: `get_outline_chapters`
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

- [ ] Confirm the pipeline still completes successfully end to end.
- [ ] Confirm `<!-- page N -->` tags are present (paginate_output doesn't
      depend on the book having real structure) but no `<!-- folio -->`
      tags or anchor-remapping activity (nothing to remap).
- [ ] Confirm chunking either found a bootstrapped chapter index (if the
      scanned TOC parsed) or cleanly fell back to fixed-interval chunking
      with the safety probe active -- check the log either way.

**Findings:**
(fill in after running)

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
- If an embedded outline's first entry is physical page 0,
  `compute_chunk_boundaries` attempts a zero-page front-matter conversion,
  which logs an alarming-looking (but harmless) "Structural layout parsing
  failure on pages 1-0" before returning empty text and moving on.
- `README.md` and `convert_textbook.py`'s own module docstring still
  describe fixed-interval chunking and don't mention the `<!-- page N -->`
  / `<!-- folio N -->` tag output -- the most user-visible change in this
  whole feature. Worth a documentation pass once VM validation confirms
  the feature works as designed.

## Open questions for next session

(running list -- add to this as issues turn up; don't just fix and forget,
note *why* so future books don't hit the same surprise)
