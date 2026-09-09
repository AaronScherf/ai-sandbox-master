# Resume Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `resume_manager/`, a subproject that bootstrap-converts the user's resume PDF into a hand-maintained master Markdown resume, then tailors it per job application via a local Ollama model, flags anything untraceable to the master, and renders a styled PDF.

**Architecture:** A one-off bootstrap (`convert_resume.py`: copy PDF → local text extraction → local-LLM reformat → bidirectional verification) produces `resume_master.md`. A per-application pipeline (`tailor_resume.py`: tailor → validate → render) then turns that master plus a job description into a submission-ready PDF. Two small modules (`fact_diff.py`, shared entry/metric extraction) back both the bootstrap's verification step and the per-application validator.

**Tech Stack:** Python 3, `unittest` + `unittest.mock` (this project's existing test stack), `notes/transcribe_notes.py`'s local-extraction primitives (PyMuPDF-based, already installed), `common/ollama_utils.py`'s `call_ollama` (Ollama's local HTTP API), `markdown` (already installed), `xhtml2pdf` (new dependency — verified working on this Windows machine during planning; `weasyprint`, the spec's original choice, does not import here).

**Spec:** `docs/superpowers/specs/2026-09-09-resume-manager-design.md`

## Global Constraints

- No paid API call anywhere in this subproject, in the normal case — conversion never calls `process_pdf()` or touches `common/gemini_utils.py`; it calls `notes/transcribe_notes.py`'s local-extraction primitives directly (spec §2, §3).
- Conversion never routes through `process_pdf()`'s tier-routing/handwriting fallback — a page that fails `page_looks_defective()` raises and stops the run instead of escalating to Gemini vision (spec §3, §8).
- Local Ollama model defaults to `qwen2.5:7b-instruct` (general-purpose, matching `video_notes`/`transcribe_excalidraw`, not `problem_gen`'s math-only `qwen2-math:7b`), overridable via `RESUMEMANAGER_OLLAMA_MODEL`; `request_timeout` defaults to `300` seconds, matching `transcribe_excalidraw.py` (spec §4).
- `common.ollama_utils.call_ollama` takes no `temperature` parameter, and no other subproject's usage of it overrides one either — resolved during planning by dropping the brainstorm draft's `temperature: 0.2` suggestion rather than extending shared code for it. Fidelity is enforced by the verification/validation guardrails (below), not sampling temperature.
- Rendering uses `xhtml2pdf`, not `weasyprint` — confirmed during planning that `weasyprint` fails to import on this machine (`OSError: cannot load library 'libgobject-2.0-0'`, its Pango/GTK native-library dependency). `xhtml2pdf` is pure Python and was verified to render the same HTML+CSS shape (spec §6).
- No indexing into the shared academic-hub source-indexer (`research/.index/`) — this subproject never calls `process_pdf()`'s indexing wrapper at all (spec §1, §3).
- No hard-blocking validation anywhere — a normalization-verification mismatch (bootstrap) or a fact-diff flag (tailoring) writes a report and/or a `.review.md` file; it never stops a PDF from being produced or a master file from being written where verification passed (spec §1, §5, §8).
- No cover-letter generation, no job-description URL scraping — resume tailoring from a local JD text file only (spec §1).
- Source PDF and every generated artifact live together under `research/independent-research/projects/resume-manager/`, independent of the personal-website repo's own layout (spec §1, §7).

---

### Task 1: Package scaffolding and the new dependency

**Files:**
- Create: `resume_manager/__init__.py`
- Modify: `requirements.txt`
- Test: `tests/test_resume_manager_package.py`

**Interfaces:**
- Produces: the `resume_manager` package (empty for now); `xhtml2pdf` installed in `.venv`. Every later task imports from `resume_manager.*`.

- [ ] **Step 1: Install the new dependency**

Run: `./.venv/Scripts/python.exe -m pip install xhtml2pdf`
Expected: installs successfully. (`markdown` is already a project dependency, used by `audio_generator/`.)

- [ ] **Step 2: Write the failing test**

Create `tests/test_resume_manager_package.py`:

```python
import importlib
import unittest


class TestResumeManagerPackageScaffolding(unittest.TestCase):
    def test_package_imports(self):
        module = importlib.import_module("resume_manager")
        self.assertIsNotNone(module)

    def test_xhtml2pdf_is_installed(self):
        import xhtml2pdf  # noqa: F401

    def test_markdown_is_installed(self):
        import markdown  # noqa: F401
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m unittest tests.test_resume_manager_package -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager'`

- [ ] **Step 4: Create the package**

Create `resume_manager/__init__.py` (empty file).

- [ ] **Step 5: Add `xhtml2pdf` to `requirements.txt`**

In `requirements.txt`, add a new section at the end:

```
# Resume Manager
xhtml2pdf
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python -m unittest tests.test_resume_manager_package -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add resume_manager/__init__.py requirements.txt tests/test_resume_manager_package.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): scaffold package, add xhtml2pdf dependency

First step of the resume-manager pipeline: an empty package plus the
one new dependency it needs for PDF rendering (xhtml2pdf, not
weasyprint -- see the design spec's §6 for why).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 2: `fact_diff.py` — shared entry/metric extraction and diff

**Files:**
- Create: `resume_manager/fact_diff.py`
- Test: `tests/test_resume_fact_diff.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Entry` (dataclass: `org: str, role: str, dates: str`), `extract_entries(markdown_text: str) -> list[Entry]`, `extract_metrics(text: str) -> set[str]`, `entries_not_traceable(candidate_text: str, source_text: str) -> list[Entry]`, `metrics_not_traceable(candidate_text: str, source_text: str) -> list[str]`. Task 4 (`normalize.py`) and Task 7 (`validate.py`) both import from this module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resume_fact_diff.py`:

```python
import unittest

from resume_manager.fact_diff import (
    Entry, entries_not_traceable, extract_entries, extract_metrics, metrics_not_traceable,
)

_MASTER = """## Experience

### Acme Corp — Engineer (2020 – Present)
- Grew revenue 30% by shipping the new pricing model, worth $2M annually.

### Old Co — Analyst (2015 – 2018)
- Built reports.
"""


class TestExtractEntries(unittest.TestCase):
    def test_parses_every_entry_heading(self):
        entries = extract_entries(_MASTER)
        self.assertEqual(entries, [
            Entry(org="Acme Corp", role="Engineer", dates="2020 – Present"),
            Entry(org="Old Co", role="Analyst", dates="2015 – 2018"),
        ])

    def test_ignores_non_matching_lines(self):
        text = "## Experience\nSome prose that is not a heading at all.\n"
        self.assertEqual(extract_entries(text), [])


class TestExtractMetrics(unittest.TestCase):
    def test_finds_percent_dollar_and_x_tokens(self):
        text = "Grew revenue 30% worth $2M, a 10x improvement."
        self.assertEqual(extract_metrics(text), {"30%", "$2M", "10x"})

    def test_plain_number_with_no_suffix_is_not_a_metric(self):
        # A known heuristic limitation (spec §10) -- documented, not fixed here.
        self.assertEqual(extract_metrics("Managed a team of 12 people."), set())


class TestEntriesNotTraceable(unittest.TestCase):
    def test_matching_entry_is_not_flagged(self):
        candidate = "### Acme Corp — Engineer (2020 – Present)\n- did stuff"
        self.assertEqual(entries_not_traceable(candidate, _MASTER), [])

    def test_fabricated_entry_is_flagged(self):
        candidate = "### New Corp — Director (2022 – Present)\n- did stuff"
        result = entries_not_traceable(candidate, _MASTER)
        self.assertEqual(result, [Entry(org="New Corp", role="Director", dates="2022 – Present")])

    def test_dropping_a_source_entry_is_not_flagged(self):
        # Only checks the candidate direction -- a tailored resume
        # omitting an old role is expected behavior (spec §5).
        candidate = "### Acme Corp — Engineer (2020 – Present)\n- did stuff"
        self.assertEqual(entries_not_traceable(candidate, _MASTER), [])


class TestMetricsNotTraceable(unittest.TestCase):
    def test_metric_present_in_source_is_not_flagged(self):
        candidate = "Grew revenue 30%."
        self.assertEqual(metrics_not_traceable(candidate, _MASTER), [])

    def test_metric_absent_from_source_is_flagged(self):
        candidate = "Grew revenue 75%."
        self.assertEqual(metrics_not_traceable(candidate, _MASTER), ["75%"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_fact_diff -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.fact_diff'`

- [ ] **Step 3: Implement**

Create `resume_manager/fact_diff.py`:

```python
"""
fact_diff.py
Shared fact-preservation checks used both to verify the bootstrap
conversion's LLM reformat step (convert_resume.py/normalize.py, spec
§3 step 4) and to flag possible fabrication in a tailored resume
(validate.py, spec §5). Two independent primitives: `### <Org> —
<Role> (<dates>)` entry headings (only meaningful once text is in the
master's structured convention) and free-text numeric metric tokens
(meaningful on any plain text, structured or not).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_ENTRY_RE = re.compile(r"^###\s+(?P<org>.+?)\s+—\s+(?P<role>.+?)\s+\((?P<dates>.+?)\)\s*$", re.MULTILINE)
_METRIC_RE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[MKBmkb]?|\d[\d,]*(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?x\b")


@dataclass(frozen=True)
class Entry:
    org: str
    role: str
    dates: str


def extract_entries(markdown_text: str) -> list[Entry]:
    """Every `### <Org> — <Role> (<dates>)` heading, in document order."""
    return [
        Entry(m.group("org").strip(), m.group("role").strip(), m.group("dates").strip())
        for m in _ENTRY_RE.finditer(markdown_text)
    ]


def extract_metrics(text: str) -> set[str]:
    """Every standalone numeric token with a $, %, or x suffix/prefix
    (e.g. '30%', '$2M', '10x') -- works on any text, markdown or raw
    (spec §5, and §3 step 4's identical use on raw extraction)."""
    return {m.group(0) for m in _METRIC_RE.finditer(text)}


def entries_not_traceable(candidate_text: str, source_text: str) -> list[Entry]:
    """Entries in `candidate_text` whose (org, role, dates) don't
    exactly match one in `source_text` -- possible fabrication. Only
    checks the candidate direction: a source entry missing from the
    candidate is never flagged (spec §5)."""
    source_entries = set(extract_entries(source_text))
    return [e for e in extract_entries(candidate_text) if e not in source_entries]


def metrics_not_traceable(candidate_text: str, source_text: str) -> list[str]:
    """Metric tokens in `candidate_text` that don't appear anywhere in
    `source_text` -- possible invented metric."""
    return sorted(m for m in extract_metrics(candidate_text) if m not in source_text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_fact_diff -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/fact_diff.py tests/test_resume_fact_diff.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add shared entry/metric fact-diff primitives

extract_entries/extract_metrics + entries_not_traceable/
metrics_not_traceable -- reused by both the bootstrap's normalization
verification (spec §3 step 4) and the per-application tailoring
validator (spec §5), so the two checks share one implementation.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 3: `extract.py` — local, zero-API-call text extraction

**Files:**
- Create: `resume_manager/extract.py`
- Test: `tests/test_resume_extract.py`

**Interfaces:**
- Consumes: `notes.transcribe_notes.extract_all_page_texts`, `notes.transcribe_notes.page_looks_defective`, `notes.transcribe_notes.build_final_markdown`, `notes.transcribe_notes.build_frontmatter` (all reused unchanged).
- Produces: `DefectivePageError` (exception), `extract_resume_text(pdf_path: str) -> str`. Task 5 (`convert_resume.py`) calls this.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resume_extract.py`:

```python
import unittest
from unittest.mock import patch

from resume_manager.extract import DefectivePageError, extract_resume_text


class TestExtractResumeText(unittest.TestCase):
    @patch("resume_manager.extract.PdfReader")
    @patch("resume_manager.extract.page_looks_defective", return_value=False)
    @patch("resume_manager.extract.extract_all_page_texts")
    def test_builds_page_tagged_markdown_when_clean(self, mock_extract_pages, mock_defective, mock_reader_cls):
        mock_reader_cls.return_value.pages = [object(), object()]
        mock_extract_pages.return_value = ["Page one text", "Page two text"]

        result = extract_resume_text("fake_resume.pdf")

        self.assertIn("<!-- page 1 -->", result)
        self.assertIn("Page one text", result)
        self.assertIn("<!-- page 2 -->", result)
        self.assertIn("Page two text", result)
        self.assertIn("source_pdf: fake_resume.pdf", result)
        self.assertIn("routing: local", result)

    @patch("resume_manager.extract.PdfReader")
    @patch("resume_manager.extract.page_looks_defective")
    @patch("resume_manager.extract.extract_all_page_texts")
    def test_raises_on_defective_page_instead_of_falling_back(self, mock_extract_pages, mock_defective, mock_reader_cls):
        mock_reader_cls.return_value.pages = [object()]
        mock_extract_pages.return_value = ["garbled"]
        mock_defective.return_value = True

        with self.assertRaises(DefectivePageError):
            extract_resume_text("fake_resume.pdf")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_extract -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.extract'`

- [ ] **Step 3: Implement**

Create `resume_manager/extract.py`:

```python
"""
extract.py
Local, zero-API-call text extraction for the resume PDF -- reuses
notes/transcribe_notes.py's Tier-1 primitives directly rather than
its process_pdf() tier-routing wrapper. That wrapper's
has_reliable_pagination() check sniffs /Creator//Producer metadata for
LaTeX/Word/LibreOffice/FOP/XEP and fails safe to the handwriting/
messy-export fallback for anything else -- confirmed against the real
resume.pdf (/Producer: Skia/PDF m124, a headless-Chrome export) that
this would misroute a clean typeset resume through that fallback
purely on an unrecognized metadata string. Spec §3.
"""
from __future__ import annotations

import os

from pypdf import PdfReader

from notes.transcribe_notes import (
    build_final_markdown, build_frontmatter, extract_all_page_texts, page_looks_defective,
)


class DefectivePageError(Exception):
    """Raised when a page's local text extraction looks defective.
    Conversion stops here rather than silently escalating to Gemini
    vision -- a 1-2 page resume is short enough to deserve the user's
    direct attention instead (spec §3, §8)."""


def extract_resume_text(pdf_path: str) -> str:
    """Local PyMuPDF extraction of every page, page-tagged and
    frontmatter-wrapped the same way the rest of the corpus's Markdown
    is (build_final_markdown/build_frontmatter, reused unchanged).
    Raises DefectivePageError if any page fails page_looks_defective()
    -- never falls back to a Gemini call."""
    total_pages = len(PdfReader(pdf_path).pages)
    all_page_texts = extract_all_page_texts(pdf_path, total_pages)

    defective_pages = [n for n in range(1, total_pages + 1) if page_looks_defective(all_page_texts[n - 1])]
    if defective_pages:
        raise DefectivePageError(
            f"page(s) {defective_pages} of {pdf_path} look defective under local extraction -- "
            f"re-export the source PDF, or transcribe those pages by hand, rather than escalating "
            f"to a vision model this pipeline doesn't use (spec §3)."
        )

    cache = {str(n): all_page_texts[n - 1].strip() for n in range(1, total_pages + 1)}
    final_md = build_final_markdown(cache, total_pages)
    frontmatter = build_frontmatter({
        "source_pdf": os.path.basename(pdf_path), "total_pages": total_pages, "routing": "local", "tags": [],
    })
    return frontmatter + final_md
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_extract -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/extract.py tests/test_resume_extract.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add local zero-API-call resume text extraction

Calls notes/transcribe_notes.py's Tier-1 primitives directly instead
of process_pdf()'s tier-routing wrapper, which would misroute this
resume's actual PDF (Skia/PDF-produced, unrecognized by the
reliable-pagination check) through the handwriting/messy-export
Gemini vision fallback. A defective page raises instead of silently
escalating.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 4: `normalize.py` — local-LLM reformat + verification

**Files:**
- Create: `resume_manager/normalize.py`
- Test: `tests/test_resume_normalize.py`

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama`; `resume_manager.fact_diff.extract_entries`, `extract_metrics`, `metrics_not_traceable`.
- Produces: `normalize_resume_text(raw_text: str, model: str = ...) -> str | None`, `verify_normalization(raw_text: str, normalized_text: str) -> list[str]`. Task 5 (`convert_resume.py`) calls both.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resume_normalize.py`:

```python
import unittest
from unittest.mock import patch

from resume_manager.normalize import normalize_resume_text, verify_normalization


class TestNormalizeResumeText(unittest.TestCase):
    @patch("resume_manager.normalize.call_ollama")
    def test_returns_ollama_response_text(self, mock_call):
        mock_call.return_value = "## Experience\n### Acme — Engineer (2020 – Present)\n- Did a thing"
        result = normalize_resume_text("raw text here", model="qwen2.5:7b-instruct")
        self.assertEqual(result, "## Experience\n### Acme — Engineer (2020 – Present)\n- Did a thing")
        mock_call.assert_called_once()
        self.assertEqual(mock_call.call_args[0][1], "qwen2.5:7b-instruct")

    @patch("resume_manager.normalize.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(normalize_resume_text("raw text here"))


class TestVerifyNormalization(unittest.TestCase):
    def test_clean_reformat_has_no_problems(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue 30%"
        normalized = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%"
        self.assertEqual(verify_normalization(raw, normalized), [])

    def test_dropped_metric_is_flagged(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue 30%"
        normalized = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue"
        problems = verify_normalization(raw, normalized)
        self.assertTrue(any("30%" in p for p in problems))

    def test_invented_metric_is_flagged(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue"
        normalized = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%"
        problems = verify_normalization(raw, normalized)
        self.assertTrue(any("30%" in p for p in problems))

    def test_invented_entry_is_flagged(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue"
        normalized = (
            "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue\n\n"
            "### Globex — CTO (2018 – 2020)\n- Ran things"
        )
        problems = verify_normalization(raw, normalized)
        self.assertTrue(any("Globex" in p for p in problems))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_normalize -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.normalize'`

- [ ] **Step 3: Implement**

Create `resume_manager/normalize.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_normalize -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/normalize.py tests/test_resume_normalize.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add local-LLM master-resume reformatting + verification

Replaces hand-transcription with one local Ollama call (strict
reformat-only prompt) plus a bidirectional fact-preservation check
against the raw extraction -- catches both dropped and invented
content before convert_resume.py trusts the reformat (spec §3).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 5: `convert_resume.py` — bootstrap orchestration + CLI

**Files:**
- Create: `resume_manager/convert_resume.py`
- Test: `tests/test_convert_resume.py`

**Interfaces:**
- Consumes: `resume_manager.extract.extract_resume_text`, `DefectivePageError`; `resume_manager.normalize.normalize_resume_text`, `verify_normalization`.
- Produces: `bootstrap_resume(source_pdf: str, resume_manager_dir: str) -> str`, a `main()` CLI entry point. Not consumed by any later task (this is the one-off bootstrap script) — Task 9's `tailor_resume.py` only depends on `resume_master.md` existing on disk, not on this module's code.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_convert_resume.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

from resume_manager.convert_resume import bootstrap_resume
from resume_manager.extract import DefectivePageError


class TestBootstrapResume(unittest.TestCase):
    def _make_fake_pdf(self, tmp):
        path = os.path.join(tmp, "source.pdf")
        with open(path, "w", encoding="utf-8") as f:
            f.write("fake pdf bytes")
        return path

    @patch("resume_manager.convert_resume.verify_normalization", return_value=[])
    @patch(
        "resume_manager.convert_resume.normalize_resume_text",
        return_value="## Experience\n### Acme — Eng (2020 – Present)\n- Did a thing",
    )
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_clean_pass_writes_master_not_review(self, mock_extract, mock_normalize, mock_verify):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume.pdf")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            master_path = os.path.join(resume_manager_dir, "resume_master.md")
            self.assertTrue(os.path.exists(master_path))
            with open(master_path, encoding="utf-8") as f:
                self.assertIn("Acme", f.read())
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.md")))

    @patch(
        "resume_manager.convert_resume.verify_normalization",
        return_value=["metric '30%' found in raw extraction but missing from normalized output"],
    )
    @patch(
        "resume_manager.convert_resume.normalize_resume_text",
        return_value="## Experience\n### Acme — Eng (2020 – Present)\n- Did a thing",
    )
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text with 30%")
    def test_flagged_mismatch_writes_review_not_master(self, mock_extract, mock_normalize, mock_verify):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.md")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.md")))

    @patch("resume_manager.convert_resume.extract_resume_text", side_effect=DefectivePageError("page 1 looks defective"))
    def test_defective_page_propagates(self, mock_extract):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            with self.assertRaises(DefectivePageError):
                bootstrap_resume(source_pdf, resume_manager_dir)

    @patch("resume_manager.convert_resume.normalize_resume_text", return_value=None)
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_ollama_failure_still_leaves_raw_extraction_on_disk(self, mock_extract, mock_normalize):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.md")))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_convert_resume -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.convert_resume'`

- [ ] **Step 3: Implement**

Create `resume_manager/convert_resume.py`:

```python
"""
convert_resume.py
One-off bootstrap: copies the source resume PDF into resume-manager/,
extracts + normalizes it into the master resume's Markdown convention,
and verifies the reformat before trusting it (spec §3). Not part of
the per-application pipeline -- run once, or re-run if the source PDF
changes.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from resume_manager.extract import DefectivePageError, extract_resume_text
from resume_manager.normalize import normalize_resume_text, verify_normalization

_DEFAULT_SOURCE_PDF = (
    Path(__file__).resolve().parent.parent.parent / "personal-website" / "AaronScherf.github.io"
    / "static" / "uploads" / "resume.pdf"
)
_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)


def bootstrap_resume(source_pdf: str, resume_manager_dir: str) -> str:
    """Runs the full bootstrap (spec §3) and returns a one-line status
    message. A DefectivePageError from extraction propagates -- that's
    meant to stop the run for the user's direct attention (spec §8). A
    normalization-verification mismatch does NOT raise -- that's the
    expected "flag for review" path."""
    os.makedirs(resume_manager_dir, exist_ok=True)
    dest_pdf = os.path.join(resume_manager_dir, "resume.pdf")
    shutil.copyfile(source_pdf, dest_pdf)

    raw_text = extract_resume_text(dest_pdf)
    processed_dir = os.path.join(resume_manager_dir, "processed_outputs")
    os.makedirs(processed_dir, exist_ok=True)
    raw_path = os.path.join(processed_dir, "resume_raw.md")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    normalized_text = normalize_resume_text(raw_text)
    if normalized_text is None:
        return (
            f"Extraction wrote {raw_path}, but the local Ollama normalization call failed -- "
            f"is `ollama serve` running?"
        )

    problems = verify_normalization(raw_text, normalized_text)
    master_path = os.path.join(resume_manager_dir, "resume_master.md")
    if not problems:
        with open(master_path, "w", encoding="utf-8") as f:
            f.write(normalized_text)
        return f"Wrote {master_path} (normalization verified clean)."

    review_path = os.path.join(resume_manager_dir, "resume_master.review.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(normalized_text)
    report = "\n".join(f"- {p}" for p in problems)
    return (
        f"Normalization verification flagged {len(problems)} issue(s) -- wrote {review_path} "
        f"for manual review instead of {master_path}:\n{report}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-off bootstrap: convert resume.pdf into the master resume Markdown.",
    )
    parser.add_argument("--source-pdf", default=str(_DEFAULT_SOURCE_PDF))
    parser.add_argument("--resume-manager-dir", default=str(_DEFAULT_RESUME_MANAGER_DIR))
    args = parser.parse_args()

    try:
        print(bootstrap_resume(args.source_pdf, args.resume_manager_dir))
    except DefectivePageError as err:
        print(f"ERROR: {err}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_convert_resume -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/convert_resume.py tests/test_convert_resume.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add bootstrap orchestration (convert_resume.py)

Wires copy -> extract -> normalize -> verify into one bootstrap run:
a clean verification writes resume_master.md directly, a flagged
mismatch writes resume_master.review.md instead so only the flagged
content needs manual reconciliation (spec §3).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 6: `tailor.py` — local-LLM job-description tailoring

**Files:**
- Create: `resume_manager/tailor.py`
- Test: `tests/test_resume_tailor.py`

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama`.
- Produces: `tailor_resume(master_resume: str, job_description: str, model: str = ...) -> str | None`. Task 9 (`tailor_resume.py`, the CLI) calls this.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resume_tailor.py`:

```python
import unittest
from unittest.mock import patch

from resume_manager.tailor import tailor_resume


class TestTailorResume(unittest.TestCase):
    @patch("resume_manager.tailor.call_ollama")
    def test_prompt_includes_master_and_jd_and_rules(self, mock_call):
        mock_call.return_value = "## Experience\n..."

        tailor_resume("MASTER CONTENT HERE", "JOB DESCRIPTION HERE", model="qwen2.5:7b-instruct")

        prompt_arg = mock_call.call_args[0][0]
        self.assertIn("MASTER CONTENT HERE", prompt_arg)
        self.assertIn("JOB DESCRIPTION HERE", prompt_arg)
        self.assertIn("Do NOT invent", prompt_arg)
        mock_call.assert_called_once_with(prompt_arg, "qwen2.5:7b-instruct", 300)

    @patch("resume_manager.tailor.call_ollama")
    def test_returns_ollama_response_text(self, mock_call):
        mock_call.return_value = "tailored markdown"
        self.assertEqual(tailor_resume("master", "jd"), "tailored markdown")

    @patch("resume_manager.tailor.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(tailor_resume("master", "jd"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_tailor -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.tailor'`

- [ ] **Step 3: Implement**

Create `resume_manager/tailor.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_tailor -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/tailor.py tests/test_resume_tailor.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add job-description tailoring via local Ollama

Reuses common/ollama_utils.py's call_ollama (auto-sized num_ctx) for
the tailoring prompt instead of the brainstorm draft's raw
ollama.generate() -- avoids the context-truncation bug that
video_notes/viz/problem_gen already hit and fixed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 7: `validate.py` — automated fact-diff report

**Files:**
- Create: `resume_manager/validate.py`
- Test: `tests/test_resume_validate.py`

**Interfaces:**
- Consumes: `resume_manager.fact_diff.entries_not_traceable`, `metrics_not_traceable`.
- Produces: `validate_tailored(master_resume: str, tailored_resume: str) -> list[str]`, `format_report(problems: list[str]) -> str`. Task 9 (`tailor_resume.py`) calls both.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resume_validate.py`:

```python
import unittest

from resume_manager.validate import format_report, validate_tailored

_MASTER = """## Experience

### Acme Corp — Engineer (2020 – Present)
- Grew revenue 30%.

### Old Co — Analyst (2015 – 2018)
- Built reports.
"""


class TestValidateTailored(unittest.TestCase):
    def test_matching_entry_and_metric_not_flagged(self):
        tailored = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%.\n"
        self.assertEqual(validate_tailored(_MASTER, tailored), [])

    def test_dropping_a_master_entry_is_not_flagged(self):
        # "Old Co" is entirely absent from `tailored` -- expected
        # behavior for a shorter, targeted resume (spec §5).
        tailored = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%.\n"
        self.assertEqual(validate_tailored(_MASTER, tailored), [])

    def test_fabricated_entry_is_flagged(self):
        tailored = "## Experience\n### New Corp — Director (2022 – Present)\n- Led team.\n"
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("New Corp" in p for p in problems))

    def test_invented_metric_is_flagged(self):
        tailored = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 75%.\n"
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("75%" in p for p in problems))


class TestFormatReport(unittest.TestCase):
    def test_empty_problems_reports_clean(self):
        self.assertIn("no discrepancies", format_report([]))

    def test_problems_are_listed(self):
        report = format_report(["issue one", "issue two"])
        self.assertIn("issue one", report)
        self.assertIn("issue two", report)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_validate -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.validate'`

- [ ] **Step 3: Implement**

Create `resume_manager/validate.py`:

```python
"""
validate.py
Automated fact-diff (spec §5): flags anything in a tailored resume
that doesn't trace back to the master resume -- never blocks
rendering.
"""
from __future__ import annotations

from resume_manager.fact_diff import entries_not_traceable, metrics_not_traceable


def validate_tailored(master_resume: str, tailored_resume: str) -> list[str]:
    """Returns a list of human-readable warnings; empty means nothing
    was flagged. Only checks the tailored-output direction -- a
    tailored resume dropping a master entry is expected behavior and
    never flagged (spec §5)."""
    problems = []
    for entry in entries_not_traceable(tailored_resume, master_resume):
        problems.append(
            f"possible fabricated entry: '{entry.org} — {entry.role} ({entry.dates})' "
            f"not found in the master resume"
        )
    for metric in metrics_not_traceable(tailored_resume, master_resume):
        problems.append(f"possible invented metric: '{metric}' not found in the master resume")
    return problems


def format_report(problems: list[str]) -> str:
    if not problems:
        return "Validation: no discrepancies flagged."
    lines = [f"Validation flagged {len(problems)} possible issue(s) -- review before submitting:"]
    lines.extend(f"- {p}" for p in problems)
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_validate -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/validate.py tests/test_resume_validate.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add tailored-resume fact-diff validator

Flags any tailored-resume entry or metric not traceable to the master
resume; never blocks rendering, per spec §1/§5 -- warnings only.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 8: `render.py` — Markdown → styled PDF via xhtml2pdf

**Files:**
- Create: `resume_manager/render.py`
- Test: `tests/test_resume_render.py`

**Interfaces:**
- Consumes: `markdown` (third-party), `xhtml2pdf.pisa` (third-party).
- Produces: `render_resume_pdf(markdown_text: str, output_path: str) -> None`. Task 9 (`tailor_resume.py`) calls this.

- [ ] **Step 1: Write the failing test**

Create `tests/test_resume_render.py`:

```python
import os
import tempfile
import unittest

from resume_manager.render import render_resume_pdf


class TestRenderResumePdf(unittest.TestCase):
    def test_writes_a_non_empty_pdf(self):
        markdown_text = (
            "# Aaron Scherf\n\n## Experience\n\n"
            "### Acme Corp — Engineer (2020 – Present)\n\n- Did a thing\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(markdown_text, output_path)

            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_resume_render -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.render'`

- [ ] **Step 3: Implement**

Create `resume_manager/render.py`:

```python
"""
render.py
Markdown -> HTML -> styled PDF via xhtml2pdf (spec §6). Not
weasyprint -- confirmed during planning that weasyprint fails to
import on Windows without separately-installed Pango/GTK native
libraries; xhtml2pdf is pure Python and installs cleanly via pip.
"""
from __future__ import annotations

import markdown as markdown_lib
from xhtml2pdf import pisa

_CSS = """
<style>
@page {
    size: letter;
    margin: 0.6in 0.6in 0.8in 0.6in;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    color: #333;
    font-size: 10.5pt;
    line-height: 1.4;
}
h1 {
    text-align: center;
    text-transform: uppercase;
    color: #111;
    font-size: 22pt;
    margin-bottom: 5px;
}
h2 {
    color: #003366;
    border-bottom: 1px solid #ccc;
    font-size: 13pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 20px;
    margin-bottom: 8px;
}
h3 {
    font-size: 11pt;
    margin-top: 10px;
    margin-bottom: 3px;
}
ul {
    margin-top: 0;
    margin-bottom: 10px;
    padding-left: 20px;
}
li {
    margin-bottom: 3px;
}
</style>
"""


def render_resume_pdf(markdown_text: str, output_path: str) -> None:
    """Renders `markdown_text` to a styled PDF at `output_path`. Raises
    if xhtml2pdf reports an error (pisa.CreatePDF's `.err` is
    non-zero) -- an application's PDF is either fully written or not
    written at all, never a silently-broken partial file."""
    html_body = markdown_lib.markdown(markdown_text)
    full_html = f"<html><head>{_CSS}</head><body>{html_body}</body></html>"
    with open(output_path, "wb") as f:
        result = pisa.CreatePDF(full_html, dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} error(s) rendering {output_path}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_resume_render -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/render.py tests/test_resume_render.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add Markdown-to-PDF rendering via xhtml2pdf

Letter-size/margin/heading CSS adapted from the brainstorm draft's
weasyprint version -- xhtml2pdf renders the same HTML+CSS shape
without weasyprint's Pango/GTK native-library dependency (spec §6).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 9: `tailor_resume.py` — per-application CLI orchestration

**Files:**
- Create: `resume_manager/tailor_resume.py`
- Test: `tests/test_tailor_resume_cli.py`

**Interfaces:**
- Consumes: `resume_manager.tailor.tailor_resume`; `resume_manager.validate.validate_tailored`, `format_report`; `resume_manager.render.render_resume_pdf`.
- Produces: `run_tailoring(master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str) -> str`, a `main()` CLI entry point. Terminal task — nothing later depends on this module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tailor_resume_cli.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

from resume_manager.tailor_resume import run_tailoring


class TestRunTailoring(unittest.TestCase):
    def _setup(self, tmp):
        resume_manager_dir = os.path.join(tmp, "resume-manager")
        os.makedirs(resume_manager_dir, exist_ok=True)
        master_path = os.path.join(resume_manager_dir, "resume_master.md")
        with open(master_path, "w", encoding="utf-8") as f:
            f.write("## Experience\n### Acme — Engineer (2020 – Present)\n- Did a thing\n")
        jd_path = os.path.join(tmp, "jd.txt")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write("Looking for an engineer.")
        return resume_manager_dir, master_path, jd_path

    @patch("resume_manager.tailor_resume.render_resume_pdf")
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value="## Experience\n### Acme — Engineer (2020 – Present)\n- Did a thing\n",
    )
    def test_writes_all_application_outputs(self, mock_tailor, mock_render):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, jd_path = self._setup(tmp)

            run_tailoring(master_path, jd_path, "Acme Corp", resume_manager_dir)

            app_dirs = os.listdir(os.path.join(resume_manager_dir, "applications"))
            self.assertEqual(len(app_dirs), 1)
            self.assertTrue(app_dirs[0].endswith("-acme-corp"))
            app_dir = os.path.join(resume_manager_dir, "applications", app_dirs[0])
            self.assertTrue(os.path.exists(os.path.join(app_dir, "job_description.txt")))
            self.assertTrue(os.path.exists(os.path.join(app_dir, "tailored_resume.md")))
            self.assertTrue(os.path.exists(os.path.join(app_dir, "validation_report.txt")))
            mock_render.assert_called_once()

    def test_missing_master_resume_raises_before_any_ollama_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = os.path.join(tmp, "resume-manager")
            jd_path = os.path.join(tmp, "jd.txt")
            with open(jd_path, "w", encoding="utf-8") as f:
                f.write("jd")

            with self.assertRaises(FileNotFoundError):
                run_tailoring(
                    os.path.join(resume_manager_dir, "resume_master.md"), jd_path, "acme", resume_manager_dir,
                )

    def test_missing_jd_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, _jd_path = self._setup(tmp)

            with self.assertRaises(FileNotFoundError):
                run_tailoring(master_path, os.path.join(tmp, "does_not_exist.txt"), "acme", resume_manager_dir)

    @patch("resume_manager.tailor_resume.tailor_resume", return_value=None)
    def test_ollama_failure_raises_runtime_error(self, mock_tailor):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, jd_path = self._setup(tmp)

            with self.assertRaises(RuntimeError):
                run_tailoring(master_path, jd_path, "acme", resume_manager_dir)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_tailor_resume_cli -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.tailor_resume'`

- [ ] **Step 3: Implement**

Create `resume_manager/tailor_resume.py`:

```python
"""
tailor_resume.py
CLI entry point for one application: tailor -> validate -> render
(spec §4-§7). Run per job application, after the bootstrap
(convert_resume.py) has produced resume_master.md.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
from pathlib import Path

from resume_manager.render import render_resume_pdf
from resume_manager.tailor import tailor_resume
from resume_manager.validate import format_report, validate_tailored

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "application"


def run_tailoring(master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str) -> str:
    """Runs tailor -> validate -> render for one application and
    returns a one-line status message. Raises FileNotFoundError up
    front if either input file is missing, before any Ollama call
    (spec §8)."""
    if not os.path.exists(master_resume_path):
        raise FileNotFoundError(f"{master_resume_path} not found -- run convert_resume.py's bootstrap first.")
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"job description file not found: {jd_path}")

    with open(master_resume_path, "r", encoding="utf-8") as f:
        master_resume = f.read()
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    tailored = tailor_resume(master_resume, job_description)
    if tailored is None:
        raise RuntimeError("local Ollama tailoring call failed or timed out -- is `ollama serve` running?")

    date_str = datetime.date.today().isoformat()
    app_dir = os.path.join(resume_manager_dir, "applications", f"{date_str}-{_slugify(application_name)}")
    os.makedirs(app_dir, exist_ok=True)

    with open(os.path.join(app_dir, "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_description)
    with open(os.path.join(app_dir, "tailored_resume.md"), "w", encoding="utf-8") as f:
        f.write(tailored)

    problems = validate_tailored(master_resume, tailored)
    report = format_report(problems)
    with open(os.path.join(app_dir, "validation_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)

    pdf_path = os.path.join(app_dir, "Tailored_Resume.pdf")
    render_resume_pdf(tailored, pdf_path)

    return f"Wrote {pdf_path}.\n{report}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Tailor the master resume to one job description and render a PDF.")
    parser.add_argument("--jd-file", required=True, help="Path to a local text file containing the job description.")
    parser.add_argument("--application-name", required=True, help="Short name for this application (e.g. 'acme-corp').")
    parser.add_argument("--resume-manager-dir", default=str(_DEFAULT_RESUME_MANAGER_DIR))
    args = parser.parse_args()

    master_resume_path = os.path.join(args.resume_manager_dir, "resume_master.md")
    print(run_tailoring(master_resume_path, args.jd_file, args.application_name, args.resume_manager_dir))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_tailor_resume_cli -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `python -m unittest discover tests -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add resume_manager/tailor_resume.py tests/test_tailor_resume_cli.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add per-application CLI (tailor -> validate -> render)

python -m resume_manager.tailor_resume --jd-file ... --application-name
... runs the full per-application pipeline, writing job_description.txt,
tailored_resume.md, validation_report.txt, and Tailored_Resume.pdf into
one dated applications/ subfolder (spec §7).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 10: Documentation

**Files:**
- Create: `resume_manager/README.md`
- Create: `resume_manager_instructions.md`
- Modify: `README.md` (repository layout list + Requirements section)

**Interfaces:** none (documentation only).

- [ ] **Step 1: Create `resume_manager/README.md`**

```markdown
# Resume Manager

Converts the user's resume PDF into a hand-maintained master Markdown
resume, then tailors it per job application via a local Ollama model and
renders a styled PDF — fully local except for reading the source PDF
itself: no paid API call anywhere in this subproject.

## One-time bootstrap

```powershell
.\.venv\Scripts\python.exe -m resume_manager.convert_resume
```

Copies the source resume PDF, extracts its text locally (0 API calls),
reformats it into the master convention via a local Ollama call, and
verifies that reformat against the raw extraction before writing
`resume_master.md`. A verification mismatch writes
`resume_master.review.md` instead, for manual reconciliation of just the
flagged content.

`resume_master.md` is then yours to keep expanding by hand over time —
never overwritten by a re-run of this bootstrap.

## Per application

```powershell
.\.venv\Scripts\python.exe -m resume_manager.tailor_resume --jd-file "path\to\job_description.txt" --application-name "acme-corp"
```

Writes `job_description.txt`, `tailored_resume.md`, `validation_report.txt`,
and `Tailored_Resume.pdf` into
`research/independent-research/projects/resume-manager/applications/<date>-<application-name>/`.

## Requirements

- A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled
  (`ollama pull qwen2.5:7b-instruct`) — overridable via
  `RESUMEMANAGER_OLLAMA_MODEL`.
- No `GEMINI_API_KEY` needed anywhere in this subproject.

## Key files

- `extract.py` — local, zero-API-call PDF text extraction, reusing
  `notes/transcribe_notes.py`'s Tier-1 primitives directly (never its
  tier-routing wrapper — see the design spec's §3 for why).
- `normalize.py` — local-LLM reformat of the raw extraction into the
  master convention, verified via `fact_diff.py` before being trusted.
- `fact_diff.py` — shared entry/metric extraction and fact-preservation
  checks, used by both `normalize.py` and `validate.py`.
- `convert_resume.py` — the one-time bootstrap CLI.
- `tailor.py` — local-LLM job-description tailoring.
- `validate.py` — fact-diff report for a tailored resume against the
  master.
- `render.py` — Markdown → styled PDF via `xhtml2pdf`.
- `tailor_resume.py` — the per-application CLI, orchestrating
  tailor → validate → render.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-09-resume-manager-design.md`.
```

- [ ] **Step 2: Create `resume_manager_instructions.md`**

```markdown
# Resume Manager

Companion to `journal_articles_instructions.md`/`notes_instructions.md`,
but for a single, personal, hand-curated document rather than a corpus:
the user's resume. Two independent runs — a one-time bootstrap, and a
per-application tailoring pipeline.

## Step 1: One-time bootstrap

```powershell
cd academic-rag-model
python -m resume_manager.convert_resume
```

* Defaults to `personal-website/AaronScherf.github.io/static/uploads/resume.pdf`
  as the source and
  `research/independent-research/projects/resume-manager/` as the
  destination — both overridable via `--source-pdf`/`--resume-manager-dir`.
* Extraction is purely local (PyMuPDF-based, 0 API calls) — never routes
  through the handwriting/messy-export Gemini fallback other conversion
  pipelines in this repo have, because a resume PDF's `/Producer`/`/Creator`
  metadata (often a resume-builder tool, not LaTeX/Word/LibreOffice) isn't a
  reliable signal for a document that's already known to be typeset. A page
  that fails the local "does this look defective" check stops the run for
  your direct attention instead of silently escalating to a vision model.
* The raw extraction is reformatted into the master convention (`##`
  section headings, `### <Org> — <Role> (<dates>)` entries, bullets) via
  one local Ollama call, then checked against the raw extraction before
  being trusted — a clean check writes `resume_master.md` directly; a
  flagged mismatch writes `resume_master.review.md` instead so you only
  reconcile the flagged content by hand.
* Re-running this bootstrap never overwrites an existing `resume_master.md`
  — only run it again if the *source PDF* changes; ongoing edits to your
  master resume are yours to make directly in `resume_master.md`.

**Required structure for `resume_master.md`:** each Experience/Education
entry must be an `### ` heading of the form `### <Org> — <Role> (<Start> –
<End or "Present">)`, followed by bullet points. Other sections (Skills,
Projects, Awards, ...) are freeform. This convention is what
`fact_diff.py` parses to catch fabricated entries during tailoring —
keeping it consistent as you expand the master resume by hand is what
keeps that check useful.

## Step 2: Per-application tailoring

```powershell
python -m resume_manager.tailor_resume --jd-file "job_description.txt" --application-name "acme-corp"
```

* `--jd-file` is a local text file with the job description pasted in —
  no URL scraping in this version.
* `--application-name` becomes part of the output folder name
  (`applications/<YYYY-MM-DD>-<slugified-name>/`).
* Tailoring runs one local Ollama call (same model as the bootstrap's
  normalization step, `qwen2.5:7b-instruct` by default) with a strict
  no-fabrication prompt, then `validate.py` flags anything in the result
  that doesn't trace back to `resume_master.md` — written to
  `validation_report.txt` alongside the tailored Markdown and the
  rendered PDF. Flags are warnings, not blockers: the PDF is rendered
  regardless, and you decide whether a flag is a real problem.

## How it works

* **Reuses `notes/transcribe_notes.py`'s extraction primitives, not its
  `process_pdf()` wrapper.** That wrapper's tier-routing decision
  (`has_reliable_pagination()`) sniffs `/Creator`/`/Producer` metadata
  for LaTeX/Word/LibreOffice/Apache FOP/XEP and fails safe to the
  handwriting/messy-export fallback for anything else. Confirmed against
  the user's real `resume.pdf`: its `/Producer` is `Skia/PDF m124`
  (headless-Chrome print-to-PDF), unrecognized by that check, even though
  the extracted text is clean. A resume is also a single, manually
  verified file, unlike a batch notes corpus — there's no need for a
  generic per-file heuristic at all here.
* **No paid API call anywhere in this subproject** — extraction is local
  PyMuPDF, reformatting and tailoring are local Ollama. `GEMINI_API_KEY`
  is never read.
* **Rendering uses `xhtml2pdf`, not `weasyprint`.** `weasyprint` depends
  on the Pango/GTK native libraries, which aren't a plain `pip install` on
  Windows and were confirmed (during this subproject's own planning) not
  to import on this machine. `xhtml2pdf` is pure Python.
```

- [ ] **Step 3: Add `resume_manager` to the root `README.md`'s repository layout list**

In `README.md`, add this bullet to the "Repository layout" list, after the existing `video_notes/` bullet:

```markdown
- [`resume_manager/`](resume_manager/README.md) — converts the user's resume PDF into a hand-maintained master Markdown resume, then tailors it per job application via a local Ollama model and renders a styled PDF (`xhtml2pdf`). No paid API call anywhere in this subproject. See [`resume_manager_instructions.md`](resume_manager_instructions.md).
```

- [ ] **Step 4: Add a `resume_manager` bullet to the root `README.md`'s Requirements section**

In `README.md`, add this bullet to the "Requirements" list, after the existing `video_notes` bullet:

```markdown
- **Resume manager only** (`resume_manager/`): a local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled, overridable via `RESUMEMANAGER_OLLAMA_MODEL`. No `GEMINI_API_KEY` needed anywhere in this subproject. See [`resume_manager/README.md`](resume_manager/README.md).
```

- [ ] **Step 5: Commit**

```bash
git add resume_manager/README.md resume_manager_instructions.md README.md
git commit -m "$(cat <<'EOF'
docs(resume_manager): add subproject README, instructions, and root README entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```
