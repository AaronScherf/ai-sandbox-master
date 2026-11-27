"""Three readings of the same papers (the owner's blind labels, the pipeline, the second reader) become one reference.

A field all three agree on is settled. Where they differ the owner rules on a page that shows the candidate values and
the quoted evidence without saying who gave which. A ruling is made with the other readings in view, so the result is
an adjudicated reference, not a blind one. Only report type and applicability are compared.
"""

import json
from pathlib import Path

from agent.literature.profile.classify import TYPE_RULES

FIELDS = ("report_type", "applicability")
SOURCES = ("owner", "pipeline", "reader")
_MERGED = {"grey_literature": "report"}
_TEMPLATE = Path(__file__).with_name("adjudicate.html")


def _value(reading: dict, field: str):
    value = reading.get(field)
    return _MERGED.get(value, value) if field == "report_type" else value


def _evidence(profile: dict, quoted: list[dict], vocabs: dict) -> list[dict]:
    """Both models' quotes in one list, ordered by kind and page so the order does not show the source."""
    rows = [(kind, t["term_id"], t["quote"], t.get("quote_locator"))
            for kind in ("intervention", "outcome") for t in profile.get(f"{kind}_tags") or []]
    rows += [(e["kind"], e["term_id"], e["quote"], e["page"]) for e in quoted]
    out = {}
    for kind, term_id, quote, page in rows:
        term = vocabs[kind].terms.get(term_id)
        out[(kind, term_id, quote)] = {"kind": kind, "term": term.label if term else term_id, "quote": quote,
                                       "page": page}
    return sorted(out.values(), key=lambda e: (e["kind"], str(e["page"]).zfill(5), e["term"], e["quote"]))


def compare(owner: dict, pipeline: dict, reader: dict, evidence: dict, papers: dict, vocabs: dict,
            decisions: dict) -> dict:
    """`decisions` maps file id to a report type the owner has already ruled on; it is not asked again."""
    readings, settled, items, missing = {}, {}, [], []
    for fid in sorted(owner):
        if fid not in pipeline or fid not in reader:
            missing.append(fid)
            continue
        sources = {"owner": owner[fid], "pipeline": pipeline[fid], "reader": reader[fid]}
        readings[fid] = {f: {s: _value(sources[s], f) for s in SOURCES} for f in FIELDS}
        settled[fid], asked = {}, {}
        for field in FIELDS:
            values = {v for v in readings[fid][field].values() if v}
            if field == "report_type" and fid in decisions:
                settled[fid][field] = decisions[fid]
            elif len(values) == 1:
                settled[fid][field] = values.pop()
            else:
                asked[field] = sorted(values)
        if asked:
            publishers = {sources[s].get("publisher") for s in ("pipeline", "reader")} - {None, ""}
            items.append({"file_id": fid, "title": papers[fid]["title"], "excerpt": papers[fid]["excerpt"],
                          "fields": asked, "publishers": sorted(publishers),
                          "evidence": _evidence(pipeline[fid], evidence.get(fid, []), vocabs)})
    return {"readings": readings, "settled": settled, "items": items, "missing": missing}


def page(items: list[dict], report_types) -> str:
    """The ruling page (publish with the `db` capability). Rulings go to the `rulings` collection by file id."""
    data = {"items": items, "report_types": sorted(report_types), "type_rules": TYPE_RULES}
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return _TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob)


def apply_rulings(comparison: dict, rulings: dict) -> tuple[dict, list[str]]:
    """(reference in the shape `eval --labels` reads, fields still without a ruling). A paper with an open field is
    left out of the reference."""
    reference, still_open = {}, []
    asked = {i["file_id"]: list(i["fields"]) for i in comparison["items"]}
    for fid, settled in comparison["settled"].items():
        values = {**settled, **{f: rulings.get(fid, {}).get(f) for f in asked.get(fid, [])}}
        unruled = [f for f in FIELDS if not values.get(f)]
        if unruled:
            still_open += [f"{fid}: {f}" for f in unruled]
        else:
            reference[fid] = {f: values[f] for f in FIELDS}
    return reference, still_open


def agreement(comparison: dict, reference: dict) -> dict:
    """How many reference papers each source matches, per field."""
    return {field: {"n": len(reference),
                    **{s: sum(comparison["readings"][fid][field][s] == reference[fid][field] for fid in reference)
                       for s in SOURCES}}
            for field in FIELDS}
