"""
snowball.py
Citation-based snowball sampling per spec 2026-09-02: a third discovery
route seeded from papers already in the corpus, using OpenAlex's own
forward-citation graph ("papers that cite this one") -- no bibliography
text-parsing needed. Deliberately never auto-fetched: propose() records
candidates as a checkbox worklist for human review; confirm() fetches
only what's checked. Reuses the existing relevance/access/manifest/
worklist machinery unchanged.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from common.gemini_utils import load_dotenv_override
from journal_discovery.access import resolve_full_text
from journal_discovery.discovery import doi_url, iter_citing_works, resolve_work_by_doi
from journal_discovery.manifest import (
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
    skip_already_seen,
)
from journal_discovery.metadata_sidecar import write_sidecar
from journal_discovery.relevance import load_relevance_model, select_relevant_works
from journal_discovery.topic_routing import pdf_filename, route_to_folder
from journal_discovery.worklist import (
    _read_checked_links,
    write_needs_manual_worklist,
    write_snowball_candidates_worklist,
)

_DEFAULT_BATCH_SIZE = 25
_DEFAULT_MAX_RESULTS = 50
_DEFAULT_MAX_EXAMINED = 200
_DEFAULT_RELEVANCE_THRESHOLD = 0.5
_DEFAULT_PACE_PER_HOUR = 25.0


def iter_seed_openalex_ids(manifest: dict, mailto: str, seed_dois: list[str] | None = None):
    """Yields (seed_key, openalex_id) pairs. seed_key is what a
    downstream proposed candidate records as its cites_seed metadata
    (the seed's own DOI when known, else its OpenAlex id); openalex_id
    is what iter_citing_works() actually queries against."""
    if seed_dois:
        for doi in seed_dois:
            work = resolve_work_by_doi(doi, mailto)
            if work is None:
                print(f"WARNING: could not resolve seed DOI {doi!r}; skipping.")
                continue
            yield doi, work.openalex_id
        return

    for key, entry in manifest.items():
        if entry.get("status") not in ("fetched", "downloaded"):
            continue
        if key.startswith("http"):
            yield key, key
            continue
        work = resolve_work_by_doi(key, mailto)
        if work is None:
            print(f"WARNING: could not resolve seed {key!r} to an OpenAlex id; skipping.")
            continue
        yield key, work.openalex_id


def iter_snowball_candidates(
    manifest: dict, mailto: str, batch_size: int, counts: dict, seed_map: dict,
    seed_dois: list[str] | None = None,
):
    for seed_key, openalex_id in iter_seed_openalex_ids(manifest, mailto, seed_dois):
        citing = iter_citing_works(openalex_id, mailto, batch_size)
        for work in skip_already_seen(citing, manifest, counts):
            seed_map.setdefault(manifest_key(work), seed_key)
            yield work


def propose(args) -> dict:
    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    counts = {"examined": 0, "already_seen": 0, "proposed": 0}
    seed_map: dict[str, str] = {}

    model = load_relevance_model()
    candidates = iter_snowball_candidates(
        manifest, args.mailto, args.batch_size, counts, seed_map, args.seed_doi or None,
    )
    scored = select_relevant_works(
        candidates, model, args.relevance_prompt, args.relevance_threshold,
        args.max_results, args.max_examined,
    )
    counts["examined"] = len(scored)

    for scored_work in scored:
        work = scored_work.work
        key = manifest_key(work)
        folder = route_to_folder(args.articles_dir, work)
        record_outcome(manifest, key, "proposed", folder=folder.name, metadata={
            "title": work.title,
            "authors": work.authors,
            "year": work.year,
            "doi_url": doi_url(work),
            "relevance_score": scored_work.score,
            "cites_seed": seed_map.get(key),
        })
        counts["proposed"] += 1

    save_manifest(manifest_file, manifest)
    write_snowball_candidates_worklist(manifest, args.articles_dir)
    return counts


def confirm(args) -> dict:
    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    checked_links = _read_checked_links(Path(args.articles_dir) / "snowball_candidates.md")

    counts = {"confirmed": 0, "fetched": 0, "needs_manual": 0}
    for key, entry in list(manifest.items()):
        if entry.get("status") != "proposed":
            continue
        link = entry.get("doi_url") or (key if key.startswith("http") else f"https://doi.org/{key}")
        if link not in checked_links:
            continue
        counts["confirmed"] += 1

        work = resolve_work_by_doi(key, args.mailto) if not key.startswith("http") else None
        if work is None:
            print(f"WARNING: could not re-resolve {key!r}; leaving as proposed.")
            counts["confirmed"] -= 1
            continue

        result = resolve_full_text(work, args.mailto, args.ezproxy_cookie, args.pace_per_hour)
        # Reuse the folder/title/authors/year already recorded at propose
        # time rather than re-deriving from `work` here -- confirmed real
        # 2026-09-02 that re-resolving by DOI can hand back a work with
        # different (or empty) concepts than what propose() saw, silently
        # rerouting the PDF and rewriting metadata the user already
        # reviewed in the worklist.
        folder_name = entry.get("folder") or route_to_folder(args.articles_dir, work).name
        folder = Path(args.articles_dir) / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        if result.status == "fetched":
            pdf_path = folder / pdf_filename(work)
            pdf_path.write_bytes(result.content)
            write_sidecar(pdf_path, work, entry.get("relevance_score"), result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            counts["fetched"] += 1
        else:
            record_outcome(manifest, key, "needs_manual", folder=folder.name, metadata={
                "title": entry.get("title", work.title),
                "authors": entry.get("authors", work.authors),
                "year": entry.get("year", work.year),
                "doi_url": entry.get("doi_url") or doi_url(work),
            })
            counts["needs_manual"] += 1

    save_manifest(manifest_file, manifest)
    write_snowball_candidates_worklist(manifest, args.articles_dir)
    write_needs_manual_worklist(manifest, args.articles_dir)
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Citation-based snowball sampling: propose candidates from the corpus's own "
                     "citation network, then confirm which to fetch.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    default_articles_dir = Path(__file__).resolve().parent.parent.parent / "research" / "journal-articles"

    propose_parser = subparsers.add_parser(
        "propose", help="Find and score citing-paper candidates, write a checkbox worklist.",
    )
    propose_parser.add_argument(
        "--relevance-prompt", required=True,
        help="Free-text description of what you're actually looking for -- scored against each "
             "candidate's abstract, same as discover.py's own flag.",
    )
    propose_parser.add_argument("--relevance-threshold", type=float, default=_DEFAULT_RELEVANCE_THRESHOLD)
    propose_parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    propose_parser.add_argument("--max-results", type=int, default=_DEFAULT_MAX_RESULTS)
    propose_parser.add_argument("--max-examined", type=int, default=_DEFAULT_MAX_EXAMINED)
    propose_parser.add_argument(
        "--seed-doi", action="append", default=[],
        help="Scope seeding to these DOIs instead of every fetched/downloaded paper in the corpus (repeatable).",
    )
    propose_parser.add_argument("--articles-dir", default=str(default_articles_dir))

    confirm_parser = subparsers.add_parser(
        "confirm", help="Fetch full text for whatever's checked in snowball_candidates.md.",
    )
    confirm_parser.add_argument(
        "--pace-per-hour", type=float, default=_DEFAULT_PACE_PER_HOUR,
        help="EZProxy-tier pacing, same meaning as discover.py's own flag.",
    )
    confirm_parser.add_argument("--articles-dir", default=str(default_articles_dir))

    args = parser.parse_args()

    load_dotenv_override()
    args.mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not args.mailto:
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex).")
        sys.exit(1)
    args.ezproxy_cookie = os.environ.get("EZPROXY_SESSION_COOKIE")

    if args.command == "propose":
        counts = propose(args)
        print(f"\nExamined: {counts['examined']}")
        print(f"Already seen (skipped): {counts['already_seen']}")
        print(f"Proposed: {counts['proposed']}")
        if counts["proposed"]:
            print(f"Review: {Path(args.articles_dir) / 'snowball_candidates.md'}")
    else:
        counts = confirm(args)
        print(f"\nConfirmed: {counts['confirmed']}")
        print(f"Fetched: {counts['fetched']}")
        print(f"Needs manual download: {counts['needs_manual']}")


if __name__ == "__main__":
    main()
