# Resume Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Revision 2** — supersedes the original 10-task plan (Tasks 1–10 below, all
originally shipped and run once) with a structured-data redesign. `extract.py`
(local, zero-API-call PDF text extraction) is **unaffected by this revision**
and needs no changes — the schema change only touches what happens *after*
raw text extraction. Tasks below are renumbered from scratch to reflect the
new module set; see the design spec's Revision 2 note for why.

**Goal:** Replace `resume_manager`'s freeform-Markdown master resume and
whole-document LLM tailoring with a structured YAML schema (`resume_master.yaml`)
and a tailoring mechanism where the LLM never emits a metadata field at all —
only Work Experience selection and bullet rewrites, reconstructed into a full
resume by code.

**Architecture:** `schema.py` (shared field lists, id assignment, generic
field-traceability check) backs both `normalize.py`'s extraction verification
and is the schema every other module reads. `normalize.py` extracts raw text
into the schema via one local Ollama call. `convert_resume.py` orchestrates
copy → extract → schema-extract → verify → write `resume_master.yaml` (or
`resume_master.review.yaml`). `tailor.py` sends only `id`/`org`/`role`/`bullets`
per Work Experience entry to a local Ollama call, which returns only
`included_ids` + `bullets_by_id`; `tailor.py`'s own code (not the LLM)
reconstructs the full tailored structure from master data. `validate.py`
checks rewritten bullets' metrics against that same entry's original bullets
only. `render.py` templates the structured result into Markdown/HTML
deterministically, then to PDF via `xhtml2pdf`.

**Tech Stack:** Python 3, `unittest` + `unittest.mock`, `pyyaml` (new explicit
dependency — already transitively installed, promoted from optional/soft
usage elsewhere in this project to a load-bearing one here), `common/ollama_utils.py`'s
`call_ollama`, `markdown` + `xhtml2pdf` (unchanged from the original plan).

**Spec:** `docs/superpowers/specs/2026-09-09-resume-manager-design.md`
(Revision 2)

## Global Constraints

- `extract.py` is unchanged by this revision — reused exactly as shipped, no
  task below touches it (spec §3 steps 1-2).
- The LLM never emits a metadata field (org/role/location/dates/gpa/thesis/
  contact/education/awards/publications/skills) during **tailoring** — only
  `included_ids` and `bullets_by_id` (spec §4). Metadata fabrication during
  tailoring must be structurally impossible, not just checked for afterward.
- Every required schema field (per category, defined in `schema.py`) must be
  non-empty and traceable as a substring of the raw extraction, except
  `end_date: "Present"`, which is never required to trace (spec §3 step 4).
- `id` fields on `work_experience`/`education` entries are assigned by code
  (`schema.assign_ids`), never by the LLM — stable slug + ordinal,
  disambiguating duplicate orgs/institutions (spec §3).
- Rendering is deterministic templating over structured data — no LLM output
  is ever passed straight to the `markdown` library (spec §6).
- `RESUMEMANAGER_OLLAMA_TIMEOUT` defaults to `1800` seconds in this revision,
  not `300` — the real first bootstrap run needed `1800` on CPU-only
  inference; carrying forward the original, now-falsified `300` default
  would just reproduce that failure (spec §4, §10).
- Master/tailored resumes are YAML (`resume_master.yaml`,
  `resume_master.review.yaml`, `tailored_resume.yaml`), not Markdown (spec §7).
- No selection/rewriting for Education, Awards, Publications, or Skills in
  this version — every category but Work Experience passes through
  tailoring byte-identical (spec §1 non-goals, §10).

---

### Task 1: Add `pyyaml` as an explicit dependency

**Files:**
- Modify: `requirements.txt`
- Modify: `tests/test_resume_manager_package.py`

**Interfaces:**
- Produces: `pyyaml` available as an explicit, non-optional project
  dependency. Every later task in this plan imports `yaml`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_resume_manager_package.py` (new test method on the
existing `TestResumeManagerPackageScaffolding` class):

```python
    def test_pyyaml_is_installed(self):
        import yaml  # noqa: F401
```

- [ ] **Step 2: Run the test to verify it currently passes (it's already
  transitively installed) — confirm, don't skip**

Run: `python -m unittest tests.test_resume_manager_package -v`
Expected: PASS (pyyaml is already in the venv transitively; this step
confirms that before Step 3 makes it an explicit, pinned dependency rather
than an implicit one another package could stop pulling in).

- [ ] **Step 3: Add `pyyaml` to `requirements.txt`**

In `requirements.txt`, under the existing `# Resume Manager` section, add:

```
xhtml2pdf
pyyaml
```

(replacing the single existing `xhtml2pdf` line with both).

- [ ] **Step 4: Run the test again to confirm still passing**

Run: `python -m unittest tests.test_resume_manager_package -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/test_resume_manager_package.py
git commit -m "$(cat <<'EOF'
build(resume_manager): make pyyaml an explicit dependency

The structured master-resume format (Revision 2) makes YAML
load-bearing for this subproject, not optional the way
postprocess_discovery.py treats it -- pin it explicitly rather than
relying on another package's transitive install.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 2: `schema.py` — shared field lists, id assignment, field verification

**Files:**
- Create: `resume_manager/schema.py`
- Test: `tests/test_resume_schema.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `slugify(text: str) -> str`; `CONTACT_REQUIRED`,
  `WORK_EXPERIENCE_REQUIRED`, `WORK_EXPERIENCE_LIST_FIELDS`,
  `EDUCATION_REQUIRED`, `AWARDS_REQUIRED`, `PUBLICATIONS_REQUIRED`,
  `SKILLS_REQUIRED`, `SKILLS_LIST_FIELDS` (all `list[str]`);
  `assign_ids(entries: list[dict], key_field: str) -> None` (mutates in
  place); `verify_entry_fields(entry: dict, raw_text: str, required_fields:
  list[str], list_fields: list[str] = ()) -> list[str]`. Task 4
  (`normalize.py`) and Task 5 (`convert_resume.py`) both import from this
  module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resume_schema.py`:

```python
import unittest

from resume_manager.schema import assign_ids, slugify, verify_entry_fields


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify("U.S. Agency for International Development"), "u-s-agency-for-international-development")

    def test_empty_input_falls_back_to_entry(self):
        self.assertEqual(slugify("   "), "entry")


class TestAssignIds(unittest.TestCase):
    def test_disambiguates_duplicate_keys_with_ordinals(self):
        entries = [{"org": "USAID"}, {"org": "USAID"}, {"org": "USAID"}]
        assign_ids(entries, "org")
        self.assertEqual([e["id"] for e in entries], ["usaid-1", "usaid-2", "usaid-3"])

    def test_distinct_keys_get_distinct_slugs(self):
        entries = [{"org": "Acme"}, {"org": "Globex"}]
        assign_ids(entries, "org")
        self.assertEqual([e["id"] for e in entries], ["acme-1", "globex-1"])


