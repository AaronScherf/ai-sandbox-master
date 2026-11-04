"""Plan and create the empty academic_notes/ folders that make academic_resources/ PDFs transcribable.

    python -m tools.sync_folders plan  --hub-root PATH [--out plan.json]
    python -m tools.sync_folders apply --hub-root PATH --approve approvals.json [--yes]

Notes-PDF discovery only picks up a resource PDF when its mirror folder already exists under
academic_notes/<course>/ (eligible_resource_note_pdf). `plan` lists the missing mirror folders with the PDF
count and sizes behind each, plus resource folders whose names the hub vocabulary has not confirmed yet
(those are never created -- confirm them first with tools.hub_vocabulary). `apply` creates only the folders
named in an approvals file, and only prints what it would do unless --yes is given.

approvals.json: {"folders": ["econometrics/part_2/professor_notes", ...], "max_pdf_mb": 20}

It creates empty directories only: it never writes, moves, overwrites or deletes a file. No API calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from core.env.hub_vocabulary import is_group_name, load_vocabulary, parse_hub_path

CONFIG_NAME = "hub_config.json"
_RESOURCES, _NOTES = "academic_resources", "academic_notes"


def _unknown_names(folders: list[str], vocab) -> list[str]:
    return [f for f in folders if vocab.kind_of(f) is None and not is_group_name(f, vocab)]


def build_plan(hub_root: str, config_path: Path | None = None) -> dict:
    hub_root = str(hub_root)
    vocab = load_vocabulary(config_path)
    resources, notes = os.path.join(hub_root, _RESOURCES), os.path.join(hub_root, _NOTES)
    folders: dict[str, dict] = {}
    unconfirmed: dict[str, dict] = {}
    if not os.path.isdir(resources):
        return {"folders": [], "unconfirmed": []}
    for course in sorted(os.listdir(resources)):
        course_dir = os.path.join(resources, course)
        if course.startswith(".") or not os.path.isdir(course_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(course_dir):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "processed_outputs"
                                 and d.casefold() not in vocab.textbook_folders)
            for name in sorted(filenames):
                if name.startswith(".") or not name.lower().endswith(".pdf"):
                    continue
                path = os.path.join(dirpath, name)
                hub = parse_hub_path(path, vocab)
                if hub is None or hub.category is None:
                    continue
                size = os.path.getsize(path)
                rel_dir = os.path.relpath(dirpath, course_dir).replace(os.sep, "/")
                if hub.source != "vocabulary":
                    entry = unconfirmed.setdefault(f"{course}/{rel_dir}", {
                        "folder": f"{course}/{rel_dir}", "course": course, "pdf_count": 0, "total_bytes": 0,
                        "unknown_names": _unknown_names(rel_dir.split("/"), vocab)})
                    entry["pdf_count"] += 1
                    entry["total_bytes"] += size
                    continue
                mirror_rel = "/".join((course, *hub.groups, hub.folder))
                if os.path.isdir(os.path.join(notes, *mirror_rel.split("/"))):
                    continue
                entry = folders.setdefault(mirror_rel, {
                    "folder": mirror_rel, "course": course, "pdf_count": 0, "total_bytes": 0,
                    "nested_pdf_count": 0, "nested_dirs": [], "pdfs": []})
                below = os.path.relpath(dirpath, os.path.join(course_dir, *hub.groups, hub.folder)).replace(os.sep, "/")
                if below != ".":  # PDFs in subfolders below the category folder (e.g. "student answers")
                    entry["nested_pdf_count"] += 1
                    if below not in entry["nested_dirs"]:
                        entry["nested_dirs"].append(below)
                entry["pdf_count"] += 1
                entry["total_bytes"] += size
                entry["pdfs"].append({"path": os.path.relpath(path, hub_root).replace(os.sep, "/"), "bytes": size})
    return {"folders": [folders[k] for k in sorted(folders)], "unconfirmed": [unconfirmed[k] for k in sorted(unconfirmed)]}


def apply_approvals(hub_root: str, approvals: dict, config_path: Path | None = None, create: bool = False) -> dict:
    """Create the approved mirror folders. Unknown keys raise ValueError before anything is created."""
    plan = build_plan(hub_root, config_path)
    creatable = {entry["folder"] for entry in plan["folders"]}
    wanted = list(approvals.get("folders", []))
    unknown = [key for key in wanted if key not in creatable]
    if unknown:
        raise ValueError(f"not a creatable mirror folder (unconfirmed name, already exists or unknown): {unknown}")
    notes = os.path.realpath(os.path.join(str(hub_root), _NOTES))
    created, skipped = [], []
    for key in wanted:
        course = key.split("/")[0]
        course_notes = os.path.join(notes, course)
        target = os.path.realpath(os.path.join(notes, *key.split("/")))
        if not os.path.isdir(course_notes) or os.path.commonpath([target, notes]) != notes:
            skipped.append(key)  # never invent a course, never leave academic_notes/
            continue
        if create:
            os.makedirs(target, exist_ok=True)
        created.append(key)
    return {"created" if create else "would_create": created, "skipped_no_course": skipped,
            "max_pdf_mb": approvals.get("max_pdf_mb")}


def _fmt_mb(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan/create academic_notes mirror folders (no API calls, no file changes).")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "apply"):
        p = sub.add_parser(command)
        p.add_argument("--hub-root", required=True)
        p.add_argument("--config", help=f"vocabulary file (default: <hub-root>/{CONFIG_NAME})")
        if command == "plan":
            p.add_argument("--out", help="write the plan JSON here (for the review page)")
        else:
            p.add_argument("--approve", required=True, help="approvals JSON from the review page")
            p.add_argument("--yes", action="store_true", help="actually create the folders (default: dry run)")
    args = parser.parse_args(argv)
    config = Path(args.config) if args.config else Path(args.hub_root) / CONFIG_NAME
    if args.command == "plan":
        plan = build_plan(args.hub_root, config)
        if args.out:
            Path(args.out).write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for e in plan["folders"]:
            nested = f"  ({e['nested_pdf_count']} in subfolders)" if e["nested_pdf_count"] else ""
            print(f"create  {e['folder']:<55} {e['pdf_count']:>3} PDFs  {_fmt_mb(e['total_bytes'])}{nested}")
        for e in plan["unconfirmed"]:
            print(f"CONFIRM {e['folder']:<55} {e['pdf_count']:>3} PDFs  unknown names: {e['unknown_names']}")
        print(f"{len(plan['folders'])} folders creatable, {len(plan['unconfirmed'])} folders need vocabulary answers")
        return 0
    approvals = json.loads(Path(args.approve).read_text(encoding="utf-8"))
    try:
        result = apply_approvals(args.hub_root, approvals, config, create=args.yes)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if not args.yes:
        print("dry run: nothing created. Re-run with --yes to create these folders.")
    if result.get("max_pdf_mb"):
        print(f"then transcribe with: --max-pdf-mb {result['max_pdf_mb']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
