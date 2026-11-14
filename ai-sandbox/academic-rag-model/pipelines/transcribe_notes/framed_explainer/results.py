# pipelines/transcribe_notes/framed_explainer/results.py
"""Validate the agent's result.json against facts.json and resolve every ink
stroke to exactly one disposition (assigned | fallback_nearest | section).
The in-vault apply script re-checks the same invariants (shared fixtures)."""
from __future__ import annotations

import copy
from collections import Counter

from pipelines.transcribe_notes.framed_explainer.bands import assign_strokes
from pipelines.transcribe_notes.framed_explainer.identity import input_fingerprint
from pipelines.transcribe_notes.framed_explainer.ink import (
    Bounds, Region, anchor_for, reading_order)

FORBIDDEN = ("## Agent output", "# Markdown Images", "<!-- excalidraw-markdown-image:")
LEGIBILITY = {"legible", "partial", "unreadable"}


class ResultError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _walk_text(result: dict):
    for s in result.get("slides", []):
        for ink in s.get("ink", []):
            for k in ("rationale", "transcription"):
                yield ink.get(k)
        card = s.get("card") or {}
        yield from card.get("paragraphs", [])
        yield card.get("reason")
    for sec in result.get("sections", []):
        yield sec.get("transcription")
        yield sec.get("note")
        card = sec.get("card") or {}
        yield from card.get("paragraphs", [])
        yield card.get("reason")


def _check_card(card: dict | None, where: str) -> None:
    if card is None:
        return
    status = card.get("status")
    if status == "ok":
        paras = card.get("paragraphs", [])
        if len(paras) != 2 or not all(isinstance(p, str) and p.strip() for p in paras):
            raise ResultError("bad_card", f"{where}: ok card needs exactly two non-empty paragraphs")
    elif status != "needs_review":
        raise ResultError("bad_card", f"{where}: status must be ok or needs_review")


def validate_result(result: dict, facts: dict) -> None:
    if result.get("schema") != 1:
        raise ResultError("schema", "schema must be 1")
    if result.get("scene_sha1") != facts["scene_sha1"]:
        raise ResultError("stale_scene", "scene changed since collect")
    slides = {s["id"]: s for s in facts["slides"]}
    strokes = {s["id"] for s in facts["strokes"]}
    seen: set[str] = set()
    slide_ids: set[str] = set()

    def take(ids: list[str], where: str) -> None:
        for i in ids:
            if i not in strokes:
                raise ResultError("unknown_id", f"{where}: unknown stroke {i}")
            if i in seen:
                raise ResultError("duplicate_stroke", f"{where}: stroke {i} listed twice")
            seen.add(i)

    for s in result.get("slides", []):
        sid = s.get("slide_id")
        if sid not in slides:
            raise ResultError("unknown_id", f"unknown slide {sid}")
        if sid in slide_ids:
            raise ResultError("unknown_id", f"slide {sid} listed twice")
        slide_ids.add(sid)
        if s.get("frame_id") != slides[sid]["frame_id"]:
            raise ResultError("unknown_id", f"slide {sid}: frame_id does not match facts")
        for ink in s.get("ink", []):
            if ink.get("disposition") != "assigned":
                raise ResultError("bad_value", f"slide {sid}: ink disposition must be assigned")
            conf = ink.get("confidence")
            if conf is not None and not 0 <= conf <= 1:
                raise ResultError("bad_value", f"slide {sid}: confidence out of range")
            if ink.get("legibility") not in LEGIBILITY:
                raise ResultError("bad_value", f"slide {sid}: bad legibility")
            take(ink.get("stroke_ids", []), f"slide {sid}")
        _check_card(s.get("card"), f"slide {sid}")
    section_ids: set[str] = set()
    for sec in result.get("sections", []):
        if sec.get("section_id") in section_ids:
            raise ResultError("bad_value", f"duplicate section {sec.get('section_id')}")
        section_ids.add(sec.get("section_id"))
        if sec.get("legibility") not in LEGIBILITY:
            raise ResultError("bad_value", f"section {sec.get('section_id')}: bad legibility")
        take(sec.get("stroke_ids", []), f"section {sec.get('section_id')}")
        _check_card(sec.get("card"), f"section {sec.get('section_id')}")
    for text in _walk_text(result):
        if isinstance(text, str) and any(f in text for f in FORBIDDEN):
            raise ResultError("forbidden_text", "text contains a reserved marker string")


def _bounds_of(ids: list[str], strokes: dict[str, dict]) -> Bounds:
    xs = [strokes[i]["x"] for i in ids]
    ys = [strokes[i]["y"] for i in ids]
    xe = [strokes[i]["x"] + strokes[i]["width"] for i in ids]
    ye = [strokes[i]["y"] + strokes[i]["height"] for i in ids]
    return Bounds(min(xs), min(ys), max(xe) - min(xs), max(ye) - min(ys))


