#!/usr/bin/env python3
"""
convert_essays.py
Converts short prose .docx documents (statement-of-purpose / application
essays, and anything else "one document, one file" -- no chapters, no
OCR, no scanned pages) into Markdown.

Unlike textbook/convert_textbook.py (Marker, GPU-based OCR for scanned
PDFs) and notes/transcribe_notes.py (Gemini vision, for handwritten/
messy-export PDFs), a .docx already carries its own structure (headings,
bold/italic runs, lists) in the file format itself -- there's no OCR
problem to solve, so this needs no vision model and no GCP VM. It uses
mammoth (https://github.com/mwilliamson/python-mammoth), a pure-Python
library with no external binary dependency (unlike pandoc), to read that
existing structure directly into Markdown.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from common.gemini_utils import get_gemini_client, load_dotenv_override
from indexer.index_card import (
    compute_content_hash,
    compute_file_id,
    derive_course,
    reconcile_and_write,
)

# mammoth's markdown writer defensively backslash-escapes every occurrence
# of these characters in ordinary text (not just where it would matter,
# e.g. a literal "1." at the start of a line) -- see
# mammoth/writers/markdown.py's _escape_markdown, which runs on all text
# content unconditionally. That leaves prose like "well-known" or
# "the U.S." rendered as "well\-known"/"the U\.S\." -- harmless for
# rendering but noisy for downstream text analysis, and none of these
# essays have a real paragraph starting with a literal "1." or "-" (the
# actual case that escaping exists to protect against; confirmed by
# grepping the converted output), so it's safe to invert unconditionally.
_ESCAPED_MARKDOWN_CHAR_RE = re.compile(r"\\([`*_{}\[\]()#+\-.!])")


def _unescape_markdown(text: str) -> str:
    """Inverts mammoth's own _escape_markdown: unescapes the specific
    punctuation it defensively backslash-escapes, then collapses a
    doubled backslash (its escaping of a literal source backslash) back
    to one. Order matters -- the doubled-backslash collapse must run
    second, or "\\\\-" (an escaped literal backslash followed by an
    escaped hyphen) would incorrectly unescape as one step."""
    text = _ESCAPED_MARKDOWN_CHAR_RE.sub(r"\1", text)
    return text.replace("\\\\", "\\")


def derive_folder_category(docx_path: str) -> str:
    """The input .docx's immediate parent folder name (e.g.
    'application_essays') -- purely mechanical, same convention as
    notes/transcribe_notes.py's derive_folder_category."""
    return os.path.basename(os.path.dirname(docx_path))


def discover_docx_files(essays_dir: str, file_filter: str | None = None) -> list[str]:
    if not os.path.isdir(essays_dir):
        return []
    files = []
    for name in sorted(os.listdir(essays_dir)):
        if name.lower().endswith(".docx") and not name.startswith("~$"):
            if file_filter is None or name == file_filter:
                files.append(os.path.join(essays_dir, name))
    return files


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
    """Minimal YAML frontmatter for this script's own flat metadata dict --
    same narrow approach as notes/transcribe_notes.py's build_frontmatter,
    duplicated rather than imported so this subproject stays independent
    (see README's dependency graph -- essays needs no OCR/defect-detection
    machinery notes.transcribe_notes carries)."""
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def convert_docx_to_markdown(docx_path: str) -> tuple[str, list[str]]:
    """Converts one .docx file to Markdown via mammoth, returning the
    Markdown text and any conversion warning messages (e.g. an
    unrecognized paragraph style) mammoth reports along the way. Touches
    mammoth -- not unit-tested locally, like the other library-calling
    functions in this project (render_page_to_image_bytes etc.)."""
    import mammoth

    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_markdown(f)
    warnings = [m.message for m in result.messages if m.type == "warning"]
    return _unescape_markdown(result.value.strip()) + "\n", warnings


# The academic-hub corpus's own doc_type vocabulary (indexer.index_card.
# KNOWN_DOC_TYPES) is textbook/problem_set/ta_notes/handwritten_notes --
# none of those fit a personal essay or a loose research-brainstorming
# document. Confirmed live (2026-08-30) against the real 19-file essays
# corpus before this constant existed: every single card got force-fit
# into "textbook" or "handwritten_notes", since generate_index_card()'s
# prompt hard-codes that enum -- passing a corpus-appropriate vocabulary
# here (reconcile_and_write's known_doc_types) fixes it at the source
# rather than just the post-hoc validation.
_ESSAY_DOC_TYPES = frozenset({"personal_essay", "research_notes"})


