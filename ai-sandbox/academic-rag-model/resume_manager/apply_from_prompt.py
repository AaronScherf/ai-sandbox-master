"""
apply_from_prompt.py
CLI entry point for tailoring from a rough, free-text opportunity
description rather than an already-written job description file (spec
§15, Revision 8). Turns that description into a job description and an
application name via one local Ollama call, brainstorms which of the
master resume's content is most relevant via one Gemini call (using its
larger context window against the full resume_master.yaml), then hands
off to tailor_resume.py's existing, unmodified run_tailoring() for the
actual tailor -> validate -> render pipeline.

The only script in this subproject that needs a Gemini API key --
convert_resume.py, tailor_resume.py, and merge_resumes.py remain fully
local.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from common.ollama_utils import call_ollama
from resume_manager.llm_yaml import parse_llm_yaml
from resume_manager.tailor import RESUMEMANAGER_OLLAMA_MODEL, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)

_GEMINI_MODEL = os.environ.get("RESUMEMANAGER_GEMINI_MODEL", "gemini-3.1-flash-lite")

_INTERPRET_SYSTEM_PROMPT = """You are turning a rough, free-text description of a job opportunity into a clean job description and a short application name.
Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences:
job_description: <a clean, complete job-description-style text based on what the input actually says -- do not invent responsibilities, qualifications, or requirements not implied by the input>
application_name: <a short name for this application, e.g. "Acme Corp Senior Analyst" -- combine the company name and role title if both are given, otherwise the role/opportunity alone>"""


def interpret_opportunity_prompt(prompt: str, model: str = RESUMEMANAGER_OLLAMA_MODEL) -> dict | None:
    """Turns a rough, free-text opportunity description into
    {"job_description": str, "application_name": str} via one local
    Ollama call. Returns None (never raises) if the call fails, times
    out, or the response isn't the expected shape -- mirrors every other
    local-Ollama-call contract in this subproject (spec §8)."""
    full_prompt = f"{_INTERPRET_SYSTEM_PROMPT}\n\n### ROUGH OPPORTUNITY DESCRIPTION:\n{prompt}"
    result = call_ollama(full_prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    parsed = parse_llm_yaml(result)
    if not isinstance(parsed, dict):
        return None
    job_description = parsed.get("job_description")
    application_name = parsed.get("application_name")
    if not isinstance(job_description, str) or not job_description.strip():
        return None
    if not isinstance(application_name, str) or not application_name.strip():
        return None
    return {"job_description": job_description.strip(), "application_name": application_name.strip()}


_BRAINSTORM_SYSTEM_PROMPT = """You are helping someone decide which parts of their resume are most relevant to a specific job opportunity, before it gets tailored.
Given their full master resume (below) and a target job description, identify which Work Experience entries, skills, and other resume content are most relevant to this opportunity, and why. Write your answer as free-text guidance for whoever tailors the resume next -- not as YAML or JSON.
Do not invent or assume any experience, skill, or fact not already present in the master resume."""


def brainstorm_relevant_content(client, master: dict, job_description: str, model: str = _GEMINI_MODEL) -> str | None:
    """Sends the full resume_master.yaml (as raw YAML text -- Gemini's
    larger context window means it doesn't need merge_resumes.py's
    trimmed _build_master_context() view built for a smaller local
    model) plus the job description to Gemini, asking it to brainstorm
    which resume content is most relevant. Returns free text suitable
    for tailor_resume()'s `guidance` parameter, or None (never raises)
    on any failure -- a Gemini outage degrades to no extra guidance
    rather than blocking tailoring, mirroring tailor_resume.py's own
    _collect_guidance() contract (spec §11)."""
    master_yaml_text = yaml.safe_dump(master, sort_keys=False, allow_unicode=True)
    prompt = (
        f"{_BRAINSTORM_SYSTEM_PROMPT}\n\n### FULL MASTER RESUME:\n{master_yaml_text}"
        f"\n\n### TARGET JOB DESCRIPTION:\n{job_description}"
    )
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as err:
        print(f"WARNING: Gemini brainstorm call failed ({err}) -- continuing without it.")
        return None
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        print("WARNING: Gemini brainstorm call returned no text -- continuing without it.")
        return None
    return text.strip()
