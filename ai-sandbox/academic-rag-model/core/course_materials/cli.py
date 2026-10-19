"""Classify a course's materials, list the files that need the owner's eye, and record decisions.

  python -m core.course_materials.cli --hub-root <academic-hub> --course <course> classify
  python -m core.course_materials.cli --hub-root <academic-hub> --course <course> flagged
  python -m core.course_materials.cli --hub-root <academic-hub> --course <course> decide <path> --role instructor
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from .classify import classify_course, load_catalog, record_decision
from .model import FORMATS, ROLES, Catalog, CatalogError


def _why(evidence: list) -> str:
    return "; ".join(f"{signal} {field_}={value} +{weight}" for signal, field_, value, weight in evidence if weight)


def summarize(catalog: Catalog) -> str:
    lines = [f"{catalog.course}: {len(catalog.materials)} materials"]
    for role in ROLES:
        group = [m for m in catalog.materials if m.role == role]
        if group:
            formats = Counter(m.format for m in group)
            lines.append(f"  {role}: {len(group)} (" + ", ".join(f"{k} {v}" for k, v in sorted(formats.items())) + ")")
    for label in catalog.offerings():
        lines.append(f"  offering {label}: {sum(m.offering == label for m in catalog.materials)}")
    flagged = catalog.flagged()
    lines.append(f"flagged ({len(flagged)}):")
    lines += [f"  {m.path} -> {m.role}/{m.format} (margin {m.confidence:g}): {_why(m.evidence)}" for m in flagged]
    if catalog.unknown_decisions:
        lines.append(f"decisions for files that no longer exist ({len(catalog.unknown_decisions)}, kept):")
        lines += [f"  {p}" for p in catalog.unknown_decisions]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="course_materials", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hub-root", required=True, help="the academic-hub folder")
    p.add_argument("--course", required=True, help="course folder name under academic_notes/")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("classify", help="build or refresh the catalog and print a summary")
    sub.add_parser("flagged", help="print the flagged materials as JSON rows (for the review page)")
    d = sub.add_parser("decide", help="record the owner's decision for one file or folder")
    d.add_argument("path", help="hub-relative or absolute path; a folder applies to everything under it")
    d.add_argument("--role", choices=ROLES)
    d.add_argument("--format", choices=FORMATS)
    d.add_argument("--offering")
    d.add_argument("--book")
    d.add_argument("--date")
    d.add_argument("--exclude", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "classify":
            print(summarize(classify_course(args.hub_root, args.course)))
        elif args.cmd == "flagged":
            rows = [{"path": m.path, "role": m.role, "format": m.format, "offering": m.offering, "book": m.book,
                     "confidence": m.confidence, "evidence": m.evidence}
                    for m in load_catalog(args.hub_root, args.course).flagged()]
            print(json.dumps(rows, indent=1, ensure_ascii=False))
        else:
            key = record_decision(args.hub_root, args.course, args.path, role=args.role, format=args.format,
                                  offering=args.offering, book=args.book, date=args.date, exclude=args.exclude)
            print(f"recorded decision for {key}")
    except (CatalogError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
