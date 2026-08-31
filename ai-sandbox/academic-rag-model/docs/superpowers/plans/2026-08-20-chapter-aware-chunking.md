# Chapter-Aware Chunking and Page/Folio Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `convert_textbook.py` align chunk boundaries to chapter breaks (never splitting a table/formula/chapter), tag every output page with its physical PDF page number and (where derivable) its printed folio number, and fix the page-anchor/link collisions Marker's own output currently has across chunks.

**Architecture:** Two new pure-Python modules with zero `marker`/`torch`/`surya` dependency (`chapter_index.py` for building a chapter index from either the PDF's embedded outline or a bootstrapped parse of its own printed TOC, and `page_markers.py` for rewriting Marker's chunk-local page/anchor/link output into book-wide numbering) are unit-tested locally with stdlib `unittest`. `convert_textbook.py` is then modified to wire these in: `paginate_output=True` on the converter, a new `compute_chunk_boundaries()` orchestration function replacing the fixed-interval one-liner, and a Marker-dependent single-page safety probe for spans that aren't chapter-aligned. The Marker-dependent pieces can't run locally (this machine has no CUDA/`torch`) and are covered by a written VM validation checklist instead of automated tests.

**Tech Stack:** Python 3.13, `pypdf` (already a pipeline dependency), stdlib `unittest`, `difflib`. No new runtime dependencies.

**Spec:** `ai-sandbox/marker-conversion/docs/superpowers/specs/2026-08-19-textbook-chunking-and-page-tracking-design.md`

## Global Constraints

