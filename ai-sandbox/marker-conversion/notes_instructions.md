# Notes/Problem Set/Exam Transcription Pipeline

Companion to `gcp_instructions.md`, for a different category of document:
short (tens of pages, not hundreds), no table of contents, often a mix of
typed and handwritten content -- sometimes on the same page. Unlike the
textbook pipeline, this one needs **no GCP VM, no Docker, no Marker** --
it runs entirely on your local machine. See
`docs/superpowers/specs/` (once written) for the full design rationale;
short version: Marker/Surya's OCR is tuned for printed text and does
poorly on handwriting, while a vision-capable Gemini model reads
typed-and-handwritten pages directly, and these documents are short
enough that per-page API cost is trivial regardless.

## Prerequisites

* A `GEMINI_API_KEY` in your `.env` (see `ai-sandbox/.env.example`), with
  billing actually upgraded for that project -- linking a Cloud Billing
  account alone isn't enough; you also need to click **Upgrade** for that
  project on the [AI Studio API keys page](https://aistudio.google.com/apikey).
  Otherwise every call falls back to (much lower) free-tier quota limits.
* A folder of input PDFs under `academic-hub/`, e.g.
  `academic_notes/math-camp/Problem_Sets/` -- this becomes `$NOTES_SUBDIR`
  below. Output lands in a `processed_outputs/` folder created alongside
  the inputs, same convention as the textbook pipeline.

## Step 1: One-time local setup

```powershell
cd marker-conversion
pip install google-genai python-dotenv pymupdf
```

`pymupdf` renders each PDF page to an image locally -- a self-contained
Python wheel, no external binary dependency (unlike `poppler`/`pdftoppm`,
which this environment doesn't have installed).

## Step 2: Run it

Batches over every PDF found directly under
`academic-hub/$NOTES_SUBDIR/` by default.

```powershell
$NOTES_SUBDIR="academic_notes/math-camp/Problem_Sets"

python transcribe_notes.py --notes-subdir $NOTES_SUBDIR
```

* Add `--file "Linear Algebra Problem Set.pdf"` to process just one file
  instead of the whole folder.
* Add `--dry-run` first to see which pages would be processed (and which
  are already cached from a prior run) without spending any API calls.
* Each page's transcription is cached in
  `processed_outputs/<PDFName>_pages_cache.json` as it's produced -- if
  the run is interrupted (network blip, rate limit, closed terminal),
  rerunning the same command picks up where it left off instead of
  re-billing already-processed pages. Pages are always processed in
  strict order (see "Full accumulating context" below), so a resumed
  run reconstructs the context it needs from the cache rather than
  re-deriving anything.
* Output: `processed_outputs/<PDFName>.md`, one file per input PDF --
  every page's transcription concatenated in order, with a
  `<!-- page N -->` tag per page (physical PDF page number) so results
  stay traceable back to the source, same tagging convention as the
  textbook pipeline.

## How it works

For each page: render it to an image via `pymupdf`, pull whatever text
`pypdf` can extract natively (often present but unreliable for
handwriting-app exports -- included as a hint, not trusted outright), and
send both to Gemini with a single request: transcribe everything on this
page -- typed and/or handwritten -- into clean markdown, preserving math
notation and problem/part structure. No page is pre-classified as
"typed" or "handwritten" before this call; a single page can contain
both, and the model reads whatever's actually there.

**Full accumulating context.** Every already-transcribed page's clean
markdown is included as context for the next page's call, growing as
the document is processed -- not just the immediately preceding page.
This matters specifically for OneNote exports: OneNote's page windowing
can split a paragraph non-adjacently (e.g. a sidebar comment cut down
the middle, where the other half lands a few pages later rather than on
the very next page), so a fixed one-page-back window wouldn't reliably
catch it. The prompt explicitly flags this possibility and asks the
model to use the accumulated context to detect and reassemble split
content. At the scale these documents run (well under 50 pages, each
contributing at most a few paragraphs once transcribed -- a few tens of
thousands of tokens accumulated by the last page), this is cheap and
avoids the "lost in the middle" degradation that shows up mostly in
much larger, needle-in-haystack-style contexts, not this kind of
short, uniformly-relevant one.

This does mean pages **must** be processed strictly in order (page N's
call needs pages 1..N-1 already transcribed) -- no page-level
parallelization. At a few seconds per page, a ~50-page document still
finishes in a few minutes, so this isn't a practical cost.

No chunking, no outline/TOC detection, no chapter-boundary logic -- these
documents are short enough that page-by-page processing with full
accumulating context is sufficient on its own.
