"""
Frontmatter/page parsing and candidate-pool derivation for
postprocess_notes.py -- see
docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md.
Pure Python, no PyMuPDF/transformers/network import at module scope,
matching chapter_index.py/page_markers.py's dependency-free-module
pattern in this project.
"""
from __future__ import annotations

import re

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n\n?", re.DOTALL)
_PAGE_TAG_RE = re.compile(r"<!-- page (\d+) -->\n\n")


def parse_frontmatter(md_text: str) -> tuple[dict, str]:
    """
    Splits a transcribe_notes.py-produced .md file's leading YAML
    frontmatter block from its body. Returns ({}, md_text unchanged) for
    any file with no frontmatter block at all -- a normal, expected case
    (e.g. Analysis_Exercises.md before its 2026-08-26 re-run, or any
    textbook output this project doesn't control the format of), not an
    error condition.
    """
    match = _FRONTMATTER_RE.match(md_text)
    if not match:
        return {}, md_text
    metadata = yaml.safe_load(match.group(1)) or {}
    body = md_text[match.end():]
    return metadata, body


def split_pages_by_tag(body: str) -> dict[int, str]:
    """
    Inverse of transcribe_notes.py's build_final_markdown: splits a
    <!-- page N --> tagged body back into {page_number: page_text}.
    """
    matches = list(_PAGE_TAG_RE.finditer(body))
    pages: dict[int, str] = {}
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        pages[page_num] = body[start:end].rstrip("\n")
    return pages


def derive_eligible_pages(frontmatter: dict) -> list[int]:
    """
    Local-only pages eligible for post-processing, per the design spec's
    table: routing="local" -> every page; routing="hybrid" -> every page
    except repaired_pages; anything else (gemini_batched,
    gemini_accumulating, or missing routing entirely -- textbook output)
    -> no eligible pages, since those are already fully model-verified
    or aren't a notes-transcription document at all.
    """
    routing = frontmatter.get("routing")
    total_pages = frontmatter.get("total_pages")
    if not isinstance(total_pages, int) or total_pages < 1:
        return []
    if routing == "local":
        return list(range(1, total_pages + 1))
    if routing == "hybrid":
        repaired = set(frontmatter.get("repaired_pages") or [])
        return [p for p in range(1, total_pages + 1) if p not in repaired]
    return []


def is_correction_target(frontmatter: dict) -> bool:
    """
    True for a notes-transcription document (has a "routing" field --
    textbook output never does) that hasn't already been through this
    post-processing pass.
    """
    return "routing" in frontmatter and not frontmatter.get("postprocessed", False)
