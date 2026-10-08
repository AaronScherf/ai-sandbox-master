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
from agent.summary_enhance.llm import UnusableResponse, usage_line

GENERATED_BY = "academic-rag-model/agent/study_guide/draft.py"
INTRO = ("Each section below was written from the source passages planned for that topic; the passages "
         "retrieved for each section are listed beneath it.")
INTRO_STRIPPED = "Each section below was written from the source passages planned for that topic."
_TAG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_RESIDUAL_CITATION_RE = re.compile(r"\bpp?\.\s?\d+(?:\s*[-–]\s*\d+)?\s*[\)\]]")
_PAGE_PIECE = r"[^;()\[\]]*?\bpp?\.\s?\d+(?:\s*[-\u2013]\s*\d+)?[^;()\[\]]*?"
_PAGE_ITEM = rf"\[?{_PAGE_PIECE}\]?"
_PAGE_CITATION_RE = re.compile(rf"\s*[\(\[]\s*{_PAGE_ITEM}(?:\s*;\s*{_PAGE_ITEM})*[\s;,]*[\)\]]")
_EMPTY_PARENS_RE = re.compile(r"[ \t]+\([\s;,]*\)")
_HEADING_RE = re.compile(r"^(#{1,2})\s+(.*?)\s*$")


class DraftError(Exception):
    pass


def output_path(root: str, spec: GuideSpec, tag: str = "") -> Path:
    name = f"{spec.id}.{tag}.md" if tag else f"{spec.id}.md"
    return Path(root) / "academic_notes" / spec.course / "summaries" / name


def validate_tag(tag: str) -> None:
    if tag and not _TAG_RE.match(tag):
        raise DraftError(f"tag {tag!r} may contain only letters, digits, '_' and '-'")


def check_output(root: str, spec: GuideSpec, tag: str = "", force: bool = False) -> Path:
    """The output path, after checking the tag and that nothing would be overwritten."""
    validate_tag(tag)
    out = output_path(root, spec, tag)
    if out.exists() and not force:
        raise DraftError(f"{out} already exists; pass --force to replace it")
    return out


def _save_partial(out: Path, spec: GuideSpec, blocks: list[str]) -> None:
    """A paid call failed midway: keep the sections already generated next to the intended output."""
    done = [b for b in blocks if b]
    if not done:
        return
    try:
        rec = out.with_name(out.stem + ".recovered.md")
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(f"# {spec.title} (partial: generation failed)\n\n" + "\n\n---\n\n".join(done) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"The sections finished before the failure were saved to {rec}")
    except OSError as err:
        print(f"WARNING: could not save a recovery copy: {err}")


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


def strip_citations(text: str, labels: list[str]) -> tuple[str, int]:
    """Remove "(label; label)" and "[label]" groups made only of the section's own passage labels.
    Returns the cleaned text and how many citation-looking parentheticals were left unmatched."""
    labels = sorted({l for l in labels if l}, key=len, reverse=True)
    if labels:
        alt = "|".join(re.escape(l) for l in labels)
        item = rf"\[?(?:{alt})\]?"
        sep = r"\s*(?:[;,]|and)?\s*"
        text = re.sub(rf"\s*[\(\[]\s*{item}(?:{sep}{item})*[\s;,]*[\)\]]", "", text)
    text = _PAGE_CITATION_RE.sub("", text)  # the model often shortens labels, e.g. "(Hansen, p. 268)"
    text = _EMPTY_PARENS_RE.sub("", text)
    return text, len(_RESIDUAL_CITATION_RE.findall(text))


def normalize_headings(answer: str, title: str) -> str:
    """The section already has an H2 title: drop a repeated title line and demote any other H1/H2 the
    model wrote to H3, so a stray H1 cannot swallow the rest of the guide in an outline view."""
    out, fenced = [], False
    for line in answer.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else _HEADING_RE.match(line)
        if m:
            if m.group(2).strip().rstrip(":").lower() == title.strip().rstrip(":").lower():
                continue
            line = "### " + m.group(2)
        out.append(line)
    return "\n".join(out).strip()


