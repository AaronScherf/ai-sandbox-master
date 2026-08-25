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

Full accumulating context: every already-transcribed page is included as
context for the next page's call, not just the immediately preceding
one. This matters specifically for OneNote exports, where the page's
internal layout window can split a paragraph non-adjacently rather than
at a clean page boundary. This requires strictly sequential processing
(page N's call needs pages 1..N-1 already transcribed) -- see
process_pdf().

Everything except the actual PyMuPDF rendering, the Gemini network
call, and the CLI driver is pure-Python and independently unit-tested
(tests/test_transcribe_notes.py) -- no torch/marker dependency, matching
chapter_index.py/page_markers.py/describe_images.py.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from gemini_utils import (
    call_with_retries,
    get_gemini_client,
    load_dotenv_override,
    load_json_cache,
    save_json_cache,
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
_RELIABLE_PAGINATION_MARKERS = ("latex", "pdftex", "word", "libreoffice", "openoffice")

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
_ALLOWED_MATH_RANGES = (
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

# Above this fraction of a document's pages scoring as defective, treat
# it as not a good hybrid-repair candidate at all -- fall back to
# transcribing every page via Gemini instead of piecemeal-repairing a
# document that's mostly broken locally.
_MAX_DEFECT_RATIO_FOR_HYBRID = 0.35

# Cap on how many consecutive defective pages go into one batched repair
# call -- bounds both the blast radius of one failed/malformed batch and
# the risk of the model losing track of per-page delimiters in a very
# large response.
_MAX_BATCH_SIZE = 12

_DPI_TYPESET = 150
_DPI_HANDWRITING = 200

_MODEL_TYPESET = "gemini-3.1-flash-lite"
_MODEL_HANDWRITING = "gemini-3.6-flash"


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


def _is_expected_char(c: str) -> bool:
    if ord(c) < 128:
        return True
    if c in _ALLOWED_EXTRA_CHARS:
        return True
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in _ALLOWED_MATH_RANGES)


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
    True when this page's local pypdf text extraction shows any of the
    three structural defect signatures confirmed against real documents:
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
    A blank/near-empty page is not defective -- that's a legitimate
    spacer page, not corrupted content.
    """
    if _has_collapsed_prose_run(text):
        return True
    unexpected = sum(1 for c in text if not c.isspace() and not _is_expected_char(c))
    if unexpected > _MAX_UNEXPECTED_CHARS:
        return True
    return _has_suspicious_repeated_char_run(text)


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


def build_accumulated_context(cache: dict, up_to_page: int) -> str:
    """
    Joins every already-transcribed page before up_to_page, in order.
    A gap (a page that failed and was never cached) is silently omitted
    rather than raising -- graceful degradation, not a hard requirement.
    """
    parts = []
    for page_num in range(1, up_to_page):
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
    """Only function in this module that touches PyMuPDF -- not unit-tested locally."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()


def transcribe_page_via_gemini(client, model: str, image_bytes: bytes, prompt: str) -> str:
    """Only function in this module that touches the network -- not unit-tested locally."""
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            prompt,
        ],
        config={
            "temperature": 0,
            "thinking_config": {"thinking_level": "minimal"},
        },
    )
    return parse_transcription_response(response.text)


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
        },
    )
    return response.text or ""


def _repair_batch(client, model: str, pdf_path: str, batch: list[int], prompt: str) -> dict[int, str]:
    """One capped batch's worth of defective pages, repaired in a single call."""
    images = [render_page_to_image_bytes(pdf_path, p - 1, dpi=_DPI_TYPESET) for p in batch]
    response_text = transcribe_batch_via_gemini(client, model, images, prompt)
    parsed = parse_batch_transcription_response(response_text, batch)
    if set(parsed.keys()) != set(batch):
        missing = sorted(set(batch) - set(parsed.keys()))
        raise ValueError(f"batch response missing page(s) {missing}")
    return parsed


def _repair_page_individually(client, model: str, pdf_path: str, page_num: int, hint_text: str, total_pages: int) -> str:
    image_bytes = render_page_to_image_bytes(pdf_path, page_num - 1, dpi=_DPI_TYPESET)
    prompt = build_transcription_prompt(
        "", hint_text, page_num, total_pages, hint_is_high_confidence=True,
    )
    return call_with_retries(lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt))


def process_pdf(pdf_path: str, client, model_override: str | None, dry_run: bool = False) -> None:
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
        all_page_texts = [reader.pages[i].extract_text() or "" for i in range(total_pages)]
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
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(frontmatter + final_md)
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
                        lambda: _repair_batch(client, model, pdf_path, batch, prompt)
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
                            cache[str(p)] = _repair_page_individually(
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
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(frontmatter + final_md)
        print(f"[{base_name}] wrote {md_path} (hybrid: {len(defective_page_numbers)}/{total_pages} pages repaired)")
        return

    # --- Tier 3: not reliably paginated (handwritten/messy export), or too many
    # defects to make hybrid repair worthwhile -- transcribe every page via Gemini.
    use_accumulation = not reliable_pagination
    dpi = _DPI_TYPESET if reliable_pagination else _DPI_HANDWRITING
    model = model_override or (_MODEL_TYPESET if reliable_pagination else _MODEL_HANDWRITING)

    cache = load_json_cache(cache_path)
    print(f"[{base_name}] {total_pages} page(s) ({len(cache)} already cached). "
          f"model={model}, accumulation={'on' if use_accumulation else 'off'}, dpi={dpi}.")

    if dry_run:
        for page_num in range(1, total_pages + 1):
            status = "cached" if str(page_num) in cache else "would call Gemini"
            print(f"  page {page_num}: {status}")
        return

    for page_num in range(1, total_pages + 1):
        if str(page_num) in cache:
            continue

        hint_text = reader.pages[page_num - 1].extract_text() or ""
        accumulated_context = build_accumulated_context(cache, page_num) if use_accumulation else ""
        prompt = build_transcription_prompt(
            accumulated_context, hint_text, page_num, total_pages,
            hint_is_high_confidence=reliable_pagination,
        )

        try:
            image_bytes = render_page_to_image_bytes(pdf_path, page_num - 1, dpi=dpi)
            transcription = call_with_retries(
                lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt)
            )
        except Exception as err:
            if use_accumulation:
                # Full accumulating context means later pages depend on
                # this one -- skipping ahead would silently degrade
                # every subsequent page's context. Stop instead; a
                # rerun resumes from this exact page.
                print(f"  WARNING: giving up on page {page_num} after retries ({err}); "
                      f"stopping here (later pages need this one's context) -- rerun to resume.")
                break
            else:
                # No accumulation means pages are independent -- a
                # rerun fills in just this one page later.
                print(f"  WARNING: giving up on page {page_num} after retries ({err}); "
                      f"skipping (no accumulation needed) -- rerun to fill it in.")
                continue

        cache[str(page_num)] = transcription
        save_json_cache(cache_path, cache)
        print(f"  [{page_num}/{total_pages}] transcribed ({len(transcription)} chars)")

    final_md = build_final_markdown(cache, total_pages)
    frontmatter = build_frontmatter({
        **base_metadata,
        "routing": "gemini_accumulating" if use_accumulation else "gemini_full",
        "model": model,
        "tags": [],
    })
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + final_md)
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

    academic_hub_dir = Path(__file__).resolve().parent.parent / "academic-hub"
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
        process_pdf(pdf_path, client, args.model, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
