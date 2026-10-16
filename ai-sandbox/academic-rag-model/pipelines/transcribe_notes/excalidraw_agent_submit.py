# pipelines/transcribe_notes/excalidraw_agent_submit.py
"""
submit: validates a filled Excalidraw task card's output and writes it into
the note's chunk or expansion cache, then (once a whole stage is submitted)
re-invokes process_excalidraw_note to advance to the next stage or finish
the write/index path. See docs/superpowers/specs/transcribe_notes/
2026-10-15-excalidraw-agent-driver-design.md.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from core.env.gemini_utils import load_json_cache, save_json_cache
from pipelines.transcribe_notes.agent_work import doc_work_dir, load_manifest, render_worklist, save_manifest
from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver, ExcalidrawNullDriver
from pipelines.transcribe_notes.excalidraw_agent_work import parse_card_output
from pipelines.transcribe_notes.transcribe_excalidraw import (
    chunk_cache_paths_for,
    expansion_cache_paths_for,
    process_excalidraw_note,
)

_MIN_LENGTH_FOR_DUPLICATE_CHECK = 40
_SECTION_RE_TEMPLATE = r"--- {label} (\d+) ---\n(.*?)(?=--- {label} \d+ ---|\Z)"


@dataclass
class ValidationResult:
    pages: dict[int, str] = field(default_factory=dict)
    bounce_reason: str | None = None


def _parse_sections(raw_output: str, label: str, expected_indices: list[int]) -> dict[int, str]:
    pattern = re.compile(_SECTION_RE_TEMPLATE.format(label=label), re.DOTALL)
    parsed = {int(idx): text.strip() for idx, text in pattern.findall(raw_output)}
    return {i: parsed[i] for i in expected_indices if i in parsed}


def _validate_common(parsed: dict[int, str], expected_indices: list[int]) -> str | None:
    missing = [i for i in expected_indices if i not in parsed or not parsed[i].strip()]
    if missing:
        return f"missing or empty section(s): {missing}"
    for i, text in parsed.items():
        if text.count("```") % 2 != 0:
            return f"section {i} has an unclosed code fence"
        if text.count("$$") % 2 != 0:
            return f"section {i} has unbalanced $$ display-math delimiters"
    seen: dict[str, int] = {}
    for i in sorted(parsed):
        normalized = parsed[i].strip()
        if len(normalized) < _MIN_LENGTH_FOR_DUPLICATE_CHECK:
            continue
        if normalized in seen:
            return f"section {i} is a duplicate of section {seen[normalized]} (copy-paste?)"
        seen[normalized] = i
    return None


def validate_chunk_card_output(raw_output: str, expected_indices: list[int]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "CHUNK", expected_indices)
    return ValidationResult(pages=parsed, bounce_reason=_validate_common(parsed, expected_indices))


def validate_expansion_card_output(raw_output: str, expected_indices: list[int]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "SEGMENT", expected_indices)
    return ValidationResult(pages=parsed, bounce_reason=_validate_common(parsed, expected_indices))


def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    excalidraw_md_path: str, image_path: str, client, model_override: str | None,
    expand_backend: str = "gemini", agent_name: str = "antigravity", allow_api_fallback: bool = False,
    use_grounding: bool = False,
) -> str:
    doc_dir = doc_work_dir(hub_root, run_id, doc_slug)
    entries = load_manifest(doc_dir)
    if not entries:
        return "incomplete: no manifest found for this document"

    chunk_entries = [e for e in entries if e.tier == "chunks"]
    segment_entries = [e for e in entries if e.tier == "segments"]

    def _apply(card_entries: list, cache_path: str, validator) -> None:
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
            for index, text in result.pages.items():
                cache[str(index)] = text
            entry.status = "submitted"
            entry.bounce_reason = None
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        save_json_cache(cache_path, cache)

    chunk_cache_path, _ = chunk_cache_paths_for(excalidraw_md_path)
    exp_cache_path, _ = expansion_cache_paths_for(excalidraw_md_path)
    _apply(chunk_entries, chunk_cache_path, validate_chunk_card_output)
    _apply(segment_entries, exp_cache_path, validate_expansion_card_output)
    save_manifest(doc_dir, entries)
    render_worklist(doc_dir, entries)

    any_unsubmitted = any(e.status != "submitted" for e in entries)
    if any_unsubmitted and not allow_api_fallback:
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"

    from pipelines.transcribe_notes.agent_driver import AgentPending, NullDriverFired
    from pipelines.transcribe_notes.excalidraw_agent_work import ExcalidrawAgentDriver

    if allow_api_fallback:
        driver = ExcalidrawApiDriver(client, backend=expand_backend)
        try:
            process_excalidraw_note(
                excalidraw_md_path, image_path, client, model_override, expand_backend,
                academic_hub_root, use_grounding=use_grounding, driver=driver,
            )
        except Exception as err:
            return f"write failed: {err}"
        return "complete (api fallback used for remaining chunks/segments)"

    # Re-run with collect_mode=True first: if transcription just finished but
    # expansion hasn't been staged yet, this stages the expansion card and
    # raises AgentPending -- transcribe_chunks/expand_transcription deliberately
    # let it propagate uncaught (same as the PDF driver's own AgentPending
    # contract), so it must be caught HERE, not assumed swallowed downstream.
    agent_driver = ExcalidrawAgentDriver(hub_root, run_id, agent_name=agent_name)
    try:
        process_excalidraw_note(
            excalidraw_md_path, image_path, None, model_override, expand_backend,
            academic_hub_root, use_grounding=use_grounding, driver=agent_driver, collect_mode=True,
        )
    except AgentPending:
        return "incomplete: expansion card staged, awaiting agent fill"

    # Now check whether both stages are genuinely complete: NullDriver raises
    # NullDriverFired on any real gap, which must be reported as "still
    # incomplete," not as a write failure -- caught ahead of the generic
    # except Exception below, same ordering agent_driver.py's own docstring
    # requires for AgentPending.
    try:
        process_excalidraw_note(
            excalidraw_md_path, image_path, client, model_override, expand_backend,
            academic_hub_root, use_grounding=use_grounding, driver=ExcalidrawNullDriver(), collect_mode=False,
        )
    except NullDriverFired:
        return "incomplete: a stage still has missing chunks/segments after restaging"
    except Exception as err:
        return f"write failed: {err}"

    return "complete"
