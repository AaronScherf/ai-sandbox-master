"""
page_audit.py
Finds pages of a converted textbook that carry no content, and tells apart
pages that are blank in the source from pages that failed to convert.

Needed because a conversion failure is not always an exception: when surya's
inference server dies, surya logs "Inference error" and returns an empty
result, so Marker renders the page successfully with nothing on it.

Run on a finished conversion:
    python -m pipelines.convert_textbook.page_audit <book.md> [--pdf source.pdf]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

from pypdf import PdfReader, PdfWriter

# Written under the tag of a page that has content in the source but converted
# to nothing, so the gap is visible in the output and still counted as empty.
UNCONVERTED_FLAG = "<!-- conversion-empty: source page has content that did not convert -->"

_PAGE_TAG_RE = re.compile(r"<!-- page (\d+) -->")
# HTML comments (page/folio tags, the flag above), anchor spans, and Marker's
# own "{N}----" page separators are scaffolding, not page content.
_NON_CONTENT_RE = re.compile(r"<!--.*?-->|<span[^>]*>\s*</span>|\{\d+\}-{48}", re.DOTALL)

# A page is blank when almost none of it is dark, ignoring the outer margin
# where scans carry gutter shadows and edge noise.
_MARGIN_FRACTION = 0.08
_DARK_LEVEL = 160
_BLANK_DARK_FRACTION = 0.002


def _split_pages(markdown: str) -> tuple[str, dict[int, str]]:
    """Splits into (text before the first tag, {page: tag + body})."""
    matches = list(_PAGE_TAG_RE.finditer(markdown))
    if not matches:
        return markdown, {}
    pages: dict[int, str] = {}
    ends = [m.start() for m in matches[1:]] + [len(markdown)]
    for match, end in zip(matches, ends):
        page = int(match.group(1))
        pages[page] = pages.get(page, "") + markdown[match.start():end]
    return markdown[:matches[0].start()], pages


def has_content(segment: str) -> bool:
    return bool(_NON_CONTENT_RE.sub("", segment).strip())


def empty_pages(markdown: str, start_page: int, end_page: int) -> list[int]:
    """Pages in [start_page, end_page) with no content, or no page tag at all."""
    _, pages = _split_pages(markdown)
    return [p for p in range(start_page, end_page) if not has_content(pages.get(p, ""))]


def replace_page(markdown: str, page: int, segment: str) -> str:
    """Returns markdown with page's tag and body replaced by segment."""
    preamble, pages = _split_pages(markdown)
    pages[page] = segment
    parts = [preamble] + [pages[p] for p in sorted(pages)]
    return "\n\n".join(part.strip("\n") for part in parts if part.strip())


def format_runs(pages: list[int]) -> str:
    runs: list[list[int]] = []
    for page in sorted(pages):
        if runs and page == runs[-1][1] + 1:
            runs[-1][1] = page
        else:
            runs.append([page, page])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs) or "none"


def is_blank_page(reader: PdfReader, page_index: int) -> bool:
    """
    True when the rendered source page has essentially no ink. Any failure to
    render counts as not blank, so an unreadable page is never waved through.
    """
    try:
        import pypdfium2

        writer = PdfWriter()
        writer.add_page(reader.pages[page_index])
        buf = io.BytesIO()
        writer.write(buf)
        document = pypdfium2.PdfDocument(buf.getvalue())
        try:
            image = document[0].render(scale=1.0).to_pil().convert("L")
        finally:
            document.close()
        width, height = image.size
        dx, dy = int(width * _MARGIN_FRACTION), int(height * _MARGIN_FRACTION)
        histogram = image.crop((dx, dy, width - dx, height - dy)).histogram()
        return sum(histogram[:_DARK_LEVEL]) / sum(histogram) < _BLANK_DARK_FRACTION
    except Exception as render_err:
        print(f"WARNING: could not check whether page {page_index} is blank ({render_err}).")
        return False


def _total_pages(markdown_path: str, markdown: str) -> int:
    run_config = os.path.join(os.path.dirname(os.path.abspath(markdown_path)), "run_config.json")
    if os.path.exists(run_config):
        with open(run_config, "r", encoding="utf-8") as f:
            return max(end for _, end in json.load(f)["boundaries"])
    return max((int(n) for n in _PAGE_TAG_RE.findall(markdown)), default=-1) + 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Report empty-page runs in a converted textbook.")
    parser.add_argument("markdown", help="The conversion's .md (or .rag.md) file")
    parser.add_argument("--pdf", help="Source PDF; separates source-blank pages from unexplained ones")
    args = parser.parse_args(argv)

    with open(args.markdown, "r", encoding="utf-8") as f:
        markdown = f.read()
    total = _total_pages(args.markdown, markdown)
    empty = empty_pages(markdown, 0, total)
    print(f"{os.path.basename(args.markdown)}: {len(empty)} of {total} pages empty (0-based PDF page numbers)")
    if not args.pdf:
        print(f"  empty: {format_runs(empty)}")
        return 1 if empty else 0

    reader = PdfReader(args.pdf)
    blank = [p for p in empty if is_blank_page(reader, p)]
    unexplained = sorted(set(empty) - set(blank))
    print(f"  blank in source: {format_runs(blank)}")
    print(f"  UNEXPLAINED ({len(unexplained)}): {format_runs(unexplained)}")
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())
