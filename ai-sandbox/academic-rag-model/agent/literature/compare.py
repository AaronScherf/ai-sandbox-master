"""Compare two independent extraction passes over one paper and flag where they disagree."""
from __future__ import annotations

from collections import Counter

from . import schema
from .store import RecordStore
from .transcript import normalize


def _identity(fact: dict) -> str:
    return fact["vocab_id"] if fact.get("vocab_id") else "proposed:" + normalize(fact.get("value", ""))


def _set(facts) -> set[str]:
    return {_identity(f) for f in (facts or [])}


def _only(label: str, sa: set, sb: set) -> str:
    return f"{label}: only in pass a {sorted(sa - sb)}; only in pass b {sorted(sb - sa)}"


def diff_records(a: dict, b: dict) -> list[str]:
    out: list[str] = []
    for facet in schema.FACETS:
        sa, sb = _set(a["core"].get(facet)), _set(b["core"].get(facet))
        if sa != sb:
            out.append(_only(f"core.{facet}", sa, sb))
    ga, gb = a["core"].get("geography", {}), b["core"].get("geography", {})
    ca, cb = set(ga.get("countries", [])), set(gb.get("countries", []))
    if ca != cb:
        out.append(_only("core.geography.countries", ca, cb))
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
            if _set(ma) != _set(mb):
                out.append(_only(f"modules.{module}.{facet}", _set(ma), _set(mb)))
    return out


def reconcile(records: RecordStore, file_id: str) -> None:
    a, b = records.read(file_id, "a"), records.read(file_id, "b")
    if a is None or b is None:
        return
    if a.get("review", {}).get("status") in ("accepted", "corrected"):
        return  # a human has already ruled; never override
    diffs = diff_records(a, b)
    review = {"status": "needs_review" if diffs else "unreviewed", "items_flagged": diffs}
    if not diffs:
        review["double_pass"] = "agreed"
    if a.get("review") != review:
        a["review"] = review
        records.write(a, "a")
