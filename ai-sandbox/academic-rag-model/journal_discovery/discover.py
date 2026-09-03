"""
discover.py
CLI entry point per spec S2/S4: python -m journal_discovery.discover.
Wires discovery -> relevance scoring -> dedup -> access -> topic routing
-> sidecar -> manifest -> optional Zotero sync, in that order. Never
imports indexer/ and never invokes convert_journal_articles.py -- a PDF
(+ sidecar) on disk is this subproject's entire contract with the rest
of the pipeline.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from common.gemini_utils import load_dotenv_override
from journal_discovery.access import resolve_full_text
from journal_discovery.discovery import doi_url, resolve_works
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
from journal_discovery.worklist import write_needs_manual_worklist
from journal_discovery.zotero_sync import sync_to_zotero

_DEFAULT_BATCH_SIZE = 25
_DEFAULT_MAX_RESULTS = 100
_DEFAULT_MAX_EXAMINED = 300
_DEFAULT_RELEVANCE_THRESHOLD = 0.5
_DEFAULT_PACE_PER_HOUR = 25.0


def _sync_zotero_if_configured(work, pdf_path, topic_folder: str, args) -> None:
    library_id = getattr(args, "zotero_library_id", None) or os.environ.get("ZOTERO_LIBRARY_ID")
    api_key = getattr(args, "zotero_api_key", None) or os.environ.get("ZOTERO_API_KEY")
    if not library_id or not api_key:
        print("WARNING: --zotero passed but ZOTERO_LIBRARY_ID/ZOTERO_API_KEY not set; skipping sync.")
        return
    try:
        sync_to_zotero(work, pdf_path, topic_folder, library_id, api_key)
    except Exception as err:
        print(f"WARNING: Zotero sync failed for {pdf_path.name}: {err}")


def run(args: argparse.Namespace) -> dict:
    mailto = getattr(args, "mailto", None) or os.environ.get("OPENALEX_CONTACT_EMAIL")
    ezproxy_cookie = getattr(args, "ezproxy_cookie", None) or os.environ.get("EZPROXY_SESSION_COOKIE")
    core_api_key = getattr(args, "core_api_key", None) or os.environ.get("CORE_API_KEY")

    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    counts = {"examined": 0, "already_seen": 0, "fetched": 0, "needs_manual": 0}

    model = load_relevance_model()
    works = resolve_works(args.faculty, args.topic, mailto, args.batch_size)
    unseen_works = skip_already_seen(works, manifest, counts)
    scored = select_relevant_works(
        unseen_works, model, args.relevance_prompt, args.relevance_threshold,
        args.max_results, args.max_examined,
    )
    counts["examined"] = len(scored)

    for scored_work in scored:
        work = scored_work.work
        key = manifest_key(work)

        result = resolve_full_text(work, mailto, ezproxy_cookie, args.pace_per_hour, core_api_key)
        if result.status == "fetched":
            folder = route_to_folder(args.articles_dir, work)
            pdf_path = folder / pdf_filename(work)
            pdf_path.write_bytes(result.content)
            write_sidecar(pdf_path, work, scored_work.score, result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            counts["fetched"] += 1
            if args.zotero:
                _sync_zotero_if_configured(work, pdf_path, folder.name, args)
        else:
            folder = route_to_folder(args.articles_dir, work)
            record_outcome(manifest, key, "needs_manual", folder=folder.name, metadata={
                "title": work.title,
                "authors": work.authors,
                "year": work.year,
                "doi_url": doi_url(work),
            })
            counts["needs_manual"] += 1

    save_manifest(manifest_file, manifest)
    write_needs_manual_worklist(manifest, args.articles_dir)
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Resolve a faculty name or topic query into full-text PDFs under research/journal-articles/."
    )
    parser.add_argument("--faculty", action="append", default=[], help="Faculty name to query (repeatable).")
    parser.add_argument("--topic", action="append", default=[], help="Topic/keyword query (repeatable).")
    parser.add_argument(
        "--relevance-prompt", required=True,
        help="Free-text description of what you're actually looking for -- scored against each "
             "candidate's abstract, not just matched by author/topic name.",
    )
    parser.add_argument("--relevance-threshold", type=float, default=_DEFAULT_RELEVANCE_THRESHOLD)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-results", type=int, default=_DEFAULT_MAX_RESULTS)
    parser.add_argument("--max-examined", type=int, default=_DEFAULT_MAX_EXAMINED)
    parser.add_argument("--pace-per-hour", type=float, default=_DEFAULT_PACE_PER_HOUR,
                         help="EZProxy download attempts per hour, jittered +/-30%% -- protects your own "
                              "Columbia account from automated-abuse detection. Does not affect OA/arXiv "
                              "downloads, which carry none of that risk and are never paced.")
    parser.add_argument("--zotero", action="store_true", help="Also sync fetched papers into Zotero.")
    default_articles_dir = Path(__file__).resolve().parent.parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    args = parser.parse_args()

    if not args.faculty and not args.topic:
        parser.error("at least one --faculty or --topic is required")

    load_dotenv_override()
    if not os.environ.get("OPENALEX_CONTACT_EMAIL"):
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex/Unpaywall).")
        sys.exit(1)

    counts = run(args)

    print(f"\nExamined and scored: {counts['examined']}")
    print(f"Already seen (skipped): {counts['already_seen']}")
    print(f"Fetched: {counts['fetched']}")
    print(f"Needs manual download: {counts['needs_manual']}")
    if counts["needs_manual"] or counts["already_seen"]:
        print(f"Manual-download worklist: {Path(args.articles_dir) / 'needs_manual_downloads.md'}")


if __name__ == "__main__":
    main()
