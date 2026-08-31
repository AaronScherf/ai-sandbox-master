# Notes/Problem Set/Exam Transcription Pipeline

Companion to `gcp_instructions.md`, for a different category of document:
short (tens of pages, not hundreds), often no table of contents, often a
mix of typed and handwritten content -- sometimes on the same page.
Unlike the textbook pipeline, this one needs **no GCP VM, no Docker, no
Marker** -- it runs entirely on your local machine. Short version: Marker/
Surya's OCR is tuned for printed text and does poorly on handwriting,
while a vision-capable Gemini model reads typed-and-handwritten pages
directly; and rather than always paying for that model, `transcribe_notes.py`
routes each document to the cheapest processing tier its actual content
supports, decided per-document from PDF metadata and (where safe) local
text extraction.

## Prerequisites

* A `GEMINI_API_KEY` in your `.env` (see `ai-sandbox/.env.example`), with
  billing actually upgraded for that project -- linking a Cloud Billing
  account alone isn't enough; you also need to click **Upgrade** for that
  project on the [AI Studio API keys page](https://aistudio.google.com/apikey).
  Otherwise every call falls back to (much lower) free-tier quota limits.
* A folder of input PDFs under `academic-hub/`, e.g.
  `academic_notes/math-camp/problem_sets/` -- this becomes `$NOTES_SUBDIR`
  below. Output lands in a `processed_outputs/` folder created alongside
  the inputs, same convention as the textbook pipeline.

## Step 1: One-time local setup

```powershell
cd academic-rag-model
pip install google-genai python-dotenv pymupdf pypdf
```

`pymupdf` renders each PDF page to an image locally, and also does local
text extraction (see "How it works" below) -- a self-contained Python
wheel, no external binary dependency (unlike `poppler`/`pdftoppm`, which
this environment doesn't have installed). `pypdf` is used only for page
count and PDF metadata (`has_reliable_pagination`).

## Step 2: Run it

Batches over every PDF found directly under
`academic-hub/$NOTES_SUBDIR/` by default.

```powershell
$NOTES_SUBDIR="academic_notes/math-camp/problem_sets"

python -m notes.transcribe_notes --notes-subdir $NOTES_SUBDIR
```

* Add `--file "Linear Algebra Problem Set.pdf"` to process just one file
  instead of the whole folder.
* Add `--dry-run` first to see which tier each document would route to,
  and which pages/batches are already cached from a prior run, without
  spending any API calls.
* Each page's transcription (where the document needs Gemini at all) is
  cached in `processed_outputs/<PDFName>_pages_cache.json` as it's
  produced -- if the run is interrupted (network blip, rate limit, closed
  terminal), rerunning the same command picks up where it left off
  instead of re-billing already-processed pages/batches.
* Output: `processed_outputs/<PDFName>.md`, one file per input PDF -- a
  YAML frontmatter block (recording `routing`, `model`, and how many pages
  were affected) followed by every page's transcription concatenated in
  order, with a `<!-- page N -->` tag per page (physical PDF page number)
  so results stay traceable back to the source, same tagging convention
  as the textbook pipeline.

## How it works

For each document, `process_pdf()` picks the cheapest tier its actual
content supports -- never a blanket "always call the API" or "always try
local first":

* **Local, 0 API calls.** The document must first show positive metadata
  evidence of normal, sequential pagination (LaTeX/pdfTeX, Word,
  LibreOffice/OpenOffice `/Creator`/`/Producer` strings) -- anything from a
  known messy-export source (Nebo, MyScript, OneNote) is excluded
  unconditionally regardless of any other marker present, and anything
  unrecognized defaults to *not* reliable. If every page's local text
  (extracted via PyMuPDF, not `pypdf` -- PyMuPDF's layout-aware extraction
  was confirmed not to collapse inter-word spacing the way `pypdf`'s does
  on some font/kerning setups) passes a defect check, the PDF's own
  embedded text layer is trusted outright and used as-is.
* **Hybrid batched repair, or whole-document batching.** If some pages'
  local text is defective -- garbled ligatures or dropped glyphs from a
  large delimiter symbol, collapsed word spacing, or a lost
  exponent/subscript no plain-text extraction can represent (`D^5` reads as
  bare `D5`) -- and the fraction of defective pages is at or under 10%
  (`_MAX_DEFECT_RATIO_FOR_HYBRID`), only the defective pages are sent to
  Gemini, grouped into contiguous runs and batched (up to 12 pages per
  call) with surrounding clean-page text as context. Over that 10%
  threshold, the whole document is batched through Gemini instead (same
  batching mechanism, applied to every page) -- past that point, a
  confirmed defect is treated as evidence about that PDF's own production
  quirks likely affecting pages beyond just the ones flagged, so there's
  little value in preserving free-but-flawed local text on the rest. Both
  cases use `gemini-3.1-flash-lite` at 150 DPI, no accumulated context
  (pages are independent once a document is known to be reliably
  paginated).
* **Full transcription with a sliding accumulating context window.**
  Anything not reliably paginated -- handwritten scans, or a messy app
  export (Nebo, MyScript, OneNote) -- renders every page to an image and
  sends it to `gemini-3.6-flash` at 200 DPI, no pre-classification of
  "typed" vs "handwritten" (a single page can contain both, and the model
  reads whatever's actually there). Each page's call includes the last 3
  already-transcribed pages as context (not the whole document, and not
  just one page back) -- this matters specifically for OneNote exports,
  where the page's internal layout window can split a paragraph
  non-adjacently (e.g. a sidebar comment cut down the middle, with the
  other half landing a few pages later rather than on the very next page);
  a small trailing window catches that same continuity without the input
  tokens growing with document length (confirmed quadratic under full
  accumulation on a real file; flat under the 3-page window). This does
  mean pages in this tier **must** be processed strictly in order.

No chunking, no outline/TOC detection, no chapter-boundary logic in any
tier -- these documents are short enough that page-by-page or
batched-page processing is sufficient on its own.
