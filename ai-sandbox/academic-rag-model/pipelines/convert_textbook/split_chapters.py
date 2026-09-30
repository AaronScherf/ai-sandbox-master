#!/usr/bin/env python3
"""
split_chapters.py
Post-processes an already-converted textbook's merged <Book>.rag.md
(written by describe_images.py) into one file per chapter, using
toc_identify.identify_chapters() to find confident chapter boundaries.
Exists because a single 500KB-2MB textbook .rag.md file was crashing
tablet sync -- see docs/superpowers/specs/2026-09-23-textbook-chapter-
split-design.md.

Only ever acts on a book when identify_chapters() is confident; anything
less is skipped and reported, never best-effort split. For a confident
book: chapter files land in the mirrored academic_notes/.../<Book>/
chapters/ directory (tablet-synced), and the full merged .rag.md is
relocated to academic_resources/.../<Book>/ instead -- everything else
about a book already lives there, and it's the one place too big to
sync to the tablet.

When a book has no usable folio tags at all (confirmed live: Hansen's
front-matter OCR never anchored a folio offset during conversion, so
none were ever written), falls back to matching the book's own source
PDF outline/bookmarks against its printed TOC
(toc_identify.identify_chapters_via_outline) -- see that module's
docstring for why this works with no OCR involved. The PDF is located
from the book's own _metadata.json (source_pdf_filename, or the older
source_pdf_path field -- see _locate_source_pdf), never required to
exist.

Last resort, when neither of those works either (confirmed live: Simon
has zero PDF outline entries at all): a human fills in a simple
"Title | PageNumber" template (toc_identify.generate_chapter_template)
at the book's own chapter_titles.txt. Run with --init-template to
create a starter file for every book that isn't already splittable
without overwriting one a human has started filling in; a normal run
picks it up automatically once it's filled in.

If even that's still empty, pass --allow-gemini-repair (real API cost,
so never on by default) to try toc_repair.py's Gemini-assisted repair
as the very last step: it classifies the book's own heading structure
into a chapter list (writing the same chapter_titles.txt, marked for
review) and, only when the printed TOC itself is confirmed unparseable
(not just missing folio tags), also reconstructs a clean replacement
table directly in .rag.md (never the raw .md), backing up the original
alongside it first. Never overwrites a template that already has real
content in it -- human or a prior Gemini run.

Pure-Python except for the CLI driver, filesystem I/O, and pypdf (used
only for the outline fallback's already-local source PDF, no GPU/
network/Marker dependency) -- same posture as chapter_index.py and
toc_identify.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from core.env.academic_hub_paths import textbook_rag_md_path, to_resources_root
from pipelines.convert_textbook.toc_identify import (
    TocIdentification,
    front_matter_window,
    generate_chapter_template,
    identify_chapters,
    identify_chapters_from_manual_list,
    identify_chapters_via_outline,
    parse_manual_chapter_list,
)
from pipelines.convert_textbook.toc_repair import (
    chapters_to_review_template,
    classify_chapters_via_gemini,
    extract_heading_outline,
    find_large_heading_gaps,
    reconstruct_toc_table_via_gemini,
    splice_repaired_table,
)

_CHAPTER_TEMPLATE_FILENAME = "chapter_titles.txt"


_MAX_SLUG_LEN = 60


def _slugify(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    if len(slug) > _MAX_SLUG_LEN:
        # A garbled TOC title (a chapter's own nested sub-TOC bled into
        # its title -- confirmed live in Cameron's rag.md) can otherwise
        # produce a 100+ char filename; cut at the last word boundary
        # within the cap rather than mid-word.
        slug = slug[:_MAX_SLUG_LEN].rsplit("_", 1)[0]
    return slug or "untitled"


def _chapter_files(text: str, result: TocIdentification) -> dict[str, str]:
    """
    Builds {filename: content} from an already-confident identification.
    "00_front_matter.rag.md" covers everything before the first matched
    chapter heading (omitted if the first chapter starts at offset 0);
    "NN_<slug>.rag.md" covers each chapter through the byte before the
    next chapter's heading (or end of text for the last chapter).
    """
    files: dict[str, str] = {}
    first_offset = result.matches[0].offset
    if first_offset > 0:
        files["00_front_matter.rag.md"] = text[:first_offset]

    for i, match in enumerate(result.matches, 1):
        end = result.matches[i].offset if i < len(result.matches) else len(text)
        filename = f"{i:02d}_{_slugify(match.chapter.title)}.rag.md"
        files[filename] = text[match.offset:end]

    return files


def split_into_chapter_files(text: str) -> dict[str, str] | None:
    """Returns _chapter_files(text, ...) for a confidently-identified
    book, or None if identify_chapters() isn't confident."""
    result = identify_chapters(text)
    if not result.confident:
        return None
    return _chapter_files(text, result)


