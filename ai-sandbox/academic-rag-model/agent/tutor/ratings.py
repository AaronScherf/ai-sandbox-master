"""ratings.py -- evidence-capped tri-axial rating (spec §5). The agent
PROPOSES ratings; this module computes the highest rating the event log
supports and rejects anything above it, which is the anti-inflation
mechanism for the HW4 'everything is Proficient' failure."""
from __future__ import annotations

from agent.tutor.events import Event

AXES = ("conceptual", "rigor", "directness")
RATINGS = ("Developing / Needs Review", "Proficient", "Mastered")  # ascending


class RatingRejected(ValueError):
    pass


def _norm(text: str) -> str:
    return " ".join((text or "").split())


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


def validate_close_part(ratings: dict, part_events: list[Event]) -> None:
    ids = {e.id for e in part_events}
    student_texts = [_norm(e.text) for e in part_events if e.type == "student"]
    for axis in AXES:
        entry = ratings.get(axis)
        if not isinstance(entry, dict) or "rating" not in entry:
            raise RatingRejected(f"missing rating for axis {axis!r}")
        rating = entry["rating"]
        if rating not in RATINGS:
            raise RatingRejected(f"axis {axis!r}: rating {rating!r} is not one of {list(RATINGS)}")
        evidence = entry.get("evidence") or []
        if not evidence:
            raise RatingRejected(f"axis {axis!r}: at least one evidence item (event id or student quote) is required")
        for item in evidence:
            if isinstance(item, int):
                if item not in ids:
                    raise RatingRejected(f"axis {axis!r}: evidence event id {item} is not an event of this part")
            elif isinstance(item, str):
                if not any(_norm(item) in t for t in student_texts):
                    raise RatingRejected(f"axis {axis!r}: evidence quote not found in this part's student messages")
            else:
                raise RatingRejected(f"axis {axis!r}: evidence items must be event ids or quote strings")
        cap, reasons = ceiling(part_events, axis)
        if RATINGS.index(rating) > RATINGS.index(cap):
            raise RatingRejected(
                f"axis {axis!r}: rating {rating!r} exceeds the evidence-based ceiling {cap!r} "
                f"({'; '.join(reasons) or 'no concerns logged'}). Rate at or below the ceiling."
            )
