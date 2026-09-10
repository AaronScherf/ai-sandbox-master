"""
normalize.py
One local-LLM extraction pass turning the raw page-tagged extraction
(extract.py) into the master resume's structured schema (schema.py) --
Revision 2 of spec §3 steps 3-4. Verified against the raw extraction
before being trusted.
"""
from __future__ import annotations

import os

from common.ollama_utils import call_ollama
from resume_manager.llm_yaml import parse_llm_yaml
from resume_manager.schema import (
    AWARDS_REQUIRED, CONTACT_REQUIRED, EDUCATION_REQUIRED, PUBLICATIONS_REQUIRED,
    SKILLS_LIST_FIELDS, SKILLS_REQUIRED, WORK_EXPERIENCE_LIST_FIELDS, WORK_EXPERIENCE_REQUIRED,
    verify_entry_fields,
)

OLLAMA_MODEL = os.environ.get("RESUMEMANAGER_OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("RESUMEMANAGER_OLLAMA_TIMEOUT", "1800"))

_SCHEMA_TEMPLATE = """contact:
  name: str
  location: str
  email: str
  linkedin_url: str
  github_url: str
  website_url: str
work_experience:
  - org: str
    role: str
    location: str
    start_date: str
    end_date: str  # or "Present"
    bullets: [str]
education:
  - institution: str
    degree: str
    gpa: str            # omit this key entirely if not present in the source
    location: str
    start_date: str
    end_date: str
    thesis: str          # omit this key entirely if not present in the source
awards:
  - name: str
    description: str
    date: str
publications:
  - title: str
    date: str
    venue: str
    link: str             # omit this key entirely if not present in the source
skills:
  - category: str
    items: [str]"""

_SYSTEM_PROMPT = f"""You are extracting a resume's raw text into a strict YAML structure.
CRITICAL RULES:
1. Preserve every word, number, and date exactly as written. Do not summarize, paraphrase, or reword anything.
2. Do not invent a value for any field the raw text doesn't contain -- omit optional fields (gpa, thesis, link) instead of guessing. Never write a bare "-" as a field's value.
3. Follow this exact schema (field names and nesting):
{_SCHEMA_TEMPLATE}
4. Output ONLY valid YAML -- no commentary, no markdown code fences."""


def extract_resume_schema(raw_text: str, model: str = OLLAMA_MODEL) -> dict | None:
    """Calls a local Ollama model to extract raw_text into the schema
    above, returning the parsed dict, or None if the Ollama call failed/
    timed out or the response wasn't valid YAML (spec §3 step 3, §8)."""
    prompt = f"{_SYSTEM_PROMPT}\n\n### RAW EXTRACTED RESUME TEXT:\n{raw_text}"
    result = call_ollama(prompt, model, OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    parsed = parse_llm_yaml(result)
    return parsed if isinstance(parsed, dict) else None


def verify_extraction(parsed: dict, raw_text: str) -> list[str]:
    """Schema-level verification (spec §3 step 4): every required field on
    every entry must be non-empty and traceable to raw_text. Returns a
    list of human-readable problems; empty means a clean pass."""
    problems: list[str] = []
    problems += verify_entry_fields(parsed.get("contact") or {}, raw_text, CONTACT_REQUIRED)
    for entry in parsed.get("work_experience") or []:
        problems += verify_entry_fields(entry, raw_text, WORK_EXPERIENCE_REQUIRED, WORK_EXPERIENCE_LIST_FIELDS)
    for entry in parsed.get("education") or []:
        problems += verify_entry_fields(entry, raw_text, EDUCATION_REQUIRED)
    for entry in parsed.get("awards") or []:
        problems += verify_entry_fields(entry, raw_text, AWARDS_REQUIRED)
    for entry in parsed.get("publications") or []:
        problems += verify_entry_fields(entry, raw_text, PUBLICATIONS_REQUIRED)
    for entry in parsed.get("skills") or []:
        problems += verify_entry_fields(entry, raw_text, SKILLS_REQUIRED, SKILLS_LIST_FIELDS)
    return problems
