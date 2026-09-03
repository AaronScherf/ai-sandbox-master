#!/usr/bin/env python3
"""
audit_metadata.py
Re-checks each converted journal article's folder, tags, title, and
authors against its real full text and fresh OpenAlex data -- the gap
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

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from common.gemini_utils import load_dotenv_override
from journal_discovery.discovery import resolve_work_by_doi
from journal_discovery.manifest import load_manifest, manifest_path, save_manifest
from journal_discovery.text_match import normalize
from journal_discovery.topic_routing import sanitize_topic_name
from journal_discovery.worklist import write_metadata_audit_flags_worklist
from indexer.index_card import compute_file_id, find_card_by_file_id, move_card

# Mirrors indexer/retag.py's own _FRONTMATTER_RE/_TAGS_LINE_RE exactly -- a
# deliberate small duplication rather than importing private names from
# retag.py, matching the pattern this module already follows for
# reconcile_needs_manual.py's own regex constants.
_FRONTMATTER_RE = re.compile(r"\A(---\n.*?\n---\n)", re.DOTALL)
_TAGS_LINE_RE = re.compile(r"(?m)^tags:.*$")


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


def _current_frontmatter_tags(content: str) -> list[str] | None:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None
    tags_match = _TAGS_LINE_RE.search(match.group(1))
    if not tags_match:
        return None
    bracket_match = re.search(r"\[(.*)\]", tags_match.group(0))
    if not bracket_match:
        return []
    inner = bracket_match.group(1).strip()
    if not inner:
        return []
    return [t.strip() for t in inner.split(",")]


def check_tag_sync(index_root, pdf_path: Path, md_path: Path) -> dict:
    file_id = compute_file_id(str(pdf_path))
    found = find_card_by_file_id(index_root, file_id)
    if found is None:
        return {"mismatch": False, "index_tags": None, "found_card": False}
    _, card = found
    index_tags = card.get("tags") or []

    content = md_path.read_text(encoding="utf-8")
    current_tags = _current_frontmatter_tags(content)
    if current_tags is None:
        return {"mismatch": False, "index_tags": index_tags, "found_card": True}

    return {"mismatch": sorted(current_tags) != sorted(index_tags), "index_tags": index_tags, "found_card": True}


def apply_tag_sync(md_path: Path, tags: list[str]) -> None:
    content = md_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return
    rendered = "[" + ", ".join(tags) + "]"
    new_frontmatter = _TAGS_LINE_RE.sub(f"tags: {rendered}", match.group(1), count=1)
    md_path.write_text(new_frontmatter + content[match.end():], encoding="utf-8")


def audit(articles_dir, index_root, mailto: str, recheck_all: bool = False) -> dict:
    manifest_file = manifest_path(articles_dir)
    manifest = load_manifest(manifest_file)
    targets = select_audit_targets(manifest, recheck_all)

    counts = {"audited": 0, "folder_corrections": 0, "tag_syncs": 0, "flagged": 0, "skipped": 0}

    for key, entry in targets:
        pdf_path, md_path = resolve_paper_paths(articles_dir, key, entry)
        label = entry.get("title") or key
        if pdf_path is None or md_path is None or not md_path.exists():
            print(f"  [skip] {label}: converted .md not found")
            counts["skipped"] += 1
            continue

        try:
            folder_result = check_folder(key, entry, mailto)
            if folder_result["error"]:
                print(f"  [warn] {label}: folder check skipped ({folder_result['error']})")
            elif folder_result["mismatch"]:
                old_folder = entry.get("folder")
                pdf_path, md_path = apply_folder_correction(
                    articles_dir, index_root, entry, pdf_path, md_path, folder_result["new_folder"],
                )
                print(f"  [folder] {label}: {old_folder} -> {folder_result['new_folder']}")
                counts["folder_corrections"] += 1
        except Exception as exc:
            # Broad on purpose: a failure anywhere in apply_folder_correction
            # (a file-move permission error, or move_card() failing after
            # files already moved) must never crash the whole run or leave
            # audited_at set on a half-migrated paper -- it just gets
            # retried on the next run, whatever the exact exception type.
            print(f"  [error] {label}: folder correction failed ({exc}); will retry next run")
            counts["skipped"] += 1
            continue

        tag_result = check_tag_sync(index_root, pdf_path, md_path)
        if not tag_result["found_card"]:
            print(f"  [warn] {label}: no index card found, tag-sync check skipped")
        elif tag_result["mismatch"]:
            apply_tag_sync(md_path, tag_result["index_tags"])
            print(f"  [tags] {label}: synced to {tag_result['index_tags']}")
            counts["tag_syncs"] += 1

        text = md_path.read_text(encoding="utf-8", errors="ignore")
        flags = [f for f in (check_title(entry, text), check_authors(entry, text)) if f]

        entry["audited_at"] = datetime.now(timezone.utc).isoformat()
        if flags:
            entry["audit_flags"] = flags
            counts["flagged"] += 1
            print(f"  [flag] {label}: {', '.join(f['type'] for f in flags)}")
        elif "audit_flags" in entry:
            del entry["audit_flags"]
        counts["audited"] += 1

    save_manifest(manifest_file, manifest)
    write_metadata_audit_flags_worklist(manifest, articles_dir)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_articles_dir = Path(__file__).resolve().parent.parent / "research" / "journal-articles"
    default_index_root = Path(__file__).resolve().parent.parent / "research"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    parser.add_argument("--index-root", default=str(default_index_root))
    parser.add_argument("--recheck-all", action="store_true")
    args = parser.parse_args()

    load_dotenv_override()
    mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not mailto:
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex).")
        return

    result = audit(args.articles_dir, args.index_root, mailto, recheck_all=args.recheck_all)
    print(f"\nAudited {result['audited']} paper(s): "
          f"{result['folder_corrections']} folder correction(s), "
          f"{result['tag_syncs']} tag sync(s), {result['flagged']} flagged, "
          f"{result['skipped']} skipped.")


if __name__ == "__main__":
    main()
