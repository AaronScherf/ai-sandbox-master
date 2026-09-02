"""
worklist.py
Generates a clickable Markdown worklist of needs_manual papers from the
dedup manifest, per user request 2026-09-02: after a discovery run, a
scannable list of what still needs a manual browser download -- with a
real link and exactly which auto-created topic folder to save each PDF
into, so convert_journal_articles.py picks it up automatically afterward
without the user needing to guess or re-derive it.
"""
from __future__ import annotations

from pathlib import Path


def _link_for(key: str, entry: dict) -> str:
    if entry.get("doi_url"):
        return entry["doi_url"]
    if key.startswith("http"):
        return key
    return f"https://doi.org/{key}"


def write_needs_manual_worklist(manifest: dict, articles_dir) -> Path:
    entries = [
        (key, entry) for key, entry in manifest.items()
        if entry.get("status") == "needs_manual" and entry.get("work_type") != "dataset"
    ]
    entries.sort(key=lambda kv: kv[1].get("title") or kv[0])

    lines = [
        "# Papers needing manual download",
        "",
        "Auto-fetch couldn't reach these (gated, bot-blocked, or otherwise",
        "unavailable to a scripted request). Open each link in your own",
        "authenticated browser, download the PDF, and save it into the",
        "folder listed underneath -- `convert_journal_articles.py` picks up",
        "anything sitting there automatically.",
        "",
    ]
    for key, entry in entries:
        title = entry.get("title") or key
        link = _link_for(key, entry)
        folder = entry.get("folder")
        lines.append(f"- [{title}]({link})")
        if folder:
            lines.append(f"  - Save to: `research/journal-articles/{folder}/`")
        else:
            lines.append("  - Save to: `research/journal-articles/misc/` (no folder recorded yet)")
    lines.append("")

    path = Path(articles_dir) / "needs_manual_downloads.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
