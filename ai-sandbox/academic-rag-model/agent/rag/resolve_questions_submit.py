# agent/rag/resolve_questions_submit.py
"""
submit: validates a filled question-resolver task card's output and writes
it into the note's key-terms or answers cache, then (once a whole stage is
submitted) re-invokes the agent driver to advance to the next stage, or
finalizes answers directly into the sidecar. See docs/superpowers/specs/
agent/rag/2026-10-16-question-resolver-agent-driver-design.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.env.gemini_utils import load_json_cache, save_json_cache
from agent.rag.rag_agent import _term_match_count, retrieve_passages
from agent.rag.resolve_questions import (
    _rel,
    answers_cache_path_for,
    build_answer_prompt,
    keyterms_cache_path_for,
    question_context,
    _parse_key_terms,
)
from core.indexer.questions import Entry, Tag, find_tags, read_sidecar, sidecar_path_for, write_sidecar
from core.indexer.index_card import derive_course
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import doc_work_dir, load_manifest, render_worklist, save_manifest
from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver, parse_card_output
from agent.rag.resolve_questions_driver import QuestionResolverApiDriver

_SECTION_RE_TEMPLATE = r"--- {label} ([\w-]+) ---\n(.*?)(?=--- {label} [\w-]+ ---|\Z)"


@dataclass
class ValidationResult:
    pages: dict[str, str] = field(default_factory=dict)
    bounce_reason: str | None = None


def _parse_sections(raw_output: str, label: str, expected_qids: list[str]) -> dict[str, str]:
    pattern = re.compile(_SECTION_RE_TEMPLATE.format(label=label), re.DOTALL)
    parsed = {qid: text.strip() for qid, text in pattern.findall(raw_output)}
    return {q: parsed[q] for q in expected_qids if q in parsed}


def validate_keyterms_card_output(raw_output: str, expected_qids: list[str]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "KEYTERMS", expected_qids)
    missing = [q for q in expected_qids if q not in parsed]
    if missing:
        return ValidationResult(pages=parsed, bounce_reason=f"missing section(s): {missing}")
    return ValidationResult(pages=parsed)  # an empty section is valid here -- "no specific terms"


def validate_answer_card_output(raw_output: str, expected_qids: list[str]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "ANSWER", expected_qids)
    missing = [q for q in expected_qids if q not in parsed or not parsed[q].strip()]
    if missing:
        return ValidationResult(pages=parsed, bounce_reason=f"missing or empty section(s): {missing}")
    for qid, text in parsed.items():
        if text.count("```") % 2 != 0:
            return ValidationResult(pages=parsed, bounce_reason=f"{qid} has an unclosed code fence")
        if text.count("$$") % 2 != 0:
            return ValidationResult(pages=parsed, bounce_reason=f"{qid} has unbalanced $$ display-math delimiters")
    return ValidationResult(pages=parsed)


def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    raw_path: str, hub: str, client, model_override: str | None,
    agent_name: str = "antigravity", allow_api_fallback: bool = False,
) -> str:
    doc_dir = doc_work_dir(hub_root, run_id, doc_slug)
    entries = load_manifest(doc_dir)
    if not entries:
        return "incomplete: no manifest found for this document"

    keyterm_entries = [e for e in entries if e.tier == "keyterms"]
    answer_entries = [e for e in entries if e.tier == "answers"]

    def _apply(card_entries: list, cache_path: str, validator, parser) -> None:
        if not card_entries:
            return
        cache = load_json_cache(cache_path)
        for entry in card_entries:
            if entry.status not in ("pending", "filled", "bounced"):
                continue
            raw_output = parse_card_output(doc_dir, entry.task_id)
            if raw_output is None:
                continue
            result = validator(raw_output, entry.pages)
            if result.bounce_reason:
                entry.status = "bounced"
                entry.bounce_reason = result.bounce_reason
                continue
            for qid, text in result.pages.items():
                cache[qid] = parser(text) if parser else text
            entry.status = "submitted"
            entry.bounce_reason = None
        save_json_cache(cache_path, cache)

    keyterms_path = keyterms_cache_path_for(raw_path)
    answers_path = answers_cache_path_for(raw_path)
    _apply(keyterm_entries, keyterms_path, validate_keyterms_card_output, _parse_key_terms)
    _apply(answer_entries, answers_path, validate_answer_card_output, None)
    save_manifest(doc_dir, entries)
    render_worklist(doc_dir, entries)

    any_unsubmitted = any(e.status != "submitted" for e in entries)
    if any_unsubmitted and not allow_api_fallback:
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"

    tags = find_tags(_read_raw_body(raw_path))
    _, sidecar_entries = read_sidecar(sidecar_path_for(raw_path))
    answered = {e.qid for e in sidecar_entries}
    pending_tags = [t for t in tags if t.qid not in answered]

    if allow_api_fallback:
        driver = QuestionResolverApiDriver(client)
    else:
        driver = QuestionResolverAgentDriver(hub_root, run_id, agent_name=agent_name)

    keyterms_cache = load_json_cache(keyterms_path)
    answers_cache = load_json_cache(answers_path)
    still_missing_keyterms = [t for t in pending_tags if t.qid not in keyterms_cache]
    if still_missing_keyterms:
        if allow_api_fallback:
            from agent.rag.resolve_questions import _KEY_TERM_PROMPT_TEMPLATE

            missing = [
                (t.qid, _KEY_TERM_PROMPT_TEMPLATE.format(question=t.text)) for t in still_missing_keyterms
            ]
            staged = driver.stage_key_terms(raw_path, missing)
            for qid, text in staged.items():
                keyterms_cache[qid] = _parse_key_terms(text)
            save_json_cache(keyterms_path, keyterms_cache)
        else:
            return "incomplete: key-term card not yet staged for this run"

    still_missing_answers = [t for t in pending_tags if t.qid not in answers_cache]
    if still_missing_answers:
        body = _read_raw_body(raw_path)
        course = derive_course(_rel(hub, raw_path))
        exclude = {_rel(hub, raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")),
                   _rel(hub, sidecar_path_for(raw_path))}
        missing = []
        for tag in still_missing_answers:
            key_terms = keyterms_cache.get(tag.qid, [])
            context, neighbors = question_context(body, tag.ordinal)
            found = retrieve_passages([hub], f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
            passages = [p for p in found if p.path.replace("\\", "/") not in exclude]
            grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
            prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
            missing.append((tag.qid, prompt))
        try:
            staged = driver.stage_answers(raw_path, missing)
        except AgentPending:
            return "incomplete: answer card staged, awaiting agent fill"
        for qid, text in staged.items():
            answers_cache[qid] = text
        save_json_cache(answers_path, answers_cache)

    finalize_note_answers(raw_path, hub, client, [hub], model_label="api-fallback" if allow_api_fallback else "antigravity")
    return "complete" if not allow_api_fallback else "complete (api fallback used for remaining questions)"


def _read_raw_body(raw_path: str) -> str:
    from core.env.frontmatter import parse_frontmatter
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]


def finalize_note_answers(raw_path: str, hub: str, client, roots: list[str], model_label: str = "antigravity") -> None:
    """Builds complete Entry objects from the answers cache and writes the
    sidecar -- never calls any driver. A qid in `tags` but absent from both
    the sidecar and the answers cache is simply not part of this run (e.g.
    a question added by a retranscription after this run's collect already
    happened) and is left untouched, same as the existing sequential path's
    own by-qid skip logic."""
    from core.indexer.questions import apply_markers, rag_path_for

    body = _read_raw_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    by_id = {e.qid: e for e in entries}
    course = derive_course(_rel(hub, raw_path))
    exclude = {_rel(hub, rag_path), _rel(hub, sidecar)}

    keyterms_cache = load_json_cache(keyterms_cache_path_for(raw_path))
    answers_cache = load_json_cache(answers_cache_path_for(raw_path))

    for tag in tags:
        if tag.qid in by_id or tag.qid not in answers_cache:
            continue
        try:
            key_terms = keyterms_cache.get(tag.qid, [])
            context, neighbors = question_context(body, tag.ordinal)
            found = retrieve_passages(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
            passages = [p for p in found if p.path.replace("\\", "/") not in exclude]
            grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
            by_id[tag.qid] = Entry(
                qid=tag.qid, question=tag.text, grounded=grounded, model=model_label,
                resolved_at=datetime.now(timezone.utc).isoformat(),
                context=" ".join(context.split())[:600], answer=answers_cache[tag.qid],
                sources=[f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else [],
            )
        except Exception as err:
            # One question's retrieval failing must not lose every other
            # already-cached answer in this note -- same per-question
            # resilience resolve_note's own sequential loop already has.
            # No AgentPending/NullDriverFired risk here: finalize never
            # calls any driver, so a bare except is safe, not a guardrail
            # violation.
            print(f"WARNING: {tag.qid} finalize failed: {err}")

    in_order = [by_id[t.qid] for t in tags if t.qid in by_id]
    leftover = [e for qid, e in by_id.items() if qid not in {t.qid for t in tags}]
    ordered = in_order + leftover
    fields = {
        **fields,
        "source_excalidraw": _rel(hub, raw_path),
        "resolver_model": model_label,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "questions": str(len(ordered)),
    }
    write_sidecar(sidecar, fields, ordered)
    apply_markers(raw_path, rag_path)
