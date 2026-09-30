# Tailoring from a Rough Opportunity Description Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `resume_manager/apply_from_prompt.py`, a new CLI that turns a rough, free-text opportunity description into a fully tailored application, using a local Ollama call to produce a job description + application name, a Gemini call to brainstorm which master-resume content is relevant, and the existing `tailor_resume.py` pipeline for the actual tailoring/validation/rendering.

**Architecture:** Three stages, each owning exactly one job: `interpret_opportunity_prompt()` (local Ollama) turns rough text into a clean job description + short name; `brainstorm_relevant_content()` (Gemini, via the existing `common/gemini_utils.py`) matches the full `resume_master.yaml` against that job description and returns free-text guidance; `create_application_from_prompt()` writes the job description to a temp file and calls the existing, unmodified `run_tailoring()`. No changes to `tailor.py`, `render.py`, `validate.py`, or `merge_resumes.py`.

**Tech Stack:** Python 3.13, existing `common/ollama_utils.py` (local Ollama HTTP calls) and `common/gemini_utils.py` (Gemini Developer API via `google-genai`), PyYAML, argparse.

**Spec:** `docs/superpowers/specs/2026-09-09-resume-manager-design.md` §15 ("Tailoring from a rough opportunity description", Revision 8) — executors should read both this plan and that section before starting.

## Global Constraints

