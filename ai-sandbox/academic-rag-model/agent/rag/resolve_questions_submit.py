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
from agent.rag.resolve_questions import (
    _build_answer_staging,
    _build_key_term_prompt,
    _note_card,
    _rel,
    answers_cache_path_for,
    answers_meta_cache_path_for,
    keyterms_cache_path_for,
    _parse_key_terms,
)
from core.indexer.questions import Entry, find_tags, read_sidecar, sidecar_path_for, write_sidecar
from core.indexer.index_card import compute_content_hash, derive_course, update_card_content_hash
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
    agent_name: str = "antigravity", allow_api_fallback: bool = False, redo: bool = False,
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

    body = _read_raw_body(raw_path)
    tags = find_tags(body)
    _, sidecar_entries = read_sidecar(sidecar_path_for(raw_path))
    answered = {e.qid for e in sidecar_entries}

    # Scope this submit to the qids this run's manifest actually collected --
    # a tag elsewhere in the note that was never part of this run must not
    # block completion (finalize_note_answers already treats it as "not part
    # of this run"; submit's own pending_tags must agree, or a note with any
    # uncollected tag can never finish a run). A manifest qid with no
    # matching current tag means the question text changed (a retranscription
    # ran between collect and submit, changing its qid) -- warn, don't crash.
    manifest_qids = {qid for e in entries for qid in e.pages}
    current_qids = {t.qid for t in tags}
    orphaned = sorted(manifest_qids - current_qids)
    if orphaned:
        print(f"WARNING: {len(orphaned)} collected question(s) no longer match any tag in "
              f"'{doc_slug}' (question text changed or the note was retranscribed?) -- skipping: {orphaned}")
    pending_tags = [t for t in tags if t.qid in manifest_qids and (redo or t.qid not in answered)]

    if allow_api_fallback:
        driver = QuestionResolverApiDriver(client)
    else:
        driver = QuestionResolverAgentDriver(hub_root, run_id, agent_name=agent_name)

    keyterms_cache = load_json_cache(keyterms_path)
    answers_cache = load_json_cache(answers_path)
    # Redo never forces key-term re-extraction, only re-answering -- a
    # deliberate scope decision (same one the collect path pins), since the
    # question text (and therefore its qid and key terms) hasn't changed just
    # because --redo was passed.
    still_missing_keyterms = [t for t in pending_tags if t.qid not in keyterms_cache]
    if still_missing_keyterms:
        if allow_api_fallback:
            missing = [(t.qid, _build_key_term_prompt(t, body)) for t in still_missing_keyterms]
            staged = driver.stage_key_terms(raw_path, missing)
            for qid, text in staged.items():
                keyterms_cache[qid] = _parse_key_terms(text)
            save_json_cache(keyterms_path, keyterms_cache)
        else:
            return "incomplete: key-term card not yet staged for this run"

    still_missing_answers = [t for t in pending_tags if redo or t.qid not in answers_cache]
    if still_missing_answers:
        course = derive_course(_rel(hub, raw_path))
        exclude = {_rel(hub, raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")),
                   _rel(hub, sidecar_path_for(raw_path))}
        meta_path = answers_meta_cache_path_for(raw_path)
        meta_cache = load_json_cache(meta_path)
        missing = []
        for tag in still_missing_answers:
            prompt, grounded, sources, stored_context = _build_answer_staging(
                tag, body, keyterms_cache, client, [hub], course, exclude,
            )
            meta_cache[tag.qid] = {"grounded": grounded, "sources": sources, "context": stored_context}
            missing.append((tag.qid, prompt))
        save_json_cache(meta_path, meta_cache)
        try:
            staged = driver.stage_answers(raw_path, missing)
        except AgentPending:
            return "incomplete: answer card staged, awaiting agent fill"
        for qid, text in staged.items():
            answers_cache[qid] = text
        save_json_cache(answers_path, answers_cache)

    finalize_note_answers(
        raw_path, hub, model_label="api-fallback" if allow_api_fallback else "antigravity", redo=redo,
    )
    return "complete" if not allow_api_fallback else "complete (api fallback used for remaining questions)"


def _read_raw_body(raw_path: str) -> str:
    from core.env.frontmatter import parse_frontmatter
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]


def finalize_note_answers(raw_path: str, hub: str, model_label: str = "antigravity", redo: bool = False) -> None:
    """Builds complete Entry objects from the answers cache and the
    answers-meta cache (grounded/sources/context captured at staging time)
    and writes the sidecar -- never calls any driver, and never re-runs
    retrieval, so the sidecar's grounded label always matches what the agent
    was actually shown, even if the corpus changes between collect and
    submit. A qid in `tags` but absent from the answers cache is simply not
    part of this run (e.g. a question added by a retranscription after this
    run's collect already happened) and is left untouched, same as the
    existing sequential path's own by-qid skip logic."""
    from core.indexer.questions import apply_markers, rag_path_for

    body = _read_raw_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    by_id = {e.qid: e for e in entries}

    answers_cache = load_json_cache(answers_cache_path_for(raw_path))
    meta_cache = load_json_cache(answers_meta_cache_path_for(raw_path))

    for tag in tags:
        if (tag.qid in by_id and not redo) or tag.qid not in answers_cache:
            continue
        meta = meta_cache.get(tag.qid)
        if meta is None:
            # Staging always writes this tag's meta entry before the answer
            # can land in answers_cache (both this module's fallback path and
            # resolve_questions._collect_note_answers do this unconditionally),
            # so a missing entry means a cache predating the meta cache, or a
            # hand-edited cache file. Never guess grounded/sources from
            # nothing -- skip this qid, leave every other already-cached
            # answer in the note untouched, same per-question resilience
            # resolve_note's own sequential loop already has.
            print(f"WARNING: {tag.qid} has an answer but no staging metadata -- skipping (re-collect to fix).")
            continue
        by_id[tag.qid] = Entry(
            qid=tag.qid, question=tag.text, grounded=meta["grounded"], model=model_label,
            resolved_at=datetime.now(timezone.utc).isoformat(),
            context=meta["context"], answer=answers_cache[tag.qid], sources=meta["sources"],
        )

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
    card = _note_card(hub, raw_path)
    if card:
        update_card_content_hash(hub, card["file_id"], compute_content_hash(rag_path))
    else:
        print(f"WARNING: no index card found for {raw_path} -- content_hash not refreshed; "
              f"chunk_index will not notice resolved answers until the card exists.")
