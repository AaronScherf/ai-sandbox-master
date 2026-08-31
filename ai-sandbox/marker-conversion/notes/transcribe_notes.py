#!/usr/bin/env python3
"""
transcribe_notes.py
Runs locally (no GCP VM needed) against short, non-textbook academic PDFs
-- problem sets, lecture notes, exams -- that have no table of contents
and often mix typed and handwritten content, sometimes on the same page.

Unlike convert_textbook.py (Marker, tuned for printed-text OCR at
textbook scale), this renders each page to an image and asks a
vision-capable Gemini model to transcribe it directly -- typed and/or
handwritten, whatever's actually on the page, no pre-classification.

Accumulating context: each page's call includes the last
_ACCUMULATION_WINDOW already-transcribed pages as context, not just the
immediately preceding one. This matters specifically for OneNote
exports, where the page's internal layout window can split a paragraph
non-adjacently rather than at a clean page boundary -- a small trailing
window (rather than the whole document, which was confirmed to grow
input tokens quadratically with page count on a real file) is enough
since that splitting only ever spans adjacent pages. This requires
strictly sequential processing (page N's call needs pages 1..N-1
already transcribed) -- see process_pdf().

Local text extraction (Tier 1/2, and Tier 3's per-page hint) goes through
PyMuPDF rather than pypdf's PdfReader.extract_text(): pypdf was confirmed
on a real file to collapse inter-word spacing on some font/kerning setups
("LetVbe a finite-dimensional...") that PyMuPDF's layout-aware extraction
preserves correctly ("Let V be a finite-dimensional...") -- pypdf itself
stays in use only for page count and metadata (has_reliable_pagination).

Everything except the actual PyMuPDF calls (page-image rendering, local
text extraction), the Gemini network call, and the CLI driver is
pure-Python and independently unit-tested (tests/test_transcribe_notes.py)
-- no torch/marker dependency, matching
chapter_index.py/page_markers.py/describe_images.py.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from common.gemini_utils import (
    call_with_retries,
    get_gemini_client,
    load_dotenv_override,
    load_json_cache,
    save_json_cache,
)
from indexer.index_card import (
    KNOWN_DOC_TYPES,
    compute_content_hash,
    compute_file_id,
    derive_course,
    reconcile_and_write,
)

_CODE_FENCE_RE = re.compile(r"^```(?:markdown)?\s*\n(.*)\n```\s*$", re.DOTALL)

# Checked FIRST, unconditionally: known messy-export sources, regardless
# of any other marker also present. Confirmed necessary against a real
# file -- "Microsoft® OneNote® for Microsoft 365" contains "microsoft" as
# a substring, which would otherwise misclassify OneNote (the canonical
# non-adjacent-paragraph-splitting case this whole design exists to
# handle) as reliably paginated.
_MESSY_EXPORT_MARKERS = ("nebo", "myscript", "onenote")

# Metadata markers for a normal document-processing pipeline (LaTeX,
# Word, LibreOffice) that paginates sequentially and never splits
# content non-adjacently. Confirmed against real files this project has
# handled: LN_Analysis.pdf and LN_Linear Algebra.pdf both carry
# '/Creator: LaTeX with hyperref', '/Producer: pdfTeX-1.40.27'.
# Deliberately narrow (no bare "microsoft" or "tex") to avoid stray
# substring matches -- a bare "microsoft" previously misclassified
# OneNote exports too, since Producer/Creator both mention "Microsoft".
# "apache fop" and "xep" added 2026-08-31: confirmed against real journal
# articles (research/journal-articles) -- academic publishers commonly
# render their PDFs with Apache FOP or RenderX's XEP (both XML-to-PDF
# engines), which produce the same reliably-paginated, cleanly-extractable
# text as LaTeX/Word but weren't recognized before, routing genuinely
# clean papers to expensive full-page vision transcription for no reason.
_RELIABLE_PAGINATION_MARKERS = (
    "latex", "pdftex", "word", "libreoffice", "openoffice", "apache fop", "xep",
)

# The real, confirmed failure mode for machine-generated PDFs: an
# extensible delimiter glyph (a big matrix bracket or summation/integral
# sign, built from several stacked glyph pieces) frequently lacks a
# correct ToUnicode mapping, and PDF layout can also collapse word
# spacing entirely in some paragraph runs. Both produce the same
# structural symptom -- an abnormally long, unbroken character run -- no
# real English/math word is this long. Confirmed against two real pages
# (LN_Analysis.pdf page 88, LN_Linear Algebra.pdf page 170) that produced
# *different* garbage characters ('Õ' in one, '«'/'ﬁﬁﬁﬁﬁ' in the other),
# which is why this checks a structural invariant rather than a
# blocklist of specific bad characters -- different font packages
# produce different garbage.
_MAX_WORD_LENGTH = 25

# Unicode ranges legitimately expected in an English math document --
# used by page_looks_defective's second check (delimiter-glyph
# corruption doesn't produce long words, it produces short garbage
# tokens on their own line, so word-length alone misses it). Validated
# against a real 294-page document: an earlier, narrower version of this
# allowlist flagged 148/294 pages, mostly false positives from missing
# entire categories of legitimate notation -- Greek letters (Δ Φ ...),
# angle brackets (⟨ ⟩, inner-product notation), prime marks (f′), and
# single ligature characters (ﬁ, completely normal in words like
# "significant" -- see _has_suspicious_repeated_char_run for how a
# *repeated* ligature run like 'ﬁﬁﬁﬁﬁ' is still caught separately).
ALLOWED_MATH_RANGES = (
    (0x1D400, 0x1D7FF),  # Mathematical Alphanumeric Symbols (𝐴, 𝑓, 𝜉, ...)
    (0x2200, 0x22FF),    # Mathematical Operators (∈ ∉ ⊆ ∀ ∇ ∂ − ∥ ...)
    (0x2100, 0x214F),    # Letterlike Symbols (ℝ ℂ ℤ ℕ ℚ ...)
    (0x2190, 0x21FF),    # Arrows
    (0x2A00, 0x2AFF),    # Supplemental Mathematical Operators
    (0x0370, 0x03FF),    # Greek and Coptic (α β Δ θ λ π Σ φ Φ Ω ...)
    (0x27C0, 0x27EF),    # Miscellaneous Mathematical Symbols-A (⟨ ⟩ ...)
    (0x2980, 0x29FF),    # Miscellaneous Mathematical Symbols-B
    (0xFB00, 0xFB06),    # Alphabetic Presentation Forms (ligatures ﬀ ﬁ ﬂ ﬃ ﬄ)
)
_ALLOWED_EXTRA_CHARS = set("—–‘’“”…°±×÷·∘‗†′″‴")
_MAX_UNEXPECTED_CHARS = 3

# Corruption signal independent of the allowlist above: the *same*
# non-whitespace character repeated 3+ times with no separation is
# essentially never legitimate prose or math (confirmed real cases:
# 'ﬁﬁﬁﬁﬁ', '›››››' both from a corrupted matrix bracket) -- except a
# small set of characters that legitimately do repeat this way (ellipsis
# dots in a matrix, table rules, underscored blanks).
_LEGITIMATE_REPEATABLE_CHARS = set(".-=_*#·")
_REPEATED_CHAR_RUN_RE = re.compile(r"(\S)\1{2,}")

# Not a corruption signal -- a different, unfixable-by-extraction-choice
# failure mode: PLAIN-mode text extraction (pypdf, or PyMuPDF's default
# get_text()) has no way to represent a superscript/subscript at all, so a
# single-character exponent like D^5 or a set like R^2 comes out as bare
# "D5"/"R2" -- confirmed real, in both cases genuine content loss, not a
# spacing bug. reconstruct_line_with_scripts() below now recovers most of
# these locally via PyMuPDF's structured "dict" text mode, so this regex
# is now a residual-only signal -- it still exists to catch whatever
# reconstruction doesn't (a page with no detectable dominant-size/baseline
# signal, or a case just under its offset threshold), not as the primary
# defense anymore. Deliberately \b-anchored on both ends (the whole 2-char
# token must be bounded by non-word characters): a looser
# letter-immediately-followed-by-digit check was confirmed to false-
# positive constantly against embedded hyperlink hash IDs (e.g.
# "...app/06b7ab97dac5cbbb>"), which alternate letters and digits with no
# boundary anywhere inside the run. Known gap, not exhaustive: this only
# catches a digit sitting alone between boundaries ("D5 = 0"), not one
# sandwiched inside a longer token ("x2y" for x²y) -- widening it to catch
# that case would reopen the same hash-string false-positive risk.
_LOST_EXPONENT_OR_SUBSCRIPT_RE = re.compile(r"\b[A-Za-z]\d\b")

# reconstruct_line_with_scripts() doesn't recursively re-nest a script
# inside another script -- a compound subscript like B_{infinity,r1}(x)
# comes out as one flat group rather than the fully-nested
# B_{infinity,r_1}(x) (confirmed real: Analysis_Exercises.pdf page 1).
# Stripped out before the lost-exponent check below runs, so a bare
# digit-after-letter *inside* an already-produced script group isn't
# re-flagged as still lost -- it's real, if imperfectly nested, content,
# not a case reconstruction missed entirely. Single-level only (no nested
# braces expected from reconstruct_line_with_scripts's own output).
_SCRIPT_GROUP_RE = re.compile(r"[\^_]\{[^{}]*\}")


def _has_lost_exponent_outside_scripts(text: str) -> bool:
    return bool(_LOST_EXPONENT_OR_SUBSCRIPT_RE.search(_SCRIPT_GROUP_RE.sub("", text)))


# reconstruct_line_with_scripts() thresholds, tuned against real spans
# from Practice Sheet.pdf and LN_Linear Algebra.pdf (different font
# families, same pattern held): a genuine sub/superscript span was
# consistently ~0.73-0.77x the surrounding line's dominant font size, and
# offset from its baseline by ~15-36% of that dominant size. Size alone
# isn't sufficient -- confirmed a real case (a blackboard-bold "K"
# rendered at 11.49pt against 10.91pt body text, same baseline) where a
# differently-sized span is NOT a script; only size-and-offset together
# discriminate correctly.
_SCRIPT_SIZE_RATIO = 0.85
_SCRIPT_OFFSET_RATIO = 0.08

# reconstruct_line_with_scripts()'s gap-based synthetic-space threshold,
# as a fraction of the line's dominant font size. Tuned against real
# spans from LN_Analysis.pdf: a genuine word-boundary gap with no space
# *character* in the PDF's own content stream (a common LaTeX/PDF
# pattern -- justified text using kerning-level positioning instead of a
# literal space glyph, confirmed real case: "f" directly followed by
# "uniformly." with a 4.97pt gap, ~0.46x the 10.91pt body size, and no
# space span between them at all) is roughly an order of magnitude
# larger than a tight script attachment's own gap (~0.4pt, ~0.04x, e.g.
# a subscript sitting right against its base variable). 0.15 sits
# comfortably between the two with real margin on both sides.
_WORD_GAP_RATIO = 0.15


def _dominant_size_and_baseline(spans: list[dict]) -> tuple[float | None, float | None]:
    """
    The line's dominant font size -- by total character count, not span
    count, so a short body-text run doesn't lose to two single-character
    exponent spans -- and that size's baseline (first occurrence's
    origin_y). Returns (None, None) for an empty span list.
    """
    char_counts: dict[float, int] = {}
    first_origin_y: dict[float, float] = {}
    for s in spans:
        size = s.get("size")
        if size is None:
            continue
        text = s.get("text", "")
        char_counts[size] = char_counts.get(size, 0) + len(text)
        if size not in first_origin_y:
            first_origin_y[size] = s["origin"][1]
    if not char_counts:
        return None, None
    dominant_size = max(char_counts, key=lambda sz: char_counts[sz])
    return dominant_size, first_origin_y[dominant_size]


def reconstruct_line_with_scripts(spans: list[dict]) -> str:
    """
    Reconstructs one line's text from PyMuPDF dict-mode spans, wrapping
    detected superscript/subscript spans in ^{...}/_{...} instead of
    losing them to plain concatenation (see _SCRIPT_SIZE_RATIO/
    _SCRIPT_OFFSET_RATIO above for the real data behind the thresholds),
    and inserting a synthetic space between two spans separated by a real
    positional gap with no space character of their own (see
    _WORD_GAP_RATIO above). Consecutive same-direction script spans are
    grouped into one run, so a multi-character exponent doesn't come out
    as separate ^{1}^{2}. Falls back to plain concatenation for an empty
    list or a line with no determinable dominant size -- safe by
    construction, never worse than plain get_text() would have produced.
    """
    dominant_size, baseline_y = _dominant_size_and_baseline(spans)
    if dominant_size is None:
        return "".join(s.get("text", "") for s in spans)

    size_threshold = dominant_size * _SCRIPT_SIZE_RATIO
    offset_threshold = dominant_size * _SCRIPT_OFFSET_RATIO
    gap_threshold = dominant_size * _WORD_GAP_RATIO

    parts: list[str] = []
    pending: list[str] = []
    pending_dir: str | None = None
    prev_bbox_right: float | None = None

    def flush() -> None:
        if pending:
            marker = "^" if pending_dir == "sup" else "_"
            parts.append(f"{marker}{{{''.join(pending)}}}")
            pending.clear()

    def last_output_char() -> str:
        if pending:
            return pending[-1][-1:]
        if parts:
            return parts[-1][-1:]
        return ""

    for s in spans:
        text = s.get("text", "")
        size = s.get("size")
        bbox = s.get("bbox")

        if (
            prev_bbox_right is not None and bbox is not None
            and not text.startswith((" ", "\n"))
            and last_output_char() not in (" ", "\n", "")
        ):
            if bbox[0] - prev_bbox_right > gap_threshold:
                flush()
                parts.append(" ")
                pending_dir = None
        if bbox is not None:
            prev_bbox_right = bbox[2]

        direction = None
        if size is not None and size < size_threshold:
            offset = s["origin"][1] - baseline_y
            if offset < -offset_threshold:
                direction = "sup"
            elif offset > offset_threshold:
                direction = "sub"

        if direction is not None and direction == pending_dir:
            pending.append(text)
        else:
            flush()
            if direction is not None:
                pending.append(text)
                pending_dir = direction
            else:
                parts.append(text)
                pending_dir = None
    flush()
    return "".join(parts)

# Above this fraction of a document's pages scoring as defective, treat
# it as not a good hybrid-repair candidate at all -- batch the whole
# document through Gemini instead of piecemeal-repairing just the flagged
# pages. Lowered from an initial 0.35 to 0.10 once real per-page cost was
# measured at ~$0.0007/page (gemini-3.1-flash-lite): full transcription of
# a ~40-page document costs a few cents either way, so there's little to
# gain from preserving free local extraction on a document that's already
# shown real problems -- any confirmed defect is evidence about that PDF's
# own production quirks (font encoding, or genuine content plain-text
# extraction can't represent at all, e.g. _LOST_EXPONENT_OR_SUBSCRIPT_RE)
# that plausibly affects pages beyond the specific ones any one heuristic
# happened to flag. Confirmed against real documents this project has
# processed: at 0.10, all three already-hybrid-repaired lecture-note files
# (23-29% corruption-only defect rates) and Practice Sheet.pdf (63% once
# the lost-exponent signal is counted) cross this threshold, while
# genuinely clean documents (old exams, short in-class handout PDFs) stay
# at 0% and are unaffected.
_MAX_DEFECT_RATIO_FOR_HYBRID = 0.10

# Cap on how many consecutive defective pages go into one batched repair
# call -- bounds both the blast radius of one failed/malformed batch and
# the risk of the model losing track of per-page delimiters in a very
# large response.
_MAX_BATCH_SIZE = 12

_DPI_TYPESET = 150
_DPI_HANDWRITING = 200

_MODEL_TYPESET = "gemini-3.1-flash-lite"
_MODEL_HANDWRITING = "gemini-3.6-flash"

# How many immediately-preceding pages to include as context for
# messy-export (Nebo/MyScript/OneNote) documents, instead of the entire
# transcribed-so-far document. The paragraph-splitting behavior this
# accumulation exists to handle (see module docstring) only ever spans
# adjacent pages, so a small trailing window preserves the same
# continuity while turning input-token growth from quadratic (full
# accumulation, confirmed against a real 5-page file: 1817 -> 7364
# input tokens per call) into flat per-call cost.
_ACCUMULATION_WINDOW = 3

# Hard output caps against a runaway-repetition failure (see
# _looks_like_repetition_loop below): confirmed live on three real files
# (LN_Analysis.pdf, LN_Optimization.pdf, LN_Probability.pdf) whose
# printed table-of-contents pages (dot leaders -- a naturally repetitive
# visual pattern) sent temperature=0 greedy decoding into an unbroken
# ". . . ." loop that ran to ~131,000 characters (tens of thousands of
# tokens) before the model's own internal ceiling stopped it. Real page
# content across this corpus's 772 already-cached pages has a median of
# 1,327 characters and a p95 of 2,118 -- these caps sit an order of
# magnitude above any real single page's needs and well below what a
# genuine repetition loop consumes, so a looping page gets cut off
# before completing (missing its closing content), not silently allowed
# to run to completion.
_MAX_OUTPUT_TOKENS_SINGLE_PAGE = 8192
_MAX_OUTPUT_TOKENS_BATCH = 16384

# Applied only on the single retry after a detected repetition loop (see
# transcribe_page_via_gemini). frequency_penalty was tried first as a
# more surgical lever than temperature (penalizing repeated tokens
# specifically, rather than adding randomness everywhere in the
# response) -- confirmed live it doesn't work: gemini-3.1-flash-lite
# rejects it outright with a real 400 INVALID_ARGUMENT, "Penalty is not
# enabled for this model". Temperature is the fallback because it's the
# most universally-supported sampling parameter; nonzero but modest,
# enough randomness to break a greedy-decoding (temperature=0) loop
# without destabilizing an otherwise-correct transcription. Not applied
# on first attempts, to keep normal transcription fully deterministic.
_REPETITION_RETRY_TEMPERATURE = 0.4

# Appended to the prompt only on the retry -- directly names the
# specific pattern confirmed live to trigger this failure (dot-leader
# table-of-contents entries), since the model has concrete instructions
# to follow this time rather than just different sampling parameters.
_REPETITION_RETRY_PROMPT_SUFFIX = (
    "\n\nIMPORTANT: a previous attempt at this exact page degenerated into "
    "repeating the same character or short phrase (e.g. dot-leader table-of-"
    "contents entries: \"Introduction . . . . . . .\") far more times than "
    "the page actually shows. If this page contains a dot-leader table of "
    "contents or similar repeated-punctuation formatting, transcribe each "
    "entry with a short, bounded run of separator characters (e.g. \"...\") "
    "rather than reproducing the exact printed spacing, and move on to the "
    "next entry -- never repeat the same character or phrase more than a "
    "few times in a row."
)

# Threshold confirmed against real data, not guessed: an earlier version
# of this used 25, which turned out to be a real false positive --
# LN_Analysis.pdf's own genuine, correctly-transcribed page 3 legitimately
# contains a 50-dot leader (". . . . ." x50, a long section title padded
# to a page-width right-aligned page number). Measured the true max
# across every already-recovered, verified-correct page in this corpus:
# 50. 150 sits 3x above that real legitimate maximum, while staying
# roughly 400x below the real failures (tens of thousands of repeats,
# confirmed live on three files) -- comfortable margin on both sides.
_REPETITION_LOOP_RE = re.compile(r"(\S{1,20})(?:\s+\1){149,}")


def _looks_like_repetition_loop(text: str) -> bool:
    """True if `text` degenerated into the same short token repeated
    many times in a row -- a known temperature=0 greedy-decoding failure
    mode, confirmed live specifically on printed table-of-contents pages
    (dot leaders). See _REPETITION_LOOP_RE and _MAX_OUTPUT_TOKENS_*
    above for the evidence behind the threshold."""
    return bool(_REPETITION_LOOP_RE.search(text or ""))


def has_reliable_pagination(metadata) -> bool:
    """
    True only with positive metadata evidence of a normal, sequentially-
    paginated source (LaTeX/pdfTeX, Word, LibreOffice/OpenOffice).
    Defaults to False for anything unrecognized or missing -- fail-safe:
    the cost of unnecessary accumulating context is just extra tokens;
    the cost of wrongly skipping it on a genuinely messy export is
    silently mis-transcribed content.
    """
    if not metadata:
        return False
    creator = str(metadata.get("/Creator") or "").lower()
    producer = str(metadata.get("/Producer") or "").lower()
    combined = f"{creator} {producer}"
    if any(marker in combined for marker in _MESSY_EXPORT_MARKERS):
        return False
    return any(marker in combined for marker in _RELIABLE_PAGINATION_MARKERS)


def is_expected_char(c: str) -> bool:
    if ord(c) < 128:
        return True
    if c in _ALLOWED_EXTRA_CHARS:
        return True
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in ALLOWED_MATH_RANGES)


def _has_suspicious_repeated_char_run(text: str) -> bool:
    for m in _REPEATED_CHAR_RUN_RE.finditer(text):
        ch = m.group(1)
        if ch.isascii() and ch.isalnum():
            # Plain ASCII digits/letters repeating are routinely
            # legitimate -- page numbers ("111"), Roman numerals
            # ("Analysis III") -- confirmed real false positives against
            # LN_Analysis.pdf's own table of contents and references.
            continue
        if ch in _LEGITIMATE_REPEATABLE_CHARS:
            continue
        return True
    return False


def _has_collapsed_prose_run(text: str) -> bool:
    """
    A long word made up ENTIRELY of plain ASCII letters is almost
    certainly collapsed prose spacing, not a legitimate dense equation.
    Deliberately not just "is this word long": a real equation like
    "𝑓(𝑎+ℎ)=𝑓(𝑎)+∇𝑓(𝑎)·ℎ+𝑜(∥ℎ∥)" (confirmed real, correct content from
    LN_Analysis.pdf page 100) has no internal whitespace either -- that's
    normal for math notation -- but mixes in parentheses, operators, and
    non-ASCII math symbols, which real collapsed English prose doesn't.
    """
    return any(len(w) > _MAX_WORD_LENGTH and w.isascii() and w.isalpha() for w in text.split())


def page_looks_defective(text: str) -> bool:
    """
    True when this page's local text extraction shows any of the four
    defect signatures confirmed against real documents. The first three
    are corruption (garbled/wrong output); the fourth is a different
    category -- genuine, unfixable-by-extraction-choice information loss:
    1. A long run of plain ASCII letters with no internal whitespace
       (word-spacing collapse) -- real prose doesn't do this; a real
       equation can look similarly unspaced but isn't pure letters.
    2. More than a handful of characters outside the expected range for
       an English math document -- e.g. Private Use Area characters,
       which have no legitimate meaning at all and are a strong,
       specific corruption signal on their own.
    3. The same character repeated 3+ times with no separation (e.g.
       'ﬁﬁﬁﬁﬁ', '›››››') -- catches delimiter-glyph corruption even when
       every individual character involved is otherwise a legitimate
       symbol (a single 'ﬁ' ligature is completely normal in a word like
       "significant"; five in a row with no letters between them is not).
    4. A lost exponent/subscript on an isolated variable ("D5" for D^5,
       "R2" for R^2) outside any ^{...}/_{...} group already produced by
       reconstruct_line_with_scripts() -- see
       _LOST_EXPONENT_OR_SUBSCRIPT_RE/_has_lost_exponent_outside_scripts.
       Unlike 1-3, this isn't corrupted text; it's real content plain
       (non-structured) text extraction cannot represent at all.
    A blank/near-empty page is not defective -- that's a legitimate
    spacer page, not corrupted content.
    """
    if _has_collapsed_prose_run(text):
        return True
    unexpected = sum(1 for c in text if not c.isspace() and not is_expected_char(c))
    if unexpected > _MAX_UNEXPECTED_CHARS:
        return True
    if _has_suspicious_repeated_char_run(text):
        return True
    return _has_lost_exponent_outside_scripts(text)


def group_into_runs(page_numbers: list[int]) -> list[list[int]]:
    """Groups a sorted list of page numbers into maximal runs of consecutive integers."""
    if not page_numbers:
        return []
    runs = []
    current = [page_numbers[0]]
    for p in page_numbers[1:]:
        if p == current[-1] + 1:
            current.append(p)
        else:
            runs.append(current)
            current = [p]
    runs.append(current)
    return runs


def split_run_into_batches(run: list[int], max_batch_size: int) -> list[list[int]]:
    """Splits a run of consecutive page numbers into capped-size batches, in order."""
    return [run[i:i + max_batch_size] for i in range(0, len(run), max_batch_size)]


def get_bookend_context(all_page_texts: list[str], run: list[int]) -> tuple[str, str]:
    """
    Nearest-neighbor local text immediately before/after a run of
    defective pages. Correct by construction, not a search: since
    group_into_runs produces maximal runs, the page immediately outside
    a run's boundary cannot itself be defective, or it would already be
    part of the run.
    """
    before_idx = run[0] - 2
    after_idx = run[-1]
    before = all_page_texts[before_idx] if before_idx >= 0 else ""
    after = all_page_texts[after_idx] if after_idx < len(all_page_texts) else ""
    return before, after


def derive_folder_category(pdf_path: str) -> str:
    """The input PDF's immediate parent folder name (e.g. 'ta_notes') -- purely mechanical, no LLM judgment."""
    return os.path.basename(os.path.dirname(pdf_path))


