"""The `synthesize` stage: cluster synthesis whose citations and numbers are checked mechanically."""
from __future__ import annotations

import re

STAGE = "synthesize"
_CITE = re.compile(r"P(\d+)(?:\.R(\d+))?")
_RAW_ID = re.compile(r"\bP\d+(?:\.R\d+)?\b")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def assign_ids(file_ids) -> dict:
    return {fid: f"P{n}" for n, fid in enumerate(sorted(file_ids), 1)}


def allowed_for(annotations: dict, ids: dict) -> dict:
    """annotations: file_id -> deterministic annotation (see annotation.annotation_of)."""
    out = {}
    for fid, pid in ids.items():
        ann = annotations[fid]
        out[pid] = {"year": ann["identity"].get("publication_year"),
                    "results": {r["id"]: f"{r['claim']} {r['magnitude']} {r['quote']}" for r in ann["results"]}}
    return out


def _numbers(text: str) -> set:
    return {n.rstrip(".,") for n in _NUM.findall(text or "")}


def check_sections(sections, allowed: dict, must_cover: list) -> list[str]:
    if not isinstance(sections, list) or not sections:
        return ["sections: must be a non-empty list of {heading, paragraphs}"]
    out: list[str] = []
    cited: set = set()
    for si, sec in enumerate(sections):
        where = f"sections[{si}]"
        if not isinstance(sec, dict) or not isinstance(sec.get("heading"), str) or not isinstance(sec.get("paragraphs"), list) or not sec["paragraphs"]:
            out.append(f"{where}: must be a mapping with a heading and a non-empty list of paragraphs")
            continue
        for pi, para in enumerate(sec["paragraphs"]):
            path = f"{where}.paragraphs[{pi}]"
            if not isinstance(para, dict) or not isinstance(para.get("text"), str) or not isinstance(para.get("cites"), list):
                out.append(f"{path}: must be a mapping with text and a cites list")
                continue
            text = para["text"]
            if len(text.strip()) < 30:
                out.append(f"{path}.text: at least 30 characters")
            if raw := _RAW_ID.search(text):
                out.append(f"{path}.text: contains the raw id {raw.group()}; put ids in cites, not in the sentence")
            if not para["cites"]:
                out.append(f"{path}.cites: every paragraph needs at least one citation")
                continue
            evidence: set = set()
            bad = False
            for c in para["cites"]:
                m = _CITE.fullmatch(c) if isinstance(c, str) else None
                paper = allowed.get(f"P{m.group(1)}") if m else None
                if paper is None:
                    out.append(f"{path}.cites: {c!r} is not a paper of this card")
                    bad = True
                    continue
                cited.add(f"P{m.group(1)}")
                if m.group(2) is None:
                    texts = list(paper["results"].values())
                else:
                    rid = f"R{m.group(2)}"
                    if rid not in paper["results"]:
                        out.append(f"{path}.cites: {c} is not a result of that paper")
                        bad = True
                        continue
                    texts = [paper["results"][rid]]
                for t in texts:
                    evidence |= _numbers(t)
                if paper.get("year"):
                    evidence.add(str(paper["year"]))
            if bad:
                continue
            for n in sorted(_numbers(text) - evidence):
                out.append(f"{path}.text: the number {n} does not appear in any result you cite")
    for pid in must_cover:
        if pid not in cited:
            out.append(f"{pid} is not cited anywhere; every paper on this card must appear")
    return out
