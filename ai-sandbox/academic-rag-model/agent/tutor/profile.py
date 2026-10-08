"""profile.py -- per-course concept-gap tracker (spec §6). Single writer:
Session.end(). schema_version is stable so the future learning-progress
subproject (spec §10.2) can build on it."""
from __future__ import annotations

import copy
import json
import os

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS

SCHEMA_VERSION = 1


def load_profile(path: str) -> dict:
    if not os.path.exists(path):
        return {"schema_version": SCHEMA_VERSION, "concepts": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_profile(profile: dict, *, session_id: str, date: str, events: list[Event], packet: Packet) -> dict:
    new = copy.deepcopy(profile)
    resolved = {(e.part, e.data["tag"]) for e in events if e.type == "misconception_resolved"}
    for part in packet.parts:
        for tag in part.concept_tags:
            entry = new["concepts"].setdefault(tag, {"history": [], "open_misconceptions": []})
            for e in events:
                if e.type == "close_part" and e.part == part.part_id:
                    for axis, r in e.data["ratings"].items():
                        entry["history"].append({"session": session_id, "date": date, "part": part.part_id,
                                                 "axis": axis, "rating": r["rating"]})
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


def open_gaps(profile: dict) -> list[str]:
    gaps = []
    for tag, entry in sorted(profile["concepts"].items()):
        hist = entry["history"]
        latest = max((h["session"] for h in hist), default=None)
        developing = any(h["rating"] == RATINGS[0] for h in hist if h["session"] == latest)
        if developing or entry["open_misconceptions"]:
            gaps.append(tag)
    return gaps


def render_profile_md(profile: dict) -> str:
    lines = ["# Learner profile", "", f"_schema v{profile['schema_version']}_", "", "## Open gaps", ""]
    gaps = open_gaps(profile)
    lines += [f"- `{t}`" + (f" — misconceptions: {', '.join(profile['concepts'][t]['open_misconceptions'])}"
                            if profile['concepts'][t]['open_misconceptions'] else "") for t in gaps] or ["- None"]
    lines += ["", "## History", ""]
    for tag, entry in sorted(profile["concepts"].items()):
        lines.append(f"### {tag}")
        for h in entry["history"]:
            lines.append(f"- {h['date']} {h['part']} {h['axis']}: {h['rating']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def save_profile(json_path: str, md_path: str, profile: dict) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_profile_md(profile))
