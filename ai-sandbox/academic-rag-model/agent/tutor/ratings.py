# agent/tutor/ratings.py  (replace the whole file)
"""ratings.py -- evidence-capped tri-axial rating (v1 spec §5, v1.1 §9). Ratings
default to the highest rating the event log supports; the agent may only lower
one. The CLI attaches the evidence itself, so an unrelated quote can no longer
be cited for an axis."""
from __future__ import annotations

from agent.tutor.events import Event

AXES = ("conceptual", "rigor", "directness")
RATINGS = ("Developing / Needs Review", "Proficient", "Mastered")  # ascending


class RatingRejected(ValueError):
    pass


def ceiling(part_events: list[Event], axis: str) -> tuple[str, list[str]]:
    applies = lambda e, key: e.data.get(key, "all") in (axis, "all")
    max_hint = max((e.hint_level for e in part_events), default=0)
    miscs = [e for e in part_events if e.type == "misconception" and applies(e, "axis")]
    resolved_tags = {e.data["tag"] for e in part_events if e.type == "misconception_resolved"}
    unresolved = [e for e in miscs if e.data["tag"] not in resolved_tags]
    gaps = [e for e in part_events if e.type == "student" and e.data.get("admits_gap") and applies(e, "gap_axis")]

    reasons = []
    if max_hint >= 2:
        reasons.append(f"hint level reached {max_hint}")
    if unresolved:
        reasons.append("unresolved misconception(s): " + ", ".join(sorted({e.data['tag'] for e in unresolved})))
    if gaps:
        reasons.append("student stated they did not understand")
    if reasons:
        return RATINGS[0], reasons
    if max_hint == 0 and not miscs:
        return RATINGS[2], []
    why = []
    if max_hint == 1:
        why.append("hint level reached 1")
    if miscs:
        why.append("a misconception occurred (resolved)")
    return RATINGS[1], why


def cap_evidence(part_events: list[Event], axis: str) -> list[int]:
    applies = lambda e, key: e.data.get(key, "all") in (axis, "all")
    ids = [e.id for e in part_events
           if e.type == "student" and e.intent in ("stuck", "hint_request") and e.hint_level >= 1]
    ids += [e.id for e in part_events if e.type == "misconception" and applies(e, "axis")]
    ids += [e.id for e in part_events if e.type == "student" and e.data.get("admits_gap") and applies(e, "gap_axis")]
    if not ids:
        ids = [e.id for e in part_events if e.type == "student" and e.data.get("established")]
    if not ids:
        ids = [e.id for e in part_events if e.type == "student"][-1:]
    return sorted(set(ids))


def build_ratings(part_events: list[Event], downgrades: dict | None = None) -> dict:
    downgrades = downgrades or {}
    unknown = set(downgrades) - set(AXES)
    if unknown:
        raise RatingRejected(f"unknown axis in downgrade: {sorted(unknown)}; expected {list(AXES)}")
    out = {}
    for axis in AXES:
        cap, _ = ceiling(part_events, axis)
        rating, why = cap, None
        if axis in downgrades:
            want, why = downgrades[axis]
            if want not in RATINGS:
                raise RatingRejected(f"axis {axis!r}: rating {want!r} is not one of {list(RATINGS)}")
            if RATINGS.index(want) > RATINGS.index(cap):
                raise RatingRejected(f"axis {axis!r}: cannot raise {want!r} above the evidence ceiling {cap!r}")
            rating = want
        out[axis] = {"rating": rating, "evidence": cap_evidence(part_events, axis)}
        if why:
            out[axis]["why"] = why
    return out
