"""The hand-checked gold set and the evaluation summary computed against it. Aggregates only; no paper text."""
from __future__ import annotations

from pathlib import Path

import yaml

from . import schema
from .transcript import normalize

EXPECT_KEYS = set(schema.FACETS) | {"countries"}
DEFAULT_PATH = Path(__file__).resolve().parent / "gold" / "gold_set.yaml"


def load_gold(path) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    problems: list[str] = []
    if not isinstance(data, dict):
        raise ValueError("the gold file must be a mapping with version: 1 and papers")
    if data.get("version") != 1:
        problems.append("version: must be 1")
    papers = data.get("papers")
    if not isinstance(papers, list):
        raise ValueError("; ".join(problems + ["papers: must be a list"]))
    for i, p in enumerate(papers):
        where = f"papers[{i}]"
        if not isinstance(p, dict):
            problems.append(f"{where}: must be a mapping with file_id and expect")
            continue
        if not p.get("file_id"):
            problems.append(f"{where}: file_id is required")
        expect = p.get("expect") or {}
        for k, v in expect.items():
            if k not in EXPECT_KEYS:
                problems.append(f"{where}.expect: unknown facet {k!r}")
            elif not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                problems.append(f"{where}.expect.{k}: must be a list of text")
    if problems:
        raise ValueError("; ".join(problems))
    return papers


def _found_keys(record: dict, facet: str) -> set[str]:
    if facet == "countries":
        return set(record["core"].get("geography", {}).get("countries", []))
    return {f["vocab_id"] if f.get("vocab_id") else "v:" + normalize(f["value"]) for f in record["core"].get(facet, [])}


def _expected_keys(items: list[str], facet: str, vocabs: dict) -> set[str]:
    if facet == "countries":
        return set(items)
    vocab = vocabs.get(schema.FACETS[facet])
    out = set()
    for item in items:
        if vocab is not None and vocab.contains(item):
            out.add(item)
        elif vocab is not None and (term := vocab.find(item)) is not None:
            out.add(term.id)
        else:
            out.add("v:" + normalize(item))
    return out


def score_record(record: dict, expect: dict, vocabs: dict) -> dict[str, dict]:
    out = {}
    for facet, items in expect.items():
        want, got = _expected_keys(items, facet, vocabs), _found_keys(record, facet)
        out[facet] = {"expected": len(want), "found": len(got), "matched": len(want & got)}
    return out


def _ratio(n: float, d: float) -> float:
    return n / d if d else 0.0


def summarize(per_paper: dict[str, dict | None], *, expects: dict[str, dict], proposals: list, records: int,
              manifests: list[dict], double: dict) -> dict:
    matched = found = expected = 0
    missing: list[str] = []
    for fid, scores in per_paper.items():
        if scores is None:
            missing.append(fid)
            expected += sum(len(v) for v in expects.get(fid, {}).values())
            continue
        for s in scores.values():
            matched += s["matched"]
            found += s["found"]
            expected += s["expected"]
    cards = [t for m in manifests for t in m.get("tasks", [])]
    bounced = sum(1 for t in cards if t.get("attempts", 0) > 0)
    compared = double.get("compared", 0)
    return {
        "facet_precision": _ratio(matched, found), "facet_recall": _ratio(matched, expected),
        "proposal_rate": _ratio(len(proposals), records), "bounce_rate": _ratio(bounced, len(cards)),
        "double_pass_agreement": (double["agreed"] / compared) if compared else None,
        "papers_missing_a_record": missing, "papers_scored": len(per_paper),
    }
