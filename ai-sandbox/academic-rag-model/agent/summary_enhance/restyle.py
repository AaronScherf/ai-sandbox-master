"""Rewrite a format-2 enhanced guide into the current format WITHOUT any API call.

    python -m agent.summary_enhance.restyle <guide.enhanced.md> [--in-place] [--output PATH] [--force]

Format 2 marked external paragraphs with a visible `*(External context)*` tag and put
worked examples under a tag line. This tool removes those tags from the text, replaces the
intro sentence, cuts prose paragraphs of more than five sentences, and records the
provenance the tags carried as the frontmatter `paragraph_kinds` (see render.py).

The kinds are INFERRED from the old tags, so the result is marked
`paragraph_kinds_inferred: true`. One ambiguity: a list, table, quote, code fence or display
formula that sits directly after an external paragraph is assumed to continue it (that is how
the format-2 renderer wrote them); a grounded block that happens to open with such an element
right after an external paragraph would be labeled E.

Default output is `<stem>.restyled.md` beside the input; the input is only replaced with
--in-place. Files must live under <corpus>/academic_notes/ (never writes elsewhere).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from agent.summary_enhance.paragraphs import is_prose, split_long_paragraph, split_paragraphs
from agent.summary_enhance.render import INTRO
from agent.summary_enhance.source_loader import SourceError, locate_vault

OLD_EXTERNAL_TAG = "*(External context)*"
_OLD_WORKED_TAG_RE = re.compile(r"^\*\(Worked example[^)]*\)\*$")
_FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n\n", re.DOTALL)


class RestyleError(Exception):
    pass


def restyle_text(text: str) -> str:
    match = _FRONT_RE.match(text)
    if not match:
        raise RestyleError("no YAML frontmatter; this is not an enhanced guide")
    front_lines = match.group(1).split("\n")
    if "format_version: 2" not in front_lines:
        found = next((l for l in front_lines if l.startswith("format_version:")), "no format_version")
        raise RestyleError(f"only format_version 2 guides can be restyled (found: {found})")

    topic = section = None
    pending: str | None = None
    prev: str | None = None
    kinds: dict[str, str] = {}
    out: list[str] = []
    for paragraph in split_paragraphs(text[match.end():]):
        if paragraph.startswith("# "):
            out.append(paragraph)
            continue
        if paragraph.startswith("*Study guide synthesized"):
            out.append(INTRO)
            continue
        if paragraph.startswith("## "):
            topic, section, pending, prev = paragraph[3:].strip(), None, None, None
            out.append(paragraph)
            continue
        if paragraph.startswith("### "):
            section, pending, prev = paragraph[4:].strip(), None, None
            out.append(paragraph)
            continue
        if paragraph == OLD_EXTERNAL_TAG:      # tag on its own line above a list/table/formula
            pending = "E"
            continue
        if _OLD_WORKED_TAG_RE.match(paragraph):
            continue

        text_body = paragraph
        if paragraph.startswith(OLD_EXTERNAL_TAG + " "):
            kind, text_body = "E", paragraph[len(OLD_EXTERNAL_TAG) + 1:]
        elif section == "Worked example":
            kind = "W"
        elif pending:
            kind, pending = pending, None
        elif not is_prose(paragraph) and prev == "E":
            kind = "E"
        else:
            kind = "G"
        pieces = split_long_paragraph(text_body)
        out.extend(pieces)
        prev = kind
        if topic and section:
            key = f"{topic} > {section}"
            kinds[key] = kinds.get(key, "") + kind * len(pieces)

    front: list[str] = []
    inserted = False
    kinds_lines = [f"paragraph_kinds: {json.dumps(kinds, ensure_ascii=False, separators=(',', ':'))}",
                   "paragraph_kinds_inferred: true"]
    for line in front_lines:
        if line.startswith("external_context_marker:"):
            continue
        front.append("format_version: 3" if line == "format_version: 2" else line)
        if line.startswith("options:"):
            front.extend(kinds_lines)
            inserted = True
    if not inserted:
        front.extend(kinds_lines)
    return "---\n" + "\n".join(front) + "\n---\n\n" + "\n\n".join(out) + "\n"


def restyle_file(path: str | Path, *, output: str | Path | None = None, in_place: bool = False,
                 force: bool = False) -> Path:
    src = Path(path).resolve()
    if not src.is_file():
        raise RestyleError(f"not found: {src}")
    try:
        root, _ = locate_vault(src)
    except SourceError as err:
        raise RestyleError(str(err)) from err
    vault = (root / "academic_notes").resolve()
    new_text = restyle_text(src.read_text(encoding="utf-8"))

    if in_place:
        dest = src
    elif output is not None:
        dest = Path(output).resolve()
    else:
        dest = src.with_name(f"{src.stem}.restyled{src.suffix}")
    if dest.suffix.lower() != ".md":
        raise RestyleError(f"output must be a .md file: {dest}")
    if not dest.is_relative_to(vault):
        raise RestyleError(f"output must be inside {vault}: {dest}")
    if dest.exists() and dest != src and not force:
        raise RestyleError(f"{dest} already exists; pass --force to replace it")

    tmp = dest.with_name(dest.name + ".tmp")
    try:
        tmp.write_text(new_text, encoding="utf-8", newline="\n")
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("guide", help="a format-2 .enhanced.md guide inside academic_notes/")
    p.add_argument("--output", help="output .md path (inside academic_notes/)")
    p.add_argument("--in-place", action="store_true", help="replace the input file")
    p.add_argument("--force", action="store_true", help="replace an existing output file")
    args = p.parse_args(argv)
    try:
        dest = restyle_file(args.guide, output=args.output, in_place=args.in_place, force=args.force)
    except RestyleError as err:
        print(f"ERROR: {err}")
        return 2
    print(f"Wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
