"""Stage 4: a SQLite database derived from the study records, tiers, annotations and clusters.

Nothing here is a source of truth: `build` recreates the file from scratch, so a changed record, tier or annotation is
picked up by building again. No LLM. The file holds quotes from papers, so it lives in a gitignored folder."""
from __future__ import annotations

import itertools
import json
import sqlite3
from pathlib import Path

from . import schema
from .cluster import FACETS, ClusterError, _matcher, load_cluster, topic_dir
from .contribute import load_annotations
from .tiers import at_least, tiered_facts

_TABLES = """
CREATE TABLE papers (file_id TEXT PRIMARY KEY, title TEXT, year INTEGER, doi TEXT, openalex_id TEXT, confidence TEXT);
CREATE TABLE facts (file_id TEXT, facet TEXT, term_id TEXT, label TEXT, tier TEXT, quote TEXT, locator TEXT);
CREATE TABLE results (file_id TEXT, rid TEXT, claim TEXT, direction TEXT, magnitude TEXT, quote TEXT, locator TEXT);
CREATE TABLE annotations (file_id TEXT, topic TEXT, contribution TEXT, limitation TEXT);
CREATE TABLE cluster_members (topic TEXT, file_id TEXT);
CREATE INDEX facts_by_facet ON facts (facet, label);
"""


def db_path(index_root) -> Path:
    return Path(index_root) / "literature_db" / "literature.sqlite"


def _json(value):
    return value if isinstance(value, (str, type(None))) else json.dumps(value)


def _topics(index_root) -> list[str]:
    root = Path(index_root) / "literature_reviews"
    return sorted(p.parent.name for p in root.glob("*/cluster.yaml")) if root.is_dir() else []


def build(target, path, floor: str = "B") -> dict:
    """Recreate the database at `path` from the records under `target`; returns the row count of each table."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_TABLES)
        for fid in sorted(target.records.ids()):
            record = target.records.read(fid, "a")
            if record is None:
                continue
            ident = record["identity"]
            year = ident.get("publication_year")
            conn.execute("INSERT INTO papers VALUES (?,?,?,?,?,?)", (
                fid, ident.get("title"), int(year) if str(year).isdigit() else None, ident.get("doi"),
                ident.get("openalex_id"), (record.get("appraisal") or {}).get("confidence")))
            for item in at_least(tiered_facts(target.records, fid, target.vocabs, target.proposals), floor):
                conn.execute("INSERT INTO facts VALUES (?,?,?,?,?,?,?)", (
                    fid, item["facet"], item["shown"], item["label"], item["tier"], item["quote"], _json(item["locator"])))
            for n, r in enumerate(record["core"].get("results") or [], 1):
                conn.execute("INSERT INTO results VALUES (?,?,?,?,?,?,?)", (
                    fid, f"R{n}", r.get("claim"), r.get("effect_direction"), r.get("magnitude"), r.get("quote"),
                    _json(r.get("locator"))))
        for topic in _topics(target.index_root):
            for fid in load_cluster(target.index_root, topic).file_ids:
                conn.execute("INSERT INTO cluster_members VALUES (?,?)", (topic, fid))
            for fid, note in load_annotations(target.index_root, topic).items():
                conn.execute("INSERT INTO annotations VALUES (?,?,?,?)", (
                    fid, topic, note["contribution"]["text"], note["limitations"]["text"]))
        conn.commit()
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("papers", "facts", "results", "annotations", "cluster_members")}
    finally:
        conn.close()


def matrix(conn) -> list[dict]:
    """Papers per intervention x outcome x study design (a paper with several of a facet counts under each)."""
    rows = conn.execute(
        "SELECT i.label, o.label, d.label, COUNT(DISTINCT i.file_id) FROM facts i "
        "JOIN facts o ON o.file_id = i.file_id AND o.facet = 'outcome' "
        "JOIN facts d ON d.file_id = i.file_id AND d.facet = 'study_design' "
        "WHERE i.facet = 'intervention' GROUP BY i.label, o.label, d.label ORDER BY 1, 2, 3").fetchall()
    return [dict(zip(("intervention", "outcome", "study_design", "papers"), r)) for r in rows]


def distribution(conn, facet: str) -> list[tuple]:
    """(label, papers) for one facet, most common first."""
    if facet not in FACETS:
        raise ValueError(f"{facet!r}: choose from {', '.join(FACETS)}")
    return conn.execute("SELECT label, COUNT(DISTINCT file_id) AS n FROM facts WHERE facet = ? "
                        "GROUP BY label ORDER BY n DESC, label", (facet,)).fetchall()


def cooccurrence(conn) -> list[tuple]:
    """(source, source, papers) for every pair of data sources used in the same paper."""
    by_paper: dict[str, set] = {}
    for fid, label in conn.execute("SELECT file_id, label FROM facts WHERE facet = 'data_sources'"):
        by_paper.setdefault(fid, set()).add(label)
    counts: dict[tuple, int] = {}
    for labels in by_paper.values():
        for pair in itertools.combinations(sorted(labels), 2):
            counts[pair] = counts.get(pair, 0) + 1
    return [(a, b, n) for (a, b), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def query(conn, vocabs: dict, where: list[str]) -> list[dict]:
    """Papers with a stored fact matching every `facet=value`, using the same matching rules as `cluster define`."""
    from .cluster import parse_constraint

    matchers = [_matcher(parse_constraint(w), vocabs) for w in where]
    facts: dict[str, list] = {}
    for fid, facet, shown, label in conn.execute("SELECT file_id, facet, term_id, label FROM facts"):
        facts.setdefault(fid, []).append({"facet": facet, "shown": shown, "label": label})
    hits = [fid for fid in sorted(facts) if all(any(m(i) for i in facts[fid]) for m in matchers)]
    out = []
    for fid in hits:
        title, year = conn.execute("SELECT title, year FROM papers WHERE file_id = ?", (fid,)).fetchone()
        out.append({"file_id": fid, "title": title, "year": year})
    return out


def export_markdown(conn, path) -> Path:
    path = Path(path)
    lines = ["# Evidence matrix", "", "| Intervention | Outcome | Study design | Papers |", "| --- | --- | --- | --- |"]
    lines += [f"| {r['intervention']} | {r['outcome']} | {r['study_design']} | {r['papers']} |" for r in matrix(conn)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path
