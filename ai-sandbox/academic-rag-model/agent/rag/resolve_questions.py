"""
resolve_questions.py
Answers the `[Question]` tags in Excalidraw notes: grounded in the course
corpus when it can be (the same key-term + retrieval + grounded check /hint
uses), clearly labeled when it can't. Answers go to a per-note sidecar; the
.rag.md gets resolved markers (core/indexer/questions.py).

Spec: docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent.rag.rag_agent import _extract_key_terms, _term_match_count, retrieve_passages
from core.env.excalidraw_text import QUESTION_TAG_RE, split_labeled_segments
from core.env.frontmatter import parse_frontmatter
from core.env.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from core.indexer.index_card import derive_course, load_shard
from core.indexer.questions import (
    Entry,
    Tag,
    apply_markers,
    find_tags,
    rag_path_for,
    read_sidecar,
    sidecar_path_for,
    write_sidecar,
)

RESOLVER_MODEL = "gemini-3.6-flash"  # the stronger tier: answers are persisted and indexed
_CONTEXT_CHARS = 1500
_NEIGHBOR_CHARS = 800
_STORED_CONTEXT_CHARS = 600

_ANSWER_PROMPT_TEMPLATE = """A student wrote this open question in the margin of their lecture notes. \
Explain the answer so the student can understand it, with the reasoning spelled out. Use LaTeX \
($...$ / $$...$$) for math.

The student's handwriting around the question:
{context}

{slides_block}{excerpts_block}Open question: {question}

{grounding_instruction}
Respond with ONLY the explanation in markdown -- no preamble, no code fence."""

_GROUNDED_INSTRUCTION = (
    "Base the explanation on the course excerpts above and do not claim anything they contradict."
)
_UNGROUNDED_INSTRUCTION = (
    "No course material supports this question. Answer from general knowledge and say plainly "
    "where you are unsure."
)


def question_context(raw_body: str, ordinal: int) -> tuple[str, list[str]]:
    """The text around the ordinal-th tag of a raw transcript body (frontmatter
    already stripped): a window of its own block, plus the adjacent slide
    blocks. Splitting preserves tag order, so counting tags across segments in
    order finds the same tag the sidecar's ordinal refers to."""
    segments = split_labeled_segments(raw_body)
    seen = 0
    for idx, (_label, text) in enumerate(segments):
        matches = list(QUESTION_TAG_RE.finditer(text))
        if seen + len(matches) >= ordinal:
            match = matches[ordinal - seen - 1]
            half = _CONTEXT_CHARS // 2
            excerpt = text[max(0, match.start() - half): min(len(text), match.end() + half)].strip()
            neighbors = [
                segments[j][1][:_NEIGHBOR_CHARS]
                for j in (idx - 1, idx + 1)
                if 0 <= j < len(segments) and segments[j][0] == "Slide"
            ]
            return excerpt, neighbors
        seen += len(matches)
    return "", []


def build_answer_prompt(question: str, context: str, neighbor_slides: list[str], passages: list | None) -> str:
    slides_block = ""
    if neighbor_slides:
        slides_block = "Lecture slide content beside the question:\n" + "\n\n---\n\n".join(neighbor_slides) + "\n\n"
    excerpts_block = ""
    if passages:
        excerpts = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
        excerpts_block = f"Course excerpts:\n{excerpts}\n\n"
    return _ANSWER_PROMPT_TEMPLATE.format(
        context=context, slides_block=slides_block, excerpts_block=excerpts_block, question=question,
        grounding_instruction=_GROUNDED_INSTRUCTION if passages else _UNGROUNDED_INSTRUCTION,
    )


def resolve_question(
    tag: Tag, context: str, neighbors: list[str], *, client, roots: list[str], course: str | None,
    model: str, exclude_basenames: set[str], retrieve=retrieve_passages, extract=_extract_key_terms,
) -> Entry:
    """One question -> one Entry. Raises on any failure (including an empty
    answer) so the caller records nothing for it. Grounded means a passage
    survived own-note exclusion and (no key terms, or one mentions a key
    term) -- /hint's check, plus a guard so an empty retrieval can never count
    as grounded."""
    key_terms = extract(f"{tag.text}\n{context}", client)
    found = retrieve(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
    passages = [p for p in found if os.path.basename(p.path) not in exclude_basenames]
    grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
    prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
    response = call_with_retries(lambda: client.models.generate_content(
        model=model, contents=prompt, config={"temperature": 0.2},
    ))
    answer = (response.text or "").strip()
    if not answer:
        raise ValueError(f"model returned an empty answer for {tag.qid}")
    return Entry(
        qid=tag.qid, question=tag.text, grounded=grounded, model=model,
        resolved_at=datetime.now(timezone.utc).isoformat(),
        context=" ".join(context.split())[:_STORED_CONTEXT_CHARS], answer=answer,
        sources=[f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else [],
    )


_DEFAULT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub"))


@dataclass
class NoteResult:
    resolved: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)


def _read_body(raw_path: str) -> str:
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]