- `GEMINI_API_KEY` (or `PAID_GEMINI_KEY`, same override every other Gemini caller in this repo supports) is required only to run `apply_from_prompt.py` — `convert_resume.py`, `tailor_resume.py`, and `merge_resumes.py` stay fully local, unaffected by this feature.
- Do not modify `resume_manager/tailor.py`, `resume_manager/render.py`, `resume_manager/validate.py`, or `resume_manager/merge_resumes.py` — the spec confirms none of them need changes.
- `run_tailoring()` (`resume_manager/tailor_resume.py`) must be called exactly as it exists today, unmodified: `run_tailoring(master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str, guidance: str | None = None) -> str`. (Corrected 2026-09-28, found in code review: this line previously listed a stray `target_pages: int = 2` parameter that `run_tailoring()` doesn't actually have on this branch — Tasks 3-4's own code never passed one, so this was a documentation-only inaccuracy.)
- Every new LLM-calling function (`interpret_opportunity_prompt`, `brainstorm_relevant_content`) must never raise on a bad/unreachable/malformed response — return `None` instead, matching every existing local-call contract in this subproject (spec §8, §11).
- Gemini's brainstorm output is free text (the same shape `tailor_resume()`'s `guidance` parameter already accepts) — never structured YAML/JSON, since nothing downstream parses it further.
- `_GEMINI_MODEL` defaults to `"gemini-3.1-flash-lite"` (flash-tier — a relevance-matching task doesn't need pro-tier reasoning), overridable via a `RESUMEMANAGER_GEMINI_MODEL` env var, matching this subproject's existing `RESUMEMANAGER_OLLAMA_MODEL` override convention.
- New test file: `tests/test_apply_from_prompt.py` (flat, matching this repo's `tests/` convention — not mirrored by package).

## Review Focus

- A Gemini call that raises (network error, quota, bad auth) must not crash the whole run — Stage 2 degrades to `guidance=None` and Stage 3 still runs. (Task 2)
- Stage 1's response can be valid YAML but still missing `job_description` or `application_name` (or have one as an empty string) — must return `None`, not a dict that later hands `run_tailoring()` a blank application name. (Task 1)
- No `GEMINI_API_KEY` configured at all (the expected common case for a first run, before the user sets it up) — `create_application_from_prompt(gemini_client=None)` must still complete Stage 3 successfully. (Task 3)
- The CLI is given neither `--prompt` nor `--prompt-file`, or both — argparse must reject this clearly rather than silently preferring one. (Task 4)
- `--prompt-file` points at a path that doesn't exist — must fail with a clear, unambiguous error, not a confusing downstream failure inside the Ollama call. (Task 4)

---

### Task 1: `interpret_opportunity_prompt()` — local Ollama call

**Files:**
- Create: `resume_manager/apply_from_prompt.py`
- Test: `tests/test_apply_from_prompt.py`

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama(prompt: str, model: str, request_timeout: int) -> str | None | OllamaTimeout`; `resume_manager.llm_yaml.parse_llm_yaml(text: str) -> object | None`; `resume_manager.tailor.RESUMEMANAGER_OLLAMA_MODEL: str`, `resume_manager.tailor.RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS: int`.
- Produces: `interpret_opportunity_prompt(prompt: str, model: str = RESUMEMANAGER_OLLAMA_MODEL) -> dict | None`, returning `{"job_description": str, "application_name": str}` on success. Task 3 calls this directly.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_apply_from_prompt.py`:

```python
import unittest
from unittest.mock import patch

from resume_manager.apply_from_prompt import interpret_opportunity_prompt


class TestInterpretOpportunityPrompt(unittest.TestCase):
    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_well_formed_response_returns_job_description_and_name(self, mock_call):
        mock_call.return_value = (
            "job_description: A senior data analyst role focused on fraud detection at a mid-size fintech.\n"
            "application_name: Fintech Co Senior Data Analyst"
        )
        result = interpret_opportunity_prompt("senior data analyst, fraud detection, mid-size fintech")
        self.assertEqual(
            result,
            {
                "job_description": "A senior data analyst role focused on fraud detection at a mid-size fintech.",
                "application_name": "Fintech Co Senior Data Analyst",
            },
        )

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_prompt_includes_the_rough_description(self, mock_call):
        mock_call.return_value = "job_description: JD text\napplication_name: A Name"
        interpret_opportunity_prompt("a rough one-line description of the role")
        prompt_arg = mock_call.call_args[0][0]
        self.assertIn("a rough one-line description of the role", prompt_arg)

    @patch("resume_manager.apply_from_prompt.call_ollama", return_value=None)
    def test_unreachable_ollama_returns_none(self, mock_call):
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama", return_value="not: [valid: yaml: at all")
    def test_malformed_yaml_returns_none(self, mock_call):
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_missing_application_name_key_returns_none(self, mock_call):
        mock_call.return_value = "job_description: Some JD text"
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_missing_job_description_key_returns_none(self, mock_call):
        mock_call.return_value = "application_name: A Name"
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_blank_application_name_returns_none(self, mock_call):
        # Real failure mode this guards against: a technically-present but
        # empty/whitespace-only field would otherwise flow through to
        # run_tailoring() as a blank application folder name.
        mock_call.return_value = 'job_description: Some JD text\napplication_name: "   "'
        self.assertIsNone(interpret_opportunity_prompt("a description"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.apply_from_prompt'` (the file doesn't exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `resume_manager/apply_from_prompt.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add resume_manager/apply_from_prompt.py tests/test_apply_from_prompt.py
git commit -m "feat(resume-manager): add interpret_opportunity_prompt for apply_from_prompt"
```

---

### Task 2: `brainstorm_relevant_content()` — Gemini call

**Files:**
- Modify: `resume_manager/apply_from_prompt.py`
- Test: `tests/test_apply_from_prompt.py`

**Interfaces:**
- Consumes: a Gemini client object shaped like `common.gemini_utils.get_gemini_client()`'s return value — specifically `client.models.generate_content(model: str, contents: str) -> object` where the response object has a `.text: str` attribute (same shape `notes/transcribe_notes.py`'s `_call_gemini_single_page()` already relies on).
- Produces: `brainstorm_relevant_content(client, master: dict, job_description: str, model: str = _GEMINI_MODEL) -> str | None`. Task 3 calls this directly, passing `client=None`-guarded (Task 3 skips calling this function at all when it has no client, rather than this function handling `client=None` itself).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_apply_from_prompt.py`. Change the existing
`from unittest.mock import patch` line (added in Task 1) to
`from unittest.mock import MagicMock, patch`, and add:

```python
from resume_manager.apply_from_prompt import brainstorm_relevant_content

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [{
        "id": "acme-1", "org": "Acme", "role": "Fraud Analyst", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Reduced fraud losses 20%"],
    }],
    "education": [], "awards": [], "publications": [], "skills": [],
}


def _fake_gemini_response(text):
    response = MagicMock()
    response.text = text
    return response


class TestBrainstormRelevantContent(unittest.TestCase):
    def test_well_formed_response_is_returned_stripped(self):
        client = MagicMock()
        client.models.generate_content.return_value = _fake_gemini_response(
            "  Your Acme fraud analyst role is directly relevant -- lead with it.  \n"
        )
        result = brainstorm_relevant_content(client, _MASTER, "A fraud detection analyst role.")
        self.assertEqual(result, "Your Acme fraud analyst role is directly relevant -- lead with it.")

    def test_prompt_includes_master_resume_and_job_description(self):
        client = MagicMock()
        client.models.generate_content.return_value = _fake_gemini_response("guidance text")
        brainstorm_relevant_content(client, _MASTER, "A fraud detection analyst role.")
        call_kwargs = client.models.generate_content.call_args.kwargs
        self.assertIn("Fraud Analyst", call_kwargs["contents"])
        self.assertIn("A fraud detection analyst role.", call_kwargs["contents"])

    def test_exception_from_generate_content_returns_none(self):
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
        self.assertIsNone(brainstorm_relevant_content(client, _MASTER, "A job description."))

    def test_blank_response_text_returns_none(self):
        client = MagicMock()
        client.models.generate_content.return_value = _fake_gemini_response("   ")
        self.assertIsNone(brainstorm_relevant_content(client, _MASTER, "A job description."))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v -k Brainstorm`
Expected: FAIL with `ImportError: cannot import name 'brainstorm_relevant_content'`

- [ ] **Step 3: Write the minimal implementation**

Add to `resume_manager/apply_from_prompt.py` (below `interpret_opportunity_prompt`):

```python
import yaml

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
```

Move the `import yaml` line to the top of the file with the other imports rather than leaving it inline.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v`
Expected: PASS (all 11 tests so far)

- [ ] **Step 5: Commit**

```bash
git add resume_manager/apply_from_prompt.py tests/test_apply_from_prompt.py
git commit -m "feat(resume-manager): add brainstorm_relevant_content Gemini call"
```

---

### Task 3: `create_application_from_prompt()` — orchestration

**Files:**
- Modify: `resume_manager/apply_from_prompt.py`
- Test: `tests/test_apply_from_prompt.py`

**Interfaces:**
- Consumes: `interpret_opportunity_prompt()` and `brainstorm_relevant_content()` from Tasks 1-2 (both patched at `resume_manager.apply_from_prompt.<name>` in tests); `resume_manager.tailor_resume.run_tailoring(master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str, guidance: str | None = None) -> str` (patched at `resume_manager.apply_from_prompt.run_tailoring`; see Global Constraints for the `target_pages` correction).
- Produces: `create_application_from_prompt(prompt: str, resume_manager_dir: str, gemini_client=None, ollama_model: str = RESUMEMANAGER_OLLAMA_MODEL, gemini_model: str = _GEMINI_MODEL) -> str`. Task 4's `main()` calls this directly.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_apply_from_prompt.py`:

```python
import os
import tempfile

import yaml

from resume_manager.apply_from_prompt import create_application_from_prompt


class TestCreateApplicationFromPrompt(unittest.TestCase):
    def _write_master(self, tmp):
        resume_manager_dir = os.path.join(tmp, "resume-manager")
        os.makedirs(resume_manager_dir, exist_ok=True)
        with open(os.path.join(resume_manager_dir, "resume_master.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(_MASTER, f)
        return resume_manager_dir

    @patch("resume_manager.apply_from_prompt.brainstorm_relevant_content", return_value="Lead with Acme.")
    @patch(
        "resume_manager.apply_from_prompt.interpret_opportunity_prompt",
        return_value={"job_description": "A fraud analyst role.", "application_name": "Acme Fraud Analyst"},
    )
    @patch("resume_manager.apply_from_prompt.run_tailoring")
    def test_full_pipeline_calls_run_tailoring_with_derived_args(self, mock_run, mock_interpret, mock_brainstorm):
        # jd_path is inside a `with tempfile.TemporaryDirectory()` block
        # that's cleaned up before create_application_from_prompt()
        # returns, so its content must be captured *during* the mocked
        # call (via side_effect), not read afterward -- reading it after
        # the fact would hit a deleted file.
        captured = {}

        def _capture_jd_and_return(master_resume_path, jd_path, application_name, resume_manager_dir_arg, guidance=None):
            with open(jd_path, encoding="utf-8") as f:
                captured["job_description"] = f.read()
            return "Wrote a PDF."

        mock_run.side_effect = _capture_jd_and_return

        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)
            client = MagicMock()

            result = create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=client)

            self.assertEqual(result, "Wrote a PDF.")
            mock_run.assert_called_once()
            call_args = mock_run.call_args.args
            self.assertEqual(call_args[2], "Acme Fraud Analyst")  # application_name
            self.assertEqual(call_args[3], resume_manager_dir)
            self.assertEqual(mock_run.call_args.kwargs["guidance"], "Lead with Acme.")
            self.assertEqual(captured["job_description"], "A fraud analyst role.")
            mock_brainstorm.assert_called_once()

    @patch("resume_manager.apply_from_prompt.interpret_opportunity_prompt", return_value=None)
    def test_stage_1_failure_raises_and_never_calls_gemini_or_run_tailoring(self, mock_interpret):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)
            client = MagicMock()
            with self.assertRaises(RuntimeError):
                create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=client)
            client.models.generate_content.assert_not_called()

    @patch("resume_manager.apply_from_prompt.run_tailoring", return_value="Wrote a PDF.")
    @patch(
        "resume_manager.apply_from_prompt.interpret_opportunity_prompt",
        return_value={"job_description": "A fraud analyst role.", "application_name": "Acme Fraud Analyst"},
    )
    def test_no_gemini_client_skips_stage_2_but_still_tailors(self, mock_interpret, mock_run):
        # Real, expected case: no GEMINI_API_KEY configured yet.
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)

            result = create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=None)

            self.assertEqual(result, "Wrote a PDF.")
            self.assertIsNone(mock_run.call_args.kwargs["guidance"])

    @patch("resume_manager.apply_from_prompt.run_tailoring", return_value="Wrote a PDF.")
    @patch("resume_manager.apply_from_prompt.brainstorm_relevant_content", return_value=None)
    @patch(
        "resume_manager.apply_from_prompt.interpret_opportunity_prompt",
        return_value={"job_description": "A fraud analyst role.", "application_name": "Acme Fraud Analyst"},
    )
    def test_stage_2_failure_still_tailors_with_no_guidance(self, mock_interpret, mock_brainstorm, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)
            client = MagicMock()

            result = create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=client)

            self.assertEqual(result, "Wrote a PDF.")
            self.assertIsNone(mock_run.call_args.kwargs["guidance"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v -k CreateApplication`
Expected: FAIL with `ImportError: cannot import name 'create_application_from_prompt'`

- [ ] **Step 3: Write the minimal implementation**

Add to `resume_manager/apply_from_prompt.py`:

```python
import tempfile

import yaml

from resume_manager.tailor_resume import run_tailoring


def create_application_from_prompt(
    prompt: str, resume_manager_dir: str, gemini_client=None,
    ollama_model: str = RESUMEMANAGER_OLLAMA_MODEL, gemini_model: str = _GEMINI_MODEL,
) -> str:
    """Orchestrates all three stages (spec §15) and returns the same
    one-line status message run_tailoring() returns. Raises RuntimeError
    up front if Stage 1 fails -- there is no job description to proceed
    with, so no Gemini call is made and no application folder is
    created, mirroring run_tailoring()'s own upfront-failure posture for
    a missing file (spec §8). `gemini_client` is optional -- pass None
    (e.g. no GEMINI_API_KEY configured) to skip Stage 2 entirely, which
    still runs Stage 3 with guidance=None."""
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
    if gemini_client is not None:
        guidance = brainstorm_relevant_content(gemini_client, master, interpreted["job_description"], gemini_model)

    with tempfile.TemporaryDirectory() as tmp_dir:
        jd_path = os.path.join(tmp_dir, "job_description.txt")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write(interpreted["job_description"])
        return run_tailoring(
            master_resume_path, jd_path, interpreted["application_name"], resume_manager_dir, guidance=guidance,
        )
```

Move the `import tempfile` and `from resume_manager.tailor_resume import run_tailoring` lines to the top of the file with the other imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v`
Expected: PASS (all 15 tests so far)

- [ ] **Step 5: Commit**

```bash
git add resume_manager/apply_from_prompt.py tests/test_apply_from_prompt.py
git commit -m "feat(resume-manager): add create_application_from_prompt orchestration"
```

---

### Task 4: CLI (`main()`)

**Files:**
- Modify: `resume_manager/apply_from_prompt.py`

**Interfaces:**
- Consumes: `create_application_from_prompt()` from Task 3; `common.gemini_utils.load_dotenv_override() -> None` and `common.gemini_utils.get_gemini_client(key_env_var: str = "GEMINI_API_KEY") -> object | None`.
- Produces: `main() -> None`, the module's `if __name__ == "__main__":` entry point. Nothing else depends on this.

This subproject doesn't unit-test its CLI `main()` functions directly (confirmed: `tests/test_tailor_resume_cli.py` only imports and tests `run_tailoring()` and its other underlying functions, never `tailor_resume.main`) — this task is verified manually instead, matching that precedent.

- [ ] **Step 1: Write the implementation**

Add to `resume_manager/apply_from_prompt.py`:

```python
import argparse

from common.gemini_utils import get_gemini_client, load_dotenv_override


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tailor the master resume from a rough, free-text opportunity description.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="Inline free-text description of the opportunity.")
    group.add_argument("--prompt-file", help="Path to a local text file containing the description.")
    parser.add_argument("--resume-manager-dir", default=str(_DEFAULT_RESUME_MANAGER_DIR))
    args = parser.parse_args()

    if args.prompt is not None:
        prompt_text = args.prompt
    else:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read()

    load_dotenv_override()
    gemini_client = get_gemini_client()
    if gemini_client is None:
        print("WARNING: no Gemini client available -- continuing without the relevance brainstorm step.")

    print(create_application_from_prompt(prompt_text, args.resume_manager_dir, gemini_client=gemini_client))


if __name__ == "__main__":
    main()
```

Move the `import argparse` and `from common.gemini_utils import get_gemini_client, load_dotenv_override` lines to the top of the file with the other imports. At this point, review the full file's import block and reorder it to the file's final shape:

```python
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
```

- [ ] **Step 2: Run the full test file to confirm nothing broke while reordering imports**

Run: `.venv/Scripts/python -m pytest tests/test_apply_from_prompt.py -v`
Expected: PASS (all 15 tests)

- [ ] **Step 3: Manually verify the CLI's argument handling**

Run: `.venv/Scripts/python -m resume_manager.apply_from_prompt --help`
Expected: prints usage showing `--prompt`, `--prompt-file`, and `--resume-manager-dir`, with `--prompt`/`--prompt-file` shown as a mutually exclusive, required group.

Run: `.venv/Scripts/python -m resume_manager.apply_from_prompt`
Expected: argparse error — one of `--prompt`/`--prompt-file` is required.

Run: `.venv/Scripts/python -m resume_manager.apply_from_prompt --prompt "x" --prompt-file "y.txt"`
Expected: argparse error — mutually exclusive arguments not allowed together.

Run: `.venv/Scripts/python -m resume_manager.apply_from_prompt --prompt-file does-not-exist.txt`
Expected: a clear `FileNotFoundError` naming `does-not-exist.txt`, raised before any Ollama or Gemini call.

- [ ] **Step 4: Run the full project test suite**

Run: `.venv/Scripts/python -m pytest tests/ -q`
Expected: all tests pass (this new module must not affect anything else, since `tailor.py`/`render.py`/`validate.py`/`merge_resumes.py` are untouched).

- [ ] **Step 5: Commit**

```bash
git add resume_manager/apply_from_prompt.py
git commit -m "feat(resume-manager): add apply_from_prompt CLI"
```

---

### Task 5: Document the routing decision in `README.md`

**Files:**
- Modify: `resume_manager/README.md`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — this is documentation only, read by whichever agent handles a "tailor my resume for this opportunity" request (spec §15's Routing section).

- [ ] **Step 1: Add a new section to `resume_manager/README.md`**

Insert a new `## Tailoring from a rough opportunity description` section immediately after the existing `## Per application` section (before `## Requirements`):

```markdown
## Tailoring from a rough opportunity description

```powershell
.\.venv\Scripts\python.exe -m resume_manager.apply_from_prompt --prompt "senior data analyst role at a mid-size fintech, focused on fraud detection"
```

or `--prompt-file path\to\notes.txt` for a longer, multi-paragraph description.
Turns a rough description into a job description and application name via
one local Ollama call, brainstorms which of your master resume's content
is most relevant via one Gemini call (needs `GEMINI_API_KEY` or
`PAID_GEMINI_KEY` in `../.env` — this is the only script in this
subproject that does), then runs the same tailor → validate → render
pipeline as `tailor_resume.py` above. If no Gemini key is configured, it
still completes, just without the extra relevance brainstorm.

**If you're an agent handling a "tailor my resume for this opportunity"
request:** which of the three tailoring entry points to use is a
judgment call based on what you were actually given, not something to
guess mechanically:
1. **You already have (or can find) a saved job description file** — the
   user names a path, or you find a matching
   `applications/*/job_description.txt` by listing the `applications/`
   directory — use `tailor_resume.py --jd-file <path> --application-name
   <name>` directly.
2. **The user pastes what reads as a complete job posting** (has the
   shape of a real listing — responsibilities, qualifications, etc., not
   just a one-line gist) — save it verbatim to a new application
   folder's `job_description.txt`, derive `--application-name` yourself
   from the posting's own company/role text, and use `tailor_resume.py
   --jd-file <path> --application-name <name>` directly. Do **not** use
   `apply_from_prompt.py` here — there's nothing left to interpret or
   brainstorm that the tailoring call doesn't already do from a real job
   description, and it would add an unneeded Gemini dependency.
3. **Only a rough, general description of the opportunity is given** —
   use `apply_from_prompt.py --prompt "..."` (above), which runs the
   full pipeline including the relevance brainstorm.
```

- [ ] **Step 2: Update the `## Requirements` section's Gemini note**

The existing line reads `- No \`GEMINI_API_KEY\` needed anywhere in this subproject.` — replace it with:

```markdown
- No `GEMINI_API_KEY` needed for the bootstrap, `tailor_resume.py`, or
  `merge_resumes.py`. `apply_from_prompt.py`'s relevance-brainstorm step
  needs `GEMINI_API_KEY` (or `PAID_GEMINI_KEY`) in `../.env` — if it's
  missing, that one script still completes, just without the extra
  brainstormed guidance.
```

- [ ] **Step 3: Update the `## Key files` section**

Add a line after the existing `tailor_resume.py` entry:

```markdown
- `apply_from_prompt.py` — turns a rough, free-text opportunity
  description into a job description and application name (local
  Ollama), brainstorms relevant master-resume content (Gemini), then
  calls `tailor_resume.py`'s `run_tailoring()` directly.
```

- [ ] **Step 4: Proofread**

Read the full `README.md` top to bottom once. Confirm: the new section reads clearly on its own, the routing numbered list matches spec §15's Routing section exactly in substance, and no existing content was accidentally altered.

- [ ] **Step 5: Commit**

```bash
git add resume_manager/README.md
git commit -m "docs(resume-manager): document apply_from_prompt and tailoring routing"
```
