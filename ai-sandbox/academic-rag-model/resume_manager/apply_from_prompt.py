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

import argparse
import os
import tempfile
from pathlib import Path

import yaml

from common.gemini_utils import get_gemini_client, load_dotenv_override
from common.ollama_utils import call_ollama
from resume_manager.llm_yaml import parse_llm_yaml
from resume_manager.tailor import RESUMEMANAGER_OLLAMA_MODEL, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS
from resume_manager.tailor_resume import run_tailoring
from resume_manager.user_facts import load_user_facts

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)

_GEMINI_MODEL = os.environ.get("RESUMEMANAGER_GEMINI_MODEL", "gemini-3.1-flash-lite")

_INTERPRET_SYSTEM_PROMPT = """You are turning a rough, free-text description of a job opportunity into a clean job description and a short application name.
Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences, and no keys other than these two:
application_name: <a short name for this application, e.g. "Acme Corp Senior Analyst" -- combine the company name and role title if both are given, otherwise the role/opportunity alone>
job_description: |
  <a clean, complete job-description-style text based on what the input actually says -- do not invent responsibilities, qualifications, or requirements not implied by the input. Use the YAML block-scalar "|" style shown here (every line of the description indented under it), never a plain unindented multi-line value, since a real job description often spans multiple paragraphs and a plain scalar would silently cut it down to its first line.>"""


