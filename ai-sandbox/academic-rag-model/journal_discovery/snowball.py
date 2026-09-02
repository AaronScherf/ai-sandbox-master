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

from journal_discovery.discovery import iter_citing_works, resolve_work_by_doi
from journal_discovery.manifest import manifest_key, skip_already_seen


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