class TestVerifyEntryFields(unittest.TestCase):
    def test_clean_entry_has_no_problems(self):
        entry = {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "2022", "bullets": ["Did a thing"],
        }
        raw = "Acme\nEngineer\nNYC\n2020 - 2022\nDid a thing"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"], ["bullets"])
        self.assertEqual(problems, [])

    def test_empty_required_field_is_flagged(self):
        entry = {"id": "acme-1", "org": "Acme", "role": "", "location": "NYC", "start_date": "2020", "end_date": "2022"}
        raw = "Acme\nNYC\n2020 - 2022"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"])
        self.assertTrue(any("role" in p for p in problems))

    def test_untraceable_field_value_is_flagged(self):
        entry = {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "Los Angeles",
            "start_date": "2020", "end_date": "2022",
        }
        raw = "Acme\nEngineer\nNYC\n2020 - 2022"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"])
        self.assertTrue(any("location" in p for p in problems))

    def test_present_end_date_is_never_flagged_as_untraceable(self):
        entry = {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present",
        }
        raw = "Acme\nEngineer\nNYC\n2020"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"])
        self.assertEqual(problems, [])

    def test_untraceable_list_item_is_flagged(self):
        entry = {"id": "acme-1", "bullets": ["Did a thing that never appears in the raw text"]}
        raw = "Acme\nEngineer"
        problems = verify_entry_fields(entry, raw, [], ["bullets"])
        self.assertTrue(any("bullets" in p for p in problems))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_schema -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resume_manager.schema'`

- [ ] **Step 3: Implement**

Create `resume_manager/schema.py`:

```python
"""
schema.py
The structured master-resume schema (spec §3 Revision 2): field lists per
category, stable id assignment, and a generic required-field/traceability
check shared by normalize.py's extraction verification.
"""
from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "entry"


CONTACT_REQUIRED = ["name", "location", "email", "linkedin_url", "github_url", "website_url"]
WORK_EXPERIENCE_REQUIRED = ["org", "role", "location", "start_date", "end_date"]
WORK_EXPERIENCE_LIST_FIELDS = ["bullets"]
EDUCATION_REQUIRED = ["institution", "degree", "location", "start_date", "end_date"]
AWARDS_REQUIRED = ["name", "description", "date"]
PUBLICATIONS_REQUIRED = ["title", "date", "venue"]
SKILLS_REQUIRED = ["category"]
SKILLS_LIST_FIELDS = ["items"]


def assign_ids(entries: list[dict], key_field: str) -> None:
    """Mutates each entry in place, adding a stable 'id' slug derived from
    key_field (e.g. 'org' for work_experience, 'institution' for
    education), disambiguated with an ordinal for duplicates -- never left
    to the LLM to invent (spec §3)."""
    seen: dict[str, int] = {}
    for entry in entries:
        base = slugify(str(entry.get(key_field, "")))
        seen[base] = seen.get(base, 0) + 1
        entry["id"] = f"{base}-{seen[base]}"


def verify_entry_fields(
    entry: dict, raw_text: str, required_fields: list[str], list_fields: list[str] = (),
) -> list[str]:
    """Returns human-readable problems for one entry: an empty required
    field, a required field whose value isn't traceable as a substring of
    raw_text, or a list-field item that's empty or untraceable (spec §3
    step 4). 'end_date' is exempt from the traceability check when its
    value is the literal "Present" -- a source resume showing no end date
    for an ongoing role has nothing to trace that sentinel to. Entry
    identified in messages by its 'id' if present."""
    label = entry.get("id") or "<entry>"
    problems: list[str] = []
    for field in required_fields:
        value = entry.get(field)
        if not value:
            problems.append(f"{label}: required field '{field}' is empty")
            continue
        if field == "end_date" and value == "Present":
            continue
        if str(value) not in raw_text:
            problems.append(f"{label}: field '{field}' value '{value}' not found in raw extraction")
    for field in list_fields:
        for item in entry.get(field) or []:
            if not item:
                problems.append(f"{label}: an item in '{field}' is empty")
            elif str(item) not in raw_text:
                problems.append(f"{label}: '{field}' item '{item}' not found in raw extraction")
    return problems
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_schema -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/schema.py tests/test_resume_schema.py
git commit -m "$(cat <<'EOF'
feat(resume_manager): add structured master-resume schema (Revision 2)

Field lists per category, stable code-assigned entry ids (never
LLM-authored), and a generic required-field/traceability check --
directly fixes the bug where a freeform Markdown heading gave the LLM
an ambiguous single slot to guess a role's location vs. its dates into
(spec §1 goal 4, §3).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 3: Trim `fact_diff.py` to metric-only primitives

**Files:**
- Modify: `resume_manager/fact_diff.py`
- Modify: `tests/test_resume_fact_diff.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `extract_metrics(text: str) -> set[str]`, `metrics_not_traceable(candidate_text: str, source_text: str) -> list[str]`
  (both unchanged from v1). **Removes** `Entry`, `extract_entries`,
  `entries_not_traceable` — meaningless once master entries are structured
  dicts rather than Markdown headings. Task 7 (`validate.py`) imports
  `metrics_not_traceable`.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_resume_fact_diff.py` entirely with:

```python
import unittest

from resume_manager.fact_diff import extract_metrics, metrics_not_traceable


class TestExtractMetrics(unittest.TestCase):
    def test_finds_percent_dollar_and_x_tokens(self):
        text = "Grew revenue 30% worth $2M, a 10x improvement."
        self.assertEqual(extract_metrics(text), {"30%", "$2M", "10x"})

    def test_plain_number_with_no_suffix_is_not_a_metric(self):
        # A known heuristic limitation (spec §10) -- documented, not fixed here.
        self.assertEqual(extract_metrics("Managed a team of 12 people."), set())


