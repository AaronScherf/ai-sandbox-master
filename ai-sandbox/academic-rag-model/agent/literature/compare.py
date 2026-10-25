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


def _closed_partners(facts_a: list, facts_b: list, vocab) -> dict[str, dict]:
    """_key() of a pass-a fact -> the pass-b fact it closed against (same matching _apply_rules does), for every
    ancestor/descendant or near-duplicate-proposed pair treated as one agreed concept rather than two different
    facts. Lets agreed_facts tell which side of a closed pair is the finer (descendant) term."""
    by_b = {_key(f, vocab): f for f in facts_b}
    fa = {k: v for k, v in _facts(facts_a, vocab).items() if v not in IGNORED}
    fb = {k: v for k, v in _facts(facts_b, vocab).items() if v not in IGNORED}
    ua = {k: v for k, v in fa.items() if k not in fb}
    ub = {k: v for k, v in fb.items() if k not in fa}
    out: dict[str, dict] = {}
    used_b: set[str] = set()
    for ka, va in ua.items():
        for kb, vb in ub.items():
            if kb in used_b:
                continue
            if _close(va, vb, vocab):
                out[ka] = by_b[kb]
                used_b.add(kb)
                break
    return out


def agreed_facts(a: dict, b: dict, vocabs: dict | None = None) -> list[dict]:
    """The facts both passes found. Normally pass a's own copy; but when a parent/child pair closed the
    disagreement (one pass named the broad vocabulary bucket, the other its more specific child), shows the
    child's copy instead -- otherwise a paper whose second pass found the specific term would still display only
    the coarser one forever."""
    vocabs = vocabs or {}
    only_a = {(i["facet"], i["shown"]) for i in single_pass_facts(a, b, vocabs) if i["pass"] == "a"}
    out: list[dict] = []
    for facet in schema.FACETS:
        voc = vocabs.get(schema.FACETS[facet])
        facts_a = a["core"].get(facet) or []
        closed = _closed_partners(facts_a, b["core"].get(facet) or [], voc)
        for fact in facts_a:
            shown = _shown(fact)
            if (facet, shown) in only_a:
                continue
            chosen = fact
            partner = closed.get(_key(fact, voc))
            if partner is not None:
                vid_a, vid_b = fact.get("vocab_id"), partner.get("vocab_id")
                if vid_a and vid_b and vid_a in _ancestors(vid_b, voc):
                    chosen = partner  # partner's term is the descendant (finer) one
            term = voc.terms.get(chosen.get("vocab_id")) if voc is not None and chosen.get("vocab_id") else None
            out.append({"facet": facet, "shown": _shown(chosen), "label": term.label if term else chosen.get("value", ""),
                        "quote": chosen["quote"], "locator": chosen["locator"]})
    g = a["core"].get("geography", {})
    for code in g.get("countries", []):
        if ("countries", code) not in only_a:
            out.append({"facet": "countries", "shown": code, "label": code, "quote": g["quote"], "locator": g["locator"]})
    return out


COPY_RATIO = 0.95  # honest passes quote the same sentence for some facts, and rarely for all of them (2 of 62 real pairs)
COPY_MIN_FACTS = 5


def _support(record: dict) -> list[tuple]:
    out = []
    for facet, value in record["core"].items():
        rows = [value] if facet == "geography" else (value or [])
        out += [(facet, normalize(r.get("quote", "")), repr(r.get("locator"))) for r in rows]
    return out


def copy_ratio(a: dict, b: dict) -> float:
    """The share of pass b's supporting quotes (same text on the same page) that pass a also used."""
    in_a = set(_support(a))
    mine = _support(b)
    return sum(1 for f in mine if f in in_a) / len(mine) if mine else 0.0


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
    if len(_support(b)) >= COPY_MIN_FACTS and copy_ratio(a, b) >= COPY_RATIO:
        diffs = diffs + ["the two passes cite the same quotes for almost every fact, so they may not be independent; "
                         "extract pass b again without access to pass a"]
    review = {"status": "needs_review" if diffs else "unreviewed", "items_flagged": diffs}
    if not diffs:
        review["double_pass"] = "agreed"
    if a.get("review") != review:
        a["review"] = review
        records.write(a, "a")
