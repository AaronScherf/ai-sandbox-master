# Image Description: Status Summary

Start here for "what happened and where do we stand" on the image-description
subproject -- the RAG-ready `.rag.md` output that adds text descriptions of
each book's figures/diagrams alongside `convert_textbook.py`'s existing
markdown conversion. Follows on from the chapter-aware chunking work (see
`docs/2026-08-22-chapter-aware-chunking-status.md`).

## What this project built

`describe_images.py`: a new, **local-only** script (no GPU, no VM, no
gcloud/IAP tunnel needed -- just local files and network access to the
Gemini API) that runs against already-converted books:

- **Two-stage filter.** A free filter first (any image on or before the
  book's last front-matter physical page -- cover art, publisher logos,
  title-page decoration -- is dropped with zero API calls, using
  `run_config.json`'s already-computed chapter boundary). Then a single
  combined Gemini call per surviving image decides both whether it's worth
  describing at all (skipping decorative/non-informational images) and, if
  so, produces the description -- one call does both jobs.
- **Context**: the prose paragraph immediately before and after each image's
  position in the markdown, plus the nearest preceding chapter/section
  heading, all extracted directly from the already-converted text.
- **Output**: a derived `<BookName>.rag.md` file, strictly additive -- a
  description is inserted as a blockquote directly beneath each kept image's
  link; the original `<BookName>.md` is never modified, and skipped images
  are left untouched.
- **Resumable**: each image's result is cached to disk
  (`<BookName>_image_descriptions.json`) as soon as it's produced, so an
  interrupted run (network blip, rate limit, closed terminal) picks back up
  without re-billing already-processed images.

Almost all of the logic (link parsing, front-matter filtering, context
extraction, prompt building, response parsing, caching, and the final
markdown assembly) is pure Python with no `torch`/`marker`/`google-genai`
import at module load time -- same dependency-free-module pattern as
`chapter_index.py`/`page_markers.py`, so it's independently unit-testable.
Only the actual network call and the CLI driver aren't. 33 new tests
(`tests/test_describe_images.py`), 87 total across the project.

## A real, pre-existing bug found and fixed before any of this could work

While wiring up how to locate each image's file on disk, found that
**every image link in every previously-converted book was broken**:
Marker saves each extracted image as `pg_{page}_{img_key}`, but the
markdown's own `![]()` link kept referencing the bare, chunk-local
`img_key` -- confirmed directly against real Hammack output, where no link
in the `.md` matched any file in `images/`. A naive text-based relink
wasn't safe either, since `img_key` is chunk-local (Marker's internal page
counter resets per chunk) and can collide across chapters in the final
assembled file. Fixed via `remap_image_links()`, applied at the exact point
each image is saved, at both the main-chunk and per-page-fallback save
sites.

## Real-world validation: all five books, fully processed

| Book | Candidates past front matter | Described | Skipped (decorative) |
|---|---:|---:|---:|
| Axler | 36 | 31 | 5 |
| Hammack | 132 | 124 | 8 |
| Rudin | 5 | 2 | 3 |
| Simon (Mathematics for Economists) | 204 | 199 | 5 |
| Sydsæter | 416 | 408 | 8 |
| **Total** | **793** | **764** | **29** |

Confirmed via a `--dry-run` pass after the fact: 0 uncached candidates
across all five books -- the quota interruptions during the run (see
below) left no gaps.

Cache-entry counts match `.rag.md` description-block counts exactly in
every book -- no insertion bugs, no duplicates, no drops. Spot-checked
description content across Axler, Rudin, and Sydsæter: genuinely accurate,
specific descriptions (a position-vector diagram, a cobweb diagram and a
Brouwer fixed-point-theorem setup, a number line correctly distinguished
from a skipped decorative calculator line-drawing) -- not generic
hand-waving. Called validated and ready for RAG/study use.

## Key errors encountered and overcome

Roughly in the order they were hit, across two real batch-conversion runs
and the image-description runs that followed:

