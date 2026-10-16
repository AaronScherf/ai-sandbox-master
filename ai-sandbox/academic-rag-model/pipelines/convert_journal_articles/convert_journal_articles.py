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
import datetime
import os
import sys
from pathlib import Path

from core.env.academic_hub_paths import resolve_output_dir
from core.env.corpus_write_lock import corpus_write_lock
from core.env.gemini_utils import get_gemini_client, load_dotenv_override
from core.indexer.index_card import compute_file_id
from pipelines.transcribe_notes.agent_driver import NullDriver, NullDriverFired
from pipelines.transcribe_notes.agent_submit import submit_doc
from pipelines.transcribe_notes.agent_work import AgentDriver, agent_work_dir, dedupe_by_file_id, doc_slug_for
from pipelines.transcribe_notes.transcribe_notes import process_pdf

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


_CHECK_MATH_NOTATION = False  # journal prose: a bare "R2" or "H1" is a statistic or hypothesis label, not a lost exponent


def _bootstrap_text(run_id: str) -> str:
    return f"""Agent-driven journal-article transcription contract for run '{run_id}':

1. Open each document's directory under <index-root>/.agent_work/{run_id}/<doc-slug>/.
2. Read worklist.md to see which task cards are pending.
3. For each pending task-NNNN.md: read every page's image and prompt in
   the card, then fill ONLY the "Agent output" section at the bottom with
   one "--- PAGE <number> ---" section per page, in order, using exactly
   the page numbers the card lists. Never edit any other file or section.
4. For a tier-3 card with more than one page: only the first page has
   real prior-page context supplied. For every later page in that same
   card, carry forward your own transcription of the card's earlier
   pages as continuity context.
5. Once you've filled one or more cards, run:
   python -m pipelines.convert_journal_articles.convert_journal_articles --submit {run_id}
6. If a card comes back marked "bounced: <reason>" in worklist.md, redo
   only that card in place and re-run step 5.
7. Stop once worklist.md shows nothing "pending"/"filled" left for this run.

Papers that are clean machine text have no cards at all: --submit converts them locally.
"""


def _eligible_pdfs(pdf_paths: list[str], max_pages: int) -> list[str]:
    keep = []
    for pdf_path in pdf_paths:
        page_count = _page_count(pdf_path)
        if page_count is None:
            print(f"WARNING: could not read {pdf_path}; skipping.")
        elif page_count > max_pages:
            print(f"FLAGGED: {pdf_path} has {page_count} pages (over --max-pages {max_pages}) -- "
                  f"likely a book or monograph, not a journal article. Skipping. If you want it "
                  f"processed, move it into academic-hub/ and run convert_textbook.py there.")
        else:
            keep.append(pdf_path)
    return keep


def _process_kwargs() -> dict:
    return {"known_doc_types": _JOURNAL_DOC_TYPES, "check_math_notation": _CHECK_MATH_NOTATION}


def _collect(pdf_paths: list[str], args) -> None:
    run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    canonical, _duplicates_of = dedupe_by_file_id(pdf_paths)
    driver = AgentDriver(args.index_root, run_id)
    for pdf_path in canonical:
        process_pdf(pdf_path, None, args.model, args.index_root, driver=driver, collect_mode=True,
                    **_process_kwargs())
    print(f"Collect run '{run_id}' complete under {os.path.join(args.index_root, '.agent_work', run_id)}. "
          f"Papers that are clean machine text have no cards; --submit converts them locally.")


def _finish_locally(pdf_path: str, client, args) -> str:
    """A paper with no cards is clean machine text (collect never writes), so convert it with a NullDriver:
    tier-1 local extraction needs no transcription calls, and any attempt to reach the driver is a hard error."""
    md_path = os.path.join(resolve_output_dir(pdf_path), os.path.splitext(os.path.basename(pdf_path))[0] + ".md")
    if os.path.exists(md_path):
        return "already converted"
    try:
        process_pdf(pdf_path, client, args.model, args.index_root, driver=NullDriver(), **_process_kwargs())
    except NullDriverFired:
        return "needs agent transcription: run --collect first"
    return "converted locally (0 transcription calls)"


