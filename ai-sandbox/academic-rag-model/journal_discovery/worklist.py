"""
worklist.py
Generates a clickable Markdown worklist of needs_manual papers from the
dedup manifest, per user request 2026-09-02: after a discovery run, a
scannable list of what still needs a manual browser download -- with a
real link, a checkbox to track progress, and exactly which auto-created
topic folder to save each PDF into, so convert_journal_articles.py picks
it up automatically afterward without the user needing to guess or
re-derive it.
"""
from __future__ import annotations

import re
from pathlib import Path

_CHECKBOX_LINE_RE = re.compile(r"^- \[(x| )\] \[.*?\]\((\S+)\)")


def _link_for(key: str, entry: dict) -> str:
    if entry.get("doi_url"):
        return entry["doi_url"]
    if key.startswith("http"):
        return key
    return f"https://doi.org/{key}"


def _read_checked_links(path: Path) -> set[str]:
    """Regenerating this file must not silently wipe a user's own
    progress-tracking checkmarks (distinct from the automatic removal a
    conversion-reconciliation pass does once a download is confirmed)."""
    if not path.exists():
        return set()
    checked = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _CHECKBOX_LINE_RE.match(line)
        if match and match.group(1) == "x":
            checked.add(match.group(2))
    return checked


def _write_checkbox_worklist(
    manifest: dict, articles_dir, filename: str, heading_lines: list[str], status_filter: str,
) -> Path:
    entries = [
        (key, entry) for key, entry in manifest.items()
        if entry.get("status") == status_filter and entry.get("work_type") != "dataset"
    ]
    entries.sort(key=lambda kv: kv[1].get("title") or kv[0])

    path = Path(articles_dir) / filename
    previously_checked = _read_checked_links(path)

    lines = list(heading_lines) + [""]
    for key, entry in entries:
        title = entry.get("title") or key
        link = _link_for(key, entry)
        folder = entry.get("folder")
        checkbox = "x" if link in previously_checked else " "
        lines.append(f"- [{checkbox}] [{title}]({link})")
        if folder:
            lines.append(f"  - Save to: `research/journal-articles/{folder}/`")
        else:
            lines.append("  - Save to: `research/journal-articles/misc/` (no folder recorded yet)")
        if entry.get("relevance_score") is not None:
            lines.append(f"  - Relevance score: {entry['relevance_score']:.2f}")
        if "cites_seed" in entry:
            lines.append(f"  - Cites: {entry['cites_seed']}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_needs_manual_worklist(manifest: dict, articles_dir) -> Path:
    heading = [
        "# Papers needing manual download",
        "",
        "Auto-fetch couldn't reach these (gated, bot-blocked, or otherwise",
        "unavailable to a scripted request). Open each link in your own",
        "authenticated browser, download the PDF, and save it into the",
        "folder listed underneath -- `convert_journal_articles.py` picks up",
        "anything sitting there automatically. Check a box to track your own",
        "progress; once conversion confirms a download landed, the reconciler",
        "removes that entry from this list entirely.",
    ]
    return _write_checkbox_worklist(manifest, articles_dir, "needs_manual_downloads.md", heading, "needs_manual")


def write_snowball_candidates_worklist(manifest: dict, articles_dir) -> Path:
    heading = [
        "# Snowball-sampled candidates awaiting review",
        "",
        "Found by following citations from papers already in your corpus,",
        "via OpenAlex's own citation graph, then narrowed by your",
        "--relevance-prompt. Nothing here has been downloaded yet. Check the",
        "papers you actually want, then run:",
        "",
        "    python -m journal_discovery.snowball confirm",
        "",
        "to fetch just those.",
    ]
    return _write_checkbox_worklist(manifest, articles_dir, "snowball_candidates.md", heading, "proposed")
