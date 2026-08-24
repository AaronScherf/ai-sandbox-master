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
    accumulated_context: str, hint_text: str, page_number: int, total_pages: int
) -> str:
    context_block = (
        f"Already-transcribed content from earlier pages, for continuity:\n{accumulated_context}\n\n"
        if accumulated_context else ""
    )
    hint_block = (
        "This page's PDF-embedded text layer (often unreliable for handwriting-app "
        f"exports -- a hint only, not authoritative):\n{hint_text}\n\n"
        if hint_text else ""
    )
    return (
        f"This is page {page_number} of {total_pages} from a scanned/exported set of "
        "academic notes, problem sets, or exam pages -- possibly typed, handwritten, or "
        "both on the same page. Transcribe everything on this page into clean markdown: "
        "preserve problem/part numbering, mathematical notation (LaTeX-style, e.g. $...$ "
        "or $$...$$), and reading order.\n\n"
        "This document may be a OneNote export, where the page's internal layout window "
        "can split a paragraph non-adjacently -- e.g. a sidebar comment cut down the "
        "middle, where the other half of the sentence appears on a different page than "
        "the very next one. Use the already-transcribed context below to detect and "
        "correctly reassemble any such split content rather than transcribing a fragment "
        "in isolation.\n\n"
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


def process_pdf(pdf_path: str, client, model: str, dry_run: bool = False) -> None:
    from pypdf import PdfReader

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), "processed_outputs")
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    cache_path = os.path.join(output_dir, f"{base_name}_pages_cache.json")

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    cache = load_json_cache(cache_path)

    print(f"[{base_name}] {total_pages} page(s) ({len(cache)} already cached).")

    if dry_run:
        for page_num in range(1, total_pages + 1):
            status = "cached" if str(page_num) in cache else "would call Gemini"
            print(f"  page {page_num}: {status}")
        return

    for page_num in range(1, total_pages + 1):
        if str(page_num) in cache:
            continue

        hint_text = reader.pages[page_num - 1].extract_text() or ""
        accumulated_context = build_accumulated_context(cache, page_num)
        prompt = build_transcription_prompt(accumulated_context, hint_text, page_num, total_pages)

        try:
            image_bytes = render_page_to_image_bytes(pdf_path, page_num - 1)
            transcription = call_with_retries(
                lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt)
            )
        except Exception as err:
            # Full accumulating context means later pages depend on this
            # one -- unlike describe_images.py's independent images,
            # skipping ahead here would silently degrade every
            # subsequent page's context. Stop instead; a rerun resumes
            # from this exact page.
            print(f"  WARNING: giving up on page {page_num} after retries ({err}); "
                  f"stopping here (later pages need this one's context) -- rerun to resume.")
            break

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
    parser.add_argument("--model", default="gemini-3.6-flash")
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
