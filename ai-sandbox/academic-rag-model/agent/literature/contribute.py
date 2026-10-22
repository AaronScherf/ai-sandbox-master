"""The `annotate` stage: a one-sentence contribution and limitation per paper, each backed by a verified quote."""
from __future__ import annotations

import json
import os
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from .annotation import annotation_of, render_annotation_md
from .cluster import Cluster, topic_dir
from .papers import Paper
from .stage import MAX_CARD_CHARS, Target, _offered_pages, _sha
from .transcript import check_quote, split_pages

STAGE = "annotate"
PARTS = ("contribution", "limitations")

INSTRUCTIONS = """\
Below is what the study record says about one paper, and the pages it cites. Write two short notes about the paper as an
answer, a YAML mapping under `## Result`:

  contribution: {text: "one sentence on what this study adds", quote: "...", locator: 3}
  limitations: {text: "one sentence on a limitation the paper itself states or that its design implies", quote: "...", locator: 4}

Rules:
- `text` is one plain sentence (20 to 400 characters) about this study, not a topic from its literature review.
- `quote` is copied exactly from the offered page text (8 to 300 characters) and `locator` is that page number.
- Use only what the offered pages say."""


def _path(index_root, topic: str, file_id: str) -> Path:
    return topic_dir(index_root, topic) / "annotations" / f"{file_id}.json"


def load_annotations(index_root, topic: str) -> dict:
    folder = topic_dir(index_root, topic) / "annotations"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))} if folder.is_dir() else {}


def make_tasks(target: Target, cluster: Cluster, papers: list[Paper], *, redo: bool = False, limit: int | None = None):
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    done = load_annotations(target.index_root, cluster.name)
    for paper in papers:
        if paper.file_id not in cluster.file_ids:
            continue
        try:
            md = (Path(target.index_root) / paper.path).read_text(encoding="utf-8")
        except OSError as exc:
            skipped[paper.file_id] = f"cannot read the transcript: {exc}"
            continue
        sha = _sha(md)
        if not redo and done.get(paper.file_id, {}).get("transcript_sha") == sha:
            skipped[paper.file_id] = "already annotated (use --redo to annotate again)"
            continue
        ann = annotation_of(target.records, paper.file_id, target.vocabs, cluster.floor)
        record = target.records.read(paper.file_id, "a")
        pages = split_pages(md)
        wanted: set = set()
        for loc in [r["locator"] for r in ann["results"]] + [(record.get("appraisal") or {}).get("locator")]:
            wanted |= {loc} if isinstance(loc, int) else {n for n in (loc or []) if isinstance(n, int)}
        wanted = sorted(n for n in wanted if n in pages)
        if not wanted:
            skipped[paper.file_id] = "none of the cited pages is in the transcript"
            continue
        while sum(len(pages[n]) for n in wanted) > MAX_CARD_CHARS and len(wanted) > 1:
            wanted.pop()
        tasks.append(Task(
            id=f"annotate-{paper.file_id}", stage=STAGE,
            subject={"file_id": paper.file_id, "topic": cluster.name, "transcript_sha": sha},
            instructions=INSTRUCTIONS, context=render_annotation_md(ann, "This paper"),
            passages=[Passage(id=f"P{n}", source=paper.title or paper.file_id, ref=f"page {n}", text=pages[n]) for n in wanted]))
    if limit is not None:
        tasks = tasks[:limit]
    return tasks, skipped


def validate_result(entry: dict, result, target: Target) -> list[str]:
    if not isinstance(result, dict):
        return ["result: must be a mapping with contribution and limitations"]
    pages = _offered_pages(entry)
    out: list[str] = []
    for part in PARTS:
        row = result.get(part)
        if not isinstance(row, dict):
            out.append(f"{part}: must be a mapping with text, quote and locator")
            continue
        text = row.get("text")
        if not isinstance(text, str) or not 20 <= len(text.strip()) <= 400:
            out.append(f"{part}.text: one sentence of 20 to 400 characters")
        if "locator" not in row:
            out.append(f"{part}.locator: required")
        elif problem := check_quote(row.get("quote"), row["locator"], pages):
            out.append(f"{part}.quote: {problem}")
    return out


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    path = _path(target.index_root, s["topic"], s["file_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"file_id": s["file_id"], "transcript_sha": s["transcript_sha"], "run_id": provenance["run"],
            "agent_name": provenance["agent"], **{p: {k: result[p][k] for k in ("text", "quote", "locator")} for p in PARTS}}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return None
