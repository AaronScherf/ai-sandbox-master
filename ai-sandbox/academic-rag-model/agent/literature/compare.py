"""Compare two independent extraction passes over one paper and flag where they disagree."""
from __future__ import annotations

from collections import Counter

from . import schema
from .store import RecordStore
from .transcript import normalize


def _key(fact: dict, vocab=None) -> str:
    """A vocabulary term, or a proposed value. Ids that share one label (the same wording filed under two branches)
    are one fact when the vocabulary is known."""
    vid = fact.get("vocab_id")
    if not vid:
        return "proposed:" + normalize(fact.get("value", ""))
    term = vocab.terms.get(vid) if vocab is not None else None
    return "term:" + normalize(term.label) if term is not None else vid


def _shown(fact: dict) -> str:
    return fact["vocab_id"] if fact.get("vocab_id") else "proposed:" + normalize(fact.get("value", ""))


def _facts(facts, vocab=None) -> dict[str, str]:
    return {_key(f, vocab): _shown(f) for f in (facts or [])}


# Rules that close cosmetic differences between passes. Anything they do not close stays flagged for a person.
IGNORED = {"population.general_population"}  # says nothing a paper-wide default would not


def _ancestors(vid: str, vocab) -> set[str]:
    out: set[str] = set()
    while vocab is not None and vid in vocab.terms and vocab.terms[vid].parent and vocab.terms[vid].parent not in out:
        vid = vocab.terms[vid].parent
        out.add(vid)
    return out


def _words(shown: str) -> set[str]:
    return {w.rstrip("s") for w in normalize(shown.removeprefix("proposed:")).split()}


def _close(x: str, y: str, vocab) -> bool:
    """One fact is the other's ancestor in the vocabulary, or one proposed value's words contain the other's."""
    if x.startswith("proposed:") and y.startswith("proposed:"):
        wx, wy = _words(x), _words(y)
        return bool(wx and wy) and (wx <= wy or wy <= wx)
    if x.startswith("proposed:") or y.startswith("proposed:"):
        return False
    return y in _ancestors(x, vocab) or x in _ancestors(y, vocab)


def _apply_rules(fa: dict, fb: dict, vocab) -> tuple[dict, dict]:
    fa = {k: v for k, v in fa.items() if v not in IGNORED}
    fb = {k: v for k, v in fb.items() if v not in IGNORED}
    ua = {k: v for k, v in fa.items() if k not in fb}
    ub = {k: v for k, v in fb.items() if k not in fa}
    for ka, va in list(ua.items()):
        for kb, vb in list(ub.items()):
            if _close(va, vb, vocab):
                fa.pop(ka, None)
                fb.pop(kb, None)
                ua.pop(ka)
                ub.pop(kb)
                break
    return fa, fb


def _only(label: str, fa: dict, fb: dict) -> str:
    return (f"{label}: only in pass a {sorted(v for k, v in fa.items() if k not in fb)}; "
            f"only in pass b {sorted(v for k, v in fb.items() if k not in fa)}")


def diff_records(a: dict, b: dict, vocabs: dict | None = None) -> list[str]:
    vocabs = vocabs or {}
    out: list[str] = []
    for facet in schema.FACETS:
        voc = vocabs.get(schema.FACETS[facet])
        fa, fb = _apply_rules(_facts(a["core"].get(facet), voc), _facts(b["core"].get(facet), voc), voc)
        if fa.keys() != fb.keys():
            out.append(_only(f"core.{facet}", fa, fb))
    ga, gb = a["core"].get("geography", {}), b["core"].get("geography", {})
    ca, cb = set(ga.get("countries", [])), set(gb.get("countries", []))
    if ca != cb:
        out.append(f"core.geography.countries: only in pass a {sorted(ca - cb)}; only in pass b {sorted(cb - ca)}")
    if ga.get("scale") != gb.get("scale"):
        out.append(f"core.geography.scale: pass a {ga.get('scale')!r}; pass b {gb.get('scale')!r}")
    ra, rb = a["core"].get("results", []), b["core"].get("results", [])
    da, db = Counter(r.get("effect_direction") for r in ra), Counter(r.get("effect_direction") for r in rb)
    if len(ra) != len(rb) or da != db:
        out.append(f"core.results: pass a has {len(ra)} ({dict(da)}); pass b has {len(rb)} ({dict(db)})")
    if a["appraisal"].get("confidence") != b["appraisal"].get("confidence"):
        out.append(f"appraisal.confidence: pass a {a['appraisal'].get('confidence')!r}; pass b {b['appraisal'].get('confidence')!r}")
    for module, facets in schema.MODULE_FACETS.items():
        for facet in facets:
            ma = (a.get("modules", {}).get(module) or {}).get(facet, [])
            mb = (b.get("modules", {}).get(module) or {}).get(facet, [])
            voc = vocabs.get(facets[facet])
            fa, fb = _apply_rules(_facts(ma, voc), _facts(mb, voc), voc)
            if fa.keys() != fb.keys():
                out.append(_only(f"modules.{module}.{facet}", fa, fb))
    return out