class TestMetricsNotTraceable(unittest.TestCase):
    def test_metric_present_in_source_is_not_flagged(self):
        self.assertEqual(metrics_not_traceable("Grew revenue 30%.", "Grew revenue 30% via pricing."), [])

    def test_metric_absent_from_source_is_flagged(self):
        self.assertEqual(metrics_not_traceable("Grew revenue 75%.", "Grew revenue 30%."), ["75%"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_fact_diff -v`
Expected: FAIL — `ImportError` (the old `Entry`/`extract_entries` symbols
are still exported by the current `fact_diff.py`, but the test file no
longer imports them; this step's failure is really about confirming the
*new* smaller test file runs against the *old* file first, as a sanity
check that Step 3 is the only thing that should make it pass cleanly).
If it unexpectedly passes already, proceed directly to Step 3 anyway --
the module content still needs trimming.

- [ ] **Step 3: Trim `resume_manager/fact_diff.py`**

Replace its contents entirely with:

```python
"""
fact_diff.py
Free-text numeric-metric primitives (spec §5) -- the only fact-diff
mechanism Revision 2 still needs. Entry-heading extraction/diffing was
removed: master entries are now structured dicts (schema.py), not
Markdown headings, so there's no heading string left to regex-parse.
Metrics stay here (not schema.py) because they're meaningful on any
plain text regardless of schema -- used to scope validate.py's
per-entry bullet check to that entry's own original bullets.
"""
from __future__ import annotations

import re

_METRIC_RE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[MKBmkb]?|\d[\d,]*(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?x\b")


def extract_metrics(text: str) -> set[str]:
    """Every standalone numeric token with a $, %, or x suffix/prefix
    (e.g. '30%', '$2M', '10x')."""
    return {m.group(0) for m in _METRIC_RE.finditer(text)}


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
refactor(resume_manager): trim fact_diff.py to metric-only primitives

Entry-heading regex extraction/diffing is obsolete now that master
entries are structured dicts (schema.py), not Markdown headings.
Metrics stay here -- still needed to scope validate.py's per-entry
bullet check (spec §5).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 4: `normalize.py` — schema-driven local-LLM extraction + verification

**Files:**
- Modify: `resume_manager/normalize.py` (full rewrite)
- Modify: `tests/test_resume_normalize.py` (full rewrite)

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama`; `resume_manager.schema.*`
  (all field-list constants and `verify_entry_fields`).
- Produces: `extract_resume_schema(raw_text: str, model: str = ...) -> dict | None`,
  `verify_extraction(parsed: dict, raw_text: str) -> list[str]`. Task 5
  (`convert_resume.py`) calls both.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_resume_normalize.py` entirely with:

```python
import unittest
from unittest.mock import patch

from resume_manager.normalize import extract_resume_schema, verify_extraction

_VALID_YAML_RESPONSE = """
contact:
  name: Aaron Scherf
  location: USA
  email: a@example.com
  linkedin_url: https://linkedin.com/in/a
  github_url: https://github.com/a
  website_url: https://a.dev
work_experience:
  - org: Acme Corp
    role: Engineer
    location: NYC
    start_date: "2020"
    end_date: Present
    bullets:
      - Did a thing
education: []
awards: []
publications: []
skills: []
"""


class TestExtractResumeSchema(unittest.TestCase):
    @patch("resume_manager.normalize.call_ollama", return_value=_VALID_YAML_RESPONSE)
    def test_parses_valid_yaml_response(self, mock_call):
        result = extract_resume_schema("raw text", model="qwen2.5:7b-instruct")
        self.assertEqual(result["contact"]["name"], "Aaron Scherf")
        self.assertEqual(result["work_experience"][0]["org"], "Acme Corp")

    @patch("resume_manager.normalize.call_ollama", return_value="```yaml\n" + _VALID_YAML_RESPONSE + "```")
    def test_strips_code_fence_before_parsing(self, mock_call):
        result = extract_resume_schema("raw text")
        self.assertEqual(result["contact"]["name"], "Aaron Scherf")

    @patch("resume_manager.normalize.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(extract_resume_schema("raw text"))

    @patch("resume_manager.normalize.call_ollama", return_value="not: [valid: yaml: at all")
    def test_returns_none_on_invalid_yaml(self, mock_call):
        self.assertIsNone(extract_resume_schema("raw text"))


class TestVerifyExtraction(unittest.TestCase):
    def test_clean_extraction_has_no_problems(self):
        raw = (
            "Acme Corp\nEngineer\nNYC\n2020\nDid a thing\n"
            "Aaron Scherf\nUSA\na@example.com\n"
            "https://linkedin.com/in/a\nhttps://github.com/a\nhttps://a.dev"
        )
        parsed = {
            "contact": {
                "name": "Aaron Scherf", "location": "USA", "email": "a@example.com",
                "linkedin_url": "https://linkedin.com/in/a", "github_url": "https://github.com/a",
                "website_url": "https://a.dev",
            },
            "work_experience": [{
                "id": "acme-1", "org": "Acme Corp", "role": "Engineer", "location": "NYC",
                "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
            }],
            "education": [], "awards": [], "publications": [], "skills": [],
        }
        self.assertEqual(verify_extraction(parsed, raw), [])

    def test_untraceable_field_is_flagged(self):
        raw = "Acme Corp\nEngineer\nNYC\n2020"
        parsed = {
            "contact": {
                "name": "", "location": "", "email": "", "linkedin_url": "", "github_url": "", "website_url": "",
            },
            "work_experience": [{
                "id": "acme-1", "org": "Acme Corp", "role": "Engineer", "location": "Los Angeles",
                "start_date": "2020", "end_date": "Present", "bullets": [],
            }],
            "education": [], "awards": [], "publications": [], "skills": [],
        }
        problems = verify_extraction(parsed, raw)
        self.assertTrue(any("location" in p for p in problems))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_normalize -v`
Expected: FAIL — `extract_resume_schema`/`verify_extraction` don't exist yet
in `resume_manager/normalize.py` (it currently exports
`normalize_resume_text`/`verify_normalization` from v1).

- [ ] **Step 3: Replace `resume_manager/normalize.py` entirely**

```python
"""
normalize.py
One local-LLM extraction pass turning the raw page-tagged extraction
(extract.py) into the master resume's structured schema (schema.py) --
Revision 2 of spec §3 steps 3-4. Verified against the raw extraction
before being trusted.
"""
from __future__ import annotations

import os

import yaml

from common.ollama_utils import call_ollama
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
2. Do not invent a value for any field the raw text doesn't contain -- omit optional fields (gpa, thesis, link) instead of guessing.
3. Follow this exact schema (field names and nesting):
{_SCHEMA_TEMPLATE}
4. Output ONLY valid YAML -- no commentary, no markdown code fences."""


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


def extract_resume_schema(raw_text: str, model: str = OLLAMA_MODEL) -> dict | None:
    """Calls a local Ollama model to extract raw_text into the schema
    above, returning the parsed dict, or None if the Ollama call failed/
    timed out or the response wasn't valid YAML (spec §3 step 3, §8)."""
    prompt = f"{_SYSTEM_PROMPT}\n\n### RAW EXTRACTED RESUME TEXT:\n{raw_text}"
    result = call_ollama(prompt, model, OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return None
    try:
        parsed = yaml.safe_load(_strip_code_fence(result))
    except yaml.YAMLError:
        return None
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_normalize -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/normalize.py tests/test_resume_normalize.py
git commit -m "$(cat <<'EOF'
refactor(resume_manager): rewrite normalize.py for schema-driven extraction

Replaces v1's freeform-Markdown reformat prompt with a schema-driven
YAML extraction prompt + schema.py-based field verification (spec §3
Revision 2). RESUMEMANAGER_OLLAMA_TIMEOUT default raised to 1800s,
matching the real CPU-only timing the first bootstrap run needed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 5: `convert_resume.py` — bootstrap orchestration for YAML output

**Files:**
- Modify: `resume_manager/convert_resume.py` (full rewrite)
- Modify: `tests/test_convert_resume.py` (full rewrite)

**Interfaces:**
- Consumes: `resume_manager.extract.extract_resume_text`, `DefectivePageError`
  (unchanged); `resume_manager.normalize.extract_resume_schema`,
  `verify_extraction`; `resume_manager.schema.assign_ids`.
- Produces: `bootstrap_resume(source_pdf: str, resume_manager_dir: str) -> str`
  (same signature as v1), a `main()` CLI entry point. Not consumed by any
  later task.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_convert_resume.py` entirely with:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.convert_resume import bootstrap_resume
from resume_manager.extract import DefectivePageError


def _parsed_resume():
    return {
        "contact": {
            "name": "Aaron", "location": "USA", "email": "a@x.com",
            "linkedin_url": "l", "github_url": "g", "website_url": "w",
        },
        "work_experience": [
            {"org": "Acme", "role": "Engineer", "location": "NYC", "start_date": "2020",
             "end_date": "Present", "bullets": ["Did a thing"]},
            {"org": "Acme", "role": "Director", "location": "NYC", "start_date": "2018",
             "end_date": "2020", "bullets": ["Did another thing"]},
        ],
        "education": [], "awards": [], "publications": [], "skills": [],
    }


class TestBootstrapResume(unittest.TestCase):
    def _make_fake_pdf(self, tmp):
        path = os.path.join(tmp, "source.pdf")
        with open(path, "w", encoding="utf-8") as f:
            f.write("fake pdf bytes")
        return path

    @patch("resume_manager.convert_resume.verify_extraction", return_value=[])
    @patch("resume_manager.convert_resume.extract_resume_schema")
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_clean_pass_writes_master_yaml_with_assigned_ids(self, mock_extract, mock_schema, mock_verify):
        mock_schema.return_value = _parsed_resume()
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume.pdf")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
            self.assertTrue(os.path.exists(master_path))
            with open(master_path, encoding="utf-8") as f:
                written = yaml.safe_load(f)
            self.assertEqual([e["id"] for e in written["work_experience"]], ["acme-1", "acme-2"])
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.yaml")))

    @patch("resume_manager.convert_resume.verify_extraction", return_value=["some field problem"])
    @patch("resume_manager.convert_resume.extract_resume_schema")
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_flagged_mismatch_writes_review_not_master(self, mock_extract, mock_schema, mock_verify):
        mock_schema.return_value = _parsed_resume()
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.yaml")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.yaml")))

    @patch("resume_manager.convert_resume.extract_resume_text", side_effect=DefectivePageError("page 1 looks defective"))
    def test_defective_page_propagates(self, mock_extract):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            with self.assertRaises(DefectivePageError):
                bootstrap_resume(source_pdf, resume_manager_dir)

    @patch("resume_manager.convert_resume.extract_resume_schema", return_value=None)
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_ollama_failure_still_leaves_raw_extraction_on_disk(self, mock_extract, mock_schema):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.yaml")))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_convert_resume -v`
Expected: FAIL — the current `convert_resume.py` imports/calls
`normalize_resume_text`/`verify_normalization` (removed in Task 4), so
these tests' patches of `extract_resume_schema`/`verify_extraction`
target names that don't exist there yet.