def _yaml_scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_scalar(v) for v in value) + "]"
    text = str(value)
    if not text:
        return '""'
    if any(c in text for c in ':#[]{},&*!|>\'"%@`') or text.strip() != text:
        return f'"{text.replace(chr(34), chr(92) + chr(34))}"'
    return text


def build_frontmatter(metadata: dict) -> str:
    """
    Renders a minimal YAML frontmatter block for a flat metadata dict
    (str/int/float/bool/list-of-primitives values) -- sufficient for
    this project's own metadata, not a general-purpose YAML serializer,
    so no new dependency (PyYAML) for something this narrow.
    """
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def discover_pdf_files(notes_dir: str, file_filter: str | None = None) -> list[str]:
    if not os.path.isdir(notes_dir):
        return []
    files = []
    for name in sorted(os.listdir(notes_dir)):
        if name.lower().endswith(".pdf"):
            if file_filter is None or name == file_filter:
                files.append(os.path.join(notes_dir, name))
    return files


def build_accumulated_context(cache: dict, up_to_page: int, window: int | None = None) -> str:
    """
    Joins already-transcribed pages before up_to_page, in order. A gap (a
    page that failed and was never cached) is silently omitted rather
    than raising -- graceful degradation, not a hard requirement.

    window=None (default) includes every prior page. A positive window
    includes only the trailing `window` pages, e.g. window=3 at
    up_to_page=10 includes pages 7, 8, 9 -- see _ACCUMULATION_WINDOW.
    """
    start_page = 1 if window is None else max(1, up_to_page - window)
    parts = []
    for page_num in range(start_page, up_to_page):
        text = cache.get(str(page_num))
        if text:
            parts.append(f"--- Page {page_num} ---\n{text}")
    return "\n\n".join(parts)


