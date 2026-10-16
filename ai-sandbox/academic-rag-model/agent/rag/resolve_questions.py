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
from typing import TYPE_CHECKING

from agent.rag.rag_agent import _KEY_TERM_PROMPT_TEMPLATE, _extract_key_terms, _term_match_count, retrieve_passages

if TYPE_CHECKING:
    from agent.rag.resolve_questions_driver import QuestionResolverDriver
from core.env.excalidraw_text import QUESTION_TAG_RE, split_labeled_segments
from core.env.frontmatter import parse_frontmatter
from core.env.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from core.indexer.index_card import compute_content_hash, derive_course, load_shard, update_card_content_hash
from core.indexer.questions import (
    Entry,
    Tag,
    apply_markers,
    find_tags,
    rag_path_for,
    read_sidecar,
    rekey_entries,
    sidecar_path_for,
    write_sidecar,
)

def keyterms_cache_path_for(raw_path: str) -> str:
    return raw_path[: -len(".excalidraw.md")] + ".excalidraw.keyterms_cache.json"


def answers_cache_path_for(raw_path: str) -> str:
    return raw_path[: -len(".excalidraw.md")] + ".excalidraw.answers_cache.json"


def answers_meta_cache_path_for(raw_path: str) -> str:
    """Grounded/sources/context for each staged answer, captured at the
    moment retrieval ran for that answer (collect or fallback staging) --
    never recomputed at finalize, so the sidecar's grounded label always
    matches what the agent actually saw in its prompt, even if the corpus
    changes between collect and submit."""
    return raw_path[: -len(".excalidraw.md")] + ".excalidraw.answers_meta_cache.json"


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


def _parse_key_terms(text: str) -> list[str]:
    """Same comma-split logic as rag_agent._extract_key_terms's own parsing
    -- duplicated deliberately rather than calling that function, which must
    stay untouched (shared with /hint and the tutor)."""
    text = (text or "").strip()
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t.strip()]


