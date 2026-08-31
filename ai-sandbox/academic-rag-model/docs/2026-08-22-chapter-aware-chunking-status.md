# Chapter-Aware Chunking: Status Summary

Start here for "what happened and where do we stand" -- the full history
(design rationale, task-by-task implementation, every fix's reasoning) is
in the linked docs below if you need it, but this page is the one-stop
answer.

**Full detail, in order:**
1. Design spec: `docs/superpowers/specs/2026-08-19-textbook-chunking-and-page-tracking-design.md`
2. Implementation plan: `docs/superpowers/plans/2026-08-20-chapter-aware-chunking.md`
3. VM validation checklist (running log across real runs): `docs/superpowers/plans/2026-08-20-vm-validation-checklist.md`

## What this project built

`convert_textbook.py`'s PDF-to-markdown pipeline used to split every book
into fixed 150-page chunks with no page-number tracking at all -- a chunk
boundary could silently land mid-table or mid-formula, and there was no
way to resolve an author's own "see page 157" cross-references in the
output. This project rebuilt that into:

- **Chapter-aware chunking.** Chunk boundaries now align to real chapter
  breaks -- sourced from the PDF's embedded outline when the printed table
  of contents can confirm it's actually chapter-granular (not, say, a
  Part-level outline with real chapters nested underneath), or bootstrapped
  directly from the printed TOC when there's no usable outline at all.
  Any span that still can't be chapter-aligned falls back to a live Marker
  safety probe that shifts the cut away from anything that looks like a
  mid-table/mid-formula split.