def build_transcription_prompt(
    accumulated_context: str, hint_text: str, page_number: int, total_pages: int,
    hint_is_high_confidence: bool = False,
) -> str:
    context_block = (
        f"Already-transcribed content from earlier pages, for continuity:\n{accumulated_context}\n\n"
        if accumulated_context else ""
    )
    if hint_is_high_confidence:
        hint_block = (
            "This page's PDF-embedded text layer, from a machine-generated document -- "
            "generally reliable, though large delimiter glyphs (matrix brackets, big "
            "summation/integral signs) can sometimes extract as garbage characters. Trust "
            f"it as a strong prior and use the image to verify/correct any such spots:\n{hint_text}\n\n"
            if hint_text else ""
        )
    else:
        hint_block = (
            "This page's PDF-embedded text layer (often unreliable for handwriting-app "
            f"exports -- a hint only, not authoritative):\n{hint_text}\n\n"
            if hint_text else ""
        )
    context_note = (
        "This document may be a OneNote export, where the page's internal layout window "
        "can split a paragraph non-adjacently -- e.g. a sidebar comment cut down the "
        "middle, where the other half of the sentence appears on a different page than "
        "the very next one. Use the already-transcribed context below to detect and "
        "correctly reassemble any such split content rather than transcribing a fragment "
        "in isolation.\n\n"
    ) if accumulated_context else ""
    return (
        f"This is page {page_number} of {total_pages} from a scanned/exported set of "
        "academic notes, problem sets, or exam pages -- possibly typed, handwritten, or "
        "both on the same page. Transcribe everything on this page into clean markdown: "
        "preserve problem/part numbering, mathematical notation (LaTeX-style, e.g. $...$ "
        "or $$...$$), and reading order.\n\n"
        f"{context_note}"
        f"{context_block}{hint_block}"
        "Respond with ONLY the transcribed markdown for THIS page -- no commentary, no "
        "code fence, no repetition of earlier pages' content.\n"
    )