def _submit(pdf_paths: list[str], args) -> None:
    client = get_gemini_client()
    if client is None:
        sys.exit(1)
    run_dir = agent_work_dir(args.index_root, args.submit)
    if not os.path.isdir(run_dir):
        print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
        sys.exit(1)
    print("Note: index cards and embeddings are generated through the Gemini API at this step "
          "(small calls); transcription itself is not.")
    by_slug = {doc_slug_for(p, compute_file_id(p)): p for p in pdf_paths}
    staged = set(os.listdir(run_dir))
    with corpus_write_lock([args.index_root], "journal PDF transcription (agent submit)"):
        for slug in sorted(staged):
            pdf_path = by_slug.get(slug)
            if pdf_path is None:
                print(f"Skipping {slug}: no matching PDF found under {args.articles_dir}.")
                continue
            try:
                status = submit_doc(
                    args.index_root, args.index_root, args.submit, slug, pdf_path, client, args.model,
                    allow_api_fallback=args.allow_api_fallback, **_process_kwargs(),
                )
            except Exception as err:  # one malformed document must not abort the rest
                print(f"[{slug}] error: {err}")
                continue
            print(f"[{slug}] {status}")
        for slug, pdf_path in sorted(by_slug.items()):
            if slug not in staged:
                print(f"[{slug}] {_finish_locally(pdf_path, client, args)}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert journal-article PDFs into Markdown, reusing transcribe_notes/transcribe_notes.py's tiered pipeline."
    )
    default_articles_dir = (
        Path(__file__).resolve().parent.parent.parent.parent / "research" / "journal-articles"
    )
    parser.add_argument(
        "--articles-dir", default=str(default_articles_dir),
        help=f"Directory containing journal-article PDFs, searched recursively. Default: {default_articles_dir}",
    )
    parser.add_argument("--file", default=None, help="Only process this one PDF filename (default: every PDF found).")
    default_index_root = Path(__file__).resolve().parent.parent.parent.parent / "research"
    parser.add_argument(
        "--index-root", default=str(default_index_root),
        help=f"Root for this corpus's own source-indexer .index/ (course is derived from each PDF's "
             f"path relative to this root -- with the default, a paper's thematic subfolder becomes "
             f"its course). Also holds .agent_work/. Default: {default_index_root}",
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
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Transcription transport. Default: agent (the Antigravity subscription). "
             "Use 'api' for a fully metered run.",
    )
    parser.add_argument("--collect", action="store_true", help="With --driver agent: write task cards instead of transcribing.")
    parser.add_argument("--run-id", default=None, help="Run id for --collect's .agent_work/ directory (default: a timestamp).")
    parser.add_argument("--submit", default=None, metavar="RUN_ID", help="Validate filled task cards for this run and write through.")
    parser.add_argument(
        "--allow-api-fallback", action="store_true",
        help="With --submit: finish any still-pending/bounced cards via the metered API instead "
             "of leaving them pending. Explicit opt-in only -- never automatic.",
    )
    parser.add_argument("--bootstrap", default=None, metavar="RUN_ID", help="Print the agent's operating contract for this run.")
    args = parser.parse_args()

    if args.bootstrap:
        print(_bootstrap_text(args.bootstrap))
        return

    pdf_paths = discover_pdf_files(args.articles_dir, args.file)
    if not pdf_paths:
        print(f"No PDF files found under {args.articles_dir}.")
        sys.exit(1)

    load_dotenv_override()
    pdf_paths = _eligible_pdfs(pdf_paths, args.max_pages)

    if args.submit:
        _submit(pdf_paths, args)
        return

    if args.collect:
        if args.driver != "agent":
            print("--collect requires --driver agent.")
            sys.exit(1)
        _collect(pdf_paths, args)
        return

    if args.dry_run:
        for pdf_path in pdf_paths:
            process_pdf(pdf_path, None, args.model, args.index_root, dry_run=True, **_process_kwargs())
        return

    if args.driver == "agent":
        # Reaching here means no --collect/--submit: falling through to the API loop would spend real money,
        # which is exactly what the agent driver exists to avoid.
        print("--driver agent requires --collect or --submit (or --dry-run).")
        sys.exit(1)

    client = get_gemini_client()
    if client is None:
        sys.exit(1)
    for pdf_path in pdf_paths:
        process_pdf(pdf_path, client, args.model, args.index_root, **_process_kwargs())


if __name__ == "__main__":
    main()
