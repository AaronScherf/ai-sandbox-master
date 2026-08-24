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

# The observed failure mode for a PDF whose math font lacks a proper
# ToUnicode mapping: prose extracts perfectly, but every math
# symbol/variable comes through as a bare '?' (confirmed identically via
# both pypdf and pymupdf against LN_Analysis.pdf -- not a library
# weakness, a broken font encoding in the PDF itself). A ratio this low
# only trips on genuine garbling, not a document's occasional real "?".
_MAX_GARBLING_RATIO = 0.05

_DPI_TYPESET = 150
_DPI_HANDWRITING = 200

_MODEL_TYPESET = "gemini-3.6-flash-lite"
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


def should_use_local_extraction(page_texts: list[str], max_garbling_ratio: float = _MAX_GARBLING_RATIO) -> bool:
    """
    True when this document's own pypdf text extraction looks clean
    enough to trust outright, skipping Gemini entirely. Purely
    content-based (unlike has_reliable_pagination) -- a "machine-
    generated" document can still fail this if its math font is broken,
    which is exactly the real case that motivated this split.

    Callers MUST pass every page's text, not a sparse sample: an earlier
    sampled version of this check (5 evenly-spaced pages) missed real
    garbling in two different real documents purely by landing on
    unrepresentative pages -- title/blank pages in one case, math-light
    pages in the other. A full-document scan costs under 10 seconds even
    on a 294-page PDF, so there's no real reason to sample.
    """
    total_words = 0
    garbled_words = 0
    for text in page_texts:
        words = text.split()
        total_words += len(words)
        garbled_words += sum(1 for w in words if "?" in w)
    if total_words == 0:
        return False
    return (garbled_words / total_words) <= max_garbling_ratio


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
            "generally reliable for prose wording, but math symbols/variables may appear "
            "corrupted as a literal '?' due to a broken font encoding. Trust it for "
            f"prose, and use the image to identify what each '?' should actually be:\n{hint_text}\n\n"
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


def process_pdf(pdf_path: str, client, model_override: str | None, dry_run: bool = False) -> None:
    from pypdf import PdfReader

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), "processed_outputs")
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    cache_path = os.path.join(output_dir, f"{base_name}_pages_cache.json")

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    # Local extraction is only ever considered for documents with
    # positive metadata evidence of normal pagination -- a Nebo/MyScript
    # export never reaches the (content-based) garbling check at all,
    # regardless of what any single page's text happens to look like.
    # Confirmed necessary against a real file: a Nebo export with several
    # near-blank spacer pages would otherwise pass the garbling check on
    # sampled text alone.
    reliable_pagination = has_reliable_pagination(reader.metadata)
    all_page_texts = None
    use_local = False
    if reliable_pagination:
        all_page_texts = [reader.pages[i].extract_text() or "" for i in range(total_pages)]
        use_local = should_use_local_extraction(all_page_texts)

    if use_local:
        print(f"[{base_name}] {total_pages} page(s) -- clean machine-generated text "
              f"detected, using free local extraction (0 API calls).")
        if dry_run:
            print(f"  would extract all {total_pages} pages locally, no API calls needed.")
            return
        assert all_page_texts is not None  # use_local implies reliable_pagination populated it
        pages_text = {
            str(n): all_page_texts[n - 1].strip()
            for n in range(1, total_pages + 1)
        }
        final_md = build_final_markdown(pages_text, total_pages)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(final_md)
        print(f"[{base_name}] wrote {md_path} (local extraction, 0 API calls)")
        return

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
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_md)
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