- **Dual page/folio tagging.** Every page in the output gets a
  `<!-- page N -->` tag (physical PDF page index) and, where derivable, a
  `<!-- folio N -->` tag (the book's own printed page number -- what an
  author's internal cross-reference actually means).
- **A real bug fix along the way:** Marker's own internal anchors
  (`<span id="page-N-M">`) and links collided across chunks in the old
  pipeline (confirmed directly in real output) -- any chapter past the
  first chunk had broken internal navigation. Fixed as part of the same
  offset-remapping infrastructure built for page tagging.

Two new, deliberately dependency-free modules (`chapter_index.py`,
`page_markers.py` -- no `torch`/`marker` import, unlike `convert_textbook.py`
itself) carry almost all of the new logic, specifically so it's unit
testable on a plain machine without GPU/CUDA. 50 local tests currently
cover them.

## How it was built

Implemented via a 13-task plan executed with fresh-subagent-per-task
review (see the plan doc for the full breakdown). Two real regressions
were caught and fixed *during* that process, before anything shipped:

- A consensus-threshold formula that briefly required unanimous agreement
  instead of majority.
- An unguarded exception path and an inverted CLI flag registration in the
  boundary safety probe.

The final whole-branch review (after all 13 tasks) caught two more,
genuinely cross-task bugs that no single task's review could have seen --
this is the concrete case for why that final review step exists, not just
ceremony:

- The documented VM deploy step never copied the two new modules over, so
  the pipeline would have crashed at import on first real use.
- A probe-shifted chunk boundary wasn't propagated into the *next* chunk's
  start, so a shift could make two adjacent chunks overlap -- duplicating
  pages, duplicate page tags, and re-introducing the exact anchor-collision
  bug this project exists to fix.

Both fixed and verified before merge.

## VM validation: where it actually stands

Two full batch runs against three real, structurally different books
(Axler -- born-digital with real embedded links; Hammack -- born-digital,
messier table-based TOC; Rudin -- scanned, no embedded structure at all).

**Confirmed solid, both runs, all three books:**
- Zero duplicate `<span id="page-N-M">` anchors anywhere -- the
  anchor-collision fix holds in production, not just in unit tests.
- `<!-- page N -->` tag coverage: exact for Axler and Hammack; Rudin is 3
  pages short out of 594, understood and accepted (a pre-existing gap
  where two back-to-back blank-page markers can swallow each other --
  see the checklist for detail).

**Folio tagging (`<!-- folio N -->`) -- the real story, three separate bugs:**

Run 1 found folio tags at 0/0/0 across all three books, for three
*different* reasons -- not one bug wearing three faces:

1. **Axler**: its PDF outline bookmarks the title page itself as the first
   entry, which made the front-matter scan a zero-page range and silently
   skipped folio computation entirely. **Fixed, confirmed working**:
   404/404 folio tags on run 2.
2. **Rudin**: its bootstrap anchor search only ever tried to match the
   *first* chapter's own printed folio number, and that specific page
   doesn't print one (a standard convention for chapter-opening pages).
   **Fixed, confirmed working**: 591/591 folio tags (matches its page-tag
   count exactly) on run 2.
3. **Hammack**: its PDF outline is organized at the *Part* level (6
   top-level entries), with the real 14 chapters nested one level
   underneath -- title-matching against the printed TOC's chapter titles
   found zero overlap. This also meant Hammack only ever got Part-level
   chunk alignment, not chapter-level -- a chunking-safety gap, not just a
   cosmetic one. **Fixed, NOT yet re-confirmed** -- still showed 0/380 on
   run 2 (the fix landed after that run). Needs a third run.

## TODO -- pending before calling this fully validated

- [x] **Re-run all three books** (or at least Hammack) and confirm
      `<!-- folio ` count > 0 for Hammack specifically. **Confirmed**: a
      later real run (part of the 5-book batch described in
      `docs/2026-08-23-image-description-status.md`) showed 366/380
      (96%) folio tag coverage for Hammack -- the outline-flattening fix
      holds in production. Axler, Rudin, and Sydsæter (a fourth book,
      not in the original 3-book validation set) all landed in the
      96-98% range too.
- [x] Confirm `run_config.json` contents and resume/interrupt behavior on
      a real run. **Confirmed**: contents read correctly by
      `describe_images.py` across all 5 books in the later batch; resume
      behavior was exercised for real when a VRAM crash (see the
      image-description status doc) required killing and re-running the
      pipeline mid-batch -- already-completed books and chunks were
      correctly skipped on rerun.
- [x] Confirm whether `probe_and_shift_boundary`'s structured block-type
      check actually fires on the real installed Marker version, and
      whether it fires *too often*. **Confirmed firing correctly**: a
      real run logged `"[System] Chunk boundary at page 470 looks unsafe
      (page 470 may end mid-table/mid-formula); shifting forward."` --
      exactly once for that book, not excessively.
- [ ] Fix a real, low-stakes parser bug found during Hammack's diagnosis:
      `parse_printed_toc` extracts one spurious entry from Hammack's front
      matter (`folio=2, title='='`). Harmless today (fails to fuzzy-match
      any real outline title, silently dropped), but worth a proper fix.
- [ ] Everything logged as a deferred Minor in the VM validation checklist
      -- off-by-one in the boundary-shift cap, `_boundary_bootstrap_images`
      never cleaned up across a batch, hardcoded timeouts in the two
      bootstrap `process_page_range` calls inside `compute_chunk_boundaries`,
      a harmless-but-alarming log line when an outline's first entry is
      physical page 0, and a stale `README.md`/module docstring that still
      describes fixed-interval chunking with no mention of the new tag
      output. None of these block anything; they're just not fixed yet.

**Revisit note (2026-08-26):** both items above are still open. Neither
needs code changes that require the VM -- the `parse_printed_toc` fix and
the stale README/docstring are pure local edits -- but *confirming* any
fix for the boundary-shift/timeout/cleanup items needs a real run, since
`convert_textbook.py`/`chapter_index.py` import `torch`/`marker` at
module scope and only execute against Marker/Surya on the GPU VM; none of
it is testable locally. Deliberately not picked up on
`marker-conversion-notes-transcription` (this branch is notes-transcription
scope only, and touching the textbook pipeline here would mean spinning up
the GCP VM to validate anything, unrelated to what this branch is for) --
revisit on a branch scoped to the textbook pipeline, with a VM run
available to validate against.

## What's next

Image-to-text description for the `images/` folders, so a RAG/study
pipeline can consume figure descriptions directly instead of an opaque
image reference -- **done**, see `docs/2026-08-23-image-description-status.md`.