def resolve_question(
    tag: Tag, context: str, neighbors: list[str], *, client, roots: list[str], course: str | None,
    model: str, exclude_paths: set[str], retrieve=retrieve_passages, extract=_extract_key_terms,
    driver: "QuestionResolverDriver | None" = None, note_key: str | None = None,
) -> Entry:
    """One question -> one Entry. Raises on any failure (including an empty
    answer) so the caller records nothing for it. Grounded means a passage
    survived own-note exclusion and (no key terms, or one mentions a key
    term) -- /hint's check, plus a guard so an empty retrieval can never count
    as grounded.

    driver=None (the default) reproduces today's behavior exactly via
    `extract`/`retrieve` and a direct generate_content call. A given driver
    routes key-term extraction and answer generation through it instead;
    retrieval (`retrieve`) always stays local regardless."""
    if driver is not None:
        key_term_prompt = _KEY_TERM_PROMPT_TEMPLATE.format(question=f"{tag.text}\n{context}")
        key_terms = _parse_key_terms(driver.extract_key_terms(note_key, tag.qid, key_term_prompt))
    else:
        key_terms = extract(f"{tag.text}\n{context}", client)
    found = retrieve(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
    # Hub-relative paths, not basenames: a same-named note in another folder is a legitimate source.
    passages = [p for p in found if p.path.replace("\\", "/") not in exclude_paths]
    grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
    prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
    if driver is not None:
        answer = driver.generate_answer(note_key, tag.qid, prompt).strip()
    else:
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


def discover_pending_notes(hub: str, course: str | None = None, note: str | None = None) -> list[str]:
    """Notes from discover_notes() that still have at least one unanswered
    question and are not a subset-of duplicate of another note -- the same
    filter resolve_questions.py's own CLI already applies before resolving
    or staging anything (see main()'s collect/plain-run loops), factored
    out so a caller like the consolidated orchestrator can compute
    eligibility without duplicating it."""
    pending = []
    for raw_path in discover_notes(hub, course, note):
        card = _note_card(hub, raw_path)
        if card and card.get("subset_of"):
            continue
        answered = {e.qid for e in read_sidecar(sidecar_path_for(raw_path))[1]}
        if any(t.qid not in answered for t in find_tags(_read_body(raw_path))):
            pending.append(raw_path)
    return pending


def _build_key_term_prompt(tag: Tag, body: str) -> str:
    """Same question+context shape the API path (`resolve_question`) feeds
    to `_extract_key_terms` -- used identically by the agent/collect path
    and submit's --allow-api-fallback path, so grounding quality does not
    drift between driver transports."""
    context, _neighbors = question_context(body, tag.ordinal)
    return _KEY_TERM_PROMPT_TEMPLATE.format(question=f"{tag.text}\n{context}")


def _build_answer_staging(
    tag: Tag, body: str, keyterms_cache: dict, client, roots: list[str],
    course: str | None, exclude: set[str],
) -> tuple[str, bool, list[str], str]:
    """Runs retrieval exactly once for this tag and returns
    (prompt, grounded, sources, stored_context). The caller persists the
    grounded/sources/context alongside the staged prompt (the answers-meta
    cache) so a later finalize never re-runs retrieval and can't disagree
    with what the agent was actually shown."""
    key_terms = keyterms_cache.get(tag.qid, [])
    context, neighbors = question_context(body, tag.ordinal)
    found = retrieve_passages(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
    passages = [p for p in found if p.path.replace("\\", "/") not in exclude]
    grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
    prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
    sources = [f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else []
    stored_context = " ".join(context.split())[:_STORED_CONTEXT_CHARS]
    return prompt, grounded, sources, stored_context


def _collect_note_answers(
    raw_path: str, body: str, pending_tags: list[Tag], client, roots: list[str],
    course: str | None, exclude: set[str], driver, keyterms_cache: dict, redo: bool = False,
) -> None:
    from core.env.gemini_utils import load_json_cache, save_json_cache
    from pipelines.transcribe_notes.agent_driver import AgentPending

    answers_path = answers_cache_path_for(raw_path)
    answers_cache = load_json_cache(answers_path)
    meta_path = answers_meta_cache_path_for(raw_path)
    meta_cache = load_json_cache(meta_path)
    missing_answers = []
    for tag in pending_tags:
        if not redo and tag.qid in answers_cache:
            continue
        prompt, grounded, sources, stored_context = _build_answer_staging(
            tag, body, keyterms_cache, client, roots, course, exclude,
        )
        meta_cache[tag.qid] = {"grounded": grounded, "sources": sources, "context": stored_context}
        missing_answers.append((tag.qid, prompt))
    if not missing_answers:
        return
    save_json_cache(meta_path, meta_cache)
    try:
        staged = driver.stage_answers(raw_path, missing_answers)
    except AgentPending:
        raise
    for qid, text in staged.items():
        answers_cache[qid] = text
    save_json_cache(answers_path, answers_cache)


def _collect_note_questions(
    raw_path: str, body: str, tags: list[Tag], by_id: dict, client, roots: list[str],
    course: str | None, exclude: set[str], model: str, driver, redo: bool,
) -> None:
    from core.env.gemini_utils import load_json_cache, save_json_cache
    from pipelines.transcribe_notes.agent_driver import AgentPending

    pending_tags = [t for t in tags if redo or t.qid not in by_id]
    if not pending_tags:
        return

    keyterms_path = keyterms_cache_path_for(raw_path)
    keyterms_cache = load_json_cache(keyterms_path)
    missing_key_terms = [
        (t.qid, _build_key_term_prompt(t, body))
        for t in pending_tags if t.qid not in keyterms_cache
    ]
    if missing_key_terms:
        try:
            staged = driver.stage_key_terms(raw_path, missing_key_terms)
        except AgentPending:
            raise
        for qid, text in staged.items():
            keyterms_cache[qid] = _parse_key_terms(text)
        save_json_cache(keyterms_path, keyterms_cache)
        # Re-check: an ApiDriver-style call returns synchronously and may have
        # filled everything in this same call; an AgentDriver always raises
        # AgentPending above and never reaches here.
        missing_key_terms = [
            (t.qid, "") for t in pending_tags if t.qid not in keyterms_cache
        ]
        if missing_key_terms:
            return  # still incomplete; nothing more to do this call

    _collect_note_answers(raw_path, body, pending_tags, client, roots, course, exclude, driver, keyterms_cache, redo=redo)


def resolve_note(
    raw_path: str, hub: str, client, roots: list[str], model: str = RESOLVER_MODEL, redo: bool = False,
    budget: int | None = None, retrieve=retrieve_passages, extract=_extract_key_terms,
    driver: "QuestionResolverDriver | None" = None, collect_mode: bool = False,
) -> NoteResult:
    """Resolves a note's unanswered questions into its sidecar, then applies
    markers. A question that fails records nothing and is retried next run.

    collect_mode=True stages task cards instead of resolving anything, and
    returns before reaching the sidecar-writing loop below -- callers in
    agent mode never see a NoteResult that means anything beyond "ran"."""
    body = _read_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    rekeyed = rekey_entries(tags, entries)  # answers survive a re-transcription that shifted ordinals
    by_id = {e.qid: e for e in entries}
    card = _note_card(hub, raw_path)
    course = derive_course(_rel(hub, raw_path))
    exclude = {_rel(hub, rag_path), _rel(hub, sidecar)}

    if collect_mode:
        _collect_note_questions(
            raw_path, body, tags, by_id, client, roots, course, exclude, model, driver, redo,
        )
        return NoteResult()

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
                exclude_paths=exclude, retrieve=retrieve, extract=extract,
            )
            result.resolved += 1
        except Exception as err:
            print(f"WARNING: {tag.qid} ({tag.text[:60]!r}) failed: {err}")
            result.failed.append(tag.qid)

    if result.resolved or rekeyed:
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
    if card:
        update_card_content_hash(hub, card["file_id"], compute_content_hash(rag_path))
    else:
        print(f"WARNING: no index card found for {raw_path} -- content_hash not refreshed; "
              f"chunk_index will not notice resolved answers until the card exists.")
    return result


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Answer the [Question] tags in Excalidraw notes.")
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Corpus root (academic-hub).")
    parser.add_argument("--course", default=None)
    parser.add_argument("--note", default=None, help="Only raw transcripts whose filename contains this text.")
    parser.add_argument("--dry-run", action="store_true", help="List questions; no API calls, no writes.")
    parser.add_argument("--redo", action="store_true", help="Re-answer questions that already have an entry.")
    parser.add_argument("--model", default=RESOLVER_MODEL)
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Generation transport. Default: agent (the Antigravity subscription). "
             "Use 'api' for a fully metered run.",
    )
    parser.add_argument("--collect", action="store_true",
                         help="With --driver agent: write task cards instead of resolving.")
    parser.add_argument("--run-id", default=None,
                         help="Run id for --collect/--submit's .agent_work/ directory (default: a timestamp).")
    parser.add_argument("--submit", default=None, metavar="RUN_ID",
                         help="Validate this run's filled task cards and write them through.")
    parser.add_argument(
        "--allow-api-fallback", action="store_true",
        help="With --submit: finish any still-pending/bounced cards via the metered API instead of "
             "leaving them pending. Explicit opt-in only -- never automatic.",
    )
    parser.add_argument("--bootstrap", default=None, metavar="RUN_ID",
                         help="Print the agent's operating contract for this run.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.bootstrap:
        print(f"""Agent-driven question-resolution contract for run '{args.bootstrap}':

1. Open each note's directory under .agent_work/{args.bootstrap}/<doc-slug>/.
2. Read worklist.md to see which task cards are pending.
3. For a key-terms card: fill ONLY the "Agent output" section with one
   "--- KEYTERMS <qid> ---" section per question listed, in order, using
   exactly the qids the card lists. A comma-separated list of specific named
   terms, or nothing if none apply -- never answer the question itself here.
4. For an answers card: fill ONLY the "Agent output" section with one
   "--- ANSWER <qid> ---" section per question listed, in order. Write the
   full explanation markdown for that question.
5. Once you've filled one or more cards, run:
   python -m agent.rag.resolve_questions --submit {args.bootstrap}
6. If a card comes back marked "bounced: <reason>" in worklist.md, redo only
   that card in place and re-run step 5.
7. Stop once worklist.md shows nothing "pending"/"filled" left for this run.
   A note's key-terms card must be fully submitted before its answers card
   is staged -- submit stages the answers card automatically once that
   happens, on your next --submit call.
""")
        return 0

    if args.dry_run and (args.collect or args.submit):
        print("--dry-run cannot be combined with --collect/--submit.")
        return 1
    if args.collect and args.driver != "agent":
        print("--collect requires --driver agent.")
        return 1
    if args.driver == "agent" and not args.collect and not args.submit and not args.dry_run:
        print("--driver agent requires --collect or --submit.")
        return 1

    hub = os.path.abspath(args.root)

    if args.collect:
        import datetime

        from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver

        load_dotenv_override()
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return 1
        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        driver = QuestionResolverAgentDriver(hub, run_id)
        for raw_path in discover_notes(hub, args.course, args.note):
            card = _note_card(hub, raw_path)
            if card and card.get("subset_of"):
                continue
            try:
                resolve_note(raw_path, hub, client, [hub], model=args.model, redo=args.redo,
                             driver=driver, collect_mode=True)
            except Exception as err:
                from pipelines.transcribe_notes.agent_driver import AgentPending

                if isinstance(err, AgentPending):
                    print(f"[{os.path.basename(raw_path)}] collected")
                else:
                    print(f"ERROR: {raw_path} failed: {err}")
        print(f"Collect run '{run_id}' complete under {os.path.join(hub, '.agent_work', run_id)}.")
        return 0

    if args.submit:
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_work import agent_work_dir, doc_slug_for
        from agent.rag.resolve_questions_submit import submit_doc

        load_dotenv_override()
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return 1
        run_dir = agent_work_dir(hub, args.submit)
        if not os.path.isdir(run_dir):
            print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
            return 1

        notes_by_slug = {
            doc_slug_for(raw_path, compute_file_id(raw_path)): raw_path
            for raw_path in discover_notes(hub, args.course, args.note)
        }
        failed = []
        for doc_slug in sorted(os.listdir(run_dir)):
            raw_path = notes_by_slug.get(doc_slug)
            if raw_path is None:
                print(f"WARNING: no matching pending note for collected doc '{doc_slug}' "
                      f"(already submitted, or outside this --course/--note filter?) -- skipping.")
                continue
            try:
                status = submit_doc(
                    hub, hub, args.submit, doc_slug, raw_path, hub, client, args.model,
                    allow_api_fallback=args.allow_api_fallback, redo=args.redo,
                )
            except Exception as err:
                print(f"[{doc_slug}] error: {err}")
                failed.append(doc_slug)
                continue
            print(f"[{doc_slug}] {status}")
        return 1 if failed else 0

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
