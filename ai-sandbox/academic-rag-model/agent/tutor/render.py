"""render.py -- vault markdown from the event log (spec §5, §6)."""
from __future__ import annotations

import os

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import AXES, RATINGS

AXIS_NAMES = {"conceptual": "Conceptual Fluency", "rigor": "Mathematical Rigor & Notation", "directness": "Directness & Proof Elegance"}


def render_transcript(events: list[Event]) -> str:
    lines = ["# Transcript", ""]
    for e in events:
        if e.type == "student":
            lines += [f"**Student:** {e.text}", ""]
        elif e.type == "tutor_say":
            lines += [f"**Tutor:** {e.text}", ""]
    return "\n".join(lines)


def _evidence_text(item, by_id: dict) -> str:
    if isinstance(item, int):
        e = by_id.get(item)
        text = (e.text or e.data.get("tag", "")) if e else f"event {item}"
        return f'"{" ".join(text.split())[:140]}" (event {item})'
    return f'"{item}"'


def render_summary(events: list[Event], packet: Packet, big_picture: str, prior_gaps: list[str], date: str) -> str:
    by_id = {e.id: e for e in events}
    closed = {e.part: e.data["ratings"] for e in events if e.type == "close_part"}
    lines = [f"# Session Summary — {packet.problem_set} ({date})", "", "## 1. Diagnostic", "",
             "| Part | Concepts | " + " | ".join(AXIS_NAMES[a] for a in AXES) + " |",
             "|---|---|" + "---|" * len(AXES)]
    for part in packet.parts:
        r = closed.get(part.part_id)
        cells = [r[a]["rating"] if r else "—" for a in AXES]
        lines.append(f"| {part.label or part.part_id} | {', '.join(part.concept_tags)} | " + " | ".join(cells) + " |")
    lines += ["", "## 2. Big Picture", "", big_picture.strip(), "", "## 3. Tri-Axial Rubric", ""]
    for part in packet.parts:
        r = closed.get(part.part_id)
        if not r:
            continue
        lines.append(f"### {part.label or part.part_id}")
        for a in AXES:
            ev_text = "; ".join(_evidence_text(i, by_id) for i in r[a]["evidence"])
            lines.append(f"- **{AXIS_NAMES[a]} — {r[a]['rating']}**: {ev_text}")
        lines.append("")
    lines += ["## 4. Action Menu", ""]
    review = []
    for part in packet.parts:
        r = closed.get(part.part_id)
        if r and any(r[a]["rating"] == RATINGS[0] for a in AXES):
            review += [t for t in part.concept_tags if t not in review]
    for tag in review:
        lines.append(f"- Review `{tag}` (rated Developing / Needs Review this session)")
    for tag in prior_gaps:
        if tag not in review:
            lines.append(f"- Previously flagged, still open: `{tag}`")
    if not review and not prior_gaps:
        lines.append("- No review items flagged.")
    return "\n".join(lines) + "\n"


def write_session_docs(session_dir, events, packet, big_picture, prior_gaps, date) -> tuple[str, str]:
    os.makedirs(session_dir, exist_ok=True)
    t = os.path.join(session_dir, "transcript.md")
    s = os.path.join(session_dir, "summary.md")
    with open(t, "w", encoding="utf-8") as f:
        f.write(render_transcript(events))
    with open(s, "w", encoding="utf-8") as f:
        f.write(render_summary(events, packet, big_picture, prior_gaps, date))
    return t, s
