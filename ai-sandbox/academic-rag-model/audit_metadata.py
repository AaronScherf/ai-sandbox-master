#!/usr/bin/env python3
"""
audit_metadata.py
Re-checks each converted journal article's folder, tags, title, authors,
and DOI against its real full text and fresh OpenAlex data -- the gap
flagged in docs/2026-09-01-journal-discovery-status.md point 6:
.meta.json sidecars are written once at discovery time and never
revisited, and reconcile_needs_manual.py's folder/content preview was
read-only. Design: docs/superpowers/specs/2026-09-02-metadata-folder-audit-design.md.

Two ways to run this: automatically, chained onto the end of
reconcile_needs_manual.py's own run (the normal way this runs day to
day); or standalone for a forced full re-audit:
    python -m audit_metadata --recheck-all
"""
from __future__ import annotations

from pathlib import Path

from journal_discovery.discovery import resolve_work_by_doi
from journal_discovery.text_match import normalize
from journal_discovery.topic_routing import sanitize_topic_name
from indexer.index_card import compute_file_id, move_card


def select_audit_targets(manifest: dict, recheck_all: bool) -> list[tuple[str, dict]]:
    targets = []
    for key, entry in manifest.items():
        if entry.get("status") not in ("fetched", "downloaded"):
            continue
        if not recheck_all and entry.get("audited_at"):
            continue
        targets.append((key, entry))
    return targets


def resolve_paper_paths(articles_dir, key: str, entry: dict) -> tuple[Path | None, Path | None]:
    """Returns (pdf_path, md_path) for a paper already known to be
    fetched/downloaded. A fetched entry's paths are deterministic from
    its manifest key (mirrors topic_routing.pdf_filename()'s own
    derivation, since the manifest key is already
    `work.doi or work.openalex_id`, the same precedence pdf_filename()
    uses). A downloaded (manually-placed) entry's PDF filename is
    arbitrary, so its path is derived from matched_md_path, which
    reconcile_needs_manual.py's content-matching already recorded --
    process_pdf() names a manually-downloaded file's .md after that
    PDF's own (arbitrary) stem, so the relationship is recoverable."""
    if entry.get("status") == "downloaded":
        matched = entry.get("matched_md_path")
        if not matched:
            return None, None
        md_path = Path(matched)
        pdf_path = md_path.parent.parent / f"{md_path.stem}.pdf"
        return pdf_path, md_path

    folder = entry.get("folder")
    if not folder:
        return None, None
    stem = sanitize_topic_name(key)[:80] or "paper"
    pdf_path = Path(articles_dir) / folder / f"{stem}.pdf"
    md_path = Path(articles_dir) / folder / "processed_outputs" / f"{stem}.md"
    return pdf_path, md_path


def check_title(entry: dict, text: str) -> dict | None:
    title = entry.get("title")
    if not title:
        return None
    if normalize(title) in normalize(text):
        return None
    excerpt = " ".join(text.split())[:200]
    return {"type": "title_mismatch",
            "detail": f'stored title "{title}" not found in text (excerpt: "{excerpt}")'}


def check_authors(entry: dict, text: str) -> dict | None:
    authors = entry.get("authors") or []
    if not authors:
        return None
    normalized_text = normalize(text)
    for author in authors:
        surname = author.strip().split()[-1] if author.strip() else ""
        if surname and normalize(surname) in normalized_text:
            return None
    return {"type": "author_mismatch", "detail": f"none of {authors} found in text"}


def check_doi(key: str, entry: dict, text: str) -> dict | None:
    if key.startswith("http"):
        return None
    if key.lower() in text.lower():
        return None
    return {"type": "doi_mismatch", "detail": f"stored DOI ({key}) not found in text"}


def check_folder(key: str, entry: dict, mailto: str) -> dict:
    if key.startswith("http"):
        return {"mismatch": False, "new_folder": None, "error": "non-DOI key, folder check skipped"}
    work = resolve_work_by_doi(key, mailto)
    if work is None:
        return {"mismatch": False, "new_folder": None, "error": "resolve_work_by_doi failed"}
    top_concept = work.concepts[0] if work.concepts else None
    new_folder = sanitize_topic_name(top_concept)
    current_folder = entry.get("folder")
    return {"mismatch": new_folder != current_folder, "new_folder": new_folder, "error": None}


def apply_folder_correction(
    articles_dir, index_root, entry: dict, pdf_path: Path, md_path: Path, new_folder: str,
) -> tuple[Path, Path]:
    """Moves every file belonging to this paper into its corrected
    folder and relocates its index card to match. Lets any filesystem
    or index-update exception propagate -- audit()'s caller (Task 8) is
    responsible for catching it and leaving audited_at unset so the
    paper is retried on the next run, rather than silently left
    half-migrated."""
    dest_folder = Path(articles_dir) / new_folder
    dest_folder.mkdir(parents=True, exist_ok=True)

    file_id = compute_file_id(str(pdf_path))

    new_pdf_path = dest_folder / pdf_path.name
    pdf_path.rename(new_pdf_path)

    meta_path = pdf_path.with_suffix(".meta.json")
    if meta_path.exists():
        meta_path.rename(dest_folder / meta_path.name)

    new_processed_dir = dest_folder / "processed_outputs"
    new_processed_dir.mkdir(exist_ok=True)
    new_md_path = new_processed_dir / md_path.name
    md_path.rename(new_md_path)

    cache_path = md_path.parent / f"{md_path.stem}_pages_cache.json"
    if cache_path.exists():
        cache_path.rename(new_processed_dir / cache_path.name)

    move_card(index_root, file_id, new_folder)
    entry["folder"] = new_folder
    return new_pdf_path, new_md_path


if __name__ == "__main__":
    pass