def parse_transcription_response(response_text) -> str:
    text = (response_text or "").strip()
    match = _CODE_FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()
    # U+FFFD (the Unicode replacement character) is never a legitimate
    # intentional character -- it only ever means a byte sequence
    # couldn't be decoded. Observed repeatedly in live responses
    # (LN_Analysis.pdf, LN_Optimization.pdf), consistently standing in
    # for the model's own em-dash ("Theorem 6.5 <replaced> Equality of
    # ..."), so this substitution is safe regardless of the exact root
    # cause on the API/SDK side.
    text = text.replace("�", "—")
    return text


def build_batch_transcription_prompt(
    page_numbers: list[int], before_context: str, after_context: str, total_pages: int,
) -> str:
    """Prompt for repairing a run of consecutive defective pages in one call (see process_pdf)."""
    before_block = (
        f"Text from the page immediately before this batch, for continuity:\n{before_context}\n\n"
        if before_context else ""
    )
    after_block = (
        f"Text from the page immediately after this batch, for continuity:\n{after_context}\n\n"
        if after_context else ""
    )
    page_list = ", ".join(str(p) for p in page_numbers)
    return (
        f"This is a batch of {len(page_numbers)} consecutive pages (page numbers {page_list} "
        f"of {total_pages} total) from a machine-generated academic document, attached as "
        "images in that exact order. Each page's own local text extraction showed signs of "
        "corruption -- most likely a broken font encoding for extensible delimiter glyphs "
        "(large matrix brackets, big summation/integral signs are built from several stacked "
        "glyph pieces that often lack a correct Unicode mapping), or PDF word-spacing "
        "collapse. Transcribe each page from its image into clean markdown: preserve "
        "problem/part numbering, mathematical notation (LaTeX-style, e.g. $...$ or $$...$$, "
        "with correctly reconstructed matrices/sums/integrals), and reading order.\n\n"
        f"{before_block}{after_block}"
        "Respond with each page's transcription clearly separated using this exact format, "
        "one section per page, in page order, using exactly these page numbers as headers: "
        f"{page_list}.\n"
        "--- PAGE <number> ---\n"
        "<transcribed markdown for that page>\n\n"
        "No commentary, no code fences, nothing outside these page sections.\n"
    )