def single_pass_facts(a: dict, b: dict, vocabs: dict | None = None) -> list[dict]:
    """The facts only one pass found, after the same rules diff_records applies. Each item carries the fact's own quote."""
    vocabs = vocabs or {}
    out: list[dict] = []
    for facet in schema.FACETS:
        voc = vocabs.get(schema.FACETS[facet])
        by = {p: {_key(f, voc): f for f in (r["core"].get(facet) or [])} for p, r in (("a", a), ("b", b))}
        fa, fb = _apply_rules(_facts(a["core"].get(facet), voc), _facts(b["core"].get(facet), voc), voc)
        for p, left, right in (("a", fa, fb), ("b", fb, fa)):
            for key in left.keys() - right.keys():
                fact = by[p][key]
                term = voc.terms.get(fact.get("vocab_id")) if voc is not None and fact.get("vocab_id") else None
                out.append({"facet": facet, "pass": p, "shown": left[key], "label": term.label if term else fact.get("value", ""),
                            "value": fact.get("value", ""), "quote": fact["quote"], "locator": fact["locator"]})
    ga, gb = a["core"].get("geography", {}), b["core"].get("geography", {})
    for p, g, other in (("a", ga, gb), ("b", gb, ga)):
        for code in sorted(set(g.get("countries", [])) - set(other.get("countries", []))):
            out.append({"facet": "countries", "pass": p, "shown": code, "label": code, "value": code,
                        "quote": g["quote"], "locator": g["locator"]})
    return sorted(out, key=lambda i: (i["facet"], i["shown"], i["pass"]))


def agreed_facts(a: dict, b: dict, vocabs: dict | None = None) -> list[dict]:
    """The facts both passes found (pass a's copy of each), after the same rules diff_records applies."""
    vocabs = vocabs or {}
    only_a = {(i["facet"], i["shown"]) for i in single_pass_facts(a, b, vocabs) if i["pass"] == "a"}
    out: list[dict] = []
    for facet in schema.FACETS:
        voc = vocabs.get(schema.FACETS[facet])
        for fact in a["core"].get(facet) or []:
            shown = _shown(fact)
            if (facet, shown) in only_a:
                continue
            term = voc.terms.get(fact.get("vocab_id")) if voc is not None and fact.get("vocab_id") else None
            out.append({"facet": facet, "shown": shown, "label": term.label if term else fact.get("value", ""),
                        "quote": fact["quote"], "locator": fact["locator"]})
    g = a["core"].get("geography", {})
    for code in g.get("countries", []):
        if ("countries", code) not in only_a:
            out.append({"facet": "countries", "shown": code, "label": code, "quote": g["quote"], "locator": g["locator"]})
    return out


def reconcile(records: RecordStore, file_id: str, vocabs: dict | None = None) -> None:
    a, b = records.read(file_id, "a"), records.read(file_id, "b")
    if a is None or b is None:
        return
    if a.get("review", {}).get("status") in ("accepted", "corrected"):
        return  # a human has already ruled; never override
    if a.get("transcript_sha") != b.get("transcript_sha"):
        diffs = ["the two passes were extracted from different transcript versions; extract the older pass again "
                 "(collect --redo) before comparing"]
    else:
        diffs = diff_records(a, b, vocabs)
    review = {"status": "needs_review" if diffs else "unreviewed", "items_flagged": diffs}
    if not diffs:
        review["double_pass"] = "agreed"
    if a.get("review") != review:
        a["review"] = review
        records.write(a, "a")
