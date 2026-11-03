"""Propose, preview and confirm the hub's folder-name vocabulary (no API calls).

    python -m tools.hub_vocabulary propose --hub-root PATH
    python -m tools.hub_vocabulary impact  --hub-root PATH [--limit N]
    python -m tools.hub_vocabulary confirm NAME {category,group,ignore} --hub-root PATH [--alias-of CANONICAL] [--replace]

`propose` prints candidate names learned from the tree (read-only). `impact` lists the files and cards whose
category or group layers would parse differently from the pre-vocabulary rules; run it before relying on a
newly confirmed name. `confirm` stores one owner answer in <hub-root>/hub_config.json (or --config); each name
is asked once, and a different later answer needs --replace.

Spec: docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md; plan P2, Task 7.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

from core.env.hub_vocab_learn import CONTENT_EXTENSIONS, ROOTS, propose_vocabulary
from core.env.hub_vocabulary import KINDS, Vocabulary, load_vocabulary, parse_hub_path
from core.indexer.index_card import list_courses, load_shard

CONFIG_NAME = "hub_config.json"


def _differs(rel_path: str, vocab: Vocabulary, legacy: Vocabulary) -> tuple | None:
    new, old = parse_hub_path(rel_path, vocab), parse_hub_path(rel_path, legacy)
    if new is None or old is None or (new.groups, new.category) == (old.groups, old.category):
        return None
    return old, new


def _transcribable_pdfs(hub_root: str, config_path: Path) -> set[str]:
    """PDFs the notes-transcription discovery would pick up under the given vocabulary file (real discovery code)."""
    from pipelines.transcribe_notes.route_notes_transcribe import discover_pdf_sources
    previous = os.environ.get("ACADEMIC_HUB_CONFIG")
    os.environ["ACADEMIC_HUB_CONFIG"] = str(config_path)
    try:
        found: set[str] = set()
        notes_root = os.path.join(hub_root, "academic_notes")
        for course in sorted(os.listdir(notes_root)) if os.path.isdir(notes_root) else []:
            if os.path.isdir(os.path.join(notes_root, course)) and not course.startswith("."):
                found.update(os.path.relpath(p, hub_root).replace(os.sep, "/")
                             for p in discover_pdf_sources(os.path.join(notes_root, course)))
        return found
    finally:
        if previous is None:
            os.environ.pop("ACADEMIC_HUB_CONFIG", None)
        else:
            os.environ["ACADEMIC_HUB_CONFIG"] = previous


def newly_eligible_pdfs(hub_root: str, config_path: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        legacy_config = Path(tmp) / CONFIG_NAME
        legacy_config.write_text('{"names": {}}', encoding="utf-8")
        before = _transcribable_pdfs(hub_root, legacy_config)
    return sorted(_transcribable_pdfs(hub_root, config_path) - before)


def impact(hub_root: str, config_path: Path, limit: int = 20) -> dict:
    vocab, legacy = load_vocabulary(config_path), Vocabulary()
    by_course: Counter = Counter()
    samples: list[dict] = []
    changed = 0
    for root_name in ROOTS:
        root = os.path.join(hub_root, root_name)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for name in sorted(filenames):
                if name.startswith(".") or not name.lower().endswith(CONTENT_EXTENSIONS):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), hub_root).replace(os.sep, "/")
                diff = _differs(rel, vocab, legacy)
                if diff is None:
                    continue
                old, new = diff
                changed += 1
                by_course[new.course] += 1
                if len(samples) < limit:
                    samples.append({"path": rel, "legacy_category": old.category, "legacy_groups": list(old.groups),
                                    "category": new.category, "groups": list(new.groups)})
    cards_changed = 0
    for course in list_courses(hub_root):
        for card in load_shard(hub_root, course):
            if card.get("path") and _differs(card["path"], vocab, legacy) is not None:
                cards_changed += 1
    return {"changed": changed, "by_course": dict(sorted(by_course.items())), "cards_changed": cards_changed,
            "newly_eligible_pdfs": newly_eligible_pdfs(hub_root, config_path), "samples": samples}


def _find_key(names: dict, name: str) -> str | None:
    return next((key for key in names if key.casefold() == name.casefold()), None)


def _write_config(path: Path, data: dict) -> None:
    fd, temporary = tempfile.mkstemp(prefix="hub_config-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def confirm(config_path: Path, name: str, kind: str, alias_of: str | None, replace: bool) -> int:
    if not config_path.is_file():
        print(f"error: {config_path} not found; run against a hub that has {CONFIG_NAME}", file=sys.stderr)
        return 2
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"error: {config_path} is not valid JSON ({exc})", file=sys.stderr)
        return 2
    names = data.setdefault("names", {})
    if alias_of is not None:
        target = _find_key(names, alias_of)
        if kind != "category" or target is None or names[target].get("kind") != "category":
            print(f"error: --alias-of needs kind 'category' and an existing category named {alias_of!r}", file=sys.stderr)
            return 2
        alias_of = target
    entry = {"kind": kind, "source": "owner", **({"alias_of": alias_of} if alias_of else {})}
    existing_key = _find_key(names, name)
    if existing_key is not None:
        existing = names[existing_key]
        if {k: v for k, v in existing.items() if k != "source"} == {k: v for k, v in entry.items() if k != "source"}:
            print(f"{existing_key!r} is already confirmed as {kind}")
            return 0
        if not replace:
            print(f"error: {existing_key!r} was already answered as {existing.get('kind')}"
                  f"{' (alias of ' + existing['alias_of'] + ')' if existing.get('alias_of') else ''}; "
                  "pass --replace to change it", file=sys.stderr)
            return 1
        del names[existing_key]
    names[name] = entry
    _write_config(config_path, data)
    print(f"confirmed {name!r} as {kind}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hub folder-name vocabulary: propose, impact, confirm (no API calls).")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("propose", "impact", "confirm"):
        p = sub.add_parser(command)
        p.add_argument("--hub-root", required=True)
        p.add_argument("--config", help=f"vocabulary file (default: <hub-root>/{CONFIG_NAME})")
        if command == "impact":
            p.add_argument("--limit", type=int, default=20, help="sample paths to print")
        if command == "confirm":
            p.add_argument("name")
            p.add_argument("kind", choices=KINDS)
            p.add_argument("--alias-of")
            p.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    config_path = Path(args.config) if args.config else Path(args.hub_root) / CONFIG_NAME
    if args.command == "propose":
        print(json.dumps(propose_vocabulary(Path(args.hub_root), load_vocabulary(config_path)), indent=2, ensure_ascii=False))
        return 0
    if args.command == "impact":
        print(json.dumps(impact(args.hub_root, config_path, args.limit), indent=2, ensure_ascii=False))
        return 0
    return confirm(config_path, args.name, args.kind, args.alias_of, args.replace)


if __name__ == "__main__":
    raise SystemExit(main())
