# Chapter-aware chunking and dual page/folio tracking

## Problem

`convert_textbook.py` currently splits each PDF into fixed-size page-range
chunks (`--chunk-size`, default 150 pages) and converts each chunk with
Marker independently. Two problems with this:

1. A chunk boundary can land in the middle of a table or formula that spans
   the split, silently corrupting that content in the output.
2. The output markdown carries no page-number information at all, so the
   book's own table of contents and any internal author cross-references
   ("see page 157") are meaningless once converted -- an LLM reading the
   output has no way to resolve them.

## Goals

- Chunk boundaries should never land inside a table, formula, or (ideally)
  a chapter.
- Every page's content in the output markdown is tagged with its physical
  PDF page index.
- Where derivable, pages are *also* tagged with the book's own printed folio
  number (the number an author's internal "see page N" reference actually
  means), so an LLM can resolve such references against nearby tags.
- Degrade gracefully at every stage: a book with no embedded outline, no
  parseable TOC, or no detectable printed folio numbers should still convert
  correctly using today's fixed-interval chunking -- it just won't get the
  chapter-alignment or folio-tagging benefits.
- Preserve existing checkpoint/resume guarantees: boundaries and any
  derived offsets are computed once and persisted, never recomputed
  differently across a resume.

## Non-goals

- OCR'ing every page's header/footer to independently verify its printed
  folio number. We derive one global offset (or a small number of
  anchor-validated offsets) from the front matter and TOC instead.
- Handling books with non-linear or multiple independent folio sequences
  (e.g. a photo-plate section renumbered separately). If offset anchors
  disagree, we drop folio tagging entirely and log a warning rather than
  guessing.
- Sub-chapter (section-level) chunk alignment. Chunking aligns to top-level
  chapter boundaries only.

## Design

### New module: `chapter_index.py`

All logic in this section has **no dependency on `marker`, `torch`, or
`surya`** -- only `pypdf` and the standard library. This is a deliberate
split, not just tidiness: `convert_textbook.py` imports `marker`/`torch` at
module scope, which requires the VM's CUDA environment to even succeed, so
none of that logic can be unit tested from a plain machine. Everything in
`chapter_index.py` can be, right now, without VM access.

#### Data model

```python
@dataclass
class ChapterEntry:
    title: str
    physical_page: int | None   # 0-indexed PDF page, None if not yet resolved
    folio_page: int | None      # printed page number, None if unknown/roman
```

#### `get_outline_chapters(reader: PdfReader) -> list[ChapterEntry]`

Walks `reader.outline`, taking only **top-level** entries (depth 1) as
chapters -- nested subsections are ignored so chunks aren't fragmented at
every subsection. Resolves each entry's physical page via
`reader.get_destination_page_number(item)`. Returns `[]` (never raises) if
there's no outline or any entry fails to resolve.

#### `parse_printed_toc(markdown_text: str) -> list[ChapterEntry]`

Regex-based parse of the front matter's *own rendered* table of contents
page(s) (folio-only; `physical_page=None`). Finds a heading matching
`Table of Contents` / `Contents`, then reads subsequent lines until two
consecutive non-matching lines end the section. A line is a TOC entry if it
ends in a short numeric or roman-numeral token (`\d{1,4}$` or
`[ivxlcdm]{1,7}$`, case-insensitive), which becomes `folio_page`; the rest
of the line (dot leaders and markdown/heading syntax stripped) becomes
`title`. Returns `[]` if no TOC heading is found -- this is expected and
fine for books without a formal TOC page.

#### `detect_printed_folio(page_text: str) -> str | None`

Given the markdown slice for **one physical page** (sliced from an
already-converted chunk using our own `<!-- page N -->` markers -- see
below), checks the first and last non-empty lines. Returns the line's text
if it's purely digits or purely roman numerals and ≤4 characters (last line
checked first, since footers are more common than headers for page numbers
in textbooks). Returns `None` if neither line qualifies -- expected for
books that don't print folio numbers at all, or where the printed number
wasn't OCR'd cleanly.

#### `match_chapter_titles(a: list[ChapterEntry], b: list[ChapterEntry]) -> list[tuple[ChapterEntry, ChapterEntry]]`

Fuzzy-matches titles between two chapter lists (normalize: lowercase, strip
leading "Chapter N"/punctuation, then `difflib.SequenceMatcher` ratio
> 0.8). Returns matched pairs only; unmatched entries on either side are
dropped silently (logged at debug level).

#### `compute_folio_offset(outline_chapters, toc_chapters) -> int | None`