def _rel(hub: str, path: str) -> str:
    return os.path.relpath(path, hub).replace(os.sep, "/")


def _note_card(hub: str, raw_path: str) -> dict | None:
    rel_rag = _rel(hub, rag_path_for(raw_path))
    for card in load_shard(hub, derive_course(rel_rag)):
        if card.get("path") == rel_rag:
            return card
    return None


def discover_notes(hub: str, course: str | None = None, note: str | None = None) -> list[str]:
    """Raw transcripts (`processed_outputs/*.excalidraw.md`) under academic_notes/
    that contain at least one tag, optionally limited to a course or to
    filenames containing `note`."""
    found = []
    for dirpath, _dirs, files in os.walk(os.path.join(hub, "academic_notes")):
        if os.path.basename(dirpath) != "processed_outputs":
            continue
        if course and derive_course(_rel(hub, dirpath)) != course:
            continue
        for name in sorted(files):
            if not name.endswith(".excalidraw.md") or (note and note not in name):
                continue
            raw_path = os.path.join(dirpath, name)
            if find_tags(_read_body(raw_path)):
                found.append(raw_path)
    return sorted(found)


def resolve_note(
    raw_path: str, hub: str, client, roots: list[str], model: str = RESOLVER_MODEL, redo: bool = False,
    budget: int | None = None, retrieve=retrieve_passages, extract=_extract_key_terms,
) -> NoteResult:
    """Resolves a note's unanswered questions into its sidecar, then applies
    markers. A question that fails records nothing and is retried next run."""
    body = _read_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    by_id = {e.qid: e for e in entries}
    card = _note_card(hub, raw_path)
    course = derive_course(_rel(hub, raw_path))
    exclude = {os.path.basename(rag_path), os.path.basename(sidecar)}

    result = NoteResult()
    for tag in tags:
        if tag.qid in by_id and not redo:
            result.skipped += 1
            continue
        if budget is not None and result.resolved >= budget:
            break
        context, neighbors = question_context(body, tag.ordinal)
        try:
            by_id[tag.qid] = resolve_question(
                tag, context, neighbors, client=client, roots=roots, course=course, model=model,
                exclude_basenames=exclude, retrieve=retrieve, extract=extract,
            )
            result.resolved += 1
        except Exception as err:
            print(f"WARNING: {tag.qid} ({tag.text[:60]!r}) failed: {err}")
            result.failed.append(tag.qid)

    if result.resolved:
        in_order = [by_id[t.qid] for t in tags if t.qid in by_id]
        leftover = [e for qid, e in by_id.items() if qid not in {t.qid for t in tags}]
        ordered = in_order + leftover
        fields = {
            **fields,
            "source_excalidraw": _rel(hub, raw_path),
            "source_note_file_id": card["file_id"] if card else "",
            "resolver_model": model,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "questions": str(len(ordered)),
        }
        write_sidecar(sidecar, fields, ordered)
    apply_markers(raw_path, rag_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer the [Question] tags in Excalidraw notes.")
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Corpus root (academic-hub).")
    parser.add_argument("--course", default=None)
    parser.add_argument("--note", default=None, help="Only raw transcripts whose filename contains this text.")
    parser.add_argument("--dry-run", action="store_true", help="List questions; no API calls, no writes.")
    parser.add_argument("--redo", action="store_true", help="Re-answer questions that already have an entry.")
    parser.add_argument("--model", default=RESOLVER_MODEL)
    parser.add_argument("--max-questions", type=int, default=None)
    args = parser.parse_args(argv)

    hub = os.path.abspath(args.root)
    jobs = []
    for raw_path in discover_notes(hub, args.course, args.note):
        card = _note_card(hub, raw_path)
        if card and card.get("subset_of"):
            print(f"skip (subset of another note): {os.path.basename(raw_path)}")
            continue
        answered = {e.qid for e in read_sidecar(sidecar_path_for(raw_path))[1]}
        pending = [t for t in find_tags(_read_body(raw_path)) if args.redo or t.qid not in answered]
        jobs.append((raw_path, pending))

    total = sum(len(p) for _, p in jobs)
    print(f"{len(jobs)} note(s) with [Question] tags, {total} question(s) to resolve")
    if args.dry_run:
        for raw_path, pending in jobs:
            print(f"  {os.path.basename(raw_path)}")
            for tag in pending:
                print(f"    {tag.qid}: {tag.text}")
        return 0
    if total == 0:
        return 0

    load_dotenv_override()
    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        return 1
    remaining = args.max_questions
    failed: list[str] = []
    for raw_path, _pending in jobs:
        if remaining is not None and remaining <= 0:
            print("stopping: --max-questions budget used")
            break
        print(f"Resolving {os.path.basename(raw_path)}...")
        result = resolve_note(
            raw_path, hub, client, [hub], model=args.model, redo=args.redo, budget=remaining,
        )
        failed.extend(result.failed)
        if remaining is not None:
            remaining -= result.resolved
    print(f"done; failed: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
