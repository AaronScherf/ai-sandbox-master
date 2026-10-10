"""profile.py -- per-course concept-gap tracker (v1 spec §6, v1.1 §9). Single writer: the
session (`end`, `pause`). schema_version 2 adds `status` (rated | deferred | skipped) and
`attempt` to every history entry; v1 files load with every entry `rated`, attempt 1. The
future learning-progress subproject builds on this schema."""
from __future__ import annotations

import copy
import json
import os

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS
from agent.tutor.status import attempt_records

SCHEMA_VERSION = 2


def _normalise(profile: dict) -> dict:
    prof = copy.deepcopy(profile)
    prof["schema_version"] = SCHEMA_VERSION
    for entry in prof.get("concepts", {}).values():
        for h in entry.get("history", []):
            h.setdefault("status", "rated")
            h.setdefault("attempt", 1)
    return prof


def load_profile(path: str) -> dict:
    if not os.path.exists(path):
        return {"schema_version": SCHEMA_VERSION, "concepts": {}}
    with open(path, "r", encoding="utf-8") as f:
        return _normalise(json.load(f))


def update_profile(profile: dict, *, session_id: str, date: str, events: list[Event], packet: Packet) -> dict:
    """Idempotent per session: this session's earlier entries are replaced, so `pause` followed by `end`
    does not duplicate history."""
    new = _normalise(profile)
    for entry in new["concepts"].values():
        entry["history"] = [h for h in entry["history"] if h["session"] != session_id]
    records = attempt_records(events)
    resolved = {(e.part, e.data["tag"]) for e in events if e.type == "misconception_resolved"}
    for part in packet.parts:
        for tag in part.concept_tags:
            entry = new["concepts"].setdefault(tag, {"history": [], "open_misconceptions": []})
            for rec in records:
                if rec["part"] != part.part_id:
                    continue
                base = {"session": session_id, "date": date, "part": part.part_id, "status": rec["status"],
                        "attempt": rec["attempt"]}
                if rec["status"] == "rated":
                    for axis, r in rec["event"].data["ratings"].items():
                        entry["history"].append({**base, "axis": axis, "rating": r["rating"]})
                else:
                    entry["history"].append(base)
            for e in events:
                if e.type == "misconception" and e.part == part.part_id:
                    mtag = e.data["tag"]
                    if (part.part_id, mtag) in resolved:
                        if mtag in entry["open_misconceptions"]:
                            entry["open_misconceptions"].remove(mtag)
                    elif mtag not in entry["open_misconceptions"]:
                        entry["open_misconceptions"].append(mtag)
            for (rpart, mtag) in resolved:
                if rpart == part.part_id and mtag in entry["open_misconceptions"]:
                    entry["open_misconceptions"].remove(mtag)
    return new


def _is_gap(entry: dict) -> bool:
    hist = entry["history"]
    rated = [h for h in hist if h.get("status", "rated") == "rated"]
    latest = max((h["session"] for h in rated), default=None)
    developing = any(h["rating"] == RATINGS[0] for h in rated if h["session"] == latest)
    key = lambda h: (h["session"], h.get("attempt", 1))
    last_rated = max((key(h) for h in rated), default=None)
    deferred_open = any(h.get("status") == "deferred" and (last_rated is None or key(h) > last_rated) for h in hist)
    return developing or bool(entry["open_misconceptions"]) or deferred_open


def open_gaps(profile: dict) -> list[str]:
    return [tag for tag, entry in sorted(profile["concepts"].items()) if _is_gap(entry)]


def render_profile_md(profile: dict) -> str:
    lines = ["# Learner profile", "", f"_schema v{profile['schema_version']}_", "", "## Open gaps", ""]
    gaps = open_gaps(profile)
    lines += [f"- `{t}`" + (f" — misconceptions: {', '.join(profile['concepts'][t]['open_misconceptions'])}"
                            if profile['concepts'][t]['open_misconceptions'] else "") for t in gaps] or ["- None"]
    lines += ["", "## History", ""]
    for tag, entry in sorted(profile["concepts"].items()):
        lines.append(f"### {tag}")
        for h in entry["history"]:
            suffix = f" (attempt {h['attempt']})" if h.get("attempt", 1) > 1 else ""
            status = h.get("status", "rated")
            if status == "rated":
                lines.append(f"- {h['date']} {h['part']} {h['axis']}: {h['rating']}{suffix}")
            elif status == "deferred":
                lines.append(f"- {h['date']} {h['part']}: deferred after an attempt (gap evidence){suffix}")
            else:
                lines.append(f"- {h['date']} {h['part']}: skipped (not covered){suffix}")
        lines.append("")
    return "\n".join(lines) + "\n"


def save_profile(json_path: str, md_path: str, profile: dict) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_profile_md(profile))