_BATCH_PAGE_DELIMITER_RE = re.compile(r"---\s*PAGE\s+(\d+)\s*---\s*\n", re.IGNORECASE)


def parse_batch_transcription_response(response_text, expected_page_numbers: list[int]) -> dict[int, str]:
    """
    Splits a batched multi-page response back into per-page
    transcriptions using the '--- PAGE N ---' delimiters requested in
    the prompt. Forgiving by design: returns whatever pages it can
    actually parse rather than raising -- callers detect a partial or
    malformed response (an expected page number missing from the
    result) and fall back to processing those pages individually rather
    than trusting a corrupted batch parse.
    """
    text = response_text or ""
    matches = list(_BATCH_PAGE_DELIMITER_RE.finditer(text))
    result = {}
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        if page_num not in expected_page_numbers:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[page_num] = parse_transcription_response(text[start:end])
    return result


def build_final_markdown(cache: dict, total_pages: int) -> str:
    parts = []
    for page_num in range(1, total_pages + 1):
        text = cache.get(str(page_num))
        if text is None:
            continue
        parts.append(f"<!-- page {page_num} -->\n\n{text}")
    return "\n\n".join(parts)


def render_page_to_image_bytes(pdf_path: str, page_index: int, dpi: int = 200) -> bytes:
    """Touches PyMuPDF -- not unit-tested locally, like the other PyMuPDF functions below."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()


def _page_text_from_dict(page) -> str:
    """
    Structured-mode counterpart to page.get_text(): walks PyMuPDF's "dict"
    text mode (blocks -> lines -> spans, with per-span font size and
    position) and reconstructs each line through
    reconstruct_line_with_scripts(), recovering sub/superscripts that
    plain-mode extraction silently drops. Lines are joined within a block
    with "\n" and blocks with "\n\n", approximating plain get_text()'s own
    paragraph spacing. A block with no text lines (e.g. an image) is
    skipped naturally rather than specially -- Touches PyMuPDF -- not
    unit-tested locally (the reconstruction logic itself is).
    """
    text_dict = page.get_text("dict")
    block_texts = []
    for block in text_dict.get("blocks", []):
        line_texts = [
            reconstruct_line_with_scripts(line.get("spans", []))
            for line in block.get("lines", [])
        ]
        if line_texts:
            block_texts.append("\n".join(line_texts))
    return "\n\n".join(block_texts)


def extract_all_page_texts(pdf_path: str, total_pages: int) -> list[str]:
    """
    Local page text via PyMuPDF's structured "dict" mode (see
    _page_text_from_dict/reconstruct_line_with_scripts) rather than pypdf's
    PdfReader.extract_text() or PyMuPDF's own plain get_text(). Confirmed
    on a real file (Practice Sheet.pdf) that pypdf collapses inter-word
    spacing on some font/kerning setups -- "LetVbe a finite-dimensional
    real vector space and letT:V->Vsatisfy" -- while PyMuPDF's
    layout-aware extraction preserves the same content correctly: "Let V
    be a finite-dimensional real vector space and let T : V ->V satisfy".
    That spacing fix alone doesn't need dict mode (plain get_text() already
    has it); dict mode buys the additional sub/superscript recovery on top.
    Opens the document once for every page rather than once per page.
    Touches PyMuPDF -- not unit-tested locally.
    """
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        return [_page_text_from_dict(doc[i]) for i in range(total_pages)]
    finally:
        doc.close()


def extract_page_text(pdf_path: str, page_index: int) -> str:
    """Single-page counterpart to extract_all_page_texts, for call sites that need only one page's text (e.g. Tier 3's per-page hint). Touches PyMuPDF -- not unit-tested locally."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        return _page_text_from_dict(doc[page_index])
    finally:
        doc.close()