- [ ] **Step 3: Replace `resume_manager/convert_resume.py` entirely**

```python
"""
convert_resume.py
One-off bootstrap: copies the source resume PDF into resume-manager/,
extracts it locally, extracts it into the structured schema via a local
LLM call, and verifies that extraction before trusting it (spec §3
Revision 2). Not part of the per-application pipeline -- run once, or
re-run if the source PDF changes.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import yaml

from resume_manager.extract import DefectivePageError, extract_resume_text
from resume_manager.normalize import extract_resume_schema, verify_extraction
from resume_manager.schema import assign_ids

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
    meant to stop the run for the user's direct attention (spec §8). An
    extraction-verification mismatch does NOT raise -- that's the expected
    "flag for review" path."""
    os.makedirs(resume_manager_dir, exist_ok=True)
    dest_pdf = os.path.join(resume_manager_dir, "resume.pdf")
    shutil.copyfile(source_pdf, dest_pdf)

    raw_text = extract_resume_text(dest_pdf)
    processed_dir = os.path.join(resume_manager_dir, "processed_outputs")
    os.makedirs(processed_dir, exist_ok=True)
    raw_path = os.path.join(processed_dir, "resume_raw.md")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    parsed = extract_resume_schema(raw_text)
    if parsed is None:
        return (
            f"Extraction wrote {raw_path}, but the local Ollama extraction call failed or "
            f"returned invalid YAML -- is `ollama serve` running?"
        )

    assign_ids(parsed.get("work_experience") or [], "org")
    assign_ids(parsed.get("education") or [], "institution")

    problems = verify_extraction(parsed, raw_text)
    master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
    if not problems:
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(parsed, f, sort_keys=False, allow_unicode=True)
        return f"Wrote {master_path} (extraction verified clean)."

    review_path = os.path.join(resume_manager_dir, "resume_master.review.yaml")
    with open(review_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(parsed, f, sort_keys=False, allow_unicode=True)
    report = "\n".join(f"- {p}" for p in problems)
    return (
        f"Extraction verification flagged {len(problems)} issue(s) -- wrote {review_path} "
        f"for manual review instead of {master_path}:\n{report}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-off bootstrap: convert resume.pdf into the structured master resume.",
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
refactor(resume_manager): rewrite convert_resume.py for YAML output

Same copy -> extract -> extract-schema -> verify orchestration as v1,
now writing resume_master.yaml (or resume_master.review.yaml) with
code-assigned entry ids instead of freeform Markdown headings (spec
§3 Revision 2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 6: `tailor.py` — bullets-only LLM call + code-side reconstruction

**Files:**
- Modify: `resume_manager/tailor.py` (full rewrite)
- Modify: `tests/test_resume_tailor.py` (full rewrite)

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama`.
- Produces: `tailor_resume(master: dict, job_description: str, model: str = ...) -> dict | None`
  (returns `{"included_ids": [...], "bullets_by_id": {...}}`);
  `apply_tailoring(master: dict, tailoring_result: dict) -> tuple[dict, list[str]]`.
  Task 9 (`tailor_resume.py` CLI) calls both; Task 7 (`validate.py`)
  consumes the same `tailoring_result` shape `tailor_resume` produces.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_resume_tailor.py` entirely with:

```python
import unittest
from unittest.mock import patch

