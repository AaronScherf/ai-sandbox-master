# pipelines/transcribe_notes/agent_submit.py
"""
submit: validates a filled task card's output and writes it into the
document's existing _pages_cache.json, then (once a whole document is
submitted) re-runs process_pdf to finish the write/index path. See
docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pipelines.transcribe_notes.transcribe_notes import (
    _looks_like_repetition_loop,
    parse_batch_transcription_response,
)

_MIN_LENGTH_RATIO_FOR_WARNING = 0.3  # output shorter than 30% of the local-text hint's length warns (tier-2 only)


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

    if tier == "batch" and local_text_hints:
        for page, text in parsed.items():
            hint = local_text_hints.get(page)
            if hint and len(text) < len(hint) * _MIN_LENGTH_RATIO_FOR_WARNING:
                result.warnings.append(
                    f"page {page}: output is much shorter than the local-text hint "
                    f"({len(text)} vs {len(hint)} chars) -- possible skipped/summarized page"
                )

    return result