def _resources_rag_path(rag_path: str) -> str | None:
    """The academic_resources/ mirror of a notes-side rag_path, or None
    if rag_path isn't under academic_notes/ at all (ad-hoc/test paths)."""
    parts = rag_path.replace("\\", "/").split("/")
    if "academic_notes" not in parts:
        return None
    return to_resources_root(rag_path)


def _resources_book_dir(book_dir: str) -> str:
    """book_dir mapped onto academic_resources/, where a book's
    _metadata.json and source PDF both live -- book_dir itself may
    already be there, or may be the academic_notes/ mirror."""
    parts = book_dir.replace("\\", "/").split("/")
    if "academic_notes" in parts:
        return to_resources_root(book_dir)
    return book_dir


def _locate_source_pdf(book_dir: str) -> str | None:
    """
    The book's own source PDF, if findable. Tries two tiers, same order
    describe_images.py's reconcile_book_naming already uses:

    1. source_pdf_filename from _metadata.json (recorded since
       convert_textbook.py started saving it) -- looked up directly in
       the course's textbooks/ directory.
    2. source_pdf_path -- an older field, still present on conversions
       from before source_pdf_filename existed (confirmed live: Axler,
       Simon). Usable only when it's a real, academic-hub-root-relative
       local path; a GCP VM conversion's source_pdf_path is instead the
       temp download's own path (confirmed live: Hansen's "../academic-
       rag-model/temp_gcs_input_...pdf"), never useful locally, so any
       path containing "temp_gcs_input" is skipped rather than resolved.

    Returns None if metadata, both fields, or the file itself isn't
    found; never raises.
    """
    resources_dir = _resources_book_dir(book_dir)
    folder_name = os.path.basename(os.path.normpath(resources_dir))
    metadata_path = os.path.join(resources_dir, f"{folder_name}_metadata.json")
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    # resources_dir = .../academic_resources/<course>/textbooks/processed_outputs/<Book>/
    textbooks_dir = os.path.dirname(os.path.dirname(resources_dir))

    filename = metadata.get("source_pdf_filename")
    if filename:
        pdf_path = os.path.join(textbooks_dir, filename)
        if os.path.exists(pdf_path):
            return pdf_path

    legacy_path = metadata.get("source_pdf_path")
    if legacy_path and "temp_gcs_input" not in legacy_path:
        # textbooks_dir = <hub_root>/academic_resources/<course>/textbooks
        hub_root = os.path.dirname(os.path.dirname(os.path.dirname(textbooks_dir)))
        # legacy_path is recorded with forward slashes even on Windows
        # (see academic_hub_paths.py's own normalization); os.path.join
        # alone wouldn't convert those, leaving a mixed-separator string.
        candidate = os.path.normpath(os.path.join(hub_root, legacy_path))
        if os.path.exists(candidate):
            return candidate

    return None


def _manual_chapter_list_path(book_dir: str) -> str:
    """Where a human-filled chapter template lives for this book -- see
    toc_identify.generate_chapter_template. Always returns the path;
    existence is the caller's concern."""
    resources_dir = _resources_book_dir(book_dir)
    return os.path.join(resources_dir, _CHAPTER_TEMPLATE_FILENAME)


def ensure_chapter_template(book_dir: str) -> str:
    """
    Writes a starter chapter template for this book if one doesn't
    already exist -- never overwrites a template a human may have
    already started filling in. Returns a one-line status string.
    """
    folder_name = os.path.basename(os.path.normpath(book_dir))
    template_path = _manual_chapter_list_path(book_dir)
    if os.path.exists(template_path):
        return f"[{folder_name}] template already exists at {template_path}"

    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(generate_chapter_template(folder_name))
    return f"[{folder_name}] template created at {template_path}"