def interpret_opportunity_prompt(prompt: str, model: str = RESUMEMANAGER_OLLAMA_MODEL) -> dict | None:
    """Turns a rough, free-text opportunity description into
    {"job_description": str, "application_name": str} via one local
    Ollama call. Returns None (never raises) if the call fails, times
    out, or the response isn't the expected shape -- mirrors every other
    local-Ollama-call contract in this subproject (spec §8).

    Real, confirmed bug this guards against (found in code review
    2026-09-28): a model that writes `job_description` as an unindented
    multi-paragraph plain YAML scalar -- very natural, since a real job
    description often has a "Responsibilities:" section and blank
    lines -- gets it silently parsed down to just its first line, with
    the rest landing in unrelated top-level keys nothing here reads. No
    error, just a badly-targeted job description with no warning. The
    prompt above asks for a block scalar to avoid this; the check below
    rejects (returns None) any response carrying keys beyond the two
    expected ones, catching it even when the model doesn't comply."""
    full_prompt = f"{_INTERPRET_SYSTEM_PROMPT}\n\n### ROUGH OPPORTUNITY DESCRIPTION:\n{prompt}"
    result = call_ollama(full_prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    parsed = parse_llm_yaml(result)
    if not isinstance(parsed, dict):
        return None
    if not set(parsed.keys()) <= {"job_description", "application_name"}:
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
Do not invent or assume any experience, skill, or fact not already present in the master resume or explicitly supplied by the user in the tailoring instructions below. Keep user-supplied facts associated only with the entry they identify; do not infer additional claims from them."""


def brainstorm_relevant_content(
    client, master: dict, job_description: str, model: str = _GEMINI_MODEL,
    user_guidance: str | None = None, user_facts: list[dict] | None = None,
) -> str | None:
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
    user_guidance_section = (
        f"\n\n### USER-PROVIDED TAILORING INSTRUCTIONS AND FACTS:\n{user_guidance}"
        if user_guidance else ""
    )
    structured_facts_section = (
        "\n\n### ENTRY-SCOPED USER-CONFIRMED FACTS:\n"
        + yaml.safe_dump(user_facts, sort_keys=False, allow_unicode=True)
        if user_facts else ""
    )
    prompt = (
        f"{_BRAINSTORM_SYSTEM_PROMPT}\n\n### FULL MASTER RESUME:\n{master_yaml_text}"
        f"\n\n### TARGET JOB DESCRIPTION:\n{job_description}{user_guidance_section}{structured_facts_section}"
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


def create_application_from_prompt(
    prompt: str, resume_manager_dir: str, gemini_client=None,
    ollama_model: str = RESUMEMANAGER_OLLAMA_MODEL, gemini_model: str = _GEMINI_MODEL,
    user_guidance: str | None = None, user_facts: list[dict] | None = None,
) -> str:
    """Orchestrates all three stages (spec §15) and returns the same
    one-line status message run_tailoring() returns. Raises RuntimeError
    up front if Stage 1 fails -- there is no job description to proceed
    with, so no Gemini call is made and no application folder is
    created, mirroring run_tailoring()'s own upfront-failure posture for
    a missing file (spec §8). `gemini_client` is optional -- pass None
    (e.g. no GEMINI_API_KEY configured) to skip Stage 2 entirely, which
    still runs Stage 3 with the user's guidance, if supplied, as its only
    guidance. `user_guidance` steers both Gemini's relevance brainstorm and
    the local tailoring call; it is retained even if the Gemini call fails."""
    master_resume_path = os.path.join(resume_manager_dir, "resume_master.yaml")
    with open(master_resume_path, "r", encoding="utf-8") as f:
        master = yaml.safe_load(f)

    interpreted = interpret_opportunity_prompt(prompt, ollama_model)
    if interpreted is None:
        raise RuntimeError(
            "local Ollama call to interpret the opportunity description failed, timed out, or returned "
            "an unexpected response -- is `ollama serve` running?"
        )

    guidance = None
    brainstorm_status = "skipped (no Gemini client configured)"
    if gemini_client is not None:
        guidance = brainstorm_relevant_content(
            gemini_client, master, interpreted["job_description"], gemini_model,
            user_guidance=user_guidance, user_facts=user_facts,
        )
        brainstorm_status = "succeeded" if guidance else "failed; local tailoring continued without Gemini brainstorm"
    if user_guidance:
        guidance = f"{guidance}\n\n{user_guidance}" if guidance else user_guidance

    with tempfile.TemporaryDirectory() as tmp_dir:
        jd_path = os.path.join(tmp_dir, "job_description.txt")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write(interpreted["job_description"])
        return run_tailoring(
            master_resume_path, jd_path, interpreted["application_name"], resume_manager_dir, guidance=guidance,
            user_facts=user_facts, brainstorm_status=brainstorm_status,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tailor the master resume from a rough, free-text opportunity description.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="Inline free-text description of the opportunity.")
    group.add_argument("--prompt-file", help="Path to a local text file containing the description.")
    parser.add_argument("--resume-manager-dir", default=str(_DEFAULT_RESUME_MANAGER_DIR))
    parser.add_argument(
        "--use-paid-key", action="store_true",
        help="Use PAID_GEMINI_KEY from ai-sandbox/.env instead of GEMINI_API_KEY -- for when the "
             "default key is pointed at a free-tier project for other work (see gemini_utils.get_gemini_client).",
    )
    guidance_group = parser.add_mutually_exclusive_group()
    guidance_group.add_argument(
        "--guidance", help="Extra tailoring instructions or user-confirmed facts to pass through both model steps.",
    )
    guidance_group.add_argument(
        "--guidance-file", help="Path to a text file containing extra tailoring instructions or user-confirmed facts.",
    )
    parser.add_argument(
        "--facts-file", help="YAML file with entry-scoped, user-confirmed facts and required coverage concepts.",
    )
    args = parser.parse_args()

    if args.prompt is not None:
        prompt_text = args.prompt
    else:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read()

    if args.guidance is not None:
        user_guidance = args.guidance
    elif args.guidance_file is not None:
        with open(args.guidance_file, "r", encoding="utf-8") as f:
            user_guidance = f.read()
    else:
        user_guidance = None

    load_dotenv_override()
    gemini_client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
    if gemini_client is None:
        print("WARNING: no Gemini client available -- continuing without the relevance brainstorm step.")

    user_facts = None
    if args.facts_file:
        with open(os.path.join(args.resume_manager_dir, "resume_master.yaml"), "r", encoding="utf-8") as f:
            master = yaml.safe_load(f)
        user_facts = load_user_facts(args.facts_file, master)

    print(create_application_from_prompt(
        prompt_text, args.resume_manager_dir, gemini_client=gemini_client, user_guidance=user_guidance,
        user_facts=user_facts,
    ))


if __name__ == "__main__":
    main()
