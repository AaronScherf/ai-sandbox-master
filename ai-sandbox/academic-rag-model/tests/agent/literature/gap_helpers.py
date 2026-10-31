"""Synthetic fixtures for the gap analysis tests: invented vocabularies, a toy subregion table and an in-memory db."""
import sqlite3
from pathlib import Path

from agent.literature import db
from agent.literature.gap.corpus import load_corpus
from agent.literature.vocab import Term, Vocabulary

# (id, parent, label, aliases)
INTERVENTION = [
    ("i.social", None, "Social protection programmes", ()),
    ("i.cash", "i.social", "Cash transfers", ("cash",)),
    ("i.cash_uncond", "i.cash", "Unconditional transfer", ()),
    ("i.cash_cond", "i.cash", "Conditional transfer", ()),
    ("i.voucher", "i.social", "Voucher", ()),
    ("i.grants", "i.voucher", "Cash grants", ()),
    ("i.food", "i.social", "Food aid", ()),
    ("i.root_only", "i.social", "Pension", ()),
    ("i.social.training", "i.social", "Training", ()),
    ("i.agri", None, "Agricultural programmes", ()),
    ("i.seeds", "i.agri", "Seed distribution", ()),
    ("i.agri.training", "i.agri", "Training", ()),
]
OUTCOME = [
    ("o.welfare", None, "Welfare outcomes", ()),
    ("o.food", "o.welfare", "Food security", ()),
    ("o.food_cons", "o.food", "Food consumption", ()),
    ("o.food_div", "o.food", "Dietary diversity", ()),
    ("o.food_div_hh", "o.food_div", "Household dietary diversity", ()),
    ("o.health", "o.welfare", "Health", ()),
    ("o.health_child", "o.health", "Child health", ()),
]
FLAT = {
    "sector": [("s.social", "Social protection"), ("s.agri", "Agriculture")],
    "study_design": [("d.panel", "Panel"), ("d.rct", "Randomised trial")],
    "population": [("p.households", "Households")],
    "data_source": [("ds.fsnau", "FSNAU")],
}


def _vocab(name, rows):
    return Vocabulary(name, 1, "provisional", "test fixture",
                      {tid: Term(id=tid, label=label, parent=parent, aliases=tuple(aliases))
                       for tid, parent, label, aliases in rows})


VOCABS = {"intervention": _vocab("intervention", INTERVENTION), "outcome": _vocab("outcome", OUTCOME)}
for _name, _rows in FLAT.items():
    VOCABS[_name] = _vocab(_name, [(tid, None, label, ()) for tid, label in _rows])

_FACET_VOCAB = {"intervention": "intervention", "outcome": "outcome", "study_design": "study_design",
                "sector": "sector", "population": "population", "data_sources": "data_source"}


def fx(facet, term_id, tier="A"):
    """A (facet, term_id, label, tier) fact row; the label comes from the synthetic vocabulary."""
    if facet == "countries":
        return (facet, term_id, term_id, tier)
    if term_id.startswith("proposed:"):
        return (facet, term_id, term_id.removeprefix("proposed:"), tier)
    return (facet, term_id, VOCABS[_FACET_VOCAB[facet]].terms[term_id].label, tier)


def make_conn(papers: dict) -> sqlite3.Connection:
    """papers: {file_id: {"title", "year", "facts": [fx(...)], "results": [(claim, direction)]}}"""
    conn = sqlite3.connect(":memory:")
    conn.executescript(db._TABLES)
    for fid, p in papers.items():
        conn.execute("INSERT INTO papers VALUES (?,?,?,?,?,?)", (fid, p.get("title", f"Study {fid}"), p.get("year", 2020),
                                                                  p.get("doi"), p.get("openalex_id"), "medium"))
        for n, (facet, term_id, label, tier) in enumerate(p.get("facts", []), 1):
            conn.execute("INSERT INTO facts VALUES (?,?,?,?,?,?,?)", (fid, facet, term_id, label, tier, f"quote {fid}-{n}", "1"))
        for n, (claim, direction) in enumerate(p.get("results", []), 1):
            conn.execute("INSERT INTO results VALUES (?,?,?,?,?,?,?)", (fid, f"R{n}", claim, direction, None, f"quote {fid}-r{n}", "1"))
    conn.commit()
    return conn


def make_corpus(papers: dict):
    conn = make_conn(papers)
    try:
        return load_corpus(conn)
    finally:
        conn.close()


def write_toy_tables(directory) -> tuple[Path, Path]:
    """A four-country countries.yaml (code, name) and subregion table in `directory`; returns (subregions, countries)."""
    d = Path(directory)
    countries = d / "toy_countries.yaml"
    countries.write_text("countries:\n- code: SO\n  name: Somalia\n- code: KE\n  name: Kenya\n"
                         "- code: NG\n  name: Nigeria\n- code: GH\n  name: Ghana\n", encoding="utf-8")
    subregions = d / "toy_subregions.yaml"
    subregions.write_text("countries:\n- code: SO\n  subregion: Eastern Africa\n- code: KE\n  subregion: Eastern Africa\n"
                          "- code: NG\n  subregion: Western Africa\n- code: GH\n  subregion: Western Africa\n", encoding="utf-8")
    return subregions, countries
