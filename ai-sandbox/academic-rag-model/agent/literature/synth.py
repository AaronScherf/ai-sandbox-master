"""The `synthesize` stage: cluster synthesis whose citations and numbers are checked mechanically."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from core.agent_tasks.tasks import Task

from .annotation import annotation_of, render_annotation_md
from .cluster import Cluster, topic_dir
from .contribute import load_annotations
from .stage import Target

STAGE = "synthesize"
_CITE = re.compile(r"P(\d+)(?:\.R(\d+))?")
_RAW_ID = re.compile(r"\bP\d+(?:\.R\d+)?\b")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
# Evaluative wording only: effect_direction is the sign of the welfare effect, so "reduced poverty" and "reduced yields"
# point opposite ways and the plain increase/decrease words cannot be checked against it.
_GOOD = re.compile(r"\b(?:improv\w*|benefit\w*|beneficial|enhanc\w*|strengthen\w*|favou?rabl\w*|positive\w*)\b", re.I)
_BAD = re.compile(r"\b(?:worsen\w*|harm\w*|adverse\w*|undermin\w*|deteriorat\w*|degrad\w*|detriment\w*|damag\w*|negative\w*)\b", re.I)
_NEGATION = {"not", "no", "never", "without", "little", "limited", "hardly", "fail", "fails", "failed", "failing"}
_MITIGATION = _NEGATION | {"mitigate", "mitigates", "mitigated", "mitigating", "reduce", "reduces", "reduced", "reducing",
                           "prevent", "prevents", "prevented", "avoid", "avoids", "avoided", "offset", "offsets", "cushion",
                           "cushions", "buffer", "buffers", "alleviate", "alleviates", "alleviated", "protect", "protects",
                           "protected", "against", "counter", "counters", "address", "addresses", "addressed"}
_SUPPORTS_GOOD = {"positive", "mixed"}
_SUPPORTS_BAD = {"negative", "mixed"}


def assign_ids(file_ids) -> dict:
    return {fid: f"P{n}" for n, fid in enumerate(sorted(file_ids), 1)}


def allowed_for(annotations: dict, ids: dict) -> dict:
    """annotations: file_id -> deterministic annotation (see annotation.annotation_of)."""
    out = {}
    for fid, pid in ids.items():
        ann = annotations[fid]
        out[pid] = {"year": ann["identity"].get("publication_year"),
                    "results": {r["id"]: f"{r['claim']} {r['magnitude']} {r['quote']}" for r in ann["results"]},
                    "directions": {r["id"]: r.get("effect_direction") for r in ann["results"]}}
    return out


def _numbers(text: str) -> set:
    return {n.rstrip(".,") for n in _NUM.findall(text or "")}


def _flagged(pattern, exempt: set, text: str) -> list[str]:
    """Evaluative words in the text, leaving out one with a negation or mitigation word in the three words before it."""
    out = []
    for m in pattern.finditer(text):
        before = re.findall(r"[A-Za-z']+", text[:m.start()])[-3:]
        if not {w.lower() for w in before} & exempt:
            out.append(m.group().lower())
    return out


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
            directions: set = set()
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
                    directions |= set((paper.get("directions") or {}).values())
                else:
                    rid = f"R{m.group(2)}"
                    if rid not in paper["results"]:
                        out.append(f"{path}.cites: {c} is not a result of that paper")
                        bad = True
                        continue
                    texts = [paper["results"][rid]]
                    directions.add((paper.get("directions") or {}).get(rid))
                for t in texts:
                    evidence |= _numbers(t)
                if paper.get("year"):
                    evidence.add(str(paper["year"]))
            if bad:
                continue
            for n in sorted(_numbers(text) - evidence):
                out.append(f"{path}.text: the number {n} does not appear in any result you cite")
            known = directions - {None, "not_reported"}
            if known:
                shown = ", ".join(sorted(known))
                for word in _flagged(_GOOD, _NEGATION, text):
                    if not known & _SUPPORTS_GOOD:
                        out.append(f"{path}.text: '{word}' implies a positive result, but the results you cite are {shown}; "
                                   "cite a result that shows it or reword")
                for word in _flagged(_BAD, _MITIGATION, text):
                    if not known & _SUPPORTS_BAD:
                        out.append(f"{path}.text: '{word}' implies a negative result, but the results you cite are {shown}; "
                                   "cite a result that shows it or reword")
    for pid in must_cover:
        if pid not in cited:
            out.append(f"{pid} is not cited anywhere; every paper on this card must appear")
    return out


MAX_PAPERS = 20

INSTRUCTIONS = """Write a short literature review of the papers below as a YAML mapping under `## Result`:

  sections:
    - heading: "What the studies find"
      paragraphs:
        - text: "Two or three sentences in plain prose."
          cites: [P1.R1, P3]

