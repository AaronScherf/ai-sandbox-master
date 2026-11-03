"""Enrich local taxonomy YAML from a locally saved portal JavaScript bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

import yaml


def parse_array(bundle: str, anchor: str) -> list[dict]:
    start = bundle.find("[{" + anchor + ":")
    if start < 0:
        raise ValueError(f"array not found: {anchor}")
    depth = 0
    quoted = escaped = False
    for end in range(start, len(bundle)):
        char = bundle[end]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                break
    else:
        raise ValueError(f"unterminated array: {anchor}")
    raw = bundle[start:end + 1]
    raw = re.sub(r'([{,])([A-Za-z_][A-Za-z0-9_]*):', r'\1"\2":', raw)
    raw = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: "\\u00" + m[1], raw)
    raw = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)
    return json.loads(raw)


def _path(term: dict, by_id: dict[str, dict]) -> tuple[str, ...]:
    labels = [term["label"]]
    parent = term.get("parent")
    while parent:
        node = by_id[parent]
        labels.append(node["label"])
        parent = node.get("parent")
    return tuple(reversed(labels))


def enrich(vocab_dir: Path, bundle: str, out: Path, file_date: str) -> dict:
    """Write enriched copies to out and return per-vocabulary match reports."""
    out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(bundle.encode("utf-8")).hexdigest()[:12]
    reports = {}
    for name, sector, group, leaf in (
        ("intervention", "InterventionSector", "InterventionGroup", "DisaggregatedIntervention"),
        ("outcome", "OutcomeSector", "OutcomeGroup", "DisaggregatedOutcome"),
    ):
        source = vocab_dir / f"{name}.yaml"
        if not source.exists():
            continue
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
        by_id = {t["id"]: t for t in data["terms"]}
        full = {}
        short = {}
        for term in data["terms"]:
            path = _path(term, by_id)
            full.setdefault(path, []).append(term)
            if len(path) >= 2:
                short.setdefault(path[-2:], []).append(term)
        report = {"matched": [], "unmatched": [], "ambiguous": [], "differ": []}
        touched = set()
        for row in parse_array(bundle, sector):
            path = tuple(row.get(k, "") for k in (sector, "BroadGroup", group, leaf))
            candidates = full.get(path) or short.get(path[-2:], [])
            if len(candidates) != 1:
                if len(candidates) > 1:
                    report["ambiguous"].extend(t["id"] for t in candidates)
                continue
            term = candidates[0]
            touched.add(term["id"])
            report["matched"].append(term["id"])
            for target, definition in ((term, row.get("Definition")),
                                       (by_id.get(term.get("parent")), row.get("Definition1"))):
                if target is None or not definition or not definition.strip():
                    continue
                definition = definition.strip()
                if target.get("definition") and target["definition"] != definition:
                    report["differ"].append(target["id"])
                elif not target.get("definition"):
                    target["definition"] = definition
        report["unmatched"] = [t["id"] for t in data["terms"]
                                if t["id"] not in touched and not any(x.get("parent") == t["id"] for x in data["terms"])]
        for key in report:
            report[key] = sorted(set(report[key]))
        data["version"] += 1
        data["source"] += f"; bundle {file_date} sha256:{digest}"
        dest = out / source.name
        temp = dest.with_suffix(".yaml.tmp")
        temp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10**6), encoding="utf-8")
        temp.replace(dest)
        reports[name] = report
    return reports


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocab-dir", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    content = args.bundle.read_text(encoding="utf-8", errors="replace")
    stamp = date.fromtimestamp(args.bundle.stat().st_mtime).isoformat()
    for name, report in enrich(args.vocab_dir, content, args.out or args.vocab_dir, stamp).items():
        print(name)
        for key, values in report.items():
            print(f"  {key}: {len(values)}" + (f" ({', '.join(values)})" if key != "matched" and values else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
