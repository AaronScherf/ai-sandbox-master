"""What the corpus can and cannot say about a question: counts, distributions, blind spots and a stale-db check."""
from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .. import tiers
from ..papers import eligible_papers
from .classify import GapResult
from .corpus import Corpus
from .match import Constraint

COMPLETENESS = ("Corpus completeness: not measured (needs OpenAlex, slice 2). The corpus was assembled by discovery, "
                "not sampled; absence here is not absence in the literature.")
THIN_BELOW = 3
BROAD_SCALES = ("multi_country", "global")


@dataclass
class Sidecar:
    eligible: int
    excluded: int
    without_record: int
    open_tier_c: int
    db_stale: bool
    db_path: str
    db_mtime: float
    db_papers: int
    scales: dict[str, str | None]


def read_sidecar(target, index_root, db_file) -> Sidecar:
    """Counts that live outside the db (eligible papers, exclusions, open tier C facts) and whether the db is stale."""
    db_file = Path(db_file)
    papers, _ = eligible_papers(str(index_root))
    have = set(target.records.all_ids())
    ids = target.records.ids()
    open_c = 0
    scales = {}
    for fid in ids:
        open_c += sum(1 for i in tiers.tiered_facts(target.records, fid, target.vocabs, target.proposals) if i["tier"] == "C")
        scales[fid] = (((target.records.read(fid, "a") or {}).get("core") or {}).get("geography") or {}).get("scale")
    db_mtime = db_file.stat().st_mtime if db_file.is_file() else 0.0
    watched = [p for p in Path(target.records.dir).glob("*.json") if not p.name.startswith("_")]
    watched += [target.records.dir / n for n in ("_excluded.json", "_proposals.json") if (target.records.dir / n).is_file()]
    conn = sqlite3.connect(db_file) if db_file.is_file() else None
    try:
        db_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0] if conn else 0
    finally:
        if conn:
            conn.close()
    return Sidecar(eligible=len(papers), excluded=len(target.records.excluded()),
                   without_record=len([p for p in papers if p.file_id not in have]), open_tier_c=open_c,
                   db_stale=any(p.stat().st_mtime > db_mtime for p in watched), db_path=str(db_file),
                   db_mtime=db_mtime, db_papers=db_papers, scales=scales)


def _tally(values) -> dict:
    return dict(Counter(values))


def coverage(corpus: Corpus, result: GapResult, constraints: list[Constraint], side: Sidecar) -> dict:
    shown = sorted(set(result.direct) | set(result.adjacent))
    facts = {fid: corpus.facts.get(fid, []) for fid in shown}
    years = [corpus.papers[fid].year for fid in shown if fid in corpus.papers and corpus.papers[fid].year]
    constrained = {c.facet for c in constraints}
    placed = set(result.direct)
    blind: dict = {}
    proposed = {}
    for facet in sorted(constrained - {"countries"}):
        ids = sorted(fid for fid, fs in corpus.facts.items()
                     if fid not in placed and any(f.facet == facet and f.shown.startswith("proposed:") for f in fs))
        if ids:
            proposed[facet] = ids
    if proposed:
        blind["proposed"] = proposed
    if "countries" in constrained:
        blind["no_country_fact"] = sorted(fid for fid in corpus.papers
                                          if not any(f.facet == "countries" for f in corpus.facts.get(fid, [])))
        blind["broad_scale"] = sorted(fid for fid in corpus.papers
                                      if fid not in placed and side.scales.get(fid) in BROAD_SCALES)
    return {
        "eligible": side.eligible, "excluded": side.excluded, "without_record": side.without_record,
        "open_tier_c": side.open_tier_c,
        "db": {"path": side.db_path, "mtime": side.db_mtime, "papers": side.db_papers, "stale": side.db_stale},
        "designs": _tally(f.label for fs in facts.values() for f in fs if f.facet == "study_design"),
        "countries": _tally(f.shown.upper() for fs in facts.values() for f in fs if f.facet == "countries"),
        "year_range": [min(years), max(years)] if years else None,
        "result_directions": _tally(r["direction"] for fid in shown for r in corpus.results.get(fid, []) if r["direction"]),
        "thin": len(result.direct) < THIN_BELOW,
        "completeness": COMPLETENESS,
        "blind_spots": blind,
    }
