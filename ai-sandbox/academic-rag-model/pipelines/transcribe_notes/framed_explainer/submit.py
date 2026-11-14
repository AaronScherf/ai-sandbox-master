# pipelines/transcribe_notes/framed_explainer/submit.py
"""Submit: validate and resolve result.json, write result.resolved.json and
state.json, and mark the manifest entry submitted. Never touches the scene."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from pipelines.transcribe_notes.agent_work import load_manifest, render_worklist, save_manifest
from pipelines.transcribe_notes.framed_explainer.identity import State
from pipelines.transcribe_notes.framed_explainer.results import resolve_result, validate_result


@dataclass
class SubmitReport:
    counts: dict[str, int]
    needs_review: list[str]
    placement_risks: list[str]


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def submit(run_dir: str) -> SubmitReport:
    facts = _load(os.path.join(run_dir, "facts.json"))
    result = _load(os.path.join(run_dir, "result.json"))
    validate_result(result, facts)
    resolved = resolve_result(result, facts)

    fingerprints = {t["slide_id"] or t["region_id"]: t["fingerprint"] for t in facts["targets"]}
    strokes = {s["id"]: s for s in facts["strokes"]}
    frames = {f["id"]: f["box"] for f in facts["frames"]}
    state: dict[str, dict] = {}
    needs_review: list[str] = []
    risks: list[str] = []
    for s in resolved["slides"]:
        card = s.get("card") or {}
        key = s["slide_id"]
        st = State.needs_review if card.get("status") == "needs_review" else State.validated
        if st is State.needs_review:
            needs_review.append(key)
        state[key] = {"state": st.value, "fingerprint": fingerprints.get(key)}
        box = frames.get(s["frame_id"] or "")
        for ink in s["ink"]:
            for i in ink["stroke_ids"]:
                e = strokes[i]
                if box and not (e["x"] >= box["x"] and e["y"] >= box["y"]
                                and e["x"] + e["width"] <= box["x"] + box["w"]
                                and e["y"] + e["height"] <= box["y"] + box["h"]):
                    if key not in risks:
                        risks.append(key)
    for sec in resolved["sections"]:
        card = sec.get("card") or {}
        if card.get("status") == "needs_review":
            needs_review.append(sec["section_id"])
        if card:
            state[sec["section_id"]] = {
                "state": (State.needs_review if card.get("status") == "needs_review"
                          else State.validated).value,
                "fingerprint": fingerprints.get(sec.get("region_id"))}
    _dump(os.path.join(run_dir, "result.resolved.json"), resolved)
    _dump(os.path.join(run_dir, "state.json"), state)
    entries = load_manifest(run_dir)
    for e in entries:
        e.status = "submitted"
    if entries:
        save_manifest(run_dir, entries)
        render_worklist(run_dir, entries)
    return SubmitReport(counts=resolved["coverage"], needs_review=needs_review,
                        placement_risks=risks)
