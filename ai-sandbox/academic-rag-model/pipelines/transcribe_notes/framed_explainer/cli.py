# pipelines/transcribe_notes/framed_explainer/cli.py
"""python -m pipelines.transcribe_notes.framed_explainer collect|submit|status"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from pipelines.transcribe_notes.agent_work import load_manifest
from pipelines.transcribe_notes.framed_explainer.collect import collect
from pipelines.transcribe_notes.framed_explainer.results import ResultError
from pipelines.transcribe_notes.framed_explainer.scene import SceneFormatError
from pipelines.transcribe_notes.framed_explainer.submit import submit


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="framed_explainer")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--scene", required=True)
    c.add_argument("--hub-root", required=True)
    c.add_argument("--run-id", default=None)
    c.add_argument("--frame-pdf", default=None)
    c.add_argument("--frames", default=None, help="comma-separated frame ids")
    for name in ("submit", "status"):
        s = sub.add_parser(name)
        s.add_argument("--run-dir", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "collect":
        if not os.path.exists(args.scene):
            print(f"scene not found: {args.scene}", file=sys.stderr)
            return 1
        run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        frames = args.frames.split(",") if args.frames else None
        try:
            res = collect(args.scene, args.hub_root, run_id, args.frame_pdf, frames)
        except SceneFormatError as exc:
            print(f"scene unreadable: {exc}", file=sys.stderr)
            return 1
        if res.status == "nothing_to_do":
            print("nothing to do: no slides and no handwriting in this scene")
            return 0
        print(f"run-dir: {res.run_dir}")
        print(f"status: {res.status}; targets: "
              + ", ".join(f"{t.slide_id or t.region_id}={t.eligibility}" for t in res.targets))
        print(f"next: have the agent follow {res.task_path}, then run submit --run-dir")
        return 0
    if args.cmd == "submit":
        try:
            report = submit(args.run_dir)
        except ResultError as exc:
            print(f"result rejected: {exc}", file=sys.stderr)
            return 2
        print(f"coverage: {report.counts}")
        if report.needs_review:
            print(f"needs_review: {', '.join(report.needs_review)}")
        if report.placement_risks:
            print(f"placement risks (ink outside frame): {', '.join(report.placement_risks)}")
        print("next: open the scene in Obsidian and run the Apply Explanations script")
        return 0
    entries = load_manifest(args.run_dir)
    for e in entries:
        print(f"{e.task_id} {e.tier} {e.status}")
    return 0