- No new runtime dependency beyond `pypdf` (already installed by `marker_setup.sh`). `paginate_output` is a config flag on the existing `marker-pdf` package, not a new package.
- `chapter_index.py` and `page_markers.py` must never import `marker`, `torch`, or `surya`, directly or transitively -- that's the entire reason they're separate modules, and it's what makes their tests runnable on this machine (no CUDA here) instead of only on the GCP VM.
- Tests use stdlib `unittest` only -- no `pytest` or other new test-framework dependency (matches the spec's Testing section).
- Every existing checkpoint/resume guarantee in `convert_textbook.py` must still hold: a resumed run must never recompute chunk boundaries or the folio offset differently than the original run.
- New CLI flags must default to preserving forward compatibility with the existing invocation in `gcp_instructions.md` Step 3.3 (`python3 -u ~/convert_textbook.py $GCS_INPUT_URIS --output ...`) -- no flag is required for that command to keep working.
- Offset sign convention, fixed throughout: `folio_offset = physical_page - folio_page`, so `folio_page = physical_page - folio_offset`. Every function that touches an offset uses this same direction.

---

## File Structure

- **Create** `ai-sandbox/marker-conversion/.gitignore` -- this branch currently has none at all; needed before Task 1 so a local test venv and `__pycache__` never get accidentally staged.
- **Create** `ai-sandbox/marker-conversion/chapter_index.py` -- `ChapterEntry`, outline extraction, printed-TOC parsing, folio detection, title matching, offset computation, front-matter bootstrap, and the pure chapter-packing algorithm. No marker/torch dependency.
- **Create** `ai-sandbox/marker-conversion/test_chapter_index.py` -- stdlib `unittest` tests for everything above, using fixtures modeled directly on the real Axler/Hammack/Rudin output.
- **Create** `ai-sandbox/marker-conversion/page_markers.py` -- rewrites Marker's chunk-local page-break markers, `<span id="page-N-M">` anchors, and `(#page-N-M)` links into book-wide numbering, plus folio tags. No marker/torch dependency.
- **Create** `ai-sandbox/marker-conversion/test_page_markers.py` -- stdlib `unittest` tests, including the real colliding-anchor pattern found in Axler's output.
- **Modify** `ai-sandbox/marker-conversion/convert_textbook.py` -- wire `paginate_output=True`, integrate `page_markers` into all three tiers of `process_page_range()`, add `probe_and_shift_boundary()` and new CLI flags, add the `compute_chunk_boundaries()` orchestration wrapper (imports `chapter_index`), wire it into `process_one_pdf()`, persist/load boundaries and folio offset via `run_config.json`.
- **Create** `ai-sandbox/marker-conversion/docs/superpowers/plans/2026-08-20-vm-validation-checklist.md` -- the manual validation runbook for the pieces that can't be tested off the VM, and the artifact the user asked to keep for reviewing/improving this across future sessions and other textbooks.

---

## Task 1: Local dev setup, `.gitignore`, `ChapterEntry`, and `get_outline_chapters`

**Files:**
- Create: `ai-sandbox/marker-conversion/.gitignore`
- Create: `ai-sandbox/marker-conversion/chapter_index.py`
- Create: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Produces: `ChapterEntry` dataclass (`title: str`, `physical_page: int | None = None`, `folio_page: int | None = None`, `folio_is_roman: bool = False`, `folio_raw: str | None = None`) and `get_outline_chapters(reader) -> list[ChapterEntry]`, both used by every later task in this module.

- [ ] **Step 1: Set up a local venv and install pypdf**

This machine has no `pypdf` installed globally (confirmed: `python -c "import pypdf"` fails), and no `torch`/`marker` either (confirmed, expected -- this pipeline is documented as VM-only). All work in this plan up through Task 8 only needs `pypdf`.

```bash
cd ai-sandbox/marker-conversion
python -m venv .venv
source .venv/Scripts/activate
pip install pypdf
python -c "import pypdf; print(pypdf.__version__)"
```

Expected: prints a version number with no error.

- [ ] **Step 2: Add `.gitignore`**

This branch has no `.gitignore` at all yet. Without one, the venv from Step 1 and any `__pycache__` directories would show up as untracked noise (or get accidentally `git add -A`'d).

```
.venv/
__pycache__/
*.pyc
```

- [ ] **Step 3: Write the failing test for `get_outline_chapters`**

`ai-sandbox/marker-conversion/test_chapter_index.py`:

```python
import io
import unittest

from pypdf import PdfReader, PdfWriter

from chapter_index import ChapterEntry, get_outline_chapters


def _pdf_with_outline(entries):
    """entries: list of (title, page_index) for top-level outline items."""
    writer = PdfWriter()
    for _ in range(10):
        writer.add_blank_page(width=200, height=200)
    for title, page_index in entries:
        writer.add_outline_item(title, page_index)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return PdfReader(buf)


class TestGetOutlineChapters(unittest.TestCase):
    def test_extracts_top_level_entries_with_physical_pages(self):
        reader = _pdf_with_outline([("Vector Spaces", 0), ("Finite-Dimensional Vector Spaces", 3)])
        chapters = get_outline_chapters(reader)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0], ChapterEntry(title="Vector Spaces", physical_page=0))
        self.assertEqual(chapters[1], ChapterEntry(title="Finite-Dimensional Vector Spaces", physical_page=3))

    def test_no_outline_returns_empty_list(self):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        reader = PdfReader(buf)
        self.assertEqual(get_outline_chapters(reader), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the test to verify it fails**

```bash
cd ai-sandbox/marker-conversion
source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'chapter_index'`.

- [ ] **Step 5: Write `chapter_index.py`**

```python
"""
chapter_index.py
Pure-Python helpers for building a chapter index from a textbook PDF --
either from its embedded outline, or bootstrapped from a parse of its own
rendered table of contents -- used by convert_textbook.py to align chunk
boundaries to chapter breaks and to tag output pages with physical PDF page
index and (where derivable) printed folio number.

Deliberately has NO dependency on marker, torch, or surya: convert_textbook.py
imports those at module scope, which requires the GCP VM's CUDA environment
to even succeed, so nothing that depends on them can be unit tested off that
VM. Everything in this module can be, on any machine with pypdf installed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChapterEntry:
    title: str
    physical_page: int | None = None
    folio_page: int | None = None
    folio_is_roman: bool = False
    folio_raw: str | None = None


def get_outline_chapters(reader) -> list[ChapterEntry]:
    """
    Top-level (depth 1) entries from the PDF's embedded outline/bookmarks,
    resolved to physical page numbers. Never raises: returns [] if there's
    no outline, or if resolving any entry fails outright.
    """
    try:
        outline = reader.outline
    except Exception:
        return []
    if not outline:
        return []

    chapters = []
    for item in outline:
        # pypdf represents nested outline levels as sub-lists; only take
        # top-level Destination objects here, not nested lists (those are
        # subsections, which chunking deliberately ignores).
        if isinstance(item, list):
            continue
        try:
            page_num = reader.get_destination_page_number(item)
            title = str(item.title).strip()
        except Exception:
            continue
        if title:
            chapters.append(ChapterEntry(title=title, physical_page=page_num))
    return chapters
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
cd ai-sandbox/marker-conversion
source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
cd ai-sandbox/marker-conversion
git add .gitignore chapter_index.py test_chapter_index.py
git commit -m "Add chapter_index.py with ChapterEntry and get_outline_chapters"
```

---

## Task 2: Folio token parsing (arabic/roman, with OCR tolerance)

**Files:**
- Modify: `ai-sandbox/marker-conversion/chapter_index.py`
- Modify: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_parse_folio_token(token: str) -> tuple[int | None, bool, str | None]` (folio_page, is_roman, folio_raw), used by Task 3 (`parse_printed_toc`) and Task 4 (`detect_printed_folio`). Not part of the module's public surface (leading underscore), but its behavior is directly load-bearing for both.

- [ ] **Step 1: Write the failing tests**

Append to `ai-sandbox/marker-conversion/test_chapter_index.py`:

```python
from chapter_index import _parse_folio_token


class TestParseFolioToken(unittest.TestCase):
    def test_arabic(self):
        self.assertEqual(_parse_folio_token("157"), (157, False, "157"))

    def test_roman(self):
        self.assertEqual(_parse_folio_token("xvii"), (17, True, "xvii"))

    def test_ocr_lowercase_l_for_i(self):
        # Rudin's printed "ix" (9) was OCR'd as literal "lX".
        self.assertEqual(_parse_folio_token("lX"), (9, True, "lX"))

    def test_genuine_capital_l_not_misread(self):
        # A real roman numeral "L" (50) is uppercase in print; a lowercase
        # 'l' as the whole token is ambiguous OCR noise, not confidently
        # correctable, so it's rejected outright rather than guessed at.
        self.assertEqual(_parse_folio_token("l"), (None, False, None))

    def test_not_a_folio(self):
        self.assertEqual(_parse_folio_token("Sets"), (None, False, None))
        self.assertEqual(_parse_folio_token("12345"), (None, False, None))  # too long to be a folio


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ImportError: cannot import name '_parse_folio_token'`.

- [ ] **Step 3: Implement in `chapter_index.py`**

Append:

```python
import re

_ROMAN_CHARS = "ivxlcdm"
_ARABIC_FOLIO_RE = re.compile(r"^\d{1,4}$")
_ROMAN_FOLIO_RE = re.compile(r"^[ivxlcdm]{1,7}$", re.IGNORECASE)
_ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
_ROMAN_TABLE = [
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
    (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
    (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
]


def _normalize_roman_ocr(token: str) -> str:
    """
    Corrects a common OCR confusion where a printed lowercase roman
    numeral 'i' is misread as lowercase 'l' -- confirmed against real
    output: Rudin's printed "ix" (9) came out as literal "lX". Only
    triggers on a leading lowercase 'l' immediately followed by another
    uppercase roman letter, since a genuine roman numeral is consistently
    cased within one token -- a lowercase 'l' next to an uppercase letter
    is itself the tell that this isn't a real roman numeral as typed.
    """
    if len(token) >= 2 and token[0] == "l" and token[1].isupper() and token[1].lower() in _ROMAN_CHARS:
        return "i" + token[1:]
    return token


def _int_to_roman(n: int) -> str:
    if n <= 0 or n > 3999:
        return ""
    result = []
    for value, symbol in _ROMAN_TABLE:
        while n >= value:
            result.append(symbol)
            n -= value
    return "".join(result)


def _roman_to_int(token: str) -> int | None:
    """Converts a roman numeral string to an int, or None if invalid.
    Round-trips the result back through _int_to_roman to reject
    non-canonical junk (e.g. "iiii", "vv") that naive subtractive-pair
    parsing would otherwise accept."""
    token = token.lower()
    if not token or any(ch not in _ROMAN_VALUES for ch in token):
        return None
    total, prev = 0, 0
    for ch in reversed(token):
        value = _ROMAN_VALUES[ch]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    if _int_to_roman(total) != token:
        return None
    return total


def _parse_folio_token(token: str) -> tuple[int | None, bool, str | None]:
    """
    Given a candidate trailing token from a TOC line or a page's own
    header/footer, returns (folio_page, is_roman, folio_raw), or
    (None, False, None) if it doesn't look like a folio number at all.
    """
    if _ARABIC_FOLIO_RE.match(token):
        return int(token), False, token
    normalized = _normalize_roman_ocr(token)
    if _ROMAN_FOLIO_RE.match(normalized):
        value = _roman_to_int(normalized)
        if value is not None:
            return value, True, token
    return None, False, None
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (7 tests total).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add chapter_index.py test_chapter_index.py
git commit -m "Add folio token parsing with roman-numeral OCR tolerance"
```

---

## Task 3: `parse_printed_toc`

**Files:**
- Modify: `ai-sandbox/marker-conversion/chapter_index.py`
- Modify: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Consumes: `ChapterEntry`, `_parse_folio_token` (Task 2).
- Produces: `parse_printed_toc(markdown_text: str) -> list[ChapterEntry]`, used by Task 6 (`bootstrap_chapter_index_from_front_matter`) and by `convert_textbook.py` directly (Task 11, for the outline-present dual-tagging path).

This is the parser the spec's "Real-world validation" section drove: no single TOC format covered by real books, so this scans every line for a chapter-level pattern rather than trying to detect "where does the TOC region start/end." That's a deliberate simplification versus the spec's "find TOC region" framing -- the chapter-level pattern match (`Chapter N` prefix, bare `N.` prefix, or a preceding standalone `Chapter N` line) is specific enough that it doesn't false-positive on ordinary body prose, so a heading-boundary detector turned out to be unnecessary complexity. It also means Rudin's TOC-split-across-two-tables case is handled for free -- there's no "region" to lose track of across the split.

- [ ] **Step 1: Write the failing tests**

Append to `test_chapter_index.py`. These fixtures are transcribed directly from the three real outputs, not invented:

```python
from chapter_index import parse_printed_toc


class TestParsePrintedToc(unittest.TestCase):
    def test_axler_style_links_with_marker_line(self):
        # Real excerpt shape from Axler_Linear_Algebra_Done_Right_2026.md
        text = (
            "# *Contents*\n\n"
            "# *[About the Author](#page-1-0)* **v**\n\n"
            "### Chapter 1\n\n"
            "# *[Vector Spaces](#page-14-0)* **1**\n\n"
            "### 1A [Complex Numbers and Lists](#page-15-0) 2\n\n"
            "[Exercises 1A](#page-23-0) 10\n\n"
            "### Chapter 2\n\n"
            "# *[Finite-Dimensional Vector Spaces](#page-40-0)* **27**\n\n"
        )
        chapters = parse_printed_toc(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "Vector Spaces")
        self.assertEqual(chapters[0].physical_page, 14)
        self.assertEqual(chapters[0].folio_page, 1)
        self.assertEqual(chapters[1].title, "Finite-Dimensional Vector Spaces")
        self.assertEqual(chapters[1].physical_page, 40)
        self.assertEqual(chapters[1].folio_page, 27)

    def test_hammack_style_table_bare_number_prefix(self):
        # Real excerpt shape from Hammack_Book_of_Proof_2025.md, including
        # the messy split-cell subsection row that must NOT match.
        text = (
            "## **Contents**\n\n"
            "| 1. Sets                             |                         |                            | 3          |\n"
            "|-------------------------------------|-------------------------|----------------------------|------------|\n"
            "| 1.1.                                | Introduction            | to Sets                    | 3          |\n"
            "| 2. Logic                            |                         |                            | 34         |\n"
            "| 3.6.                                | Pascal's                | Triangle and the Binomial  | Theorem 90 |\n"
        )
        chapters = parse_printed_toc(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "Sets")
        self.assertEqual(chapters[0].folio_page, 3)
        self.assertIsNone(chapters[0].physical_page)  # no link in this book's TOC
        self.assertEqual(chapters[1].title, "Logic")
        self.assertEqual(chapters[1].folio_page, 34)

    def test_rudin_style_two_block_table_chapter_word_prefix(self):
        # Real excerpt shape from Rudin_Principles_of_Mathematical_Analysis_2014.md:
        # the TOC is rendered as two separate markdown tables (a page break
        # in the source) with no blank-line-free continuity between them.
        text = (
            "## CONTENTS\n\n"
            "| Preface                                       | lX |\n"
            "|-----------------------------------------------|----|\n"
            "| Chapter 1 The Real and Complex Number Systems | 1  |\n"
            "| Introduction                                  | 1  |\n\n"
            "| Connected Sets                                  | 42         |\n"
            "|-------------------------------------------------|------------|\n"
            "| <b>Chapter 3 Numerical Sequences and Series</b> | <b>47</b>  |\n"
        )
        chapters = parse_printed_toc(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "The Real and Complex Number Systems")
        self.assertEqual(chapters[0].folio_page, 1)
        self.assertEqual(chapters[1].title, "Numerical Sequences and Series")
        self.assertEqual(chapters[1].folio_page, 47)

    def test_no_toc_returns_empty(self):
        self.assertEqual(parse_printed_toc("Just some ordinary prose about eigenvalues."), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ImportError: cannot import name 'parse_printed_toc'`.

- [ ] **Step 3: Implement in `chapter_index.py`**

Append:

```python
_CHAPTER_WORD_RE = re.compile(r"^chapter\s+\d+\b[.:]?\s*(.*)$", re.IGNORECASE)
_CHAPTER_WORD_NUM_RE = re.compile(r"^chapter\s+(\d+)\b", re.IGNORECASE)
_STANDALONE_CHAPTER_MARKER_RE = re.compile(r"^chapter\s+(\d+)\s*$", re.IGNORECASE)
_BARE_CHAPTER_NUM_RE = re.compile(r"^(\d+)\.?\s+(\S.*)$")
_TOC_LINK_RE = re.compile(r"\[([^\]]*)\]\(#page-(\d+)-\d+\)")


def _cells_from_markdown_line(line: str) -> str:
    """Joins a markdown table row's non-empty, non-separator cells with a
    single space. For a non-table line, strips a leading heading marker
    (#, ##, ...) and returns the rest unchanged."""
    stripped = re.sub(r"^#{1,6}\s*", "", line.strip())
    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        cells = [c for c in cells if c and not re.fullmatch(r"-+", c)]
        return " ".join(cells)
    return stripped


def _strip_markdown_inline(text: str) -> tuple[str, int | None]:
    """
    Strips bold/italic markup and <b>/<i> tags. If a markdown link
    [text](#page-N-M) is present, replaces it with its visible text and
    separately returns the physical page N; otherwise returns
    (cleaned_text, None).
    """
    physical_page = None
    m = _TOC_LINK_RE.search(text)
    if m:
        physical_page = int(m.group(2))
        text = text[: m.start()] + m.group(1) + text[m.end() :]
    text = re.sub(r"</?b>|</?i>", "", text)
    text = re.sub(r"[*_]{1,3}", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, physical_page


def parse_printed_toc(markdown_text: str) -> list[ChapterEntry]:
    """
    Extracts chapter-level (title, physical_page, folio_page) entries from
    a book's own rendered table of contents. Scans every line rather than
    trying to detect a TOC "region" -- the chapter-level match itself
    (Chapter N prefix, bare N. prefix, or a preceding standalone Chapter N
    marker line) is specific enough not to false-positive on body prose,
    and this also means a TOC split across multiple separate markdown
    tables (observed in Rudin, due to a page break mid-TOC) is handled
    without any special-casing. Subsection-level entries and non-chapter
    front-matter entries (Preface, Acknowledgments, ...) are silently
    skipped, not raised on -- confirmed necessary by a garbled OCR line
    observed in Axler's own subsection entries.
    """
    chapters: list[ChapterEntry] = []
    pending_chapter_num: str | None = None

    for raw_line in markdown_text.splitlines():
        joined = _cells_from_markdown_line(raw_line)
        if not joined:
            continue
        text, physical_page = _strip_markdown_inline(joined)
        if not text:
            continue

        standalone = _STANDALONE_CHAPTER_MARKER_RE.match(text)
        if standalone:
            pending_chapter_num = standalone.group(1)
            continue

        chapter_num, remainder = None, text
        m = _CHAPTER_WORD_NUM_RE.match(text)
        if m:
            chapter_num = m.group(1)
            remainder = _CHAPTER_WORD_RE.match(text).group(1)
        else:
            m = _BARE_CHAPTER_NUM_RE.match(text)
            if m:
                chapter_num, remainder = m.group(1), m.group(2)
            elif pending_chapter_num is not None:
                chapter_num, remainder = pending_chapter_num, text

        pending_chapter_num = None  # consumed either way -- one shot

        if chapter_num is None:
            continue

        tokens = remainder.rsplit(None, 1)
        if len(tokens) != 2:
            continue
        title_text, last_token = tokens
        folio_page, folio_is_roman, folio_raw = _parse_folio_token(last_token)
        if folio_page is None:
            continue

        title_text = title_text.strip(" .")
        if not title_text:
            continue

        chapters.append(
            ChapterEntry(
                title=title_text,
                physical_page=physical_page,
                folio_page=folio_page,
                folio_is_roman=folio_is_roman,
                folio_raw=folio_raw,
            )
        )

    return chapters
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (11 tests total).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add chapter_index.py test_chapter_index.py
git commit -m "Add parse_printed_toc, generalized across link/table/prefix TOC styles"
```

---

## Task 4: `detect_printed_folio`

**Files:**
- Modify: `ai-sandbox/marker-conversion/chapter_index.py`
- Modify: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Consumes: `_parse_folio_token` (Task 2).
- Produces: `detect_printed_folio(page_text: str) -> tuple[int, bool, str] | None`, used by Task 6.

- [ ] **Step 1: Write the failing tests**

Append to `test_chapter_index.py`:

```python
from chapter_index import detect_printed_folio


class TestDetectPrintedFolio(unittest.TestCase):
    def test_arabic_footer(self):
        page = "Some body text on this page.\n\nMore text.\n\n157"
        self.assertEqual(detect_printed_folio(page), (157, False, "157"))

    def test_roman_header_with_ocr_artifact(self):
        page = "lX\n\nPreface text starts here and continues for a while."
        self.assertEqual(detect_printed_folio(page), (9, True, "lX"))

    def test_no_folio_present(self):
        page = "Just a page of ordinary prose with no isolated page number."
        self.assertIsNone(detect_printed_folio(page))

    def test_empty_page(self):
        self.assertIsNone(detect_printed_folio(""))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ImportError: cannot import name 'detect_printed_folio'`.

- [ ] **Step 3: Implement in `chapter_index.py`**

Append:

```python
def detect_printed_folio(page_text: str) -> tuple[int, bool, str] | None:
    """
    Given the markdown slice for one physical page, checks the first and
    last non-empty lines for something that looks like a printed page
    number (arabic or roman, <=4 chars) -- last line checked first, since
    footers are more common than headers for page numbers in textbooks.
    Returns (folio_page, is_roman, raw_token), or None if neither line
    qualifies (expected for pages that don't print a folio at all, or
    where it wasn't OCR'd cleanly).
    """
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return None
    for candidate in (lines[-1], lines[0]):
        if len(candidate) > 4:
            continue
        folio_page, is_roman, raw = _parse_folio_token(candidate)
        if folio_page is not None:
            return folio_page, is_roman, raw
    return None
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (15 tests total).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add chapter_index.py test_chapter_index.py
git commit -m "Add detect_printed_folio for per-page header/footer scanning"
```

---

## Task 5: `match_chapter_titles` and `compute_folio_offset`

**Files:**
- Modify: `ai-sandbox/marker-conversion/chapter_index.py`
- Modify: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Consumes: `ChapterEntry`.
- Produces: `match_chapter_titles(a, b) -> list[tuple[ChapterEntry, ChapterEntry]]` and `compute_folio_offset(outline_chapters, toc_chapters) -> int | None`, used by `convert_textbook.py` (Task 11) for the outline-present dual-tagging path.

- [ ] **Step 1: Write the failing tests**

Append to `test_chapter_index.py`:

```python
from chapter_index import match_chapter_titles, compute_folio_offset


class TestMatchAndOffset(unittest.TestCase):
    def _outline(self):
        return [
            ChapterEntry(title="Vector Spaces", physical_page=14),
            ChapterEntry(title="Finite-Dimensional Vector Spaces", physical_page=40),
            ChapterEntry(title="Linear Maps", physical_page=64),
        ]

    def _toc(self, offset=13):
        return [
            ChapterEntry(title="Vector Spaces", folio_page=14 - offset, folio_is_roman=False),
            ChapterEntry(title="Finite-Dimensional Vector Spaces", folio_page=40 - offset, folio_is_roman=False),
            ChapterEntry(title="Linear Maps", folio_page=64 - offset, folio_is_roman=False),
        ]

    def test_match_by_fuzzy_title(self):
        pairs = match_chapter_titles(self._outline(), self._toc())
        self.assertEqual(len(pairs), 3)
        self.assertEqual(pairs[0][0].title, "Vector Spaces")
        self.assertEqual(pairs[0][1].title, "Vector Spaces")

    def test_offset_consensus(self):
        offset = compute_folio_offset(self._outline(), self._toc(offset=13))
        self.assertEqual(offset, 13)

    def test_offset_disagreement_returns_none(self):
        toc = self._toc(offset=13)
        toc[1].folio_page = 999  # deliberately inconsistent with the others
        self.assertIsNone(compute_folio_offset(self._outline(), toc))

    def test_too_few_samples_returns_none(self):
        outline = [ChapterEntry(title="Only One Chapter", physical_page=14)]
        toc = [ChapterEntry(title="Only One Chapter", folio_page=1)]
        self.assertIsNone(compute_folio_offset(outline, toc))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ImportError: cannot import name 'match_chapter_titles'`.

- [ ] **Step 3: Implement in `chapter_index.py`**

Append:

```python
import difflib
import logging
from collections import Counter

_logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"^chapter\s+\d+[.:]?\s*", "", t)
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def match_chapter_titles(
    a: list[ChapterEntry], b: list[ChapterEntry]
) -> list[tuple[ChapterEntry, ChapterEntry]]:
    """
    Fuzzy-matches titles between two chapter lists (e.g. outline-sourced
    physical pages vs. TOC-parsed folio numbers). Returns matched pairs
    only; unmatched entries on either side are dropped silently.
    """
    pairs = []
    used_b: set[int] = set()
    for entry_a in a:
        norm_a = _normalize_title(entry_a.title)
        best_idx, best_ratio = None, 0.0
        for idx, entry_b in enumerate(b):
            if idx in used_b:
                continue
            ratio = difflib.SequenceMatcher(None, norm_a, _normalize_title(entry_b.title)).ratio()
            if ratio > best_ratio:
                best_ratio, best_idx = ratio, idx
        if best_idx is not None and best_ratio > 0.8:
            pairs.append((entry_a, b[best_idx]))
            used_b.add(best_idx)
    return pairs


def compute_folio_offset(
    outline_chapters: list[ChapterEntry], toc_chapters: list[ChapterEntry]
) -> int | None:
    """
    Computes physical_page - folio_page from title-matched pairs (roman
    folios excluded -- they aren't part of the book's linear arabic
    sequence). Returns the consensus offset if a majority of samples agree
    within +/-1; otherwise logs a WARNING with the disagreement and returns
    None -- callers must treat None as "don't tag folio numbers," not 0.
    """
    samples = []
    for entry_a, entry_b in match_chapter_titles(outline_chapters, toc_chapters):
        physical = entry_a.physical_page if entry_a.physical_page is not None else entry_b.physical_page
        folio = entry_b.folio_page if entry_b.folio_page is not None else entry_a.folio_page
        is_roman = entry_a.folio_is_roman or entry_b.folio_is_roman
        if physical is not None and folio is not None and not is_roman:
            samples.append(physical - folio)

    if len(samples) < 2:
        _logger.warning(
            "Not enough matched chapter samples to compute a folio offset (%d found, need >=2).",
            len(samples),
        )
        return None

    counts = Counter(samples)
    consensus_offset, _ = counts.most_common(1)[0]
    agreeing = sum(c for value, c in counts.items() if abs(value - consensus_offset) <= 1)
    if agreeing < max(2, len(samples) // 2 + 1):
        _logger.warning("Folio offset samples disagree: %s -- not tagging folio numbers for this book.", dict(counts))
        return None
    return consensus_offset
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (19 tests total).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add chapter_index.py test_chapter_index.py
git commit -m "Add match_chapter_titles and compute_folio_offset"
```

---

## Task 6: `bootstrap_chapter_index_from_front_matter`

**Files:**
- Modify: `ai-sandbox/marker-conversion/chapter_index.py`
- Modify: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Consumes: `parse_printed_toc` (Task 3), `detect_printed_folio` (Task 4).
- Produces: `bootstrap_chapter_index_from_front_matter(front_matter_text: str) -> tuple[list[ChapterEntry], int | None]`, used by `convert_textbook.py` (Task 11) when there's no embedded outline.

Note: this expects the front-matter text to already have `<!-- page N -->` markers applied (i.e. it runs *after* `page_markers.remap_page_markers` in the real pipeline, not before) -- that dependency is why this task comes after Task 3/4 but the wiring into `convert_textbook.py` itself waits until Task 11, once `page_markers.py` (Task 8) exists.

- [ ] **Step 1: Write the failing tests**

Append to `test_chapter_index.py`:

```python
from chapter_index import bootstrap_chapter_index_from_front_matter


class TestBootstrap(unittest.TestCase):
    def test_bootstraps_physical_pages_from_folio_anchor(self):
        # Front matter chunk: page 11 is the anchor (its own printed folio
        # is "1", matching the TOC's first chapter), so offset = 11 - 1 = 10.
        front_matter = (
            "<!-- page 9 -->\n\nPreface text.\n\nlX\n\n"
            "<!-- page 10 -->\n\n"
            "## CONTENTS\n\n"
            "| Chapter 1 The Real and Complex Number Systems | 1  |\n"
            "| Chapter 2 Basic Topology                      | 24 |\n\n"
            "<!-- page 11 -->\n\nThe Real and Complex Number Systems\n\nBody text.\n\n1\n\n"
        )
        chapters, offset = bootstrap_chapter_index_from_front_matter(front_matter)
        self.assertEqual(offset, 10)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].physical_page, 11)  # 1 + 10
        self.assertEqual(chapters[1].physical_page, 34)  # 24 + 10

    def test_no_toc_fails_gracefully(self):
        chapters, offset = bootstrap_chapter_index_from_front_matter("<!-- page 0 -->\n\nJust prose.")
        self.assertEqual(chapters, [])
        self.assertIsNone(offset)

    def test_no_anchor_page_found_fails_gracefully(self):
        front_matter = (
            "<!-- page 0 -->\n\n"
            "## CONTENTS\n\n"
            "| Chapter 1 Something | 1 |\n\n"
            "<!-- page 1 -->\n\nNo isolated folio number printed on this page at all, just prose.\n\n"
        )
        chapters, offset = bootstrap_chapter_index_from_front_matter(front_matter)
        self.assertEqual(chapters, [])
        self.assertIsNone(offset)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ImportError: cannot import name 'bootstrap_chapter_index_from_front_matter'`.

- [ ] **Step 3: Implement in `chapter_index.py`**

Append:

```python
_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


def bootstrap_chapter_index_from_front_matter(
    front_matter_text: str,
) -> tuple[list[ChapterEntry], int | None]:
    """
    Used when there's no embedded PDF outline. Given the already-converted,
    already-page-tagged markdown of the front-matter chunk: parses its own
    printed TOC, then finds the one physical page in that same chunk whose
    own printed folio matches the TOC's first chapter -- from that single
    anchor, every other TOC entry's physical page follows by arithmetic
    (physical = folio + offset).
    """
    toc_chapters = parse_printed_toc(front_matter_text)
    if not toc_chapters:
        _logger.warning("No parseable table of contents found in front matter; falling back to no chapter awareness.")
        return [], None

    boundaries = [(m.start(), int(m.group(1))) for m in _PAGE_MARKER_RE.finditer(front_matter_text)]
    if not boundaries:
        _logger.warning("No page markers found in front matter text; cannot anchor TOC to physical pages.")
        return [], None

    first_folio = toc_chapters[0].folio_page
    anchor_physical = None
    for idx, (start, physical_page) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(front_matter_text)
        detected = detect_printed_folio(front_matter_text[start:end])
        if detected is not None and detected[0] == first_folio and not detected[1]:
            anchor_physical = physical_page
            break

    if anchor_physical is None:
        _logger.warning(
            "Could not find a physical page whose own printed folio matches the TOC's first "
            "chapter (folio %s); falling back to no chapter awareness.",
            first_folio,
        )
        return [], None

    offset = anchor_physical - first_folio
    resolved = [
        ChapterEntry(
            title=entry.title,
            physical_page=entry.folio_page + offset,
            folio_page=entry.folio_page,
            folio_is_roman=False,
            folio_raw=entry.folio_raw,
        )
        for entry in toc_chapters
        if not entry.folio_is_roman and entry.folio_page is not None and entry.folio_page >= first_folio
    ]
    return resolved, offset
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (22 tests total).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add chapter_index.py test_chapter_index.py
git commit -m "Add bootstrap_chapter_index_from_front_matter"
```

---

## Task 7: `pack_chapters_into_chunks`

**Files:**
- Modify: `ai-sandbox/marker-conversion/chapter_index.py`
- Modify: `ai-sandbox/marker-conversion/test_chapter_index.py`

**Interfaces:**
- Consumes: `ChapterEntry`.
- Produces: `pack_chapters_into_chunks(chapters, start_page, total_pages, max_chunk_size) -> list[tuple[int, int]]`, used by `convert_textbook.py`'s `compute_chunk_boundaries()` (Task 11).

This is the one piece of chunk-boundary math with zero PDF/Marker dependency -- pure list-of-tuples in, list-of-tuples out -- so it's factored out here rather than living inline in `convert_textbook.py`'s Marker-dependent orchestration.

- [ ] **Step 1: Write the failing tests**

Append to `test_chapter_index.py`:

```python
from chapter_index import pack_chapters_into_chunks


class TestPackChaptersIntoChunks(unittest.TestCase):
    def test_packs_multiple_chapters_under_cap(self):
        chapters = [
            ChapterEntry(title="Ch1", physical_page=14),
            ChapterEntry(title="Ch2", physical_page=40),
            ChapterEntry(title="Ch3", physical_page=64),
        ]
        chunks = pack_chapters_into_chunks(chapters, start_page=14, total_pages=200, max_chunk_size=150)
        # 40-14=26, 64-14=50, 200-14=186 (>150) -- cuts at the last chapter
        # boundary still under the cap, then takes the rest.
        self.assertEqual(chunks, [(14, 64), (64, 200)])

    def test_oversized_single_chapter_falls_back_to_cap(self):
        chapters = [
            ChapterEntry(title="Huge Chapter", physical_page=0),
            ChapterEntry(title="Ch2", physical_page=200),
        ]
        chunks = pack_chapters_into_chunks(chapters, start_page=0, total_pages=250, max_chunk_size=150)
        self.assertEqual(chunks, [(0, 150), (150, 250)])

    def test_no_chapters_produces_one_fixed_cap_chunk_sequence(self):
        chunks = pack_chapters_into_chunks([], start_page=0, total_pages=320, max_chunk_size=150)
        self.assertEqual(chunks, [(0, 150), (150, 300), (300, 320)])

    def test_chapter_pages_outside_range_are_ignored(self):
        chapters = [
            ChapterEntry(title="Front matter chapter-like entry", physical_page=5),  # before start_page
            ChapterEntry(title="Ch1", physical_page=20),
        ]
        chunks = pack_chapters_into_chunks(chapters, start_page=14, total_pages=100, max_chunk_size=150)
        self.assertEqual(chunks, [(14, 100)])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: FAIL with `ImportError: cannot import name 'pack_chapters_into_chunks'`.

- [ ] **Step 3: Implement in `chapter_index.py`**

Append:

```python
def pack_chapters_into_chunks(
    chapters: list[ChapterEntry], start_page: int, total_pages: int, max_chunk_size: int
) -> list[tuple[int, int]]:
    """
    Greedily accumulates consecutive chapters (by physical_page) starting
    at start_page into chunks no larger than max_chunk_size, never
    splitting a chapter. A span that would still exceed max_chunk_size on
    its own (an oversized single chapter, or simply no chapter data in that
    range) falls back to a plain max_chunk_size cut -- the caller
    (convert_textbook.py's compute_chunk_boundaries) is responsible for
    refining any such cut with a live Marker safety probe, which this pure
    function deliberately has no access to.
    """
    known = sorted(
        {c.physical_page for c in chapters if c.physical_page is not None and start_page <= c.physical_page < total_pages}
    )
    boundaries = known + [total_pages]

    chunks: list[tuple[int, int]] = []
    current_start = start_page
    i = 0
    while current_start < total_pages:
        while i < len(boundaries) and boundaries[i] <= current_start:
            i += 1
        next_cut = current_start
        while i < len(boundaries) and boundaries[i] - current_start <= max_chunk_size:
            next_cut = boundaries[i]
            i += 1
        if next_cut == current_start:
            fallback_limit = boundaries[i] if i < len(boundaries) else total_pages
            next_cut = min(current_start + max_chunk_size, fallback_limit)
        chunks.append((current_start, next_cut))
        current_start = next_cut
    return chunks
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_chapter_index -v
```

Expected: PASS (26 tests total).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add chapter_index.py test_chapter_index.py
git commit -m "Add pack_chapters_into_chunks, the pure chapter-boundary packing algorithm"
```

---

## Task 8: `page_markers.py`

**Files:**
- Create: `ai-sandbox/marker-conversion/page_markers.py`
- Create: `ai-sandbox/marker-conversion/test_page_markers.py`

**Interfaces:**
- Consumes: nothing from `chapter_index.py` -- deliberately independent (this is pure regex rewriting of already-rendered text; it doesn't need `ChapterEntry` or any PDF structure).
- Produces: `remap_page_markers(text, physical_offset, folio_offset, folio_start_page) -> str` and `tag_single_page(text, physical_page, folio_offset, folio_start_page) -> str`, both used by `convert_textbook.py`'s `process_page_range()` (Task 9).

- [ ] **Step 1: Write the failing tests**

`ai-sandbox/marker-conversion/test_page_markers.py`:

```python
import unittest

from page_markers import remap_page_markers, tag_single_page


class TestRemapPageMarkers(unittest.TestCase):
    def test_remaps_paginate_output_markers_with_offset(self):
        # Marker's literal paginate_output format: \n\n{N} + 48 dashes + \n\n
        text = "Some content.\n\n" + "3" + "-" * 48 + "\n\nMore content."
        result = remap_page_markers(text, physical_offset=150, folio_offset=None, folio_start_page=0)
        self.assertIn("<!-- page 153 -->", result)
        self.assertNotIn("-" * 48, result)

    def test_adds_folio_tag_when_offset_known_and_past_front_matter(self):
        text = "\n\n" + "0" + "-" * 48 + "\n\n"
        result = remap_page_markers(text, physical_offset=150, folio_offset=10, folio_start_page=20)
        self.assertIn("<!-- page 150 -->", result)
        self.assertIn("<!-- folio 140 -->", result)

    def test_no_folio_tag_before_front_matter_end(self):
        text = "\n\n" + "0" + "-" * 48 + "\n\n"
        result = remap_page_markers(text, physical_offset=5, folio_offset=10, folio_start_page=20)
        self.assertIn("<!-- page 5 -->", result)
        self.assertNotIn("folio", result)

    def test_remaps_colliding_span_anchors_and_links(self):
        # The actual collision pattern found in Axler's real output: the
        # same id="page-1-0" recurs once per chunk because chunk-local
        # numbering restarts at 0 every time.
        text = (
            '# *[Vector Spaces](#page-14-0)*\n\n'
            '<span id="page-1-0"></span>5.15 example text here.'
        )
        result = remap_page_markers(text, physical_offset=150, folio_offset=None, folio_start_page=0)
        self.assertIn('(#page-164-0)', result)
        self.assertIn('id="page-151-0"', result)

    def test_no_anchors_present_is_a_no_op(self):
        # The Rudin (scanned) case: nothing to remap.
        text = "Plain body text with no anchors, links, or page markers at all."
        self.assertEqual(remap_page_markers(text, physical_offset=300, folio_offset=None, folio_start_page=0), text)


class TestTagSinglePage(unittest.TestCase):
    def test_prepends_page_tag(self):
        result = tag_single_page("Fallback text.", physical_page=42, folio_offset=None, folio_start_page=0)
        self.assertTrue(result.startswith("<!-- page 42 -->"))
        self.assertIn("Fallback text.", result)

    def test_prepends_page_and_folio_tag(self):
        result = tag_single_page("Fallback text.", physical_page=42, folio_offset=10, folio_start_page=0)
        self.assertTrue(result.startswith("<!-- page 42 --><!-- folio 32 -->"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_page_markers -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'page_markers'`.

- [ ] **Step 3: Implement `page_markers.py`**

```python
"""
page_markers.py
Pure-Python helpers for rewriting Marker's chunk-local page markers,
anchors, and links into book-wide physical page numbers -- and, where
derivable, printed folio numbers. No dependency on marker/torch/surya:
this operates purely on already-rendered markdown text.

Each chunk is converted as an independent temp PDF, so Marker's own
paginate_output numbering, <span id="page-N-M"> anchors, and internal
(#page-N-M) links are all local to that chunk (always starting at 0).
Confirmed directly against real output (Axler_Linear_Algebra_Done_Right_2026):
the same id="page-1-0" recurs once per chunk in the merged file, so any
link generated against a chapter past the first chunk resolves to the
wrong target. Remapping by a fixed offset per chunk fixes both the display
page tags and this collision in one pass.
"""
from __future__ import annotations

import re

_MARKER_PAGE_BREAK_RE = re.compile(r"\n\n(\d+)-{48}\n\n")
_SPAN_ID_RE = re.compile(r'(<span id="page-)(\d+)(-\d+"></span>)')
_LINK_TARGET_RE = re.compile(r"(\(#page-)(\d+)(-\d+\))")


def _folio_tag(physical_page: int, folio_offset: int | None, folio_start_page: int) -> str:
    if folio_offset is not None and physical_page >= folio_start_page:
        return f"<!-- folio {physical_page - folio_offset} -->"
    return ""


def remap_page_markers(text: str, physical_offset: int, folio_offset: int | None, folio_start_page: int) -> str:
    """
    Rewrites a converted chunk's text so every page/anchor/link reference
    reflects the book's true physical page numbering instead of Marker's
    chunk-local numbering.
    """

    def _replace_page_break(m: re.Match) -> str:
        physical_page = physical_offset + int(m.group(1))
        tag = f"<!-- page {physical_page} -->" + _folio_tag(physical_page, folio_offset, folio_start_page)
        return f"\n\n{tag}\n\n"

    text = _MARKER_PAGE_BREAK_RE.sub(_replace_page_break, text)
    text = _SPAN_ID_RE.sub(lambda m: f"{m.group(1)}{physical_offset + int(m.group(2))}{m.group(3)}", text)
    text = _LINK_TARGET_RE.sub(lambda m: f"{m.group(1)}{physical_offset + int(m.group(2))}{m.group(3)}", text)
    return text


def tag_single_page(text: str, physical_page: int, folio_offset: int | None, folio_start_page: int) -> str:
    """
    Prepends a page (and, where derivable, folio) tag directly -- for
    content that never went through Marker's paginate_output at all (the
    raw-PyPDF last-resort fallback tier).
    """
    tag = f"<!-- page {physical_page} -->" + _folio_tag(physical_page, folio_offset, folio_start_page)
    return f"{tag}\n\n{text}"
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd ai-sandbox/marker-conversion && source .venv/Scripts/activate
python -m unittest test_page_markers -v
```

Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
cd ai-sandbox/marker-conversion
git add page_markers.py test_page_markers.py
git commit -m "Add page_markers.py: page/folio tagging and anchor/link collision fix"
```

---

## Task 9: Wire `paginate_output` and `page_markers` into `process_page_range`

**Files:**
- Modify: `ai-sandbox/marker-conversion/convert_textbook.py`

**Interfaces:**
- Consumes: `page_markers.remap_page_markers`, `page_markers.tag_single_page` (Task 8).
- Produces: `process_page_range()` now returns book-wide-tagged text on all three tiers; its signature gains `physical_offset` is already `start_page` (no change), plus new parameters `folio_offset: int | None` and `folio_start_page: int`.

**This task and the next two modify code that imports `torch`/`marker` at module scope, so none of it can be unit tested on this machine (no CUDA here) -- confirmed in Task 1. Each step below is implement-and-manually-verify by reading the diff, not a red/green test cycle. Live behavior is confirmed by the VM validation checklist (final task in this plan).**

- [ ] **Step 1: Add the import and enable `paginate_output`**

In `convert_textbook.py`, near the top with the other local imports (after `from marker.output import text_from_rendered`):

```python
from page_markers import remap_page_markers, tag_single_page
```

In `run_conversion()`, in the `converter_config` dict:

```python
    converter_config = {
        "langs": [args.lang],
        "paginate_output": True,
        # Off by default -- this is the setting the pipeline has been
        ...
```

(Only the new `"paginate_output": True,` line is added; everything else in that dict is unchanged.)

- [ ] **Step 2: Update `process_page_range`'s signature and the main chunk-level path**

Current signature (in `convert_textbook.py`):

```python
def process_page_range(converter, reader, workspace, start_page, end_page, images_dir,
                        chunk_timeout_s, page_timeout_s):
```

New signature:

```python
def process_page_range(converter, reader, workspace, start_page, end_page, images_dir,
                        chunk_timeout_s, page_timeout_s, folio_offset, folio_start_page):
```

Immediately after the existing line:

```python
        chunk_text, chunk_meta, chunk_images = text_from_rendered(rendered)
```

add:

```python
        chunk_text = remap_page_markers(chunk_text, start_page, folio_offset, folio_start_page)
```

- [ ] **Step 3: Update the per-page fallback tier**

The existing fallback loop has:

```python
                p_text, _, p_imgs = text_from_rendered(p_rendered)
                text_segments.append(p_text)
```

Change to:

```python
                p_text, _, p_imgs = text_from_rendered(p_rendered)
                p_text = remap_page_markers(p_text, single_p, folio_offset, folio_start_page)
                text_segments.append(p_text)
```

- [ ] **Step 4: Update the raw-PyPDF last-resort tier**

The existing line:

```python
                raw_text = reader.pages[single_p].extract_text() or ""
                text_segments.append(f"\n\n<!-- PyPDF Fallback: Page {single_p + 1} -->\n\n{raw_text}")
```

Change to:

```python
                raw_text = reader.pages[single_p].extract_text() or ""
                text_segments.append(tag_single_page(raw_text, single_p, folio_offset, folio_start_page))
```

(This replaces the old ad hoc `<!-- PyPDF Fallback: Page N -->` comment with the same `<!-- page N -->` tag format used everywhere else, per the spec's "one consistent tag format across all three tiers.")

- [ ] **Step 5: Update the one call site**

In `process_one_pdf()`, the current call:

```python
            chunk_text, chunk_meta, hit_exception = process_page_range(
                converter, reader, workspace, start_page, end_page, images_dir,
                args.chunk_timeout, args.page_timeout
            )
```

Change to (the two new arguments come from Task 11's `compute_chunk_boundaries` return value -- for now, until Task 11 lands, pass `folio_offset=None, folio_start_page=total_pages` as a temporary placeholder so the file stays syntactically valid and importable between tasks):

```python
            chunk_text, chunk_meta, hit_exception = process_page_range(
                converter, reader, workspace, start_page, end_page, images_dir,
                args.chunk_timeout, args.page_timeout, folio_offset, folio_start_page
            )
```

(`folio_offset` and `folio_start_page` become real local variables in Task 11, once `compute_chunk_boundaries` exists -- this task's Step 5 edit is written assuming Task 11 lands in the same sitting; if executed standalone, add temporary local variables `folio_offset = None` and `folio_start_page = total_pages` directly above this call so the module stays valid.)

- [ ] **Step 6: Manually verify by reading the full diff**

```bash
cd ai-sandbox/marker-conversion
git diff convert_textbook.py
```

Confirm: `paginate_output: True` is set; `process_page_range` remaps all three tiers; no remaining reference to the old `<!-- PyPDF Fallback` comment format.

- [ ] **Step 7: Commit**

```bash
cd ai-sandbox/marker-conversion
git add convert_textbook.py
git commit -m "Wire paginate_output and page_markers into process_page_range"
```

---

## Task 10: `probe_and_shift_boundary` and new CLI flags

**Files:**
- Modify: `ai-sandbox/marker-conversion/convert_textbook.py`

**Interfaces:**
- Consumes: `converter`, `reader` (existing), `text_from_rendered` (existing import).
- Produces: `probe_and_shift_boundary(converter, reader, workspace, candidate_end_page, max_shift, hard_limit_page) -> int`, used by `convert_textbook.py`'s `compute_chunk_boundaries()` (Task 11). New CLI flags `--max-boundary-shift`, `--max-front-matter-pages`, `--no-chapter-chunking`; updated help text on `--chunk-size`.

Not locally testable (needs a real Marker call) -- same manual-verification approach as Task 9.

- [ ] **Step 1: Implement `probe_and_shift_boundary`**

Add this function to `convert_textbook.py`, near `process_page_range` (same section of the file):

```python
_UNSAFE_BLOCK_TYPES = {"Table", "TableGroup", "Equation", "Form"}


def _page_looks_unterminated(rendered, page_text: str) -> bool:
    """
    Best-effort check for whether a single converted page's content looks
    like it's mid-table or mid-formula rather than cleanly ended.

    Primary signal: the page's last rendered block type, if marker's
    rendered-document structure exposes one in a form this can walk
    without guessing at an unconfirmed internal API. This is deliberately
    defensive -- the exact attribute path for a single-page render wasn't
    verified against the actual installed Marker version from outside the
    VM (no CUDA available here); if it's not available in whatever shape
    is expected, this silently falls through to the text-heuristic check
    below rather than raising.

    Fallback / second signal: the last non-empty line of the rendered
    markdown contains an unclosed table row or unbalanced math delimiters.
    """
    try:
        blocks = getattr(rendered, "children", None) or getattr(getattr(rendered, "block", None), "children", None)
        if blocks:
            last_block = blocks[-1]
            block_type = getattr(last_block, "block_type", None) or type(last_block).__name__
            if str(block_type) in _UNSAFE_BLOCK_TYPES:
                return True
    except Exception:
        pass

    lines = [ln for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return False
    last_line = lines[-1]
    if last_line.count("|") % 2 == 1:
        return True
    if last_line.count("$$") % 2 == 1:
        return True
    if "\\[" in last_line and "\\]" not in last_line:
        return True
    return False


def probe_and_shift_boundary(converter, reader, workspace, candidate_end_page, max_shift, hard_limit_page):
    """
    Checks whether the page immediately before candidate_end_page looks
    like it ends mid-table/mid-formula, and if so shifts the boundary
    forward one page at a time (re-probing each time) up to max_shift
    pages, never past hard_limit_page. Only used for chunk boundaries that
    aren't already chapter-aligned. Returns the (possibly shifted) end
    page -- always makes forward progress, even if still ambiguous at the
    shift cap.
    """
    end_page = candidate_end_page
    shifted = 0
    while shifted <= max_shift and end_page - 1 >= 0 and end_page < hard_limit_page:
        probe_page = end_page - 1
        temp_pdf = os.path.join(workspace, "temp_boundary_probe.pdf")
        writer = PdfWriter()
        writer.add_page(reader.pages[probe_page])
        with open(temp_pdf, "wb") as f:
            writer.write(f)
        try:
            rendered = converter(temp_pdf)
            page_text, _, _ = text_from_rendered(rendered)
        except Exception as probe_err:
            print(f"WARNING: boundary probe failed on page {probe_page + 1} ({probe_err}); keeping boundary as-is.")
            break
        finally:
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)

        if not _page_looks_unterminated(rendered, page_text):
            break

        print(f"[System] Chunk boundary at page {end_page} looks unsafe (page {probe_page + 1} may end "
              f"mid-table/mid-formula); shifting forward.")
        end_page += 1
        shifted += 1

    return min(end_page, hard_limit_page)
```

- [ ] **Step 2: Add new CLI flags in `parse_args`**

The existing `--chunk-size` argument:

```python
    parser.add_argument(
        "--chunk-size", type=int, default=150,
        help="Pages per chunk (default: 150). If a book has checkpoints from a prior run with "
             "a different chunk size, the recorded value is used instead -- see run_config.json."
    )
```

Change its help text and add the three new flags right after it:

```python
    parser.add_argument(
        "--chunk-size", type=int, default=150,
        help="Maximum pages per chunk (soft cap, default: 150) -- chunks are aligned to chapter "
             "boundaries when available and may be smaller. If a book has checkpoints from a "
             "prior run with a different chunk size, the recorded value is used instead -- see "
             "run_config.json."
    )
    parser.add_argument(
        "--max-boundary-shift", type=int, default=15,
        help="Max pages the safety probe may shift a fallback chunk boundary forward when it "
             "looks like it lands mid-table/mid-formula (default: 15)."
    )
    parser.add_argument(
        "--max-front-matter-pages", type=int, default=50,
        help="Cap on how far the front-matter TOC bootstrap will scan before giving up when "
             "there's no embedded PDF outline (default: 50)."
    )
    parser.add_argument(
        "--no-chapter-chunking", dest="chapter_chunking", action=argparse.BooleanOptionalAction, default=True,
        help="Disable chapter-aware chunking and fall back to pure fixed-interval chunking "
             "(default: chapter-aware chunking is enabled). Useful for debugging or A/B "
             "comparison against the new behavior on a real book."
    )
```

- [ ] **Step 3: Manually verify**

```bash
cd ai-sandbox/marker-conversion
git diff convert_textbook.py
python3 -c "import ast; ast.parse(open('convert_textbook.py').read())"
```

The `ast.parse` call confirms the file is still syntactically valid Python without needing `torch`/`marker` installed (it doesn't execute the module, just parses it).

- [ ] **Step 4: Commit**

```bash
cd ai-sandbox/marker-conversion
git add convert_textbook.py
git commit -m "Add probe_and_shift_boundary and new chunking CLI flags"
```

---

## Task 11: `compute_chunk_boundaries` orchestration and `process_one_pdf` wiring

**Files:**
- Modify: `ai-sandbox/marker-conversion/convert_textbook.py`

**Interfaces:**
- Consumes: everything from `chapter_index.py` (Tasks 1-7), `probe_and_shift_boundary` (Task 10), `process_page_range`'s new signature (Task 9).
- Produces: `compute_chunk_boundaries(converter, reader, workspace, total_pages, max_chunk_size, max_front_matter_pages, max_boundary_shift, chapter_chunking_enabled) -> tuple[list[tuple[int, int]], int | None, int]` (boundaries, folio_offset, folio_start_page) -- the `folio_offset`/`folio_start_page` locals that Task 9's `process_page_range` call site needs.

Not locally testable (needs real Marker calls for the front-matter bootstrap conversion and any boundary probing) -- manual verification, same as Tasks 9-10.

- [ ] **Step 1: Add the import**

Near the top of `convert_textbook.py`, alongside the `page_markers` import added in Task 9:

```python
import chapter_index
```

- [ ] **Step 2: Implement `compute_chunk_boundaries`**

Add this function to `convert_textbook.py`, after `probe_and_shift_boundary`:

```python
def compute_chunk_boundaries(converter, reader, workspace, total_pages, max_chunk_size,
                              max_front_matter_pages, max_boundary_shift, chapter_chunking_enabled):
    """
    Returns (boundaries, folio_offset, folio_start_page).

    boundaries is a list of (start_page, end_page) tuples covering the
    whole book. When chapter_chunking_enabled is False, this is exactly
    today's fixed-interval behavior. Otherwise: tries the PDF's embedded
    outline first (free); if absent, converts a capped front-matter chunk
    and bootstraps a chapter index from its own printed TOC. Either way,
    chapters are greedily packed into chunks up to max_chunk_size, and any
    span that's still oversized is refined with a live Marker safety
    probe. folio_offset/folio_start_page (both possibly None/0) are
    returned so callers can pass them through to process_page_range for
    page/folio tagging.
    """
    if not chapter_chunking_enabled:
        boundaries = [
            (start, min(start + max_chunk_size, total_pages))
            for start in range(0, total_pages, max_chunk_size)
        ]
        return boundaries, None, total_pages

    outline_chapters = chapter_index.get_outline_chapters(reader)
    folio_offset = None
    folio_start_page = total_pages

    if outline_chapters:
        front_matter_end = outline_chapters[0].physical_page
        # Folio tagging is independent of chunking here -- try it purely
        # for the dual page/folio tags, using whatever front matter ends
        # up in the first chunk once boundaries are packed below.
        rest_chapters = outline_chapters
    else:
        front_matter_cap = min(max_front_matter_pages, total_pages)
        images_dir = os.path.join(workspace, "marker_checkpoints", "_boundary_bootstrap_images")
        os.makedirs(images_dir, exist_ok=True)
        front_matter_text, _, _ = process_page_range(
            converter, reader, workspace, 0, front_matter_cap, images_dir,
            chunk_timeout_s=1800, page_timeout_s=240,
            folio_offset=None, folio_start_page=total_pages,
        )
        rest_chapters, folio_offset = chapter_index.bootstrap_chapter_index_from_front_matter(front_matter_text)
        if rest_chapters:
            front_matter_end = rest_chapters[0].physical_page
            folio_start_page = front_matter_end
        else:
            front_matter_end = min(20, total_pages)

    if outline_chapters:
        toc_chapters = chapter_index.parse_printed_toc(
            process_page_range(
                converter, reader, workspace, 0, front_matter_end,
                os.path.join(workspace, "marker_checkpoints", "_boundary_bootstrap_images"),
                chunk_timeout_s=1800, page_timeout_s=240,
                folio_offset=None, folio_start_page=total_pages,
            )[0]
        )
        computed_offset = chapter_index.compute_folio_offset(outline_chapters, toc_chapters)
        if computed_offset is not None:
            folio_offset = computed_offset
            folio_start_page = front_matter_end

    packed = chapter_index.pack_chapters_into_chunks(rest_chapters, front_matter_end, total_pages, max_chunk_size)

    known_chapter_pages = {c.physical_page for c in rest_chapters if c.physical_page is not None}
    boundaries = [(0, front_matter_end)] if front_matter_end > 0 else []
    for start, end in packed:
        if end == total_pages or end in known_chapter_pages:
            boundaries.append((start, end))
        else:
            refined_end = probe_and_shift_boundary(converter, reader, workspace, end, max_boundary_shift, total_pages)
            boundaries.append((start, refined_end))

    return boundaries, folio_offset, folio_start_page
```

Note on the outline-present branch: it re-converts pages `0..front_matter_end` a second time (once implicitly via the normal chunking loop later, once here to get TOC text for `compute_folio_offset`) rather than trying to thread the result through -- this trades a small amount of duplicate compute (only ever the front-matter span, a handful of pages) for keeping this function self-contained and not reaching into `process_one_pdf`'s checkpoint machinery. If this turns out to matter for cost on a real run, it's a candidate for a follow-up optimization once the VM validation pass (final task) confirms the design works at all -- not worth the added complexity up front.

- [ ] **Step 3: Wire into `process_one_pdf`**

Replace the existing line:

```python
        chunk_ranges = list(range(0, total_pages, effective_chunk_size))
```

with:

```python
        run_config_path = os.path.join(checkpoint_dir, "run_config.json")
        boundaries, folio_offset, folio_start_page = _load_or_compute_boundaries(
            run_config_path, converter, reader, workspace, total_pages,
            effective_chunk_size, args.max_front_matter_pages, args.max_boundary_shift,
            args.chapter_chunking,
        )
```

And replace the loop header:

```python
        for start_page in chunk_ranges:
            end_page = min(start_page + effective_chunk_size, total_pages)
```

with:

```python
        for start_page, end_page in boundaries:
```

- [ ] **Step 4: Add `_load_or_compute_boundaries` and update the `process_page_range` call site**

Add this helper near `resolve_effective_chunk_size` (same section of the file):

```python
def _load_or_compute_boundaries(run_config_path, converter, reader, workspace, total_pages,
                                 max_chunk_size, max_front_matter_pages, max_boundary_shift,
                                 chapter_chunking_enabled):
    """
    Loads persisted chunk boundaries and folio offset from run_config.json
    if present (a resumed run), otherwise computes them once and persists
    the result -- guarantees identical chunking and tagging across resumes
    regardless of any nondeterminism in the boundary safety probe.
    """
    if os.path.exists(run_config_path):
        try:
            with open(run_config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if "boundaries" in saved:
                boundaries = [tuple(pair) for pair in saved["boundaries"]]
                return boundaries, saved.get("folio_offset"), saved.get("folio_start_page", total_pages)
        except (json.JSONDecodeError, OSError):
            pass

    boundaries, folio_offset, folio_start_page = compute_chunk_boundaries(
        converter, reader, workspace, total_pages, max_chunk_size,
        max_front_matter_pages, max_boundary_shift, chapter_chunking_enabled,
    )
    with open(run_config_path, "w", encoding="utf-8") as f:
        json.dump({
            "chunk_size": max_chunk_size,
            "boundaries": [list(pair) for pair in boundaries],
            "folio_offset": folio_offset,
            "folio_start_page": folio_start_page,
        }, f)
    return boundaries, folio_offset, folio_start_page
```

This replaces `resolve_effective_chunk_size`'s role for chunk-size recording -- remove the old standalone call to `resolve_effective_chunk_size(checkpoint_dir, args.chunk_size, raw_input)` in `process_one_pdf` and the `effective_chunk_size = ...` line that consumed it, since `_load_or_compute_boundaries` now owns `run_config.json` entirely (including the `chunk_size` field, for the same "pin to whatever the checkpoint was created with" behavior the old function provided). Delete the now-unused `resolve_effective_chunk_size` function.

Finally, update the `process_page_range` call inside the loop (the one Task 9 Step 5 left with placeholder values) to use the real ones:

```python
            chunk_text, chunk_meta, hit_exception = process_page_range(
                converter, reader, workspace, start_page, end_page, images_dir,
                args.chunk_timeout, args.page_timeout, folio_offset, folio_start_page
            )
```

- [ ] **Step 5: Manually verify**

```bash
cd ai-sandbox/marker-conversion
git diff convert_textbook.py
python3 -c "import ast; ast.parse(open('convert_textbook.py').read())"
```

Confirm: no remaining reference to `resolve_effective_chunk_size` or `effective_chunk_size` anywhere in the file; `chunk_ranges` no longer exists; `boundaries`/`folio_offset`/`folio_start_page` flow from `_load_or_compute_boundaries` through to both the chunking loop and the `process_page_range` call.

- [ ] **Step 6: Commit**

```bash
cd ai-sandbox/marker-conversion
git add convert_textbook.py
git commit -m "Wire compute_chunk_boundaries into process_one_pdf with resume support"
```

---

## Task 12: Full local test suite run

**Files:** none (verification only)

- [ ] **Step 1: Run every local test together**

```bash
cd ai-sandbox/marker-conversion
source .venv/Scripts/activate
python -m unittest test_chapter_index test_page_markers -v
```

Expected: all tests PASS (33 total: 26 in `test_chapter_index`, 7 in `test_page_markers`).

- [ ] **Step 2: Confirm neither test module imports torch/marker**

```bash
cd ai-sandbox/marker-conversion
deactivate 2>/dev/null
python -c "import sys; sys.path.insert(0, '.'); import chapter_index, page_markers; print('OK, no torch/marker needed')"
```

Run this with the **system** Python (not the venv) if `pypdf` happens to be globally available, or confirm it fails only on the `pypdf` import specifically (not a `torch`/`marker` import) -- the point is proving `chapter_index.py`/`page_markers.py` never transitively pull in the CUDA-dependent stack, which is the entire reason they're separate modules.

- [ ] **Step 3: Commit (only if anything needed fixing)**

If both steps passed cleanly, there's nothing to commit here -- this task is a gate, not a code change.

---

## Task 13: VM validation checklist

**Files:**
- Create: `ai-sandbox/marker-conversion/docs/superpowers/plans/2026-08-20-vm-validation-checklist.md`

This is the artifact for the pieces that genuinely can't be verified from this machine (no CUDA), and it's also the running record you asked for -- something future sessions can read to know what's been checked on the real GCP pipeline and what's still open, across this book and others.

- [ ] **Step 1: Write the checklist**

```markdown
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

## Open questions for next session

(running list -- add to this as issues turn up; don't just fix and forget,
note *why* so future books don't hit the same surprise)
```

- [ ] **Step 2: Commit**

```bash
cd ai-sandbox/marker-conversion
git add docs/superpowers/plans/2026-08-20-vm-validation-checklist.md
git commit -m "Add VM validation checklist for chapter-aware chunking"
```

---

## Self-Review Notes

**Spec coverage:** every spec section has a task -- `ChapterEntry`/outline (Task 1), folio tokens (Task 2), `parse_printed_toc` (Task 3), `detect_printed_folio` (Task 4), title matching/offset (Task 5), bootstrap (Task 6), chunk packing (Task 7), page/folio tagging (Task 8-9), anchor/link remapping (Task 8-9), boundary probe + CLI flags (Task 10), orchestration + resume (Task 11), testing gate (Task 12), VM validation (Task 13).

**Deviations from the spec, made explicit rather than silent:**
- `folio_page` is resolved to an integer for roman numerals too (with a separate `folio_is_roman` flag), rather than the spec's data-model comment of "None if unknown/roman" -- this is strictly more useful (a `<!-- folio ix -->`-equivalent tag is meaningful) and the roman/arabic distinction the design actually needs (excluding roman folios from offset-anchor arithmetic) is preserved via the flag instead.
- `remap_page_markers` moved from `convert_textbook.py` (as the spec's Design section literally states) into the new `page_markers.py` module -- the spec's own Testing section already promised it'd be unit-tested with "no GPU/Marker dependency," which is only true if it doesn't live in a file that imports `torch` at module scope. Same rationale as `chapter_index.py`.
- `parse_printed_toc` scans every line for the chapter-level pattern rather than first detecting a "TOC region" boundary, per the "Real-world validation" section's finding that the chapter-pattern match is specific enough on its own -- a region detector turned out to be unneeded complexity, and its absence is also why the Rudin two-table-block split needed no special handling.

**Type/signature consistency checked:** `ChapterEntry` fields, `process_page_range`'s new parameters, and `compute_chunk_boundaries`'s return tuple are used identically everywhere they're referenced across Tasks 1-11.

**Known gap, called out rather than hidden:** Task 11's `compute_chunk_boundaries` re-converts the front-matter span a second time in the outline-present branch (once for `compute_folio_offset`'s TOC text, once again implicitly via the normal per-chunk loop). Left as-is rather than threading the result through `process_one_pdf`'s checkpoint machinery, to keep this task's scope bounded -- flagged in Task 13's checklist as something to revisit only if the VM run shows it actually costs meaningful time.
