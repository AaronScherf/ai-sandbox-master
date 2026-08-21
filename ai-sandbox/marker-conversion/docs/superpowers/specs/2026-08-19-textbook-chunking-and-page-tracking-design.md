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
- Marker's own internal anchors and links (`<span id="page-N-M">`,
  `(#page-N-M)`), which currently collide across chunks and point at the
  wrong target for every chunk past the first, resolve correctly in the
  merged output.
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

## Real-world validation

Before finalizing this design, three actual pipeline outputs were inspected
directly (`academic-hub/processed_outputs/{Axler_Linear_Algebra_Done_Right_2026,
Hammack_Book_of_Proof_2025,Rudin_Principles_of_Mathematical_Analysis_2014}`)
to check the design generalizes rather than being tailored to one book:

- **Axler** (born-digital, real embedded hyperlinks): TOC renders as
  `[Title](#page-N-0)` links followed by the printed folio number as plain
  text; chapter-level entries are preceded by a standalone `### Chapter N`
  line. Confirmed the chunk-local page reset bug directly: `id="page-1-0"`
  (and others) appear multiple times in the merged output, once per chunk,
  because each chunk is converted as an independent PDF starting its own
  page numbering at 0 -- meaning the TOC's own internal links are currently
  broken for every chapter past the first chunk.
- **Hammack** (born-digital, prose-typeset TOC): TOC renders as a markdown
  *table*, not links -- only one incidental link in the entire TOC (a Part
  heading). Chapter rows carry no separate marker line; the row itself
  starts with a bare `N.` (`1. Sets`, `2. Logic`), not the word "Chapter".
  Column-splitting is occasionally messy (a trailing page number glued into
  the wrong cell). `<span id="page-N-M">` anchors are present (Marker emits
  them from its own heading detection, independent of whether the TOC has
  clickable links) but almost nothing links to them.
- **Rudin** (scanned, no embedded text layer): zero `<span id="page-...">`
  anchors and zero markdown links anywhere in the output -- anchor/link
  emission is conditional on the source PDF having real embedded structure,
  not a universal Marker behavior. TOC is a markdown table with chapter rows
  literally prefixed `Chapter N`. The printed roman numeral "ix" was OCR'd
  as `lX` (lowercase L, not lowercase i) -- a naive roman-numeral regex
  would silently misparse this as L+X=60 rather than recognizing garbled
  "ix"=9. The TOC itself spans a page break and Marker renders it as two
  separate, adjacent markdown tables rather than one continuous block.

Net effect: no single "primary" TOC format exists across real books. The
design below treats TOC-line parsing as one generalized parser with
opportunistic link capture, not a link-based primary path with a
table-parsing fallback. The chunk-boundary corruption this design defends
against (a table/formula split across a chunk boundary) wasn't observed at
either of Axler's two chunk boundaries in this sample -- expected, since
150 pages doesn't reliably land badly every time -- but the anchor/link
collision bug is directly, concretely confirmed, and is now explicit scope
(see "Anchor and link remapping" below).

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

Parses the front matter's *own rendered* table of contents, generalized
across three observed real-world shapes (link lists, single-column
prose-style tables, and multi-block tables split across a page break) --
not tailored to any one of them.

1. Find the TOC region: a heading line matching `Contents` / `Table of
   Contents` (case-insensitive, any heading level). Keep consuming
   subsequent lines/blocks as long as they look TOC-like (table rows, or
   short lines ending in a page-number-like token -- see step 3); a markdown
   table ending doesn't end the region by itself, since Rudin's TOC
   demonstrates a single logical TOC can render as two or more separate
   adjacent table blocks across a page break. The region ends at the first
   line that's neither.
2. For each line in the region, normalize it to plain text regardless of
   its markdown shape: split markdown table rows (`|`) into cells and
   consider each cell in isolation; strip bold/italic markers; if the line
   contains a link `[text](#page-N-M)`, keep the link text as the title
   candidate and separately record `physical_page = N` -- this is a bonus
   signal, present in Axler, absent in Hammack and Rudin.
3. A normalized line/cell is a **candidate entry** if it ends in a short
   trailing token that looks like a folio number: `\d{1,4}$` (arabic), or
   `[ivxlcdm]{1,7}$` case-insensitive (roman) -- with one tolerance: a
   leading lowercase `l` immediately followed by another roman-numeral
   letter is treated as an OCR misread of lowercase `i` before matching
   (confirmed necessary: Rudin's printed "ix" was OCR'd as literal `lX`,
   which without this normalization would parse as a *valid* but wrong
   roman numeral, L+X=60, instead of being recognized as garbled ix=9).
4. A candidate entry is **chapter-level** (vs. a subsection, which is
   ignored) if any of these hold -- all three are drawn directly from the
   three books checked, since no single one covered every case:
   - the line/cell's own text starts with `Chapter\s+\d+` (Rudin), or
   - it starts with a bare `\d+\.?\s` where the digits are a plain integer,
     not decimal/dotted like `1.1` (Hammack), or
   - it's the line immediately following a standalone line that itself
     matches only `Chapter\s+\d+`, e.g. `### Chapter 1` on its own line
     (Axler) -- in this case the chapter number lives on the marker line
     and the title/folio live on the line after it.
   `title` is whatever text remains after stripping the matched
   chapter-number prefix (or, in the Axler case, the full text of the
   following title line); `folio_page` is the trailing token from step 3.
