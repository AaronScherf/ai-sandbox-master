"""
tailor.py
Given the master resume and a job description, produces a tailored
Markdown resume via a local Ollama model -- no fabrication, mirrors
the JD's vocabulary, preserves structure/dates/contact info exactly
(spec §4).
"""
from __future__ import annotations

import os

from common.ollama_utils import call_ollama

RESUMEMANAGER_OLLAMA_MODEL = os.environ.get("RESUMEMANAGER_OLLAMA_MODEL", "qwen2.5:7b-instruct")
RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("RESUMEMANAGER_OLLAMA_TIMEOUT", "300"))

_SYSTEM_PROMPT = """You are an expert resume optimizer. Your task is to tailor a master resume to perfectly match a target job description.
CRITICAL RULES:
1. Do NOT invent, hallucinate, or exaggerate any experience, skills, or metrics.
2. Rewrite existing bullet points to mirror the vocabulary, keywords, and phrasing of the job description.
3. Keep the exact same structure, dates, and contact information.
4. Output your response ONLY as valid Markdown text. Do not include conversational intros or outros."""


def tailor_resume(
    master_resume: str, job_description: str, model: str = RESUMEMANAGER_OLLAMA_MODEL,
) -> str | None:
    """Returns the tailored Markdown, or None if the local Ollama call
    failed/timed out (spec §8) -- caller decides what to do."""
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n### MASTER RESUME:\n{master_resume}\n\n"
        f"### TARGET JOB DESCRIPTION:\n{job_description}\n\n"
        f"Please optimize the resume based on the rules provided."
    )
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    return result if isinstance(result, str) else None
