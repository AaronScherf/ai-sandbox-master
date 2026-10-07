# agent/study_guide/draft.py
"""Draft stage: one grounded, cited synthesis per topic from the plan's accepted passages, written
as a `derived_summary` (frontmatter `indexer_source_refs`) that summary_enhance can consume."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from agent.study_guide.plan import Plan, PlanEntry, accepted
from agent.study_guide.prompts import guide_v1_prompt, tutor_v1_prompt, tutor_v1_question
from agent.study_guide.spec import GuideSpec, TopicSpec
from agent.summary_enhance.llm import UnusableResponse

GENERATED_BY = "academic-rag-model/agent/study_guide/draft.py"
INTRO = ("Each section below was written from the source passages planned for that topic; the passages "
         "retrieved for each section are listed beneath it.")
_TAG_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class DraftError(Exception):
    pass


def output_path(root: str, spec: GuideSpec, tag: str = "") -> Path:
    name = f"{spec.id}.{tag}.md" if tag else f"{spec.id}.md"
    return Path(root) / "academic_notes" / spec.course / "summaries" / name


def _excerpts(entries: list[PlanEntry], text_by_id: dict[str, str]) -> list[tuple[str, str]]:
    missing = [e.chunk_id for e in entries if e.chunk_id not in text_by_id]
    if missing:
        raise DraftError(f"passages missing from the chunk store (re-run plan): {', '.join(missing)}")
    return [(e.citation, text_by_id[e.chunk_id]) for e in entries]


def _generate(llm, prompt: str) -> str:
    for _ in range(2):
        try:
            text = (llm.generate_text(prompt) or "").strip()
        except UnusableResponse:
            continue
        if text:
            return text
    raise DraftError("the model returned no usable text twice")


def _topic_prompt(spec: GuideSpec, topic: TopicSpec, excerpts: list[tuple[str, str]]) -> str:
    if spec.prompt == "guide_v1":
        return guide_v1_prompt(topic.title, topic.instruction, excerpts)
    return tutor_v1_prompt(tutor_v1_question(topic.title, topic.instruction), excerpts)


def _section(title: str, answer: str, entries: list[PlanEntry]) -> str:
    sources = "\n".join(f"- [{e.citation}] `{e.path}`" for e in entries)
    return f"## {title}\n\n{answer}\n\n**Retrieved sources**\n\n{sources}"


def draft_guide(spec: GuideSpec, plan: Plan, *, root: str, llm, chunks: list[dict] | None = None,
                tag: str = "", force: bool = False, accept_unreviewed: bool = False,
                plan_path: str = "", plan_sha256: str = "", now: str | None = None) -> Path:
    if tag and not _TAG_RE.match(tag):
        raise DraftError(f"tag {tag!r} may contain only letters, digits, '_' and '-'")
    out = output_path(root, spec, tag)
    if out.exists() and not force:
        raise DraftError(f"{out} already exists; pass --force to replace it")
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    text_by_id = {c["chunk_id"]: c["text"] for c in chunks}

    # resolve and validate every topic's passages before spending any API call
    per_topic: dict[str, list[PlanEntry]] = {}
    for topic in spec.topics:
        per_topic[topic.title] = accepted(plan, topic.title, accept_unreviewed=accept_unreviewed)
        _excerpts(per_topic[topic.title], text_by_id)

    blocks = [f"## {n.heading}\n\n{n.body}" for n in spec.notes]
    used: dict[str, PlanEntry] = {}
    for topic in spec.topics:
        entries = per_topic[topic.title]
        answer = _generate(llm, _topic_prompt(spec, topic, _excerpts(entries, text_by_id)))
        blocks.append(_section(topic.title, answer, entries))
        for e in entries:
            used.setdefault(e.chunk_id, e)
    for cmp_ in spec.comparisons:
        chosen: list[PlanEntry] = []
        seen: set[str] = set()
        for title in cmp_.from_topics:
            for e in per_topic[title][:cmp_.take]:
                if e.chunk_id not in seen:
                    seen.add(e.chunk_id)
                    chosen.append(e)
        excerpts = _excerpts(chosen, text_by_id)
        if spec.prompt == "guide_v1":
            prompt = guide_v1_prompt(cmp_.title, cmp_.instruction, excerpts)
        else:
            prompt = tutor_v1_prompt(cmp_.instruction, excerpts)
        blocks.append(_section(cmp_.title, _generate(llm, prompt), chosen))
        for e in chosen:
            used.setdefault(e.chunk_id, e)

    refs = [{"path": e.path, "file_id": e.file_id, "chunk_id": e.chunk_id, "citation": e.citation}
            for e in used.values()]
    front = {
        "title": json.dumps(spec.title, ensure_ascii=False),
        "llm_generated": "true",
        "content_kind": "derived_summary",
        "generated_by": GENERATED_BY,
        "draft_model": json.dumps(getattr(llm, "model", spec.draft_model)),
        "prompt_id": json.dumps(spec.prompt),
        "label_match": json.dumps(spec.label_match),
        "generated_at": now or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": json.dumps({"id": spec.id, "file": Path(spec.path).name, "sha256": spec.sha256}),
        "plan": json.dumps({"file": Path(plan_path).name if plan_path else "", "sha256": plan_sha256}),
        "indexer_source_refs": json.dumps(refs, ensure_ascii=False, separators=(",", ":")),
    }
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front.items()) + "---\n\n"
    document = frontmatter + f"# {spec.title}\n\n{INTRO}\n\n" + "\n\n---\n\n".join(blocks) + "\n"

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    try:
        tmp.write_text(document, encoding="utf-8", newline="\n")
        os.replace(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)
    return out