_TOKEN_USAGE_TOTALS = {"input": 0, "output": 0}


def _log_token_usage(response) -> None:
    """Diagnostic only -- prints per-call token counts and keeps a running
    per-process total so a single-document run can report a real cost
    figure instead of a character-count guess."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return
    input_tokens = getattr(usage, "prompt_token_count", None) or 0
    output_tokens = getattr(usage, "candidates_token_count", None) or 0
    _TOKEN_USAGE_TOTALS["input"] += input_tokens
    _TOKEN_USAGE_TOTALS["output"] += output_tokens
    print(f"    [tokens] input={input_tokens} output={output_tokens} (running total: input={_TOKEN_USAGE_TOTALS['input']} output={_TOKEN_USAGE_TOTALS['output']})")


def _call_gemini_single_page(
    client, model: str, image_bytes: bytes, prompt: str,
    temperature: float = 0, prompt_suffix: str = "",
) -> str:
    from google.genai import types

    config = {
        "temperature": temperature,
        "thinking_config": {"thinking_level": "minimal"},
        "max_output_tokens": _MAX_OUTPUT_TOKENS_SINGLE_PAGE,
    }

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            prompt + prompt_suffix,
        ],
        config=config,
    )
    _log_token_usage(response)
    return parse_transcription_response(response.text)


def transcribe_page_via_gemini(client, model: str, image_bytes: bytes, prompt: str) -> str:
    """The only function in this module that calls generate_content for a
    single page -- shared by Tier 3's accumulating loop and by
    repair_page_individually (both the hybrid/whole-doc-batched fallback
    and, transitively, retag's batch-fallback path). Guards against the
    runaway-repetition failure mode (_looks_like_repetition_loop): a
    degenerate first response gets one retry with a nonzero temperature
    and a prompt addendum naming the specific pattern (not used on the
    first attempt -- see _REPETITION_RETRY_TEMPERATURE/
    _REPETITION_RETRY_PROMPT_SUFFIX), and a still-degenerate result
    after that raises rather than being returned, so every existing
    caller's own exception handling (which already exists for network
    errors) treats it as a failed page rather than silently keeping
    garbage."""
    text = _call_gemini_single_page(client, model, image_bytes, prompt)
    if _looks_like_repetition_loop(text):
        print(f"    WARNING: output looks like a runaway repetition loop "
              f"({len(text)} chars); retrying with higher temperature.")
        text = _call_gemini_single_page(
            client, model, image_bytes, prompt,
            temperature=_REPETITION_RETRY_TEMPERATURE,
            prompt_suffix=_REPETITION_RETRY_PROMPT_SUFFIX,
        )
        if _looks_like_repetition_loop(text):
            raise ValueError(
                f"output still looks like a runaway repetition loop after "
                f"retry with higher temperature ({len(text)} chars)"
            )
    return text


def transcribe_batch_via_gemini(client, model: str, images: list[bytes], prompt: str) -> str:
    """
    Sends multiple page images in one call for batched defective-run
    repair -- see build_batch_transcription_prompt/
    parse_batch_transcription_response. Not unit-tested locally (network
    call); returns the raw response text, since splitting it into
    per-page transcriptions is parse_batch_transcription_response's job,
    not this function's.
    """
    from google.genai import types

    contents = [prompt] + [types.Part.from_bytes(data=img, mime_type="image/png") for img in images]
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "temperature": 0,
            "thinking_config": {"thinking_level": "minimal"},
            "max_output_tokens": _MAX_OUTPUT_TOKENS_BATCH,
        },
    )
    _log_token_usage(response)
    return response.text or ""


def repair_batch(client, model: str, pdf_path: str, batch: list[int], prompt: str) -> dict[int, str]:
    """One capped batch's worth of defective pages, repaired in a single
    call. Any page whose text looks like a runaway repetition loop
    (_looks_like_repetition_loop) is dropped from the result before the
    completeness check below, rather than trusted -- this reuses the
    existing "missing page(s)" ValueError/fallback path (process_pdf
    retries a missing page individually, where transcribe_page_via_gemini
    has its own detect-and-retry guard) instead of needing a separate
    repair mechanism for batch responses specifically."""
    images = [render_page_to_image_bytes(pdf_path, p - 1, dpi=_DPI_TYPESET) for p in batch]
    response_text = transcribe_batch_via_gemini(client, model, images, prompt)
    parsed = parse_batch_transcription_response(response_text, batch)
    for page_num, text in list(parsed.items()):
        if _looks_like_repetition_loop(text):
            print(f"  WARNING: page {page_num} in this batch looks like a "
                  f"runaway repetition loop ({len(text)} chars); dropping it "
                  f"so it's retried individually.")
            del parsed[page_num]
    if set(parsed.keys()) != set(batch):
        missing = sorted(set(batch) - set(parsed.keys()))
        raise ValueError(f"batch response missing page(s) {missing}")
    return parsed


def repair_page_individually(client, model: str, pdf_path: str, page_num: int, hint_text: str, total_pages: int) -> str:
    image_bytes = render_page_to_image_bytes(pdf_path, page_num - 1, dpi=_DPI_TYPESET)
    prompt = build_transcription_prompt(
        "", hint_text, page_num, total_pages, hint_is_high_confidence=True,
    )
    return call_with_retries(lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt))


def _write_markdown_and_index(md_path, frontmatter, final_md, pdf_path, academic_hub_root,
                               folder_category, total_pages, client, known_doc_types=KNOWN_DOC_TYPES):
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + final_md)

    try:
        file_id = compute_file_id(pdf_path)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")
        course = derive_course(rel_pdf_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_pdf_path,
            course=course, folder_category=folder_category, content_sample=final_md,
            page_count=total_pages, client=client, content_hash=compute_content_hash(md_path),
            known_doc_types=known_doc_types,
        )
    except Exception as err:
        # Indexing must never block or corrupt the actual transcription
        # output (spec §4.2) -- the markdown file above is already
        # written and complete regardless of what happens here.
        print(f"WARNING: source-indexer update failed for {md_path} ({err}); "
              f"rerun `python index_search.py rebuild` later to catch it up.")


def process_pdf(pdf_path: str, client, model_override: str | None, academic_hub_root: str,
                 dry_run: bool = False, known_doc_types=KNOWN_DOC_TYPES) -> None:
    from pypdf import PdfReader

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), "processed_outputs")
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    cache_path = os.path.join(output_dir, f"{base_name}_pages_cache.json")

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    folder_category = derive_folder_category(pdf_path)
    base_metadata = {
        "source_pdf": os.path.basename(pdf_path),
        "folder_category": folder_category,
        "total_pages": total_pages,
    }

    # Defect scoring is only ever attempted for documents with positive
    # metadata evidence of normal pagination -- a Nebo/MyScript/OneNote
    # export never reaches it at all, regardless of what any single
    # page's text happens to look like. Confirmed necessary against a
    # real file: a Nebo export with several near-blank spacer pages
    # would otherwise look "clean" on a naive per-page check.
    reliable_pagination = has_reliable_pagination(reader.metadata)
    all_page_texts = None
    defective_page_numbers: list[int] = []
    if reliable_pagination:
        all_page_texts = extract_all_page_texts(pdf_path, total_pages)
        defective_page_numbers = [
            n for n in range(1, total_pages + 1) if page_looks_defective(all_page_texts[n - 1])
        ]
    defect_ratio = (len(defective_page_numbers) / total_pages) if (reliable_pagination and total_pages) else 1.0

    # --- Tier 1: fully clean, reliably-paginated -- pure local extraction, 0 API calls. ---
    if reliable_pagination and not defective_page_numbers:
        print(f"[{base_name}] {total_pages} page(s) -- clean machine-generated text "
              f"detected, using free local extraction (0 API calls).")
        if dry_run:
            print(f"  would extract all {total_pages} pages locally, no API calls needed.")
            return
        assert all_page_texts is not None
        pages_text = {str(n): all_page_texts[n - 1].strip() for n in range(1, total_pages + 1)}
        final_md = build_final_markdown(pages_text, total_pages)
        frontmatter = build_frontmatter({
            **base_metadata, "routing": "local", "pages_repaired": 0, "repaired_pages": [], "tags": [],
        })
        _write_markdown_and_index(
            md_path, frontmatter, final_md, pdf_path, academic_hub_root,
            folder_category, total_pages, client, known_doc_types=known_doc_types,
        )
        print(f"[{base_name}] wrote {md_path} (local extraction, 0 API calls)")
        return

    # --- Tier 2: reliably-paginated, some pages defective, not too many -- hybrid repair. ---
    if reliable_pagination and defect_ratio <= _MAX_DEFECT_RATIO_FOR_HYBRID:
        assert all_page_texts is not None
        model = model_override or _MODEL_TYPESET
        runs = group_into_runs(defective_page_numbers)
        print(f"[{base_name}] {total_pages} page(s) -- {len(defective_page_numbers)} "
              f"({defect_ratio:.0%}) need repair across {len(runs)} run(s), rest clean locally.")

        cache = load_json_cache(cache_path)

        if dry_run:
            for run in runs:
                for batch in split_run_into_batches(run, _MAX_BATCH_SIZE):
                    status = "cached" if all(str(p) in cache for p in batch) else "would call Gemini (batch)"
                    print(f"  pages {batch[0]}-{batch[-1]}: {status}")
            return

        for run in runs:
            before_ctx, after_ctx = get_bookend_context(all_page_texts, run)
            for batch in split_run_into_batches(run, _MAX_BATCH_SIZE):
                if all(str(p) in cache for p in batch):
                    continue
                prompt = build_batch_transcription_prompt(batch, before_ctx, after_ctx, total_pages)
                try:
                    parsed = call_with_retries(
                        lambda: repair_batch(client, model, pdf_path, batch, prompt)
                    )
                    for p, text in parsed.items():
                        cache[str(p)] = text
                    save_json_cache(cache_path, cache)
                    print(f"  pages {batch[0]}-{batch[-1]}: repaired via batch ({len(batch)} pages)")
                except Exception as err:
                    print(f"  WARNING: batch repair failed for pages {batch} ({err}); "
                          f"falling back to individual per-page calls.")
                    for p in batch:
                        if str(p) in cache:
                            continue
                        try:
                            cache[str(p)] = repair_page_individually(
                                client, model, pdf_path, p, all_page_texts[p - 1], total_pages,
                            )
                            save_json_cache(cache_path, cache)
                            print(f"    page {p}: repaired individually")
                        except Exception as page_err:
                            print(f"    WARNING: giving up on page {p} after retries ({page_err}); "
                                  f"keeping its local text as-is -- rerun to retry.")

        pages_text = {str(n): all_page_texts[n - 1].strip() for n in range(1, total_pages + 1)}
        pages_text.update(cache)
        final_md = build_final_markdown(pages_text, total_pages)
        frontmatter = build_frontmatter({
            **base_metadata, "routing": "hybrid", "model": model,
            "pages_repaired": len(defective_page_numbers), "repaired_pages": defective_page_numbers,
            "tags": [],
        })
        _write_markdown_and_index(
            md_path, frontmatter, final_md, pdf_path, academic_hub_root,
            folder_category, total_pages, client, known_doc_types=known_doc_types,
        )
        print(f"[{base_name}] wrote {md_path} (hybrid: {len(defective_page_numbers)}/{total_pages} pages repaired)")
        return

    # --- Tier 2 (whole-document batched): reliably-paginated, but over
    # _MAX_DEFECT_RATIO_FOR_HYBRID -- batch every page through Gemini
    # rather than trusting local extraction for the pages no heuristic
    # happened to flag. Reuses the same batching machinery as hybrid
    # repair (split_run_into_batches/repair_batch), just applied to the
    # whole page range instead of only the flagged runs. No bookend
    # context (build_batch_transcription_prompt's before/after params) --
    # there's no "known clean neighbor" to borrow from anymore since every
    # page is being sent -- and no accumulation, for the same reason Tier
    # 1/hybrid don't need it: reliable_pagination means pages are
    # independent, with no risk of a paragraph split non-adjacently across
    # a page boundary (that's specifically a messy-export failure mode,
    # handled by Tier 3 below).
    if reliable_pagination:
        model = model_override or _MODEL_TYPESET
        all_pages = list(range(1, total_pages + 1))
        batches = split_run_into_batches(all_pages, _MAX_BATCH_SIZE)
        print(f"[{base_name}] {total_pages} page(s) -- {len(defective_page_numbers)} "
              f"({defect_ratio:.0%}) defective, over the {_MAX_DEFECT_RATIO_FOR_HYBRID:.0%} "
              f"hybrid-repair threshold -- batching the whole document instead "
              f"({len(batches)} batch(es)).")

        cache = load_json_cache(cache_path)

        if dry_run:
            for batch in batches:
                status = "cached" if all(str(p) in cache for p in batch) else "would call Gemini (batch)"
                print(f"  pages {batch[0]}-{batch[-1]}: {status}")
            return

        for batch in batches:
            if all(str(p) in cache for p in batch):
                continue
            prompt = build_batch_transcription_prompt(batch, "", "", total_pages)
            try:
                parsed = call_with_retries(
                    lambda: repair_batch(client, model, pdf_path, batch, prompt)
                )
                for p, text in parsed.items():
                    cache[str(p)] = text
                save_json_cache(cache_path, cache)
                print(f"  pages {batch[0]}-{batch[-1]}: transcribed via batch ({len(batch)} pages)")
            except Exception as err:
                print(f"  WARNING: batch transcription failed for pages {batch} ({err}); "
                      f"falling back to individual per-page calls.")
                for p in batch:
                    if str(p) in cache:
                        continue
                    try:
                        assert all_page_texts is not None
                        cache[str(p)] = repair_page_individually(
                            client, model, pdf_path, p, all_page_texts[p - 1], total_pages,
                        )
                        save_json_cache(cache_path, cache)
                        print(f"    page {p}: transcribed individually")
                    except Exception as page_err:
                        print(f"    WARNING: giving up on page {p} after retries ({page_err}); "
                              f"local text is already known unreliable so it's omitted "
                              f"entirely rather than used as a fallback -- rerun to retry.")

        final_md = build_final_markdown(cache, total_pages)
        frontmatter = build_frontmatter({
            **base_metadata, "routing": "gemini_batched", "model": model,
            "pages_repaired": len(defective_page_numbers), "repaired_pages": defective_page_numbers,
            "tags": [],
        })
        _write_markdown_and_index(
            md_path, frontmatter, final_md, pdf_path, academic_hub_root,
            folder_category, total_pages, client, known_doc_types=known_doc_types,
        )
        print(f"[{base_name}] wrote {md_path} (whole-document batched, {len(cache)}/{total_pages} pages transcribed)")
        return

    # --- Tier 3: not reliably paginated -- handwritten, or a messy app
    # export (Nebo/MyScript/OneNote). Every reliably-paginated case is
    # already handled above (Tier 1, hybrid repair, or whole-document
    # batching), so reliable_pagination is always False by this point.
    dpi = _DPI_HANDWRITING
    model = model_override or _MODEL_HANDWRITING

    cache = load_json_cache(cache_path)
    print(f"[{base_name}] {total_pages} page(s) ({len(cache)} already cached). "
          f"model={model}, accumulation=on, dpi={dpi}.")

    if dry_run:
        for page_num in range(1, total_pages + 1):
            status = "cached" if str(page_num) in cache else "would call Gemini"
            print(f"  page {page_num}: {status}")
        return

    for page_num in range(1, total_pages + 1):
        if str(page_num) in cache:
            continue

        hint_text = extract_page_text(pdf_path, page_num - 1)
        accumulated_context = build_accumulated_context(cache, page_num, window=_ACCUMULATION_WINDOW)
        prompt = build_transcription_prompt(
            accumulated_context, hint_text, page_num, total_pages,
            hint_is_high_confidence=False,
        )

        try:
            image_bytes = render_page_to_image_bytes(pdf_path, page_num - 1, dpi=dpi)
            transcription = call_with_retries(
                lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt)
            )
        except Exception as err:
            # Accumulating context means later pages depend on this one --
            # skipping ahead would silently degrade every subsequent
            # page's context. Stop instead; a rerun resumes from here.
            print(f"  WARNING: giving up on page {page_num} after retries ({err}); "
                  f"stopping here (later pages need this one's context) -- rerun to resume.")
            break

        cache[str(page_num)] = transcription
        save_json_cache(cache_path, cache)
        print(f"  [{page_num}/{total_pages}] transcribed ({len(transcription)} chars)")

    final_md = build_final_markdown(cache, total_pages)
    frontmatter = build_frontmatter({
        **base_metadata,
        "routing": "gemini_accumulating",
        "model": model,
        "tags": [],
    })
    _write_markdown_and_index(
        md_path, frontmatter, final_md, pdf_path, academic_hub_root,
        folder_category, total_pages, client, known_doc_types=known_doc_types,
    )
    print(f"[{base_name}] wrote {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe typed/handwritten notes, problem sets, or exams into "
                    "markdown. Runs locally -- no GCP VM needed."
    )
    parser.add_argument(
        "--notes-subdir", required=True,
        help="Path, relative to the academic-hub/ folder next to this project, "
             "containing the input PDFs directly (not nested in per-book folders).",
    )
    parser.add_argument("--file", default=None, help="Only process this one PDF filename (default: every PDF found).")
    parser.add_argument(
        "--model", default=None,
        help=f"Gemini model override. Default: auto-selects {_MODEL_TYPESET} for reliably-"
             f"paginated machine-generated documents (LaTeX/Word), {_MODEL_HANDWRITING} otherwise.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List which pages would be processed (and which are already cached) without calling the API.",
    )
    args = parser.parse_args()

    load_dotenv_override()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent / "academic-hub"
    notes_dir = academic_hub_dir / args.notes_subdir
    pdf_paths = discover_pdf_files(str(notes_dir), args.file)
    if not pdf_paths:
        print(f"No PDF files found under {notes_dir}.")
        sys.exit(1)

    client = None
    if not args.dry_run:
        client = get_gemini_client()
        if client is None:
            sys.exit(1)

    for pdf_path in pdf_paths:
        process_pdf(pdf_path, client, args.model, str(academic_hub_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
