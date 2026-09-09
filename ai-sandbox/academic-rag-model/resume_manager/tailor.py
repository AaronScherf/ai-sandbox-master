"""
tailor.py
Given the master resume and a job description, an LLM call selects which
Work Experience entries to highlight and rewrites their bullets -- and
returns ONLY ids and bullets, never a metadata field (spec §4 Revision 2).
apply_tailoring() then reconstructs the full tailored resume in code,
copying every other field verbatim from the master, so metadata
fabrication during tailoring is structurally impossible.
"""
from __future__ import annotations

import os

import yaml

from common.ollama_utils import call_ollama

RESUMEMANAGER_OLLAMA_MODEL = os.environ.get("RESUMEMANAGER_OLLAMA_MODEL", "qwen2.5:7b-instruct")
RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("RESUMEMANAGER_OLLAMA_TIMEOUT", "1800"))

_SYSTEM_PROMPT = """You are selecting and rewriting resume work-experience bullets to match a target job description.
CRITICAL RULES:
1. You will be given a list of work experience entries, each with an id, org, role, and its existing bullets.
2. Choose which entries are most relevant to the job description -- you do not need to include every entry.
3. For each entry you include, rewrite its bullets to mirror the job description's vocabulary and keywords. Do NOT invent, hallucinate, or exaggerate any experience, skill, or metric not already present in that entry's original bullets.
4. Do NOT return org, role, dates, or location -- only ids and rewritten bullets.
5. Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences:
included_ids: [id1, id2, ...]
bullets_by_id:
  id1: [rewritten bullet, rewritten bullet]
  id2: [rewritten bullet]"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def _build_entry_context(work_experience: list[dict]) -> str:
    lines = []
    for entry in work_experience:
        lines.append(f"id: {entry['id']}\norg: {entry['org']}\nrole: {entry['role']}\nbullets:")
        for bullet in entry.get("bullets") or []:
            lines.append(f"  - {bullet}")
    return "\n".join(lines)


def tailor_resume(master: dict, job_description: str, model: str = RESUMEMANAGER_OLLAMA_MODEL) -> dict | None:
    """Returns {"included_ids": [...], "bullets_by_id": {...}}, or None if
    the local Ollama call failed/timed out or the response wasn't the
    expected shape (spec §4, §8). Only id/org/role/bullets are sent to the
    model -- no other metadata field ever reaches the LLM."""
    entry_context = _build_entry_context(master.get("work_experience") or [])
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n### WORK EXPERIENCE ENTRIES:\n{entry_context}\n\n"
        f"### TARGET JOB DESCRIPTION:\n{job_description}"
    )
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    try:
        parsed = yaml.safe_load(_strip_code_fence(result))
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict) or "included_ids" not in parsed or "bullets_by_id" not in parsed:
        return None
    return parsed


def apply_tailoring(master: dict, tailoring_result: dict) -> tuple[dict, list[str]]:
    """Reconstructs the tailored resume in code, never trusting the LLM
    for any metadata field (spec §4): copies contact/education/awards/
    publications/skills through unchanged, and builds work_experience
    from master entries looked up by id, splicing in the LLM's rewritten
    bullets. An id in included_ids not found in master is skipped and
    reported rather than crashing."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    bullets_by_id = tailoring_result.get("bullets_by_id") or {}
    problems: list[str] = []
    tailored_experience = []
    for entry_id in tailoring_result.get("included_ids") or []:
        source = master_by_id.get(entry_id)
        if source is None:
            problems.append(f"included id '{entry_id}' not found in master -- skipped")
            continue
        tailored_experience.append({
            "id": source["id"],
            "org": source["org"],
            "role": source["role"],
            "location": source["location"],
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "bullets": bullets_by_id.get(entry_id, source["bullets"]),
        })

    tailored = {
        "contact": master.get("contact"),
        "work_experience": tailored_experience,
        "education": master.get("education"),
        "awards": master.get("awards"),
        "publications": master.get("publications"),
        "skills": master.get("skills"),
    }
    return tailored, problems