def _topic_prompt(spec: GuideSpec, topic: TopicSpec, excerpts: list[tuple[str, str]]) -> str:
    if spec.prompt == "guide_v1":
        return guide_v1_prompt(topic.title, topic.instruction, excerpts, min_words=spec.min_words,
                               construct_examples=topic.construct_examples)
    return tutor_v1_prompt(tutor_v1_question(topic.title, topic.instruction), excerpts)


def _section(spec: GuideSpec, title: str, answer: str, entries: list[PlanEntry],
             topic_sources: dict[str, list[str]], raw: dict[str, str]) -> str:
    raw[title] = answer
    answer = normalize_headings(answer, title)
    if spec.citations == "inline":
        sources = "\n".join(f"- [{e.citation}] `{e.path}`" for e in entries)
        return f"## {title}\n\n{answer}\n\n**Retrieved sources**\n\n{sources}"
    labels = [e.citation for e in entries]
    answer, residual = strip_citations(answer, labels)
    if residual:
        print(f"WARNING: section {title!r}: {residual} citation(s) could not be matched and were left in the text")
    topic_sources[title] = list(dict.fromkeys(labels))
    return f"## {title}\n\n{answer}"


def draft_guide(spec: GuideSpec, plan: Plan, *, root: str, llm, chunks: list[dict] | None = None,
                tag: str = "", force: bool = False, accept_unreviewed: bool = False,
                plan_path: str = "", plan_sha256: str = "", now: str | None = None) -> Path:
    out = check_output(root, spec, tag, force)
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
    topic_sources: dict[str, list[str]] = {}
    raw_answers: dict[str, str] = {}
    try:
        for topic in spec.topics:
            entries = per_topic[topic.title]
            answer = _generate(llm, _topic_prompt(spec, topic, _excerpts(entries, text_by_id)))
            blocks.append(_section(spec, topic.title, answer, entries, topic_sources, raw_answers))
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
                prompt = guide_v1_prompt(cmp_.title, cmp_.instruction, excerpts, min_words=spec.min_words)
            else:
                prompt = tutor_v1_prompt(cmp_.instruction, excerpts)
            blocks.append(_section(spec, cmp_.title, _generate(llm, prompt), chosen, topic_sources, raw_answers))
            for e in chosen:
                used.setdefault(e.chunk_id, e)
    except Exception:
        _save_partial(out, spec, blocks)
        raise

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
        "accept_unreviewed": "true" if accept_unreviewed else "false",
        "generated_at": now or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": json.dumps({"id": spec.id, "file": Path(spec.path).name, "sha256": spec.sha256}),
        "plan": json.dumps({"file": Path(plan_path).name if plan_path else "", "sha256": plan_sha256}),
        "indexer_source_refs": json.dumps(refs, ensure_ascii=False, separators=(",", ":")),
    }
    if spec.citations == "strip":
        front["topic_sources"] = json.dumps(topic_sources, ensure_ascii=False, separators=(",", ":"))
    constructed = [t.title for t in spec.topics if t.construct_examples]
    if constructed:
        front["constructed_examples"] = json.dumps(constructed, ensure_ascii=False)
    usage = getattr(llm, "usage", None)
    if usage:
        front["usage"] = json.dumps(usage, separators=(",", ":"))
        print(usage_line(usage))
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front.items()) + "---\n\n"
    document = frontmatter + f"# {spec.title}\n\n{INTRO if spec.citations == 'inline' else INTRO_STRIPPED}\n\n" + "\n\n---\n\n".join(blocks) + "\n"

    if spec.citations == "strip":
        cited = Path(root) / "academic_notes" / spec.course / "guide_plans" / (out.stem + ".cited.json")
        cited.parent.mkdir(parents=True, exist_ok=True)
        cited.write_text(json.dumps(raw_answers, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    try:
        tmp.write_text(document, encoding="utf-8", newline="\n")
        os.replace(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)
    return out
