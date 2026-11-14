# pipelines/transcribe_notes/framed_explainer/collect.py
"""Collector: read one scene (read-only), stage a task card, facts.json, frame
rasters and course context under .agent_work/<run>/<scene-slug>/ for the agent."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Literal

from pipelines.transcribe_notes.agent_work import (
    ManifestEntry, doc_slug_for, doc_work_dir, load_manifest, render_worklist, save_manifest)
from pipelines.transcribe_notes.framed_explainer.course_context import build_course_context
from pipelines.transcribe_notes.framed_explainer.identity import input_fingerprint
from pipelines.transcribe_notes.framed_explainer.ink import Bounds, box_gap, cluster_ink
from pipelines.transcribe_notes.framed_explainer.rasters import rasterize_frame_pdf
from pipelines.transcribe_notes.framed_explainer.review import load_declined
from pipelines.transcribe_notes.framed_explainer.scene import classify, load_scene

PROMPT_VERSION = "explainer-v1"
_RUNBOOK = os.path.join(os.path.dirname(__file__), "runbook.md")

Eligibility = Literal["eligible", "ambiguous_match", "missing_asset", "clipped_ink",
                      "existing_card", "needs_review", "declined"]


@dataclass
class Target:
    frame_id: str | None
    slide_id: str | None
    eligibility: Eligibility
    fingerprint: str
    region_id: str | None = None


@dataclass
class CollectResult:
    run_dir: str
    facts_path: str
    task_path: str
    status: Literal["staged", "nothing_to_do", "already_staged"]
    targets: list[Target]


def _b(e: dict) -> Bounds:
    return Bounds(e["x"], e["y"], e["width"], e["height"])


def _inside(inner: Bounds, outer: Bounds) -> bool:
    return (inner.x >= outer.x and inner.y >= outer.y
            and inner.right <= outer.right and inner.bottom <= outer.bottom)


def _frame_for(slide_box: Bounds, frames: list[dict]) -> dict | None:
    for f in sorted(frames, key=lambda f: f["id"]):
        if _inside(slide_box, _b(f)):
            return f
    return None


def _box_json(b: Bounds) -> dict:
    return {"x": b.x, "y": b.y, "w": b.w, "h": b.h}


def collect(scene_path: str, hub_root: str, run_id: str, frame_pdf: str | None = None,
            frames: list[str] | None = None) -> CollectResult:
    scene = load_scene(scene_path)
    c = classify(scene)
    if not c.slides and not c.ink:
        return CollectResult("", "", "", "nothing_to_do", [])

    slug = doc_slug_for(scene_path, hashlib.sha1(
        os.path.abspath(scene_path).encode("utf-8")).hexdigest())
    run_dir = doc_work_dir(hub_root, run_id, slug)
    context = build_course_context(scene_path, hub_root)
    declined = load_declined(hub_root, slug)
    regions = cluster_ink(c.ink)
    mode = "slides" if c.slides else "ink_only"
    wanted = set(frames) if frames else None

    ink_by_id = {e["id"]: e for e in c.ink}
    slide_rows, targets = [], []
    for s in sorted(c.slides, key=lambda e: (e["y"], e["x"], e["id"])):
        frame = _frame_for(_b(s), c.frames)
        fid = frame["id"] if frame else None
        link = scene.registry.get(s.get("fileId"), "")
        existing = [x["id"] for x in c.explanations
                    if frame and (x.get("frameId") == fid or _inside(_b(x), _b(frame)))]
        near_ink = [ink_by_id[i] for r in regions for i in r.stroke_ids
                    if box_gap(r.bounds, _b(s)) == min(
                        box_gap(r.bounds, _b(o)) for o in c.slides)]
        if frame:
            near_ink = [e for e in c.ink if _inside(_b(e), _b(frame))]
        if not link:
            elig: Eligibility = "missing_asset"
        elif fid is None:
            elig = "needs_review"
        elif existing:
            elig = "existing_card"
        else:
            elig = "eligible"
        if wanted is not None and fid not in wanted:
            continue
        fp = input_fingerprint(s.get("fileId"), near_ink, fid, PROMPT_VERSION, context.version)
        if declined.get(s["id"]) == fp:
            elig = "declined"
        slide_rows.append({"id": s["id"], "file_id": s.get("fileId"), "link": link,
                           "frame_id": fid, "box": _box_json(_b(s)),
                           "existing_explanation_ids": sorted(existing)})
        targets.append(Target(fid, s["id"], elig, fp))

    region_rows = []
    for r in regions:
        near = sorted(((box_gap(r.bounds, _b(s)), s["id"]) for s in c.slides))[:2]
        region_rows.append({"region_id": r.region_id, "bounds": _box_json(r.bounds),
                            "stroke_ids": sorted(r.stroke_ids),
                            "candidate_slides": [{"id": i, "distance": round(d, 1)}
                                                 for d, i in near]})
        if mode == "ink_only":
            members = [ink_by_id[i] for i in r.stroke_ids]
            rfp = input_fingerprint(None, members, None, PROMPT_VERSION, context.version)
            targets.append(Target(None, None, "declined" if declined.get(r.region_id) == rfp
                                  else "eligible", rfp, r.region_id))

    facts = {
        "schema": 1, "scene": os.path.basename(scene_path), "namespace": slug,
        "scene_sha1": scene.sha1, "mode": mode, "prompt_version": PROMPT_VERSION,
        "context_version": context.version, "slides": slide_rows, "regions": region_rows,
        "frames": [{"id": f["id"], "name": f.get("name"), "box": _box_json(_b(f))}
                   for f in sorted(c.frames, key=lambda f: f["id"])],
        "strokes": [{"id": e["id"], "version": e.get("version", 1), "x": e["x"], "y": e["y"],
                     "width": e["width"], "height": e["height"]}
                    for e in sorted(c.ink, key=lambda e: e["id"])],
        "targets": [{"frame_id": t.frame_id, "slide_id": t.slide_id, "region_id": t.region_id,
                     "eligibility": t.eligibility, "fingerprint": t.fingerprint}
                    for t in targets],
    }
    facts_text = json.dumps(facts, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    facts_path = os.path.join(run_dir, "facts.json")
    task_path = os.path.join(run_dir, "task.md")
    if os.path.exists(facts_path):
        with open(facts_path, "r", encoding="utf-8", newline="") as f:
            if f.read() == facts_text:
                return CollectResult(run_dir, facts_path, task_path, "already_staged", targets)

    os.makedirs(run_dir, exist_ok=True)
    with open(facts_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(facts_text)
    with open(os.path.join(run_dir, "course_context.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(context.text + "\n")
    if frame_pdf:
        listed = [f for f in c.frames if wanted is None or f["id"] in wanted]
        rasterize_frame_pdf(frame_pdf, listed, os.path.join(run_dir, "images"))
    with open(_RUNBOOK, "r", encoding="utf-8") as f:
        runbook = f.read()
    with open(task_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Explainer task: {facts['scene']}\n\nRun directory: this folder. "
                f"Read `facts.json`, `course_context.md` and `images/`; write "
                f"`result.json` here.\n\n{runbook}")
    entries = load_manifest(run_dir)
    entries.append(ManifestEntry(task_id=f"task-{len(entries) + 1:04d}", tier="cards",
                                 pages=list(range(1, len(targets) + 1)) or [1],
                                 status="pending"))
    save_manifest(run_dir, entries)
    render_worklist(run_dir, entries)
    return CollectResult(run_dir, facts_path, task_path, "staged", targets)