For each title-matched pair with both a `physical_page` and a `folio_page`,
computes `physical_page - folio_page`. If **at least 2 samples agree**
(exact match, or all within the same small range consistent with off-by-one
matching noise), returns the consensus offset. Otherwise logs a `WARNING`
listing the disagreeing samples and returns `None` -- callers must treat
`None` as "don't tag folio numbers for this book," not as 0.

#### `bootstrap_chapter_index_from_front_matter(front_matter_text, front_matter_start_page) -> tuple[list[ChapterEntry], int | None]`

Used only when there's no embedded outline. Given the **already-converted**
markdown of the front-matter chunk (with `<!-- page N -->` markers already
applied -- see Chunk 0 below):

1. `parse_printed_toc()` on the whole front-matter text → `toc_chapters`
   (folio only). If empty, return `([], None)` -- bootstrap failed, caller
   falls back to no chapter awareness at all.
2. Slice the front-matter text per physical page using the `<!-- page N -->`
   markers; run `detect_printed_folio()` on each page.
3. Find the physical page whose detected folio equals `toc_chapters[0]`'s
   folio (typically "1"). This is the anchor. If no page matches, return
   `([], None)` -- bootstrap failed.
4. `offset = anchor_physical_page - anchor_folio`. For every `toc_chapters`
   entry with a purely-numeric `folio_page >= anchor_folio`, set
   `physical_page = folio_page + offset`. Entries with roman-numeral or
   otherwise unresolvable folios are kept with `physical_page=None` and
   excluded from chunking (they're always front matter anyway).
5. Return `(resolved_chapters, offset)`.

This reuses the exact same TOC-parsing and folio-detection primitives as
the dual-tagging path (step below) -- it's the same offset computation, just
run before any embedded outline exists to short-circuit it.

### Page/folio tagging

`run_conversion()` sets `"paginate_output": True` on the shared converter
config. Marker then inserts `\n\n{N}` + 48 dashes + `\n\n` between pages in
every rendered chunk, where `N` is **local to that chunk's temp PDF**
(always starts at 0).

New function in `convert_textbook.py`:

```python
def remap_page_markers(text: str, physical_offset: int, folio_offset: int | None) -> str
```

Regex-replaces each Marker page marker with:

```
<!-- page {physical_offset + N} -->
```

or, when `folio_offset is not None` and `physical_offset + N >= front_matter_end_page`:

```
<!-- page {physical_offset + N} --><!-- folio {physical_offset + N - folio_offset} -->
```

Applied after every `text_from_rendered()` call in `process_page_range()` --
the main chunk-level path (`physical_offset = start_page`), the per-page
fallback path (`physical_offset = single_p`), and the raw-PyPDF last-resort
tier, which gets the same `<!-- page N -->` tag prepended directly (no
Marker output to remap there) in place of its current ad hoc
`<!-- PyPDF Fallback: Page N -->` comment -- folded into one consistent tag
format across all three tiers.

Folio tags are physical-page-index-anchored, not folio-number-anchored --
only pages at or after `front_matter_end_page` get one, since front matter
almost always uses a separate roman-numeral sequence this design doesn't
attempt to track.

### Chunk boundary computation

Replaces the current `chunk_ranges = list(range(0, total_pages, effective_chunk_size))`
one-liner in `process_one_pdf()`.

```python
def compute_chunk_boundaries(converter, reader, workspace, total_pages,
                              max_chunk_size, max_front_matter_pages,
                              max_boundary_shift) -> tuple[list[tuple[int, int]], int | None]
```

Returns `(boundaries, folio_offset)`.

1. **Chunk 0 (front matter).** `get_outline_chapters(reader)` first. If it
   returns entries, `front_matter_end_page = outline_chapters[0].physical_page`
   -- clean, free, no extra Marker call. If it returns `[]`, front matter is
   converted up front as its own chunk, capped at
   `min(--max-front-matter-pages, total_pages)`, and
   `bootstrap_chapter_index_from_front_matter()` is run on the result to
   both find `front_matter_end_page` (the first resolved chapter's physical
   page) and synthesize a chapter index for the rest of the book. If
   bootstrap also fails, `front_matter_end_page` falls back to a fixed
   small guess (e.g. `min(20, total_pages)`) and chunking proceeds with no
   chapter awareness at all -- today's behavior, safety-netted by the
   probe.
2. **Folio offset**, independent of which path found chapters: if an
   embedded outline was used, still attempt `parse_printed_toc()` +
   `compute_folio_offset()` against it purely for tagging purposes (chunking
   doesn't need it in this case). If bootstrap was used, the offset it
   already computed is reused directly.
3. **Chapter packing.** Starting from `front_matter_end_page`, greedily
   accumulate consecutive chapter-index entries into a chunk while
   `next_chapter.physical_page - current_start <= max_chunk_size`; cut when
   the next chapter would exceed it. Produces chunks that never split a
   chapter, sized up to `max_chunk_size`.
4. **Oversized chapters / no chapter index.** Any span still exceeding
   `max_chunk_size` (a single chapter bigger than the cap, or the entire
   remainder when no chapter index exists at all) is subdivided by
   `probe_and_shift_boundary()`.
5. Persist `boundaries` and `folio_offset` to `run_config.json` (alongside
   the existing `chunk_size`). A resumed run loads them directly rather
   than recomputing -- guarantees identical chunking and tagging across
   resumes regardless of any nondeterminism in the probe step.

### Boundary safety probe (fallback only)

```python
def probe_and_shift_boundary(converter, reader, workspace, candidate_end_page,
                              max_shift, hard_limit_page) -> int
```

Only invoked for spans not already chapter-aligned. Runs a single-page
Marker conversion on page `candidate_end_page - 1` (cost: one page-level
inference, comparable to the existing per-page fallback tier -- negligible
against 150-page chunks). Checks whether that page's content looks
unterminated:

- **Primary check:** inspect Marker's rendered block structure for the
  page; if the last block's type is one of `{Table, TableGroup, Equation,
  Form}`, treat as unsafe. *Caveat, stated plainly:* I can't verify the
  exact attribute path for this from outside the VM's installed Marker
  version -- this needs confirming against a real run.
- **Fallback check** (used if the structured path isn't available, or
  always as a second signal): the last non-empty line of the rendered
  markdown contains an unclosed table row (`|` with no matching close on
  the same line) or unbalanced math delimiters (`$$`/`\[` opened, not
  closed).

If unsafe, shift the candidate forward one page and re-probe, up to
`max_shift` pages, then commit wherever it lands (bounded forward progress
guaranteed either way). Never shifts past `hard_limit_page` (the start of
the next already-known chapter boundary, or `total_pages`).

### New CLI flags

- `--chunk-size` (existing, default 150): help text updated to "maximum
  pages per chunk (soft cap) -- chunks are aligned to chapter boundaries
  when available and may be smaller."
- `--max-boundary-shift` (new, default 15): max pages the safety probe may
  shift a fallback chunk boundary forward.
- `--max-front-matter-pages` (new, default 50): cap on how far the
  front-matter bootstrap will scan before giving up.
- `--no-chapter-chunking` (new, `BooleanOptionalAction`, default enabled):
  escape hatch back to today's pure fixed-interval chunking, for debugging
  or A/B comparison against the new behavior on a real book.

## Edge cases

| Situation | Behavior |
|---|---|
| No outline, no parseable TOC | Full fallback to fixed-interval + shift-probe chunking, no folio tags. Today's behavior, safety-netted. |
| Outline present, TOC parse/match fails | Chunking is chapter-aware (from outline); no folio tags (page tags still present). |
| Offset anchors disagree | No folio tags, `WARNING` logged with the disagreeing samples. Chunking unaffected -- it never depends on folio offset. |
| Single chapter larger than `--chunk-size` | Subdivided within its span via the shift-probe. |
| Front matter longer than `--max-front-matter-pages` | Chunk 0 capped there; bootstrap only scans within the cap, treated as failed if no anchor found in range. |
| Resumed run | Loads persisted `boundaries`/`folio_offset` from `run_config.json` verbatim; never recomputes. |

## Testing

**Unit tests (new, `test_chapter_index.py`, stdlib `unittest`, no GPU/Marker
dependency -- runnable on this machine):**

- `get_outline_chapters` against a synthetic PDF built with
  `PdfWriter.add_outline_item` (pypdf can construct this locally).
- `parse_printed_toc` against sample markdown TOC text fixtures (dot-leader
  style, plain-trailing-number style, and a negative case with no TOC
  heading).
- `detect_printed_folio` against sample page-text fixtures (arabic, roman,
  and no-folio cases).
- `match_chapter_titles` / `compute_folio_offset`, including a
  disagreeing-samples case that must return `None`.
- `compute_chunk_boundaries`'s greedy packing logic, given a fake
  pre-built chapter index and `max_chunk_size` (no real PDF/PDF I/O
  needed -- pure list-of-tuples in, list-of-tuples out).
- `remap_page_markers` against Marker's literal paginate_output format.

**Not unit-testable here:** `probe_and_shift_boundary`'s Marker-dependent
block-type inspection. It will log its decisions clearly (page number,
detected block type or heuristic match, shift applied) so they can be
sanity-checked against a real run on the VM. This is the one piece of the
design I'd flag as needing a live validation pass -- specifically on a book
with a known mid-page table or formula -- before trusting it in production.
