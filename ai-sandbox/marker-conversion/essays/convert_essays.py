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


def process_docx(docx_path: str, output_dir: str) -> str:
    """Converts one .docx and writes it to <output_dir>/<basename>.md with
    a small YAML frontmatter block. Returns the path written."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(docx_path))[0]
    md_path = os.path.join(output_dir, f"{base_name}.md")

    markdown, warnings = convert_docx_to_markdown(docx_path)
    frontmatter = build_frontmatter({
        "source_docx": os.path.basename(docx_path),
        "word_count": len(markdown.split()),
        "conversion_warnings": len(warnings),
    })

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + markdown)

    for warning in warnings:
        print(f"  WARNING: {warning}")
    print(f"[{base_name}] wrote {md_path} ({len(markdown.split())} words)")
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
        "--dry-run", action="store_true",
        help="List which .docx files would be converted without actually converting them.",
    )
    args = parser.parse_args()

    docx_paths = discover_docx_files(args.essays_dir, args.file)
    if not docx_paths:
        print(f"No .docx files found under {args.essays_dir}.")
        sys.exit(1)

    output_dir = os.path.join(args.essays_dir, "processed_outputs")

    if args.dry_run:
        for docx_path in docx_paths:
            print(f"  would convert {os.path.basename(docx_path)}")
        return

    for docx_path in docx_paths:
        process_docx(docx_path, output_dir)


if __name__ == "__main__":
    main()