5. Returns `[]` if no TOC heading is found at all -- expected and fine for
   books without a formal TOC page. Malformed/garbled lines that don't
   cleanly match are skipped, not raised on -- confirmed necessary by a
   garbled OCR line observed in Axler's own subsection entries
   (`### 1A ... [and](#page-15-0) ... 2`, a mangled merge of two adjacent TOC
   lines). Chapter-level extraction deliberately doesn't depend on
   subsection lines parsing cleanly at all.

#### `detect_printed_folio(page_text: str) -> str | None`

Given the markdown slice for **one physical page** (sliced from an
already-converted chunk using our own `<!-- page N -->` markers -- see
below), checks the first and last non-empty lines. Returns the line's text
if it's purely digits, or purely roman numerals under the same
lowercase-`l`-tolerant matching used in `parse_printed_toc` step 3, and
≤4 characters (last line checked first, since footers are more common than
headers for page numbers in textbooks). Returns `None` if neither line
qualifies -- expected for books that don't print folio numbers at all
(common on scanned front-matter pages), or where the printed number wasn't
OCR'd cleanly.

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

### Anchor and link remapping

New scope, added after inspecting real output: Marker emits
`<span id="page-N-M"></span>` anchors from its own heading/structure
detection (confirmed present in both born-digital books checked, Axler and
Hammack; absent entirely in the scanned Rudin output, where Marker has no
structure to anchor). Internal links -- both the TOC's own `[Title](#page-N-M)`
entries and any in-body cross-references Marker generated -- point at these
same ids. Because `N` is chunk-local, the *current* pipeline already
produces colliding, wrong anchors: confirmed directly in Axler's output,
where `id="page-1-0"` (and others) appear three times in the merged file,
once per chunk, so any link generated against a chapter past the first
chunk resolves to the wrong (first-chunk) target once rendered by a
markdown viewer that respects anchors.

Fix: `remap_page_markers` (or a small sibling run over the same chunk text)
also rewrites every `id="page-N-M"` and every `(#page-N-M)` link target it
finds, applying the same `physical_offset` used for the page tags. This is
a no-op for books like Rudin with no anchors to begin with -- the regex
simply finds nothing to rewrite. No new fallback tier needed; it rides on
the offset already being computed for page tagging.

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
| TOC has no clickable links at all (Hammack, Rudin) | `parse_printed_toc` still extracts title+folio from table rows/prose lines; `physical_page` stays unresolved from the parse itself and is filled in by the outline (if present) or the anchor-bootstrap (if not). Not a degraded case -- this is the *common* case, not the exception. |
| TOC spans a page break, rendered as 2+ separate markdown tables (Rudin) | `parse_printed_toc`'s region-detection keeps consuming consecutive TOC-shaped blocks rather than stopping at the first table's end. |
| Roman-numeral folio OCR'd with a stray lowercase `l` for `i` (Rudin: printed "ix" → literal `lX`) | Normalized before roman-numeral matching, everywhere it's checked (`parse_printed_toc` and `detect_printed_folio`). A garbled front-matter entry that still slips through doesn't threaten offset correctness either way -- offsets are only computed from arabic chapter-level entries. |
| Book has `<span id="page-N-M">` anchors but no/few TOC links (Hammack) | Anchor remapping (see "Anchor and link remapping") still applies -- it isn't conditioned on the TOC being link-based. |

## Testing

**Unit tests (new, `test_chapter_index.py`, stdlib `unittest`, no GPU/Marker
dependency -- runnable on this machine):**

- `get_outline_chapters` against a synthetic PDF built with
  `PdfWriter.add_outline_item` (pypdf can construct this locally).
- `parse_printed_toc` against fixtures drawn directly from the three real
  outputs inspected: an Axler-style link list with a separate
  `### Chapter N` marker line, a Hammack-style markdown table with a bare
  `N.` chapter prefix and a messy split-cell row, a Rudin-style two-block
  table split across a page break with a `Chapter N` prefix and the `lX`
  roman-numeral OCR artifact, and a negative case with no TOC heading.
- `detect_printed_folio` against sample page-text fixtures (arabic, roman
  including the `l`-for-`i` OCR case, and no-folio cases).
- `match_chapter_titles` / `compute_folio_offset`, including a
  disagreeing-samples case that must return `None`.
- `compute_chunk_boundaries`'s greedy packing logic, given a fake
  pre-built chapter index and `max_chunk_size` (no real PDF/PDF I/O
  needed -- pure list-of-tuples in, list-of-tuples out).
- `remap_page_markers` against Marker's literal paginate_output format, and
  a variant covering `<span id="page-N-M">` / `(#page-N-M)` remapping using
  the actual colliding-anchor pattern found in the Axler output.

**Not unit-testable here:** `probe_and_shift_boundary`'s Marker-dependent
block-type inspection. It will log its decisions clearly (page number,
detected block type or heuristic match, shift applied) so they can be
sanity-checked against a real run on the VM. This is the one piece of the
design I'd flag as needing a live validation pass -- specifically on a book
with a known mid-page table or formula -- before trusting it in production.
