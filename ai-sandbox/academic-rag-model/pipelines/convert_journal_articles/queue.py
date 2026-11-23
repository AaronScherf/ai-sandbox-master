"""A read-only list of the PDFs that still need transcription, for planning Gemini subscription runs.

Built from the disk and the oversize ledger, never from a model: a PDF is pending when it has no transcript
(`processed_outputs/<name>.md`) or its transcript is missing pages. Short ones are "ready", longest-last so a small quota clears the most papers; long ones
the owner cleared as articles are "ready (long)"; over-limit ones with no answer wait on the owner's decision.
`write_queue` renders it to `<articles_dir>/TRANSCRIPTION_QUEUE.md`.
"""

import os
import re

from pipelines.convert_journal_articles import oversize


def _pages_present(md_path: str) -> int:
    """Distinct `<!-- page N -->` markers in a transcript. A metered run that gives up on a page still writes the file,
    so fewer markers than the PDF has pages means a truncated transcript."""
    with open(md_path, encoding="utf-8") as f:
        return len({int(n) for n in re.findall(r"<!-- page (\d+) -->", f.read())})


def build(articles_dir: str, index_root: str, pdf_paths: list[str], page_count) -> dict[str, list[dict]]:
    ledger = oversize.load(index_root)
    out: dict[str, list[dict]] = {"ready": [], "ready_long": [], "waiting": [], "unreadable": []}
    for pdf in pdf_paths:
        folder, name = os.path.split(pdf)
        md = os.path.join(folder, "processed_outputs", os.path.splitext(name)[0] + ".md")
        rel = os.path.relpath(pdf, index_root).replace(os.sep, "/")
        pages = page_count(pdf)
        row = {"path": os.path.relpath(pdf, articles_dir).replace(os.sep, "/"), "pages": pages}
        if os.path.exists(md):
            have = _pages_present(md)
            if pages is None or have >= pages:
                continue
            row["incomplete"] = f"transcript has {have} of {pages} pages"
        choice = ledger.get(rel, {}).get("choice")
        if pages is None:
            out["unreadable"].append(row)
        elif choice in ("leave", "move"):
            continue
        elif pages > oversize.THRESHOLD and choice != "article":
            out["waiting"].append(row)
        elif pages > oversize.THRESHOLD:
            out["ready_long"].append(row)
        else:
            out["ready"].append(row)
    for rows in out.values():
        rows.sort(key=lambda r: (r["pages"] or 0, r["path"]))
    return out


def render(queue: dict[str, list[dict]]) -> str:
    def table(rows):
        def cell(r):
            pages = r["pages"] if r["pages"] is not None else "?"
            return f"{pages} ({r['incomplete']})" if r.get("incomplete") else str(pages)

        return "\n".join(f"| {r['path']} | {cell(r)} |" for r in rows) or "| (none) | |"

    def total(rows):
        return sum(r["pages"] or 0 for r in rows)

    head = "| PDF | Pages |\n|---|---|\n"
    ready, long_, wait = queue["ready"], queue["ready_long"], queue["waiting"]
    return "\n".join([
        "# Transcription queue",
        "",
        "Generated; do not edit. Rebuild with `python -m pipelines.convert_journal_articles.convert_journal_articles --queue`.",
        "A PDF is pending when it has no `processed_outputs/<name>.md`. Agent runs transcribe six pages per document per round, "
        "so the pages column is the quota to plan with.",
        "",
        f"## Ready: {len(ready)} PDFs, {total(ready)} pages (shortest first)", "", head + table(ready), "",
        f"## Ready, long (cleared as articles): {len(long_)} PDFs, {total(long_)} pages", "", head + table(long_), "",
        f"## Waiting on an owner decision (over {oversize.THRESHOLD} pages): {len(wait)} PDFs", "", head + table(wait), "",
        f"## Unreadable: {len(queue['unreadable'])}", "", head + table(queue["unreadable"]), ""])


def write_queue(articles_dir: str, index_root: str, pdf_paths: list[str], page_count) -> str:
    path = os.path.join(articles_dir, "TRANSCRIPTION_QUEUE.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(build(articles_dir, index_root, pdf_paths, page_count)))
    return path