from resume_manager.tailor import apply_tailoring, tailor_resume

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [
        {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
         "start_date": "2020", "end_date": "Present", "bullets": ["Grew revenue 30%"]},
        {"id": "globex-1", "org": "Globex", "role": "Analyst", "location": "LA",
         "start_date": "2015", "end_date": "2018", "bullets": ["Built reports"]},
    ],
    "education": [{"id": "school-1", "institution": "State U"}],
    "awards": [{"name": "Award"}],
    "publications": [],
    "skills": [{"category": "Programming", "items": ["Python"]}],
}


class TestTailorResume(unittest.TestCase):
    @patch("resume_manager.tailor.call_ollama")
    def test_prompt_includes_only_id_org_role_bullets_no_other_metadata(self, mock_call):
        mock_call.return_value = "included_ids: [acme-1]\nbullets_by_id:\n  acme-1: [rewritten bullet]"

        tailor_resume(_MASTER, "a job description")

        prompt_arg = mock_call.call_args[0][0]
        self.assertIn("acme-1", prompt_arg)
        self.assertIn("Acme", prompt_arg)
        self.assertIn("Engineer", prompt_arg)
        self.assertIn("Grew revenue 30%", prompt_arg)
        self.assertNotIn("NYC", prompt_arg)
        self.assertNotIn("2020", prompt_arg)

    @patch("resume_manager.tailor.call_ollama", return_value="included_ids: [acme-1]\nbullets_by_id:\n  acme-1: [x]")
    def test_returns_parsed_yaml_dict(self, mock_call):
        result = tailor_resume(_MASTER, "jd")
        self.assertEqual(result, {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["x"]}})

    @patch("resume_manager.tailor.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(tailor_resume(_MASTER, "jd"))

    @patch("resume_manager.tailor.call_ollama", return_value="not valid: [yaml: at all")
    def test_returns_none_on_invalid_yaml(self, mock_call):
        self.assertIsNone(tailor_resume(_MASTER, "jd"))

    @patch("resume_manager.tailor.call_ollama", return_value="just_a_string_not_a_mapping")
    def test_returns_none_when_response_is_not_the_expected_shape(self, mock_call):
        self.assertIsNone(tailor_resume(_MASTER, "jd"))


class TestApplyTailoring(unittest.TestCase):
    def test_included_entry_gets_master_metadata_and_rewritten_bullets(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Rewrote this bullet"]}}
        tailored, problems = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual(problems, [])
        self.assertEqual(len(tailored["work_experience"]), 1)
        entry = tailored["work_experience"][0]
        self.assertEqual(entry["org"], "Acme")
        self.assertEqual(entry["location"], "NYC")
        self.assertEqual(entry["start_date"], "2020")
        self.assertEqual(entry["bullets"], ["Rewrote this bullet"])

    def test_excluded_entry_is_dropped(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["x"]}}
        tailored, _ = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual([e["id"] for e in tailored["work_experience"]], ["acme-1"])

    def test_other_categories_pass_through_unchanged(self):
        tailoring_result = {"included_ids": [], "bullets_by_id": {}}
        tailored, _ = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual(tailored["contact"], _MASTER["contact"])
        self.assertEqual(tailored["education"], _MASTER["education"])
        self.assertEqual(tailored["awards"], _MASTER["awards"])
        self.assertEqual(tailored["publications"], _MASTER["publications"])
        self.assertEqual(tailored["skills"], _MASTER["skills"])

    def test_unknown_id_is_skipped_and_reported_not_crashed(self):
        tailoring_result = {"included_ids": ["nonexistent"], "bullets_by_id": {}}
        tailored, problems = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual(tailored["work_experience"], [])
        self.assertTrue(any("nonexistent" in p for p in problems))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_tailor -v`
Expected: FAIL — `apply_tailoring` doesn't exist yet, and the current
`tailor_resume()` has a different signature (`(master_resume: str,
job_description: str)` returning `str | None`).

- [ ] **Step 3: Replace `resume_manager/tailor.py` entirely**

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_tailor -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/tailor.py tests/test_resume_tailor.py
git commit -m "$(cat <<'EOF'
refactor(resume_manager): rewrite tailor.py for bullets-only LLM output

The LLM now receives only id/org/role/bullets per Work Experience
entry and returns only included_ids + bullets_by_id -- apply_tailoring()
reconstructs the full tailored resume in code, copying every other
field verbatim, so metadata fabrication during tailoring is
structurally impossible rather than checked for afterward (spec §4
Revision 2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 7: `validate.py` — per-entry bullet-metric fact-diff

**Files:**
- Modify: `resume_manager/validate.py` (full rewrite)
- Modify: `tests/test_resume_validate.py` (full rewrite)

**Interfaces:**
- Consumes: `resume_manager.fact_diff.metrics_not_traceable`.
- Produces: `validate_tailored(master: dict, tailoring_result: dict) -> list[str]`
  (new signature — takes the raw `tailoring_result` from
  `tailor.tailor_resume`, not a rendered string), `format_report(problems: list[str]) -> str`
  (unchanged). Task 9 (`tailor_resume.py`) calls both.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_resume_validate.py` entirely with:

```python
import unittest

from resume_manager.validate import format_report, validate_tailored

_MASTER = {
    "work_experience": [
        {"id": "acme-1", "bullets": ["Grew revenue 30%"]},
        {"id": "globex-1", "bullets": ["Built reports"]},
    ],
}


class TestValidateTailored(unittest.TestCase):
    def test_matching_metric_is_not_flagged(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Grew revenue 30% via new pricing"]}}
        self.assertEqual(validate_tailored(_MASTER, tailoring_result), [])

    def test_invented_metric_is_flagged(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Grew revenue 75%"]}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("75%" in p for p in problems))

    def test_metric_is_checked_against_its_own_entry_only_not_the_whole_master(self):
        # "30%" belongs to acme-1's original bullets, not globex-1's --
        # globex-1's rewrite claiming it must still be flagged.
        tailoring_result = {"included_ids": ["globex-1"], "bullets_by_id": {"globex-1": ["Grew revenue 30%"]}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("30%" in p for p in problems))

    def test_unknown_included_id_is_flagged(self):
        tailoring_result = {"included_ids": ["nonexistent"], "bullets_by_id": {}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("nonexistent" in p for p in problems))


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
Expected: FAIL — the current `validate_tailored(master_resume: str,
tailored_resume: str)` has an incompatible signature/behavior for these
dict-based tests.

- [ ] **Step 3: Replace `resume_manager/validate.py` entirely**

```python
"""
validate.py
Per-entry bullet-metric fact-diff (spec §5 Revision 2): flags any metric
token in a rewritten bullet that isn't traceable to that SAME entry's
original bullets -- narrower and stronger than v1's whole-document check,
made possible by knowing exactly which master entry a rewritten bullet
came from. Never blocks rendering.
"""
from __future__ import annotations

from resume_manager.fact_diff import metrics_not_traceable


def validate_tailored(master: dict, tailoring_result: dict) -> list[str]:
    """Returns a list of human-readable warnings; empty means nothing was
    flagged. Also flags any included id absent from the master -- should
    be structurally impossible given tailor.apply_tailoring's own
    skip-and-report behavior, but checked here too so a report is never
    silently missing an issue apply_tailoring already knows about."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    bullets_by_id = tailoring_result.get("bullets_by_id") or {}
    problems: list[str] = []
    for entry_id in tailoring_result.get("included_ids") or []:
        source = master_by_id.get(entry_id)
        if source is None:
            problems.append(f"included id '{entry_id}' not found in master resume")
            continue
        original_text = "\n".join(source.get("bullets") or [])
        rewritten_text = "\n".join(bullets_by_id.get(entry_id) or [])
        for metric in metrics_not_traceable(rewritten_text, original_text):
            problems.append(f"{entry_id}: possible invented metric '{metric}' not found in original bullets")
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
refactor(resume_manager): rewrite validate.py for per-entry bullet checks

Metric fact-diff now scopes to each rewritten bullet's own original
entry, not the whole master document -- a tighter check made possible
by tailor.py knowing exactly which entry a rewritten bullet came from
(spec §5 Revision 2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 8: `render.py` — deterministic structured-data templating

**Files:**
- Modify: `resume_manager/render.py` (full rewrite)
- Modify: `tests/test_resume_render.py` (full rewrite)

**Interfaces:**
- Consumes: `markdown` (third-party), `xhtml2pdf.pisa` (third-party).
- Produces: `build_markdown(resume: dict) -> str` (new — pure templating,
  no I/O), `render_resume_pdf(resume: dict, output_path: str) -> None`
  (same name as v1, new signature — takes a structured dict, not a
  Markdown string). Task 9 (`tailor_resume.py`) calls `render_resume_pdf`.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_resume_render.py` entirely with:

```python
import os
import tempfile
import unittest

from resume_manager.render import build_markdown, render_resume_pdf

_RESUME = {
    "contact": {
        "name": "Aaron Scherf", "location": "USA", "email": "a@x.com",
        "linkedin_url": "https://linkedin.com/in/a", "github_url": "https://github.com/a",
        "website_url": "https://a.dev",
    },
    "work_experience": [{
        "org": "Acme", "role": "Engineer", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
    }],
    "education": [{
        "institution": "State U", "degree": "BS", "gpa": "3.9", "location": "TX",
        "start_date": "2016", "end_date": "2020", "thesis": None,
    }],
    "awards": [{"name": "Award", "description": "For doing things", "date": "2019"}],
    "publications": [{"title": "A Paper", "date": "2021", "venue": "A Venue", "link": None}],
    "skills": [{"category": "Programming", "items": ["Python", "R"]}],
}


class TestBuildMarkdown(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(build_markdown(_RESUME), build_markdown(_RESUME))

    def test_includes_every_category(self):
        markdown_text = build_markdown(_RESUME)
        for expected in ["Aaron Scherf", "Acme", "State U", "Award", "A Paper", "Python"]:
            self.assertIn(expected, markdown_text)

    def test_missing_optional_category_is_omitted_cleanly(self):
        resume = {**_RESUME, "publications": []}
        markdown_text = build_markdown(resume)
        self.assertNotIn("Research Presentations", markdown_text)


class TestRenderResumePdf(unittest.TestCase):
    def test_writes_a_non_empty_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path)

            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_resume_render -v`
Expected: FAIL — `build_markdown` doesn't exist yet, and the current
`render_resume_pdf(markdown_text: str, output_path: str)` expects a
string, not the structured dict these tests pass.

- [ ] **Step 3: Replace `resume_manager/render.py` entirely**

```python
"""
render.py
Deterministic templating of a structured resume (schema.py's shape) into
Markdown, then HTML, then a styled PDF via xhtml2pdf (spec §6 Revision 2)
-- no LLM output is ever handed straight to the `markdown` library.
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


def build_markdown(resume: dict) -> str:
    """Pure templating, no I/O, no LLM -- the same input always produces
    the same output (spec §6)."""
    parts: list[str] = []

    contact = resume.get("contact") or {}
    if contact.get("name"):
        parts.append(f"# {contact['name']}")
    contact_line = " • ".join(
        value for value in [
            contact.get("location"), contact.get("email"), contact.get("linkedin_url"),
            contact.get("github_url"), contact.get("website_url"),
        ] if value
    )
    if contact_line:
        parts.append(contact_line)

    if resume.get("work_experience"):
        parts.append("## Work Experience")
        for entry in resume["work_experience"]:
            parts.append(f"### {entry['org']} — {entry['role']} ({entry['start_date']} – {entry['end_date']})")
            if entry.get("location"):
                parts.append(entry["location"])
            for bullet in entry.get("bullets") or []:
                parts.append(f"- {bullet}")

    if resume.get("education"):
        parts.append("## Education")
        for entry in resume["education"]:
            parts.append(f"### {entry['institution']}")
            degree_line = entry.get("degree", "")
            if entry.get("gpa"):
                degree_line += f" • GPA: {entry['gpa']}"
            parts.append(f"- {degree_line}")
            parts.append(f"- {entry.get('location', '')} • {entry['start_date']} – {entry['end_date']}")
            if entry.get("thesis"):
                parts.append(f"- Thesis: {entry['thesis']}")

    if resume.get("awards"):
        parts.append("## Awards & Scholarships")
        for entry in resume["awards"]:
            parts.append(f"- {entry['name']} ({entry['date']}) — {entry['description']}")

    if resume.get("publications"):
        parts.append("## Research Presentations & Publications")
        for entry in resume["publications"]:
            line = f"- {entry['title']} ({entry['date']}) — {entry['venue']}"
            if entry.get("link"):
                line += f" ([link]({entry['link']}))"
            parts.append(line)

    if resume.get("skills"):
        parts.append("## Skills")
        for entry in resume["skills"]:
            items = ", ".join(entry.get("items") or [])
            parts.append(f"- **{entry['category']}**: {items}")

    return "\n\n".join(parts)


def render_resume_pdf(resume: dict, output_path: str) -> None:
    """Templates `resume` to Markdown, then HTML, then a styled PDF at
    `output_path`. Raises if xhtml2pdf reports an error (pisa.CreatePDF's
    `.err` is non-zero) -- an application's PDF is either fully written
    or not written at all, never a silently-broken partial file."""
    markdown_text = build_markdown(resume)
    html_body = markdown_lib.markdown(markdown_text)
    full_html = f"<html><head>{_CSS}</head><body>{html_body}</body></html>"
    with open(output_path, "wb") as f:
        result = pisa.CreatePDF(full_html, dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} error(s) rendering {output_path}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_resume_render -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_manager/render.py tests/test_resume_render.py
git commit -m "$(cat <<'EOF'
refactor(resume_manager): rewrite render.py for structured-data templating

Markdown is now built deterministically from the structured resume
dict (build_markdown()) instead of being authored by an LLM -- the
same input always produces byte-identical formatting, and formatting
can no longer drift per application (spec §6 Revision 2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 9: `tailor_resume.py` — per-application CLI for the new modules

**Files:**
- Modify: `resume_manager/tailor_resume.py` (full rewrite)
- Modify: `tests/test_tailor_resume_cli.py` (full rewrite)

**Interfaces:**
- Consumes: `resume_manager.tailor.tailor_resume`, `apply_tailoring`;
  `resume_manager.validate.validate_tailored`, `format_report`;
  `resume_manager.render.render_resume_pdf`.
- Produces: `run_tailoring(master_resume_path: str, jd_path: str,
  application_name: str, resume_manager_dir: str) -> str` (same signature
  as v1), a `main()` CLI entry point. Terminal task.

- [ ] **Step 1: Replace the test file**

Replace the contents of `tests/test_tailor_resume_cli.py` entirely with:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.tailor_resume import run_tailoring

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [{
        "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
    }],
    "education": [], "awards": [], "publications": [], "skills": [],
}


class TestRunTailoring(unittest.TestCase):
    def _setup(self, tmp):
        resume_manager_dir = os.path.join(tmp, "resume-manager")
        os.makedirs(resume_manager_dir, exist_ok=True)
        master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(_MASTER, f)
        jd_path = os.path.join(tmp, "jd.txt")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write("Looking for an engineer.")
        return resume_manager_dir, master_path, jd_path

    @patch("resume_manager.tailor_resume.render_resume_pdf")
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
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
            tailored_path = os.path.join(app_dir, "tailored_resume.yaml")
            self.assertTrue(os.path.exists(tailored_path))
            with open(tailored_path, encoding="utf-8") as f:
                tailored = yaml.safe_load(f)
            self.assertEqual(tailored["work_experience"][0]["bullets"], ["Did a rewritten thing"])
            self.assertEqual(tailored["work_experience"][0]["org"], "Acme")
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
                    os.path.join(resume_manager_dir, "resume_master.yaml"), jd_path, "acme", resume_manager_dir,
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
Expected: FAIL — the current `tailor_resume.py` reads/writes `.md` files
and calls the old `tailor_resume`/`validate_tailored` signatures.

- [ ] **Step 3: Replace `resume_manager/tailor_resume.py` entirely**

```python
"""
tailor_resume.py
CLI entry point for one application: tailor -> validate -> render (spec
§4-§7 Revision 2). Run per job application, after the bootstrap
(convert_resume.py) has produced resume_master.yaml.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
from pathlib import Path

import yaml

from resume_manager.render import render_resume_pdf
from resume_manager.tailor import apply_tailoring, tailor_resume
from resume_manager.validate import format_report, validate_tailored

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "application"


def run_tailoring(master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str) -> str:
    """Runs tailor -> validate -> render for one application and returns
    a one-line status message. Raises FileNotFoundError up front if
    either input file is missing, before any Ollama call (spec §8)."""
    if not os.path.exists(master_resume_path):
        raise FileNotFoundError(f"{master_resume_path} not found -- run convert_resume.py's bootstrap first.")
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"job description file not found: {jd_path}")

    with open(master_resume_path, "r", encoding="utf-8") as f:
        master = yaml.safe_load(f)
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    tailoring_result = tailor_resume(master, job_description)
    if tailoring_result is None:
        raise RuntimeError(
            "local Ollama tailoring call failed, timed out, or returned invalid YAML -- "
            "is `ollama serve` running?"
        )

    tailored, reconstruction_problems = apply_tailoring(master, tailoring_result)

    date_str = datetime.date.today().isoformat()
    app_dir = os.path.join(resume_manager_dir, "applications", f"{date_str}-{_slugify(application_name)}")
    os.makedirs(app_dir, exist_ok=True)

    with open(os.path.join(app_dir, "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_description)
    with open(os.path.join(app_dir, "tailored_resume.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(tailored, f, sort_keys=False, allow_unicode=True)

    problems = reconstruction_problems + validate_tailored(master, tailoring_result)
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

    master_resume_path = os.path.join(args.resume_manager_dir, "resume_master.yaml")
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
refactor(resume_manager): rewrite tailor_resume.py CLI for the new modules

Reads/writes resume_master.yaml / tailored_resume.yaml, and wires
tailor.py's apply_tailoring() + validate.py's tailoring_result-based
signature into the same tailor -> validate -> render orchestration as
v1 (spec §7 Revision 2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```

---

### Task 10: Documentation

**Files:**
- Modify: `resume_manager/README.md`
- Modify: `resume_manager_instructions.md`
- Modify: `README.md` (repository layout list entry, if wording needs a touch-up)

**Interfaces:** none (documentation only).

- [ ] **Step 1: Rewrite `resume_manager/README.md`**

Replace its contents entirely with:

```markdown
# Resume Manager

Converts the user's resume PDF into a hand-maintained **structured** master
resume (`resume_master.yaml`), then tailors it per job application via a
local Ollama model and renders a styled PDF — fully local except for
reading the source PDF itself: no paid API call anywhere in this
subproject.

## One-time bootstrap

```powershell
.\.venv\Scripts\python.exe -m resume_manager.convert_resume
```

Copies the source resume PDF, extracts its text locally (0 API calls),
extracts it into the structured schema via a local Ollama call, and
verifies every required field's traceability against the raw extraction
before writing `resume_master.yaml`. A verification mismatch writes
`resume_master.review.yaml` instead, for manual reconciliation of just the
flagged field(s).

`resume_master.yaml` is then yours to keep expanding by hand over time —
never overwritten by a re-run of this bootstrap.

## Per application

```powershell
.\.venv\Scripts\python.exe -m resume_manager.tailor_resume --jd-file "path\to\job_description.txt" --application-name "acme-corp"
```

Selects which Work Experience entries to highlight and rewrites their
bullets to mirror the job description — every other field (org, role,
location, dates, and every other resume section) is copied through
unchanged by code, never re-emitted by the LLM. Writes
`job_description.txt`, `tailored_resume.yaml`, `validation_report.txt`, and
`Tailored_Resume.pdf` into
`research/independent-research/projects/resume-manager/applications/<date>-<application-name>/`.

## Requirements

- A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled
  (`ollama pull qwen2.5:7b-instruct`) — overridable via
  `RESUMEMANAGER_OLLAMA_MODEL`. CPU-only inference on this model can take
  up to `RESUMEMANAGER_OLLAMA_TIMEOUT` seconds (default `1800`).
- No `GEMINI_API_KEY` needed anywhere in this subproject.

## Key files

- `extract.py` — local, zero-API-call PDF text extraction, reusing
  `notes/transcribe_notes.py`'s Tier-1 primitives directly (never its
  tier-routing wrapper — see the design spec's §3 for why).
- `schema.py` — the structured master-resume schema's field lists, stable
  id assignment, and generic required-field/traceability verification.
- `normalize.py` — local-LLM extraction of the raw text into that schema,
  verified via `schema.py` before being trusted.
- `fact_diff.py` — free-text numeric-metric extraction/traceability, used
  by `validate.py` to scope a check to one entry's own original bullets.
- `convert_resume.py` — the one-time bootstrap CLI.
- `tailor.py` — the bullets-only local-LLM call, plus code-side
  reconstruction of the full tailored resume (`apply_tailoring`).
- `validate.py` — per-entry bullet-metric fact-diff for a tailored resume.
- `render.py` — deterministic Markdown templating of a structured resume,
  then → styled PDF via `xhtml2pdf`.
- `tailor_resume.py` — the per-application CLI, orchestrating
  tailor → validate → render.

See the design spec for the full reasoning (Revision 2 note at the top
covers what changed and why):
`../docs/superpowers/specs/2026-09-09-resume-manager-design.md`.
```

- [ ] **Step 2: Rewrite `resume_manager_instructions.md`**

Replace its contents entirely with:

```markdown
# Resume Manager

Companion to `journal_articles_instructions.md`/`notes_instructions.md`,
but for a single, personal, hand-curated document rather than a corpus:
the user's resume. Two independent runs — a one-time bootstrap, and a
per-application tailoring pipeline. **Revision 2**: the master resume is a
structured YAML file, not freeform Markdown — see "How it works" below for
why.

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
* The raw extraction is parsed into the structured schema (below) via one
  local Ollama call, then every required field is checked for
  traceability against the raw extraction before being trusted — a clean
  check writes `resume_master.yaml` directly; a flagged mismatch writes
  `resume_master.review.yaml` instead so you only reconcile the flagged
  field(s) by hand.
* Re-running this bootstrap never overwrites an existing
  `resume_master.yaml` — only run it again if the *source PDF* changes;
  ongoing edits to your master resume are yours to make directly in
  `resume_master.yaml`.

**Schema for `resume_master.yaml`:**

```yaml
contact:
  name: str
  location: str
  email: str
  linkedin_url: str
  github_url: str
  website_url: str
work_experience:
  - id: str              # auto-assigned, e.g. "usaid-1" -- don't hand-edit
    org: str
    role: str
    location: str
    start_date: str
    end_date: str         # or "Present"
    bullets: [str]
education:
  - id: str
    institution: str
    degree: str
    gpa: str              # optional
    location: str
    start_date: str
    end_date: str
    thesis: str            # optional
awards:
  - name: str
    description: str
    date: str
publications:
  - title: str
    date: str
    venue: str
    link: str              # optional
skills:
  - category: str
    items: [str]
```

`id` fields are assigned once by the bootstrap and referenced by
`tailor.py` to key rewritten bullets back to the correct entry — leave
them as-is when hand-editing (add new entries freely; each gets its own
id automatically only via a fresh bootstrap run, so a hand-added entry
needs its own manually-chosen, unique `id` in the meantime, e.g.
`"my-new-role-1"`).

## Step 2: Per-application tailoring

```powershell
python -m resume_manager.tailor_resume --jd-file "job_description.txt" --application-name "acme-corp"
```

* `--jd-file` is a local text file with the job description pasted in —
  no URL scraping in this version.
* `--application-name` becomes part of the output folder name
  (`applications/<YYYY-MM-DD>-<slugified-name>/`).
* Tailoring sends the LLM only each Work Experience entry's `id`/`org`/
  `role`/`bullets` and the job description — it returns only which ids to
  include and rewritten bullets per id. Every other field, and every
  other resume section (Education, Awards, Publications, Skills, Contact),
  is copied through unchanged by code — the LLM never sees or re-emits a
  date, an org name, a location, a GPA, or anything outside Work
  Experience bullets. `validate.py` then flags any rewritten bullet whose
  numbers/`$`/`%` don't trace back to that *same entry's* original
  bullets — written to `validation_report.txt` alongside the tailored
  YAML and the rendered PDF. Flags are warnings, not blockers.

## How it works

* **Structured schema, not freeform Markdown (Revision 2).** v1 asked the
  LLM to author a Markdown heading per entry; against the real resume, two
  roles shared one printed date range with their employer, and the LLM
  silently substituted each role's location into the heading's date slot
  instead — an ambiguity a single freeform text slot had no way to avoid.
  Named fields remove the ambiguity entirely, and verification becomes a
  direct field check instead of a heuristic.
* **Tailoring never lets the LLM touch metadata**, for the same reason:
  not "the LLM was told not to change it," but "the LLM's response has no
  field to put it in even if it wanted to."
* **Reuses `notes/transcribe_notes.py`'s extraction primitives, not its
  `process_pdf()` wrapper.** That wrapper's tier-routing decision sniffs
  `/Creator`/`/Producer` metadata for LaTeX/Word/LibreOffice/Apache
  FOP/XEP and fails safe to the handwriting/messy-export fallback for
  anything else. Confirmed against the user's real `resume.pdf`: its
  `/Producer` is `Skia/PDF m124` (headless-Chrome print-to-PDF),
  unrecognized by that check, even though the extracted text is clean.
* **No paid API call anywhere in this subproject** — extraction is local
  PyMuPDF, schema extraction and tailoring are local Ollama.
  `GEMINI_API_KEY` is never read.
* **Rendering uses `xhtml2pdf`, not `weasyprint`.** `weasyprint` depends
  on the Pango/GTK native libraries, which aren't a plain `pip install` on
  Windows and were confirmed not to import on this machine. `xhtml2pdf` is
  pure Python, and rendering is now deterministic templating over
  structured data rather than converting LLM-authored Markdown.
```

- [ ] **Step 3: Commit**

```bash
git add resume_manager/README.md resume_manager_instructions.md
git commit -m "$(cat <<'EOF'
docs(resume_manager): update docs for structured YAML master resume

Reflects Revision 2 throughout: the schema itself, id-based tailoring
(bullets-only LLM output, code-side reconstruction), and why the
freeform-Markdown design was replaced.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01XMPj3X98CBxd3PsEL63e3U
EOF
)"
```