def split_book(
    book_dir: str,
    dry_run: bool = False,
    gemini_client=None,
    gemini_model: str = "gemini-3.6-flash",
) -> str:
    """
    book_dir: a book's processed_outputs/<Book>/ directory, under either
    academic_resources/ or academic_notes/ -- textbook_rag_md_path
    resolves either to the same notes-mirrored .rag.md. Returns a
    one-line status string; never raises for a missing or unconfident
    book, so a caller looping over many books can just print each result.

    gemini_client: pass an already-built client (common.gemini_utils.
    get_gemini_client) to enable the last-resort Gemini-assisted repair
    (toc_repair.py) once folio tags, PDF outline, and any existing
    manual template have all failed. None (the default) disables it
    entirely -- never attempted during dry_run either, since it's the
    one path here that costs a real (if small) API call.
    """
    folder_name = os.path.basename(os.path.normpath(book_dir))
    rag_path = textbook_rag_md_path(book_dir)
    if not os.path.exists(rag_path):
        return f"[{folder_name}] SKIP -- no .rag.md found at {rag_path}"

    with open(rag_path, "r", encoding="utf-8") as f:
        text = f.read()

    result = identify_chapters(text)
    method = "folio tags"

    # Table repair -- runs before any other matching attempt, and
    # whenever folio tags alone weren't enough to split the book,
    # regardless of the specific reason why. Deliberately not narrowed
    # to "TOC fully unparseable": confirmed live (Simon) that a TOC can
    # parse to real, correct entries -- reason "no folio tags found in
    # the body" -- while still rendering just as unusably for a human
    # reader as a fully garbled one. It exists to fix the file as a
    # standalone artifact (see toc_repair.py's docstring), so it must
    # also run ahead of outline/manual-template regardless of whether
    # one of those ends up making the split itself confident on its own
    # (confirmed live: Hayashi) -- text may grow/shrink here, so every
    # offset computed afterward must be against the same final text;
    # nothing above this point may be trusted once repair has run.
    # Never repeats once a backup exists.
    if not result.confident and gemini_client is not None and not dry_run:
        backup_path = (_resources_rag_path(rag_path) or rag_path) + ".bak"
        if not os.path.exists(backup_path):
            repair = reconstruct_toc_table_via_gemini(front_matter_window(text), gemini_client, gemini_model)
            if repair is None:
                print(f"WARNING: [{folder_name}] Gemini did not return a usable TOC table repair.")
            else:
                patched = splice_repaired_table(text, repair)
                if patched is None:
                    print(
                        f"WARNING: [{folder_name}] Gemini's repair markers weren't found "
                        f"verbatim in the text; TOC table left untouched."
                    )
                else:
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    with open(rag_path, "w", encoding="utf-8") as f:
                        f.write(patched)
                    text = patched
                    print(f"[{folder_name}] repaired TOC table in {rag_path} (original backed up to {backup_path}).")
                    result = identify_chapters(text)  # the repaired table may now parse on its own
                    if result.confident:
                        method = "folio tags (after Gemini TOC repair)"

    if not result.confident:
        pdf_path = _locate_source_pdf(book_dir)
        if pdf_path is not None:
            try:
                outline_result = identify_chapters_via_outline(text, PdfReader(pdf_path))
            except Exception as err:
                outline_result = None
                print(f"WARNING: [{folder_name}] could not read source PDF at {pdf_path} ({err}).")
            if outline_result is not None and outline_result.confident:
                result = outline_result
                method = "PDF outline"

    template_path = _manual_chapter_list_path(book_dir)
    if not result.confident and os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            manual_result = identify_chapters_from_manual_list(text, f.read())
        if manual_result.confident:
            result = manual_result
            method = "manual chapter template"

    if not result.confident and gemini_client is not None and not dry_run:
        # Never overwrite a template that already has real content -- a
        # human (or an earlier Gemini run) may already be partway
        # through it. An untouched blank scaffold (0 parsed chapters) is
        # safe to auto-fill.
        existing_chapters = []
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                existing_chapters = parse_manual_chapter_list(f.read())
        if not existing_chapters:
            outline = extract_heading_outline(text)
            for start_page, end_page in find_large_heading_gaps(outline):
                print(
                    f"WARNING: [{folder_name}] no headings at all between pages {start_page} and "
                    f"{end_page} -- a real chapter's heading may not have converted there (confirmed "
                    f"live: Hayashi). Worth checking the source PDF for a bad scan or missing pages "
                    f"in that range, or a better copy of it."
                )
            chapters = classify_chapters_via_gemini(outline, gemini_client, gemini_model)
            if not chapters:
                print(f"WARNING: [{folder_name}] Gemini did not return a usable chapter classification.")
            else:
                template_text = chapters_to_review_template(folder_name, chapters)
                os.makedirs(os.path.dirname(template_path), exist_ok=True)
                with open(template_path, "w", encoding="utf-8") as f:
                    f.write(template_text)
                manual_result = identify_chapters_from_manual_list(text, template_text)
                if manual_result.confident:
                    result = manual_result
                    method = "Gemini chapter classification (needs review)"

    if not result.confident:
        return f"[{folder_name}] SKIP -- {result.reason}"

    if dry_run:
        return f"[{folder_name}] OK -- {len(result.matches)} chapter(s) matched via {method} (dry run, no writes)"

    files = _chapter_files(text, result)
    chapters_dir = os.path.join(os.path.dirname(rag_path), "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    for filename, content in files.items():
        with open(os.path.join(chapters_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    resources_path = _resources_rag_path(rag_path)
    if resources_path is not None:
        os.makedirs(os.path.dirname(resources_path), exist_ok=True)
        os.replace(rag_path, resources_path)
        source_note = resources_path
    else:
        source_note = rag_path

    return (
        f"[{folder_name}] OK -- wrote {len(files)} chapter file(s) via {method} to {chapters_dir}; "
        f"source at {source_note}"
    )


def discover_book_dirs(processed_outputs_dir: str) -> list[str]:
    if not os.path.isdir(processed_outputs_dir):
        return []
    dirs = []
    for name in sorted(os.listdir(processed_outputs_dir)):
        full = os.path.join(processed_outputs_dir, name)
        if os.path.isdir(full) and os.path.exists(textbook_rag_md_path(full)):
            dirs.append(full)
    return dirs


def main():
    parser = argparse.ArgumentParser(
        description="Split already-converted textbooks' merged .rag.md files into "
                    "per-chapter files under academic_notes/, moving the full merged "
                    "file to academic_resources/. Only acts on books whose chapters "
                    "can be confidently identified from their own printed TOC."
    )
    parser.add_argument(
        "--textbook-subdir", required=True,
        help="Path, relative to the academic-hub/ folder next to this project, "
             "containing processed_outputs/ (e.g. academic_resources/math-camp/textbooks).",
    )
    parser.add_argument("--book", default=None, help="Only process this one book folder name (default: every book found).")
    parser.add_argument(
        "--report", action="store_true",
        help="Dry run: report per-book confidence without writing or moving anything.",
    )
    parser.add_argument(
        "--init-template", action="store_true",
        help="For each book that isn't already confidently splittable (folio tags or "
             "PDF outline), write a starter chapter_titles.txt for manual fill-in, unless "
             "one already exists. Does not split anything itself.",
    )
    parser.add_argument(
        "--allow-gemini-repair", action="store_true",
        help="For any book that still can't be split after folio tags, PDF outline, and "
             "any existing manual template have all failed, try toc_repair.py's "
             "Gemini-assisted repair as a last resort (real, if small, API cost per book -- "
             "never attempted without this flag, and never during --report).",
    )
    parser.add_argument(
        "--gemini-model", default="gemini-3.6-flash",
        help="Model to use for --allow-gemini-repair (default: %(default)s).",
    )
    parser.add_argument(
        "--use-paid-key", action="store_true",
        help="Use PAID_GEMINI_KEY from ai-sandbox/.env instead of GEMINI_API_KEY for "
             "--allow-gemini-repair, same flag as describe_images.py.",
    )
    args = parser.parse_args()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent.parent / "academic-hub"
    processed_outputs_dir = academic_hub_dir / args.textbook_subdir / "processed_outputs"
    book_dirs = discover_book_dirs(str(processed_outputs_dir))
    if args.book:
        book_dirs = [d for d in book_dirs if os.path.basename(d) == args.book]
    if not book_dirs:
        print(f"No books with a .rag.md found under {processed_outputs_dir}.")
        sys.exit(1)

    if args.init_template:
        for book_dir in book_dirs:
            report = split_book(book_dir, dry_run=True)
            if "SKIP" in report:
                print(ensure_chapter_template(book_dir))
            else:
                print(f"{report} -- template not needed")
        return

    gemini_client = None
    if args.allow_gemini_repair and not args.report:
        from core.env.gemini_utils import get_gemini_client, load_dotenv_override
        load_dotenv_override()
        gemini_client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
        if gemini_client is None:
            sys.exit(1)

    for book_dir in book_dirs:
        print(split_book(book_dir, dry_run=args.report, gemini_client=gemini_client, gemini_model=args.gemini_model))


if __name__ == "__main__":
    main()
