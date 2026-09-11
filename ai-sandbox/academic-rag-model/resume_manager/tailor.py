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

from common.ollama_utils import call_ollama
from resume_manager.llm_yaml import parse_llm_yaml

RESUMEMANAGER_OLLAMA_MODEL = os.environ.get("RESUMEMANAGER_OLLAMA_MODEL", "qwen2.5:7b-instruct")
RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("RESUMEMANAGER_OLLAMA_TIMEOUT", "1800"))

_SYSTEM_PROMPT = """You are selecting and rewriting resume work-experience bullets to match a target job description.
CRITICAL RULES:
1. You will be given a list of work experience entries, each with an id, org, role, and its existing bullets.
2. Choose which entries are most relevant to the job description -- you do not need to include every entry.
3. For each entry you include, rewrite its bullets to mirror the job description's vocabulary and keywords. Do NOT invent, hallucinate, or exaggerate any experience, skill, or metric not already present in that entry's original bullets. Do NOT add any outcome, result, or claim that isn't stated in the original bullets, even if it sounds plausible.
4. Preserve every specific number, dollar amount, percentage, named tool or technology, and named award or recognition from the original bullets -- carry each one into your rewrite rather than summarizing it away. If you combine two original bullets into one, make sure every such detail from both survives in the result; if you cannot fit them all, keep the bullets separate instead of merging.
5. You will see every included entry's bullets together in this same request -- use that to vary sentence openings across ALL of them. Do NOT start two different bullets (whether in the same entry or different entries) with the same opening phrase, even when the job description itself repeats that phrase across multiple duty statements. Echoing the job description's own repeated wording verbatim into more than one bullet is exactly what this rule forbids -- mirror its vocabulary and keywords (rule 3), not its sentence-opening pattern.
6. Do NOT return org, role, dates, or location -- only ids and rewritten bullets.
7. Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences:
included_ids: [id1, id2, ...]
bullets_by_id:
  id1: [rewritten bullet, rewritten bullet]
  id2: [rewritten bullet]"""

_QUESTIONS_SYSTEM_PROMPT = """You are helping someone tailor their resume to a target job description.
Given their work experience entries and the job description below, write 2-4 short, open-ended
questions that would help decide which entries to emphasize and how to frame them for this
specific role. Do not ask about facts already visible in the entries or the job description --
ask about the person's own priorities and preferred framing instead.
Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences:
questions: [question one, question two]"""


def _build_entry_context(work_experience: list[dict]) -> str:
    lines = []
    for entry in work_experience:
        lines.append(f"id: {entry['id']}\norg: {entry['org']}\nrole: {entry['role']}\nbullets:")
        for bullet in entry.get("bullets") or []:
            lines.append(f"  - {bullet}")
    return "\n".join(lines)


def generate_clarifying_questions(
    master: dict, job_description: str, model: str = RESUMEMANAGER_OLLAMA_MODEL,
) -> list[str] | None:
    """Returns 2-4 open-ended questions grounded in the master's work
    experience entries and the job description, or None if the local
    Ollama call failed/timed out or the response wasn't the expected
    shape (spec §11) -- mirrors tailor_resume()'s own failure contract,
    so tailor_resume.py's --interactive flow handles both the same way:
    a warning and a fallback to no guidance, never a crash."""
    entry_context = _build_entry_context(master.get("work_experience") or [])
    prompt = (
        f"{_QUESTIONS_SYSTEM_PROMPT}\n\n### WORK EXPERIENCE ENTRIES:\n{entry_context}\n\n"
        f"### TARGET JOB DESCRIPTION:\n{job_description}"
    )
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    parsed = parse_llm_yaml(result)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("questions"), list):
        return None
    return parsed["questions"]


def tailor_resume(
    master: dict, job_description: str, model: str = RESUMEMANAGER_OLLAMA_MODEL, guidance: str | None = None,
) -> dict | None:
    """Returns {"included_ids": [...], "bullets_by_id": {...}}, or None if
    the local Ollama call failed/timed out or the response wasn't the
    expected shape (spec §4, §8). Only id/org/role/bullets are sent to the
    model -- no other metadata field ever reaches the LLM. `guidance`
    (spec §11) is optional free text -- typically a Q&A transcript from
    tailor_resume.py's --interactive flow -- inserted as one extra prompt
    section; when it's None (the default, and every call in this
    codebase before this revision), the prompt is byte-for-byte identical
    to before Revision 4."""
    entry_context = _build_entry_context(master.get("work_experience") or [])
    guidance_section = (
        f"\n\n### USER GUIDANCE (prioritize this when selecting entries and framing bullets):\n{guidance}"
        if guidance else ""
    )
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n### WORK EXPERIENCE ENTRIES:\n{entry_context}"
        f"{guidance_section}\n\n### TARGET JOB DESCRIPTION:\n{job_description}"
    )
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    parsed = parse_llm_yaml(result)
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
