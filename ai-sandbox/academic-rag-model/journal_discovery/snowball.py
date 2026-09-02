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

from journal_discovery.discovery import doi_url, iter_citing_works, resolve_work_by_doi
from journal_discovery.manifest import (
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
    skip_already_seen,
)
from journal_discovery.relevance import load_relevance_model, select_relevant_works
from journal_discovery.topic_routing import route_to_folder
from journal_discovery.worklist import write_snowball_candidates_worklist

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