def resolve_result(result: dict, facts: dict) -> dict:
    out = copy.deepcopy(result)
    strokes = {s["id"]: s for s in facts["strokes"]}
    slide_elems = [{"id": s["id"], "x": s["box"]["x"], "y": s["box"]["y"],
                    "width": s["box"]["w"], "height": s["box"]["h"]} for s in facts["slides"]]
    frame_of = {s["id"]: s["frame_id"] for s in facts["slides"]}
    slide_of = {i: sid for sid, ids in assign_strokes(slide_elems, facts["strokes"]).by_slide.items()
                for i in ids}               # band rule, same as the framer
    frames = {f["id"]: f["box"] for f in facts.get("frames", [])}

    def in_frame(sid: str, fid: str) -> bool:
        b, e = frames.get(fid), strokes[sid]
        return b is None or (e["x"] >= b["x"] and e["y"] >= b["y"]
                             and e["x"] + e["width"] <= b["x"] + b["w"]
                             and e["y"] + e["height"] <= b["y"] + b["h"])

    sections = list(out.get("sections", []))
    for s in out["slides"]:           # assigned ink the frame cannot hold becomes a section
        kept_ink = []
        for ink in s["ink"]:
            outside = [i for i in ink["stroke_ids"] if not in_frame(i, s["frame_id"])]
            if outside:
                sections.append({"section_id": ink["region_id"], "region_id": ink["region_id"],
                                 "stroke_ids": outside, "transcription": ink.get("transcription", ""),
                                 "legibility": ink["legibility"],
                                 "context_assisted": ink.get("context_assisted", False)})
                ink["stroke_ids"] = [i for i in ink["stroke_ids"] if i not in outside]
            if ink["stroke_ids"]:
                kept_ink.append(ink)
        s["ink"] = kept_ink
    covered = {i for s in out["slides"] for ink in s["ink"] for i in ink["stroke_ids"]}
    covered |= {i for sec in sections for i in sec["stroke_ids"]}
    for r in facts["regions"]:
        left = [i for i in r["stroke_ids"] if i not in covered]
        if left:
            sections.append({"section_id": f"auto-{r['region_id']}", "region_id": r["region_id"],
                             "stroke_ids": left, "transcription": "", "legibility": "unreadable",
                             "context_assisted": False, "omitted_by_agent": True})
            covered |= set(left)
    sections = [sec for sec in sections if sec["stroke_ids"]]
    for sec in sections:              # deterministic ids: match the framer's notes-<first stroke>
        sec.setdefault("region_id", sec["section_id"])
        sec["section_id"] = "notes-" + min(sec["stroke_ids"])

    all_regions = [Region(ink["region_id"], _bounds_of(ink["stroke_ids"], strokes), ink["stroke_ids"])
                   for s in out["slides"] for ink in s["ink"] if ink["stroke_ids"]]
    all_regions += [Region(sec["section_id"], _bounds_of(sec["stroke_ids"], strokes),
                           sec["stroke_ids"]) for sec in sections]
    kept: list[tuple[dict, Region]] = []
    for sec in sections:
        region = next(r for r in all_regions if r.region_id == sec["section_id"])
        votes = Counter(slide_of.get(i) for i in sec["stroke_ids"])
        best, n = votes.most_common(1)[0]
        target = best if best is not None and n >= 0.6 * len(sec["stroke_ids"]) else None
        if target and not all(in_frame(i, frame_of[target]) for i in sec["stroke_ids"]):
            target = None            # a frame that cannot hold the ink keeps it as a section
        if target:
            rec = next((s for s in out["slides"] if s["slide_id"] == target), None)
            if rec is None:
                rec = {"slide_id": target, "frame_id": frame_of[target], "ink": [],
                       "existing_explanation_id": None, "card": None}
                out["slides"].append(rec)
            rec["ink"].append({"region_id": sec.get("region_id", sec["section_id"]),
                               "stroke_ids": sec["stroke_ids"], "disposition": "fallback_nearest",
                               "confidence": None, "rationale": "band rule: ink sits in this slide's band",
                               "transcription": sec.get("transcription", ""),
                               "legibility": sec["legibility"],
                               "context_assisted": sec.get("context_assisted", False)})
        else:
            anchor, also = anchor_for(region, slide_elems)
            sec["kind"] = "anchored" if anchor else "standalone"
            sec["anchor_slide_id"], sec["also_near"] = anchor, also
            kept.append((sec, region))

    groups: dict[str | None, list[tuple[dict, Region]]] = {}
    for sec, region in kept:
        groups.setdefault(sec["anchor_slide_id"], []).append((sec, region))
    ordered: list[dict] = []
    for anchor in sorted(groups, key=lambda a: (a is None, a or "")):
        by_region = {id(region): sec for sec, region in groups[anchor]}
        for seq, region in enumerate(reading_order([r for _, r in groups[anchor]]), start=1):
            sec = by_region[id(region)]
            sec["seq"] = seq
            ordered.append(sec)
    out["sections"] = ordered

    counts = {"assigned": 0, "fallback_nearest": 0, "section": 0}
    for s in out["slides"]:
        for ink in s["ink"]:
            counts[ink["disposition"]] += len(ink["stroke_ids"])
    counts["section"] = sum(len(sec["stroke_ids"]) for sec in out["sections"])
    if sum(counts.values()) != len(strokes):
        raise ResultError("coverage", f"strokes {len(strokes)} != dispositions {counts}")
    out["coverage"] = counts
    out["namespace"] = facts["namespace"]
    out["fingerprints"] = {(t["slide_id"] or t["region_id"]): t["fingerprint"]
                           for t in facts["targets"]}
    for sec in out["sections"]:
        out["fingerprints"][sec["section_id"]] = input_fingerprint(
            None, [strokes[i] for i in sec["stroke_ids"]], None,
            facts.get("prompt_version", ""), facts.get("context_version", ""))
    out["strokes"] = [{"id": s["id"], "x": s["x"], "y": s["y"], "width": s["width"],
                       "height": s["height"]} for s in sorted(facts["strokes"], key=lambda s: s["id"])]
    out["resolved"] = True
    return out