def _index_essay(docx_path: str, md_path: str, markdown: str, index_root: str, client) -> None:
    """Best-effort source-indexer hook, mirroring notes/transcribe_notes.py's
    _write_markdown_and_index: reconciles this essay into its own index
    card under `index_root`'s .index/ (course derived from the essay's
    path relative to index_root -- e.g. every file under
    independent-research/notes/** resolves to course 'notes', regardless
    of whether it's nested in application_essays/ or sits directly in
    notes/). Indexing must never block or corrupt the actual conversion
    output -- the .md file is already written and complete regardless of
    what happens here, same failure-isolation philosophy as the notes
    pipeline's own hook."""
    try:
        file_id = compute_file_id(docx_path)
        rel_md_path = os.path.relpath(md_path, index_root).replace(os.sep, "/")
        rel_docx_path = os.path.relpath(docx_path, index_root).replace(os.sep, "/")
        course = derive_course(rel_docx_path)
        reconcile_and_write(
            index_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_docx_path,
            course=course, folder_category=derive_folder_category(docx_path),
            content_sample=markdown, page_count=None, client=client,
            content_hash=compute_content_hash(md_path), known_doc_types=_ESSAY_DOC_TYPES,
        )
    except Exception as err:
        print(f"  WARNING: source-indexer update failed for {md_path} ({err}); "
              f"rerun `python -m indexer.index_search rebuild --academic-hub {index_root}` "
              f"later to catch it up.")


def process_docx(docx_path: str, output_dir: str, index_root: str | None = None, client=None) -> str:
    """Converts one .docx and writes it to <output_dir>/<basename>.md with
    a small YAML frontmatter block. If index_root and client are given,
    also reconciles a source-indexer card for it (see _index_essay).
    Returns the path written."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(docx_path))[0]
    md_path = os.path.join(output_dir, f"{base_name}.md")

    markdown, warnings = convert_docx_to_markdown(docx_path)
    frontmatter = build_frontmatter({
        "source_docx": os.path.basename(docx_path),
        "word_count": len(markdown.split()),
        "conversion_warnings": len(warnings),
        "tags": [],
    })

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + markdown)

    for warning in warnings:
        print(f"  WARNING: {warning}")
    print(f"[{base_name}] wrote {md_path} ({len(markdown.split())} words)")

    if index_root and client:
        _index_essay(docx_path, md_path, markdown, index_root, client)

    return md_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert .docx essays into Markdown. Runs locally -- no GCP VM, no API calls."
    )
    default_essays_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "research" / "independent-research" / "notes" / "application_essays"
    )
    parser.add_argument(
        "--essays-dir", default=str(default_essays_dir),
        help=f"Directory containing the input .docx files directly (not nested in subfolders). "
             f"Default: {default_essays_dir}",
    )
    parser.add_argument("--file", default=None, help="Only process this one .docx filename (default: every .docx found).")
    parser.add_argument(
        "--output-dir", default=None,
        help="Where to write the converted .md files. Default: a 'processed_outputs' folder "
             "created inside --essays-dir. Override this to consolidate output from several "
             "--essays-dir folders (e.g. subfolders of a shared parent) into one place.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List which .docx files would be converted without actually converting them.",
    )
    default_index_root = Path(__file__).resolve().parent.parent.parent / "research"
    parser.add_argument(
        "--index-root", default=str(default_index_root),
        help="Root for this corpus's own source-indexer .index/ (sibling of academic-hub/'s own "
             f"root, same reconcile_and_write() the notes/textbook pipelines use). Default: {default_index_root}",
    )
    parser.add_argument(
        "--no-index", action="store_true",
        help="Skip the source-indexer hook entirely (no Gemini calls) -- just convert.",
    )
    args = parser.parse_args()

    docx_paths = discover_docx_files(args.essays_dir, args.file)
    if not docx_paths:
        print(f"No .docx files found under {args.essays_dir}.")
        sys.exit(1)

    output_dir = args.output_dir or os.path.join(args.essays_dir, "processed_outputs")

    if args.dry_run:
        for docx_path in docx_paths:
            print(f"  would convert {os.path.basename(docx_path)}")
        return

    client = None
    if not args.no_index:
        load_dotenv_override()
        client = get_gemini_client()
        if client is None:
            print("WARNING: no Gemini client available -- converting without indexing "
                  "(pass --no-index to silence this).")

    for docx_path in docx_paths:
        process_docx(docx_path, output_dir, index_root=args.index_root, client=client)


if __name__ == "__main__":
    main()