1. **Broken image links** (above) -- pre-existing in every prior book's
   output, fixed via `remap_image_links()`.
2. **VRAM accumulation crash mid-batch.** A 5-book/899-page batch run in
   one continuous process (`SURYA_INFERENCE_KEEP_ALIVE` keeps the
   inference server warm across the whole batch) hit repeated
   `"Inference error: Connection error"` ~620 pages into the largest book,
   after 4 other books had already completed successfully in the same
   process. Root cause: `torch.cuda.empty_cache()` was only called after a
   chunk that hit an exception, never after a successful one -- VRAM
   accumulated silently across the whole batch until it starved the
   inference server. Fixed to run unconditionally after every chunk.
3. **`run_config.json` missing from a fresh run's output.** Confirmed via
   real GCS output: a just-completed batch run was missing it entirely.
   Root cause: the export (`shutil.copy2` into the final output folder)
   had only ever landed on this feature branch, never backported to the
   stable pipeline branch the VM actually runs. Backported.
4. **`gemini-2.5-flash` deprecated for new users** (`404 NOT_FOUND`,
   confirmed via the live API: *"This model ... is no longer available to
   new users. Please update your code to use models/gemini-3.6-flash"*).
   Updated the default model everywhere it's referenced (both the Vertex
   AI bibliographic-extraction call and the Developer API describe call).
5. **Gemini 3.x's `thinking_config` schema changed** -- the old integer
   `thinking_budget` is rejected outright (`400 INVALID_ARGUMENT`) in
   favor of a `thinking_level` string enum. Fixed both call sites to
   `thinking_level: "minimal"` (the lowest level Flash-tier models
   support; Pro-tier models can't disable thinking at all, irrelevant here
   since this project only ever uses Flash).
6. **`429 RESOURCE_EXHAUSTED` against the free tier despite a paid
   account** -- two distinct, compounding causes:
   - Linking a Cloud Billing account to a GCP project does **not**
     automatically move it off the free tier for the Gemini Developer
     API -- a separate, explicit "Upgrade" click on that project from the
     AI Studio API keys page is required.
   - Separately, the retry backoff (a fixed 5s/10s schedule) was far
     shorter than the API's own suggested wait (40-60s, a per-minute quota
     window reset) -- retries were exhausted before the quota actually
     cleared. Fixed to parse and honor the API's own `retryDelay` from the
     error response instead of guessing.
7. **A stale environment variable silently beat `.env`.** `load_dotenv()`
   doesn't override a variable that already exists in the environment by
   default -- a leftover Windows User/Machine-level `GEMINI_API_KEY` (or
   one set earlier in the same shell session) kept winning over an updated
   key in `.env`, with no visible symptom other than "the fix doesn't seem
   to be taking effect." Fixed via `override=True`, making `.env`
   authoritative as intended.
8. **Operational/GCP incidents along the way** (not code bugs, but real
   process gaps, now hardened in `gcp_instructions.md`): a `mkdir` step
   getting silently skipped when jumping straight to the download command
   broke Step 3.4 (`mkdir` now lives in its own separate block); an
   unterminated shell quote on a bucket-restore command looked like a
   stalled async operation but had actually never executed at all. A
   bucket-emptying step run before confirming the download succeeded also
   nearly caused real data loss -- recovered via GCS's default soft-delete
   retention, but worth remembering that step's ordering matters.

## Remaining open items (none blocking)

- `parse_printed_toc` still extracts one spurious entry from Hammack's
  front matter (`folio=2, title='='`) -- harmless (fails to fuzzy-match,
  silently dropped), carried over unfixed from the chunking project.
- The front-matter filter only excludes images *before* the first real
  chapter -- back matter (index, appendix, bibliography) isn't specifically
  filtered, left to the per-image LLM skip decision instead. Given the
  content-quality spot-check above, this hasn't shown up as a real problem
  in practice; worth revisiting only if it does.
