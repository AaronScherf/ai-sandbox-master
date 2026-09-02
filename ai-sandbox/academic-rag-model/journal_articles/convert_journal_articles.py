#!/usr/bin/env python3
"""
convert_journal_articles.py
Converts academic journal-article PDFs -- typically short, born-digital,
publisher-rendered documents (Apache FOP, XEP, LaTeX) -- into Markdown,
reusing notes/transcribe_notes.py's tiered cost-routing pipeline
wholesale (free local extraction for a clean text layer, hybrid repair,
full Gemini-vision transcription as the fallback) rather than
reimplementing it. process_pdf() needed no changes to be reused here
except a known_doc_types passthrough (see index_card.py's own
generalization for essays/convert_essays.py, the same fix applied one
layer up).

Unlike academic-hub's own notes pipeline (a flat folder of PDFs per
course/category), journal articles live under thematic subfolders that
may nest further (research/journal-articles/<theme>/...), so discovery
walks recursively instead of a single listdir.

A document far outside normal paper length -- a full book or
dissertation mis-filed into this corpus, confirmed real: a 402-page
monograph briefly sat here -- is flagged and skipped entirely rather
than run through per-page vision transcription one page at a time. If
it belongs in the GPU/Marker textbook pipeline instead, that's a
deliberate manual step (moving it into academic-hub/ and running
convert_textbook.py there), never something this script triggers on
its own -- the GPU VM is the most expensive part of this whole project
and stays reserved for files actually sitting in that pipeline's own
folder.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from common.gemini_utils import get_gemini_client, load_dotenv_override
from notes.transcribe_notes import process_pdf

_JOURNAL_DOC_TYPES = frozenset({"journal_article"})

_DEFAULT_MAX_PAGES = 150  # confirmed real: a 402-page monograph mis-filed
# into research/journal-articles alongside genuine ~20-page papers is
# exactly the case this guards against -- comfortably above any real
# journal article's length, comfortably below a full book's.

# Confirmed real 2026-09-02: a Zotero library synced into this same
# directory tree puts its own attachment copies under zotero/storage/
# <hash>/ -- not a topic folder, and often a duplicate of a PDF already
# converted elsewhere in the tree (re-processing it would be pure wasted
# API cost). local/ is a similar stray, non-topic folder confirmed real
# in this same corpus. Excluded by directory name at any depth.
_EXCLUDED_DIR_NAMES = frozenset({"zotero", "local"})


def discover_pdf_files(articles_dir: str, file_filter: str | None = None) -> list[str]:
    """Recursively walks articles_dir for .pdf files -- unlike notes/
    transcribe_notes.py's flat discover_pdf_files, since journal
    articles live under thematic subfolders (economics/, misc/, ...)
    that may themselves nest further. Sorted for deterministic
    ordering regardless of the OS's own directory-walk order."""
    if not os.path.isdir(articles_dir):
        return []
    files = []
    for dirpath, dirnames, filenames in os.walk(articles_dir):
        dirnames[:] = [d for d in sorted(dirnames) if d.lower() not in _EXCLUDED_DIR_NAMES]
        for name in sorted(filenames):
            if name.lower().endswith(".pdf"):
                if file_filter is None or name == file_filter:
                    files.append(os.path.join(dirpath, name))
    return sorted(files)


def _page_count(pdf_path: str) -> int | None:
    """Local, free page-count read via pypdf -- the same library
    process_pdf() itself uses, so this stays consistent with how the
    pipeline downstream will count pages. Returns None (rather than
    raising) on an unreadable PDF, so the caller can skip it with a
    clear message instead of crashing the whole batch."""
    from pypdf import PdfReader

    try:
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert journal-article PDFs into Markdown, reusing notes/transcribe_notes.py's tiered pipeline."
    )
    default_articles_dir = (
        Path(__file__).resolve().parent.parent.parent / "research" / "journal-articles"
    )
    parser.add_argument(
        "--articles-dir", default=str(default_articles_dir),
        help=f"Directory containing journal-article PDFs, searched recursively. Default: {default_articles_dir}",
    )
    parser.add_argument("--file", default=None, help="Only process this one PDF filename (default: every PDF found).")
    default_index_root = Path(__file__).resolve().parent.parent.parent / "research"
    parser.add_argument(
        "--index-root", default=str(default_index_root),
        help=f"Root for this corpus's own source-indexer .index/ (course is derived from each PDF's "
             f"path relative to this root -- with the default, a paper's thematic subfolder becomes "
             f"its course). Default: {default_index_root}",
    )
    parser.add_argument(
        "--max-pages", type=int, default=_DEFAULT_MAX_PAGES,
        help=f"Documents over this page count are flagged and skipped, not converted -- likely a "
             f"mis-filed book, not a journal article. Default: {_DEFAULT_MAX_PAGES}.",
    )
    parser.add_argument(
        "--model", default=None,
        help="Gemini model override, passed through to process_pdf() (same auto-selection as the "
             "notes pipeline otherwise).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List which PDFs would be processed (and flag oversized ones) without calling the API.",
    )
    args = parser.parse_args()

    pdf_paths = discover_pdf_files(args.articles_dir, args.file)
    if not pdf_paths:
        print(f"No PDF files found under {args.articles_dir}.")
        sys.exit(1)

    load_dotenv_override()
    client = None
    if not args.dry_run:
        client = get_gemini_client()
        if client is None:
            sys.exit(1)

    for pdf_path in pdf_paths:
        page_count = _page_count(pdf_path)
        if page_count is None:
            print(f"WARNING: could not read {pdf_path}; skipping.")
            continue
        if page_count > args.max_pages:
            print(f"FLAGGED: {pdf_path} has {page_count} pages (over --max-pages {args.max_pages}) -- "
                  f"likely a book or monograph, not a journal article. Skipping. If you want it "
                  f"processed, move it into academic-hub/ and run convert_textbook.py there.")
            continue
        process_pdf(
            pdf_path, client, args.model, args.index_root, dry_run=args.dry_run,
            known_doc_types=_JOURNAL_DOC_TYPES,
        )


if __name__ == "__main__":
    main()
