"""status.py -- what happened to each part, read from the log (v1.1 §8-§9). One record per
attempt that ended: a clean close (`rated`), or a skip request that parked it (`deferred` when
a real attempt was made first, else `skipped`)."""
from __future__ import annotations

from agent.tutor.events import Event


def attempt_records(events: list[Event]) -> list[dict]:
    out = []
    for e in events:
        if e.type == "close_part":
            out.append({"part": e.part, "attempt": e.data.get("attempt", 1), "status": "rated", "event": e})
        elif e.type == "part_status":
            out.append({"part": e.part, "attempt": e.data.get("attempt", 1), "status": e.data["status"], "event": e})
    return out


def final_status(events: list[Event], part_id: str) -> str | None:
    status = None
    for e in events:
        if e.part != part_id:
            continue
        if e.type == "close_part":
            status = "rated"
        elif e.type == "part_status":
            status = e.data["status"]
        elif e.type == "student" and e.intent == "revisit":
            status = "revisiting"
    return status
