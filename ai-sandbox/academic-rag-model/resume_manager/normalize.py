"""
normalize.py
One local-LLM reformat pass turning the raw page-tagged extraction
(extract.py) into the master resume's structured Markdown convention
(## section headings, ### <Org> — <Role> (<dates>) entries, bullets)
-- replaces hand-transcription, per spec §3 steps 3-4. Verified
against the raw extraction before being trusted.
"""
from __future__ import annotations

import os

from common.ollama_utils import call_ollama
from resume_manager.fact_diff import extract_entries, extract_metrics, metrics_not_traceable

OLLAMA_MODEL = os.environ.get("RESUMEMANAGER_OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("RESUMEMANAGER_OLLAMA_TIMEOUT", "300"))

_SYSTEM_PROMPT = """You are reformatting a resume's raw extracted text into a strict Markdown structure.
CRITICAL RULES:
1. Preserve every word, number, and date exactly as written. Do not summarize, paraphrase, or reword anything.
2. Do not add or remove any content -- no new bullets, no dropped bullets, no invented information.
3. Use "## " for each major section (e.g. Work Experience, Education, Skills), matching the input's own section boundaries.
4. Use "### <Org> — <Role> (<Start> – <End or \"Present\">)" for each Experience/Education entry.
5. Use "- " for bullet points under each entry.
6. Output ONLY the reformatted Markdown -- no commentary, no conversational text."""


def normalize_resume_text(raw_text: str, model: str = OLLAMA_MODEL) -> str | None:
    """Returns the reformatted Markdown, or None if the local Ollama
    call itself failed/timed out (spec §8) -- caller decides what to
    do."""
    prompt = f"{_SYSTEM_PROMPT}\n\n### RAW EXTRACTED RESUME TEXT:\n{raw_text}"
    result = call_ollama(prompt, model, OLLAMA_TIMEOUT_SECONDS)
    return result if isinstance(result, str) else None


def verify_normalization(raw_text: str, normalized_text: str) -> list[str]:
    """Bidirectional fact-preservation check (spec §3 step 4): metrics
    get a full bidirectional substring check (works on any text,
    structured or not); org/role names are checked only in the
    "invented" direction, since raw text has no ### headings to
    enumerate entries from in the first place -- a silently dropped
    entry is instead caught if any of its metrics disappear. Returns a
    list of human-readable mismatch descriptions; empty means a clean
    pass."""
    problems: list[str] = []

    for metric in sorted(m for m in extract_metrics(raw_text) if m not in normalized_text):
        problems.append(f"metric '{metric}' found in raw extraction but missing from normalized output")

    for metric in metrics_not_traceable(normalized_text, raw_text):
        problems.append(f"metric '{metric}' appears in normalized output but not in raw extraction")

    for entry in extract_entries(normalized_text):
        if entry.org not in raw_text or entry.role not in raw_text:
            problems.append(f"entry '{entry.org} — {entry.role}' not clearly traceable to raw extraction")

    return problems
