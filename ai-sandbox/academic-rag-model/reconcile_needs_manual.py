#!/usr/bin/env python3
"""
reconcile_needs_manual.py
Cross-cutting reconciliation between journal_discovery's dedup manifest
and journal_articles' converted output. Neither subproject calls the
other directly (journal_discovery never invokes conversion; conversion
knows nothing about the discovery manifest) -- this script is the
explicit, human-run bridge between them, per user request 2026-09-02:
confirm which needs_manual papers actually got downloaded and converted
by searching their *real content* (a manually-downloaded PDF's filename
almost never matches anything this pipeline would have generated, so
filename matching isn't viable), mark those resolved, and regenerate
the worklist so it's a living reflection of current status. Also prints
a folder/content review so folder-appropriateness can be checked
against what a paper actually says, not just its OpenAlex concept tags.

Run after convert_journal_articles.py, from the academic-rag-model root:
    python -m reconcile_needs_manual
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from journal_discovery.manifest import load_manifest, manifest_path, save_manifest
from journal_discovery.text_match import normalize
from journal_discovery.worklist import write_needs_manual_worklist

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def find_converted_md_files(articles_dir) -> list[Path]:
    """processed_outputs/*.md only -- excludes the *_pages_cache.json
    sidecars process_pdf() writes alongside them."""
    return sorted(Path(articles_dir).glob("**/processed_outputs/*.md"))


def is_confirmed_downloaded(doi: str | None, title: str, md_files: list[Path]) -> Path | None:
    """Returns the matching .md path if this paper's real content is
    found among the converted files -- a DOI substring match first
    (unambiguous when present), a normalized-title substring match as
    fallback for papers that don't print their DOI in the visible text.
    None means still needs a manual download."""
    normalized_title = normalize(title) if title else None
    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        if doi and doi.lower() in content.lower():
            return md_path
        if normalized_title and normalized_title in normalize(content):
            return md_path
    return None


def extract_preview(md_path: Path, max_chars: int = 200) -> str:
    """Strips frontmatter and HTML comments (page markers, image
    placeholders) so a human reviewing folder-appropriateness sees real
    paper content, not pipeline bookkeeping."""
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    text = _FRONTMATTER_RE.sub("", text, count=1)
    text = _HTML_COMMENT_RE.sub("", text)
    text = "\n".join(line for line in text.splitlines() if line.strip())
    return text.strip()[:max_chars]


def reconcile(articles_dir) -> dict:
    manifest_file = manifest_path(articles_dir)
    manifest = load_manifest(manifest_file)
    md_files = find_converted_md_files(articles_dir)

    confirmed = []
    still_pending = []
    for key, entry in manifest.items():
        if entry.get("status") != "needs_manual" or entry.get("work_type") == "dataset":
            continue
        doi = None if key.startswith("http") else key
        match = is_confirmed_downloaded(doi, entry.get("title", ""), md_files)
        if match:
            entry["status"] = "downloaded"
            entry["matched_md_path"] = str(match)
            confirmed.append((key, entry.get("title"), str(match)))
        else:
            still_pending.append((key, entry.get("title")))

    save_manifest(manifest_file, manifest)
    write_needs_manual_worklist(manifest, articles_dir)
    return {"confirmed": confirmed, "still_pending": still_pending, "md_files_scanned": len(md_files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_articles_dir = Path(__file__).resolve().parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    args = parser.parse_args()

    result = reconcile(args.articles_dir)

    print(f"Scanned {result['md_files_scanned']} converted .md file(s).\n")
    print(f"Confirmed downloaded ({len(result['confirmed'])}):")
    for key, title, md_path in result["confirmed"]:
        print(f"  - {title or key} -> {md_path}")
    print(f"\nStill needs manual download ({len(result['still_pending'])}):")
    for key, title in result["still_pending"]:
        print(f"  - {title or key}")

    print("\nFolder/content review (check these match what the paper is actually about):")
    for md_path in find_converted_md_files(args.articles_dir):
        folder = md_path.parent.parent.name
        preview = extract_preview(md_path, max_chars=150).replace("\n", " ")
        print(f"  [{folder}] {md_path.stem}: {preview}")


if __name__ == "__main__":
    main()
