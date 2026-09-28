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

_SYSTEM_PROMPT = """You are ranking and rewriting resume work-experience bullets to match a target job description.
CRITICAL RULES:
1. You will be given a list of work experience entries, each with an id, org, role, and its existing bullets.
2. Rank ALL of the given entries from most to least relevant to the job description -- every entry's id must appear in ranked_ids exactly once, ordered most relevant first. Code decides separately how many of your top-ranked entries actually get used.
3. For EVERY entry, rewrite each of its bullets individually to mirror the job description's vocabulary and keywords -- one rewritten bullet per original bullet, always. Do NOT combine two or more original bullets into a single rewritten bullet, even when they describe related work or the same project -- a bullet list that reads as one long run-on sentence is wrong regardless of how accurate its content is. You may omit a bullet only if it is genuinely irrelevant to the job description; otherwise every original bullet gets its own rewritten bullet in the output. Do NOT invent, hallucinate, or exaggerate any experience, skill, or metric. User Guidance may supply additional first-hand facts; use those only when clearly identified as user-supplied and only for the matching entry. The job description itself is never evidence of the user's experience. Do NOT add any outcome, result, or claim that isn't stated in the original bullets or in user-supplied facts, even if it sounds plausible.
4. Preserve every specific number, dollar amount, percentage, named tool or technology, and named award or recognition from the original bullets -- carry each one into the rewrite of whichever bullet it came from rather than summarizing it away or moving it to a different bullet.
5. You will see every entry's bullets together in this same request -- use that to vary sentence openings across ALL of them. Do NOT start two different bullets (whether in the same entry or different entries) with the same opening phrase, even when the job description itself repeats that phrase across multiple duty statements. Echoing the job description's own repeated wording verbatim into more than one bullet is exactly what this rule forbids -- mirror its vocabulary and keywords (rule 3), not its sentence-opening pattern.
6. Do NOT return org, role, dates, or location -- only ids and rewritten bullets.
7. Decide whether this job description has significant software/coding responsibility as a core duty (e.g. it asks for programming, software engineering, or building technical tools/systems yourself) -- not just incidental mentions of "data" or "technology". Set include_github to true only in that case, false otherwise.
8. Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences:
ranked_ids: [most_relevant_id, id2, ..., least_relevant_id]
bullets_by_id:
  id1: [rewritten bullet, rewritten bullet]
  id2: [rewritten bullet]
include_github: true or false"""

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
    """Returns {"ranked_ids": [...], "bullets_by_id": {...}, "include_github": bool},
    or None if the local Ollama call failed/timed out or the response
    wasn't the expected shape (spec §4, §8, §13b). `ranked_ids` (Revision
    6) replaces the earlier binary `included_ids` -- every entry is
    ranked, and `tailor_resume.py`'s render-measure-retry loop (§13b)
    decides how many of the top-ranked entries to actually use, based on
    how much fits the target page count. Only id/org/role/bullets are
    sent to the model -- no other metadata field ever reaches the LLM.
    `guidance` (spec §11) is optional free text -- typically a Q&A
    transcript from tailor_resume.py's --interactive flow -- inserted as
    one extra prompt section; when it's None (the default), the prompt is
    otherwise unchanged."""
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
    if not isinstance(parsed, dict) or "ranked_ids" not in parsed or "bullets_by_id" not in parsed:
        return None
    return parsed


def apply_tailoring(
    master: dict, tailoring_result: dict, bullet_budget: dict[str, int] | None = None,
) -> tuple[dict, list[str]]:
    """Reconstructs the tailored resume in code, never trusting the LLM
    for any metadata field (spec §4): copies contact/education/awards/
    publications/skills through unchanged, and builds work_experience
    from master entries looked up by id, splicing in the LLM's rewritten
    bullets. An id in ranked_ids not found in master is skipped and
    reported rather than crashing.

    `bullet_budget` (spec §13b, Revision 6 -- replaces the coarser
    `include_count: int` this parameter started as) maps an entry id to
    how many of its rewritten bullets to include; an id absent from the
    map is excluded entirely. `None` (the default) includes every ranked
    id with every one of its bullets, mainly for direct/test callers that
    don't need the fill loop. `tailor_resume.py`'s render-measure-retry
    fill loop (`_select_work_experience_bullets`) builds this map one
    bullet at a time, in rank order, so leftover page space gets filled
    with as much real content as fits -- confirmed real gap
    (2026-09-26): an earlier whole-entry-only version of this fill loop
    left a large blank gap at the bottom of page 1, because the *next*
    whole entry didn't fit even though there was clearly room left for
    more of it.

    Rank decides *which* entries are selected; it does NOT decide their
    display order -- the result is built by walking `master`'s own
    work_experience order and keeping only the selected ids, so the
    tailored resume stays in the master's normal (reverse-)chronological
    order like every real resume, regardless of relevance ranking. Real,
    confirmed bug this fixes (2026-09-26): ranking a later-dated sub-role
    ahead of the earlier one that actually carries their shared
    employer's dates (render.py's `_work_experience_display_dates`
    carry-forward, spec §6) broke that carry-forward once rank order
    could put the dateless sub-role first with no preceding same-org
    entry to inherit from.

    The one exception to "copied unchanged" is `contact.github_url`:
    confirmed real preference (2026-09-26) that the GitHub profile link
    is only worth showing when the job has significant coding
    responsibility. The LLM's `include_github` judgment (still never
    asked to *return* the URL itself, only a boolean) decides whether
    apply_tailoring blanks that one field; `_display()` in render.py
    already omits a blank/None contact field from the rendered PDF, so
    no render.py change is needed for this to take effect. Missing or
    non-bool `include_github` defaults to True -- unchanged behavior."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    include_github = tailoring_result.get("include_github")
    contact = dict(master.get("contact") or {})
    if include_github is False:
        contact["github_url"] = None
    bullets_by_id = tailoring_result.get("bullets_by_id") or {}
    ranked_ids = tailoring_result.get("ranked_ids") or []
    ids_to_include = ranked_ids if bullet_budget is None else [i for i in ranked_ids if i in bullet_budget]
    problems: list[str] = []
    for entry_id in ids_to_include:
        if entry_id not in master_by_id:
            problems.append(f"ranked id '{entry_id}' not found in master -- skipped")

    ids_to_include_set = set(ids_to_include)
    tailored_experience = []
    for source in master.get("work_experience") or []:
        if source["id"] not in ids_to_include_set:
            continue
        all_bullets = bullets_by_id.get(source["id"]) or source["bullets"]
        limit = None if bullet_budget is None else bullet_budget.get(source["id"])
        tailored_experience.append({
            "id": source["id"],
            "org": source["org"],
            "role": source["role"],
            "location": source["location"],
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "bullets": all_bullets if limit is None else all_bullets[:limit],
        })

    tailored = {
        "contact": contact,
        "work_experience": tailored_experience,
        "education": master.get("education"),
        "awards": master.get("awards"),
        "publications": master.get("publications"),
        "skills": master.get("skills"),
    }
    return tailored, problems