Rules:
- Every paragraph needs `cites`: paper ids (P3) or result ids (P3.R2) from this card. Do not write ids inside `text`.
- Any digit you write must appear in the claim, magnitude or quote of a result you cite (cite P3 to cover all of its results).
- Write counts of studies in words. Do not state a finding that is not in the lines below.
- Every paper on this card must be cited at least once.
- Group papers by what they find or how they were studied, and say where they disagree."""

MERGE_NOTE = """
This card joins several partial reviews of one literature. Keep their findings and citations, remove repetition, and
order the sections so the whole reads as one review. You may reuse the cites shown under each paragraph."""


def _out_path(index_root, topic: str, task_id: str) -> Path:
    return topic_dir(index_root, topic) / "synthesis" / f"{task_id}.json"


def load_outputs(index_root, topic: str) -> dict:
    folder = topic_dir(index_root, topic) / "synthesis"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))} if folder.is_dir() else {}


def chunks(cluster: Cluster, annotations: dict, max_papers: int = MAX_PAPERS) -> list[list]:
    def first_country(fid):
        countries = [f["label"] for f in annotations[fid]["facts"].get("countries", [])]
        return (countries[0] if countries else "~", fid)
    ordered = sorted(cluster.file_ids, key=first_country)
    n = max(1, -(-len(ordered) // max_papers))
    size = -(-len(ordered) // n)
    return [ordered[i:i + size] for i in range(0, len(ordered), size)]


def _paper_block(ann: dict, note: dict, pid: str) -> str:
    text = render_annotation_md(ann, pid)
    if note:
        text += f"\n  contribution: {note['contribution']['text']}\n  limitation: {note['limitations']['text']}"
    return text


def make_tasks(target: Target, cluster: Cluster, *, max_papers: int = MAX_PAPERS, merge: bool = False):
    notes = load_annotations(target.index_root, cluster.name)
    missing = [f for f in cluster.file_ids if f not in notes]
    if missing:
        raise ValueError("annotate these papers first (run `annotate`): " + ", ".join(missing))
    anns = {f: annotation_of(target.records, f, target.vocabs, cluster.floor, target.proposals) for f in cluster.file_ids}
    ids = assign_ids(cluster.file_ids)
    parts = chunks(cluster, anns, max_papers)
    if len(parts) == 1:
        merge = False
    elif merge:
        outputs = load_outputs(target.index_root, cluster.name)
        absent = [f"synth-c{i}" for i in range(1, len(parts) + 1) if f"synth-c{i}" not in outputs]
        if absent:
            raise ValueError("answer and submit these chunk cards first: " + ", ".join(absent))
    tasks: list[Task] = []
    jobs = [("synth-final", cluster.file_ids)] if merge or len(parts) == 1 else [(f"synth-c{i}", p) for i, p in enumerate(parts, 1)]
    for task_id, members in jobs:
        blocks = [_paper_block(anns[f], notes[f], ids[f]) for f in members]
        context = "\n\n".join(blocks)
        if merge:
            outputs = load_outputs(target.index_root, cluster.name)
            drafts = []
            for i in range(1, len(parts) + 1):
                for sec in outputs[f"synth-c{i}"]["sections"]:
                    for para in sec["paragraphs"]:
                        drafts.append(f"[{sec['heading']}] {para['text']} (cites: {', '.join(para['cites'])})")
            context = "Partial reviews to join:\n" + "\n".join(drafts) + "\n\nPapers and results:\n\n" + context
        tasks.append(Task(
            id=task_id, stage=STAGE,
            subject={"topic": cluster.name, "task": task_id,
                     "allowed": allowed_for(anns, {f: ids[f] for f in members}),
                     "must_cover": [ids[f] for f in members]},
            instructions=INSTRUCTIONS + (MERGE_NOTE if merge else ""), context=context))
    return tasks, {}


def validate_result(entry: dict, result, target: Target) -> list[str]:
    if not isinstance(result, dict):
        return ["result: must be a mapping with a `sections` list"]
    s = entry["subject"]
    return check_sections(result.get("sections"), s["allowed"], s["must_cover"])


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    path = _out_path(target.index_root, s["topic"], s["task"])
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"task": s["task"], "run_id": provenance["run"], "agent_name": provenance["agent"], "sections": result["sections"]}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return None
