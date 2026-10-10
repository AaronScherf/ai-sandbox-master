# pipelines/transcribe_notes/agent_submit.py
"""
submit: validates a filled task card's output and writes it into the
document's existing _pages_cache.json, then (once a whole document is
submitted) re-runs process_pdf to finish the write/index path. See
docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from core.env.gemini_utils import load_json_cache, save_json_cache
from pipelines.transcribe_notes.agent_driver import NullDriver
from pipelines.transcribe_notes.agent_work import (
    doc_work_dir,
    load_manifest,
    parse_task_card_output,
    render_worklist,
    save_manifest,
)
from pipelines.transcribe_notes.transcribe_notes import (
    _looks_like_repetition_loop,
    extract_page_text,
    parse_batch_transcription_response,
    process_pdf,
    resolve_output_dir,
)

_MIN_LENGTH_RATIO_FOR_WARNING = 0.3  # output shorter than 30% of the local-text hint's length warns (tier-2 only)
_MIN_LENGTH_FOR_DUPLICATE_CHECK = 40  # shorter identical text (e.g. "(continued)") isn't evidence of a copy-paste mistake


@dataclass
class ValidationResult:
    pages: dict[int, str] = field(default_factory=dict)
    bounce_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


def _unbalanced_display_math(text: str) -> bool:
    return text.count("$$") % 2 != 0


def _unclosed_code_fence(text: str) -> bool:
    return text.count("```") % 2 != 0


def validate_card_output(
    raw_output: str, expected_pages: list[int], tier: str,
    local_text_hints: dict[int, str] | None = None,
) -> ValidationResult:
    parsed = parse_batch_transcription_response(raw_output, expected_pages)
    result = ValidationResult(pages=parsed)

    missing = [p for p in expected_pages if p not in parsed or not parsed[p].strip()]
    if missing:
        result.bounce_reason = f"missing or empty page(s): {missing}"
        return result

    for page, text in parsed.items():
        if _looks_like_repetition_loop(text):
            result.bounce_reason = f"page {page} looks like a repetition-loop failure"
            return result
        if _unclosed_code_fence(text):
            result.bounce_reason = f"page {page} has an unclosed code fence"
            return result
        if _unbalanced_display_math(text):
            result.bounce_reason = f"page {page} has unbalanced $$ display-math delimiters"
            return result

    # Final review I7: a copy-paste mistake (the agent pastes one page's
    # text into another page of the same card) publishes a duplicate
    # page as if both were transcribed correctly. Only flags text long
    # enough that an exact match isn't just a short, legitimately
    # repeated phrase (a bare "(continued)", a page number, a heading).
    seen: dict[str, int] = {}
    for page in sorted(parsed):
        normalized = parsed[page].strip()
        if len(normalized) < _MIN_LENGTH_FOR_DUPLICATE_CHECK:
            continue
        if normalized in seen:
            result.bounce_reason = f"page {page} is a duplicate of page {seen[normalized]} (copy-paste?)"
            return result
        seen[normalized] = page

    if tier == "batch" and local_text_hints:
        for page, text in parsed.items():
            hint = local_text_hints.get(page)
            if hint and len(text) < len(hint) * _MIN_LENGTH_RATIO_FOR_WARNING:
                result.warnings.append(
                    f"page {page}: output is much shorter than the local-text hint "
                    f"({len(text)} vs {len(hint)} chars) -- possible skipped/summarized page"
                )

    return result


def _cache_paths_for(pdf_path: str) -> tuple[str, str]:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = resolve_output_dir(pdf_path)
    cache_path = os.path.join(output_dir, f"{base_name}_pages_cache.json")
    driver_path = cache_path.replace("_pages_cache.json", "_pages_driver.json")
    return cache_path, driver_path


def _md_path_for(pdf_path: str) -> str:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    return os.path.join(resolve_output_dir(pdf_path), f"{base_name}.md")


def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    pdf_path: str, client, model_override: str | None, agent_name: str = "antigravity",
    force_vision: bool = False,
) -> str:
    doc_dir = doc_work_dir(hub_root, run_id, doc_slug)
    entries = load_manifest(doc_dir)
    if not entries:
        return "incomplete: no manifest found for this document"

    # "already complete" means the .md was actually written, not merely
    # that every manifest entry so far shows submitted -- a multi-card
    # tier-3 document has more entries yet to be staged (see is_tier3
    # below), and a previous write attempt may have failed (final review
    # I4), in which case this must retry rather than report done forever.
    if all(e.status == "submitted" for e in entries) and os.path.exists(_md_path_for(pdf_path)):
        return "already complete"

    cache_path, driver_path = _cache_paths_for(pdf_path)
    # collect_mode deliberately skips os.makedirs (Task 1) since it never
    # writes anything -- submit is the first thing that does, so the
    # output directory may not exist yet.
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    cache = load_json_cache(cache_path)
    driver_provenance = load_json_cache(driver_path)

    for entry in entries:
        if entry.status not in ("pending", "filled", "bounced"):
            continue
        raw_output = parse_task_card_output(doc_dir, entry.task_id)
        if raw_output is None:
            continue  # agent hasn't filled this card yet
        local_text_hints = {
            page: extract_page_text(pdf_path, page - 1) for page in entry.pages
        } if entry.tier == "batch" else None
        result = validate_card_output(raw_output, entry.pages, entry.tier, local_text_hints)
        if result.bounce_reason:
            entry.status = "bounced"
            entry.bounce_reason = result.bounce_reason
            continue
        for page, text in result.pages.items():
            cache[str(page)] = text
            driver_provenance[str(page)] = agent_name
        entry.status = "submitted"
        entry.bounce_reason = None

    save_json_cache(cache_path, cache)
    save_json_cache(driver_path, driver_provenance)
    save_manifest(doc_dir, entries)
    render_worklist(doc_dir, entries)

    if not all(e.status == "submitted" for e in entries):
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"

    # Final review C1: "every manifest entry submitted" does NOT mean "the
    # whole document is cached" for a multi-card tier-3 document -- only
    # the cards staged SO FAR are in the manifest. Finalizing the write
    # here would publish a partial .md and make a paid classification
    # call on every round trip but the last one. Only tier-3 can have this
    # gap (manifest entries record tier3 only when AgentDriver.transcribe_page
    # staged them; batch tiers always stage every needed batch in one
    # collect call, so "all submitted" is already complete for those).
    is_tier3 = any(e.tier == "tier3" for e in entries)
    if is_tier3:
        import pypdf

        total_pages = len(pypdf.PdfReader(pdf_path).pages)
        if len(cache) < total_pages:
            from pipelines.transcribe_notes.agent_work import AgentDriver

            next_driver = AgentDriver(hub_root, run_id, agent_name=agent_name)
            process_pdf(
                pdf_path, None, model_override, academic_hub_root,
                force_vision=force_vision, driver=next_driver, collect_mode=True,
            )
            return f"incomplete: {len(cache)}/{total_pages} page(s) cached, next card staged"

    try:
        process_pdf(
            pdf_path, client, model_override, academic_hub_root,
            force_vision=force_vision, driver=NullDriver(),
        )
    except Exception as err:
        # Don't leave the document stuck "complete" if the final write
        # itself fails (final review I4) -- the "already complete" guard
        # above also checks the .md file actually exists, so a later
        # submit call will retry this.
        return f"write failed: {err}"

    return "complete"
