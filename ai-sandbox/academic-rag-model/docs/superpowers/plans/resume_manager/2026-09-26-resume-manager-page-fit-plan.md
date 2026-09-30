# Resume Manager — Page-Fit-Aware Selection & Clean Section Breaks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Status: implemented natively in the same session that wrote this plan (2026-09-26)**, after extensive empirical validation of the Typst mechanics (see Task 1's design-correction note) made the remaining work low-risk enough that a separate plan-review round trip wasn't worth the delay. This document is kept as the durable record of what was built and why, matching this project's existing convention (`docs/superpowers/plans/2026-09-09-resume-manager-plan.md`) of a written plan alongside the spec.
>
> **Further corrected after real user feedback on the shipped result, same day:** Task 5's `include_count: int` (whole-entry-at-a-time fill) turned out to leave a large, visibly wrong blank gap on page 1 -- replaced with bullet-level granularity (`bullet_budget: dict[str, int]`, `_select_work_experience_bullets()`). A second real bug surfaced at the same time: rank-ordering Work Experience broke render.py's shared-employer date carry-forward, fixed by having `apply_tailoring()` select by rank but display in master (chronological) order. See spec §13b for the corrected, actually-shipped design -- Task 5 below is kept as-written for the historical record of what was originally planned and why it needed correcting, not as an accurate description of the final code.

**Goal:** Implement spec §12/§13 → correction: §13 only ("Page-fit-aware Work Experience selection & clean section breaks", Revision 6) of `docs/superpowers/specs/2026-09-09-resume-manager-design.md`: Education/Awards/Publications/Skills never split across a page boundary, and Work Experience fills available page-1 space with as many relevant entries as fit.

**Architecture:** Two independent mechanisms per the spec: (13a) each of Education/Awards/Publications/Skills is wrapped in one Typst non-breakable block in `render.py`, purely a templating change; (13b) `tailor.py` returns *all* Work Experience entries ranked by relevance instead of a binary include/exclude list, and `tailor_resume.py` runs a greedy render-measure-retry loop (using `render.py`'s existing density-tier machinery) to decide how many top-ranked entries to actually include.

**Tech Stack:** Python 3.13, Typst (via the `typst` package), `pypdf` (page counting), `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-09-resume-manager-design.md` §13 (13a corrected during this plan's own validation — see Task 1).

## Global Constraints

- Never touch Work Experience's breakability — it's the one section §13b deliberately grows to fill space (spec §13a non-goals).
- `validate_tailored` must validate the *actually-included* tailored entries, never the raw LLM candidate pool (a gap the original spec didn't call out explicitly — see Task 4).
- `render_resume_pdf`'s existing density-tier shrink loop (spec §6) stays untouched and still applies per candidate render; the fill loop's job is purely "how many entries," never "how small can the font get."
- Every existing resume_manager test must keep passing — no regressions to the Revision 5 Typst rendering work or the pre-existing tailor/validate contracts beyond the intentional `included_ids` → `ranked_ids` rename.

## Review Focus

- A section (Education/Awards/Publications/Skills) with zero entries — must not emit an empty non-breakable block that could misbehave — covered by the existing `if resume.get("education"):` etc. guards, unchanged.
- `ranked_ids` containing an id the master doesn't have (a hallucinated id) — must be skipped and reported by `apply_tailoring`, not crash — covered by Task 3's regression test (renamed from the pre-existing `included_ids` version).
- The fill loop when `ranked_ids` is empty (Ollama returned zero entries) — must return `0`, not crash or infinite-loop — covered by Task 5's `test_no_ranked_ids_returns_zero`.
- The fill loop when even the *first* candidate overflows `target_pages` — must still return `1` (never zero Work Experience), accepting the overflow at render_resume_pdf's own tightest tier — covered by Task 5's `test_a_single_entry_that_overflows_is_still_included`.
- A section wrapped non-breakable that's taller than one full page — Typst silently clips rather than erroring (confirmed empirically, Task 1) — not defended against; documented as an accepted limitation in spec §13's non-goals given real content sizes.

---

### Task 1: Whole-section non-breakable wrapping in `render.py` (spec §13a)

**Files:**
- Modify: `resume_manager/render.py`
- Test: `tests/test_resume_render.py`

**Interfaces:**
- Consumes: existing `build_typst(resume, tier)`'s per-section `parts` construction.
- Produces: `_non_breakable_section(section_parts: list[str]) -> str`, used by the Education/Awards/Publications/Skills branches of `build_typst`. Work Experience is unaffected — still appends its heading and each entry as separate, independently-breakable `parts` entries.

**Design correction made during this task (important — read before touching this code again):** The spec as originally written said to wrap only "the heading plus its first entry." Verified empirically against the real Education content (all 6 institutions) that this does **not** prevent the section from splitting — entries after the first can still spill to the next page independently, which is the exact defect being fixed. The corrected, validated design wraps the section's **entire** content (heading through its last entry) in one `#block(breakable: false)[...]`. Confirmed empirically (see the calibration below) that this correctly moves the whole section together. The spec document (`docs/superpowers/specs/2026-09-09-resume-manager-design.md` §13a) has already been corrected to describe this validated design — if you're reading this plan without having read that update, re-read §13a in full before proceeding.

Also confirmed empirically: if a wrapped section's content is ever taller than one full page, Typst silently clips the overflow at the page boundary rather than erroring or flowing to a new page. This is why the wrap is scoped to Education/Awards/Publications/Skills only (each realistically a handful of entries) and never Work Experience (the one section that can legitimately grow large, and whose growth is the whole point of Task 5's fill loop).

- [x] **Step 1: Write the failing regression test**

Calibrated directly against the real `build_typst()` (not a synthetic approximation — this project's own testing convention, e.g. `normalize.py`'s tests, prefers real content): 37 filler bullets in one Work Experience entry pushes the real Education section (using the user's actual 3-institution excerpt below) right up against a page boundary on the pre-fix code, reproducing the exact real defect (Columbia + Georgia Tech on page 1, Indiana State spilling to page 2).

```python
class TestNonBreakableSectionRegression(unittest.TestCase):
    _EDUCATION = [
        {
            "institution": "Columbia University", "degree": "PhD in Sustainable Development",
            "gpa": None, "location": "New York, NY, USA", "start_date": "08/2026",
            "end_date": "Present", "thesis": None,
        },
        {
            "institution": "Georgia Institute of Technology", "degree": "Master of Science in Computer Science",
            "gpa": "3.88", "location": "Atlanta, GA, USA", "start_date": "01/2022",
            "end_date": "12/2025", "thesis": None,
        },
        {
            "institution": "Indiana State University", "degree": "Master of Science in Mathematics",
            "gpa": "3.85", "location": "Terre Haute, IN, USA", "start_date": "05/2021",
            "end_date": "05/2024", "thesis": None,
        },
    ]

    def test_education_section_does_not_split_across_a_forced_page_break(self):
        resume = {
            "contact": {"name": "Test Person", "email": "a@x.com"},
            "work_experience": [{
                "org": "Acme", "role": "Engineer", "location": "NYC",
                "start_date": "2020", "end_date": "Present",
                "bullets": [
                    f"Filler bullet number {i} with some descriptive padding text to take up space."
                    for i in range(37)
                ],
            }],
            "education": self._EDUCATION,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Resume.pdf")
            render_resume_pdf(resume, output_path, target_pages=50)  # never trigger tier-shrink

            from pypdf import PdfReader
            texts = [page.extract_text() for page in PdfReader(output_path).pages]
            pages_with_institution = [
                i for i, t in enumerate(texts)
                if any(entry["institution"] in t for entry in self._EDUCATION)
            ]
            self.assertEqual(len(set(pages_with_institution)), 1, "Education split across more than one page")
            for entry in self._EDUCATION:
                self.assertIn(entry["institution"], texts[pages_with_institution[0]])
```

Also add these unit tests to `TestBuildTypst`:

```python
    def test_education_awards_publications_skills_are_non_breakable_blocks(self):
        typst_text = build_typst(_RESUME)
        for heading in ["== Education", "== Awards", "== Research Presentations", "== Skills"]:
            self.assertIn(f"#block(breakable: false)[\n{heading}", typst_text)

    def test_work_experience_is_not_wrapped_non_breakable(self):
        typst_text = build_typst(_RESUME)
        self.assertNotIn("#block(breakable: false)[\n== Work Experience", typst_text)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_resume_render.py -k "non_breakable" -v`
Expected: FAIL — no `_non_breakable_section` wrapping exists yet, and the regression test reproduces the real split (`len(set(pages_with_institution))` is 2, not 1).

- [x] **Step 3: Implement `_non_breakable_section` and use it for the four sections**

In `resume_manager/render.py`, add above `build_typst`:

```python
def _non_breakable_section(section_parts: list[str]) -> str:
    """Wraps a whole section's content (heading through its last entry) in
    one Typst non-breakable block (spec §13a) so it moves to the next page
    as one atomic unit instead of splitting mid-section -- confirmed
    empirically during planning (2026-09-26) that wrapping only the
    heading + first entry does NOT stop later entries from spilling
    independently onto the next page; the whole section must be one
    block. Never used for Work Experience, which must stay
    breakable/flowing since the fill loop in tailor_resume.py (spec §13b)
    deliberately grows its length to fill available space -- and because
    a non-breakable block's content silently clips at the page boundary
    if it's ever taller than one full page (confirmed empirically), never
    errors or flows to a new page, which would be a real risk for Work
    Experience's variable, potentially large size but isn't for the
    handful of entries Education/Awards/Publications/Skills realistically
    contain."""
    return "#block(breakable: false)[\n" + "\n\n".join(section_parts) + "\n]"
```

Then change each of the Education/Awards/Publications/Skills branches to build a local `section_parts` list (starting with the `== Heading` string) instead of appending directly to `parts`, and finish each branch with `parts.append(_non_breakable_section(section_parts))`. Work Experience's branch is untouched. See the actual diff in `resume_manager/render.py` (already applied) for the exact restructuring — mechanically: replace `parts.append(...)` with `section_parts.append(...)` throughout each of those four branches, then add the one `parts.append(_non_breakable_section(section_parts))` line at the end of each.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_resume_render.py -v`
Expected: PASS (all tests, including the pre-existing 22 from Revision 5).

- [x] **Step 5: Commit**

```bash
git add resume_manager/render.py tests/test_resume_render.py docs/superpowers/specs/2026-09-09-resume-manager-design.md
git commit -m "feat(resume_manager): wrap Education/Awards/Publications/Skills as non-breakable sections"
```

---

### Task 2: `render_resume_pdf` returns the achieved page count

**Files:**
- Modify: `resume_manager/render.py`
- Test: `tests/test_resume_render.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `render_resume_pdf(resume: dict, output_path: str, target_pages: int = 2) -> int` (previously returned `None`). Task 5's fill loop relies on this return value directly instead of a separate page-count call.

- [x] **Step 1: Write the failing test**

```python
    def test_render_resume_pdf_returns_the_achieved_page_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")
            page_count = render_resume_pdf(_RESUME, output_path)
            from pypdf import PdfReader
            self.assertEqual(page_count, len(PdfReader(output_path).pages))
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_resume_render.py -k returns_the_achieved -v`
Expected: FAIL — `render_resume_pdf` returns `None`.

- [x] **Step 3: Change `render_resume_pdf` to track and return `page_count`**

```python
def render_resume_pdf(resume: dict, output_path: str, target_pages: int = 2) -> int:
    typst_path = re.sub(r"\.pdf$", ".typ", output_path, flags=re.IGNORECASE)
    if typst_path == output_path:
        typst_path = output_path + ".typ"
    page_count = 0
    for tier in _DENSITY_TIERS:
        typst_source = build_typst(resume, tier)
        with open(typst_path, "w", encoding="utf-8") as f:
            f.write(typst_source)
        typst.compile(typst_path, output=output_path)
        page_count = _pdf_page_count(output_path)
        if page_count <= target_pages:
            return page_count
    return page_count
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_resume_render.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add resume_manager/render.py tests/test_resume_render.py
git commit -m "feat(resume_manager): render_resume_pdf returns its achieved page count"
```

---

### Task 3: `tailor.py` — `ranked_ids` replaces `included_ids`

**Files:**
- Modify: `resume_manager/tailor.py`
- Test: `tests/test_resume_tailor.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `tailor_resume(...)` now returns `{"ranked_ids": [...], "bullets_by_id": {...}, "include_github": bool}` (was `included_ids`). `apply_tailoring(master, tailoring_result, include_count: int | None = None)` gains the `include_count` parameter — `None` uses every ranked id (unchanged default behavior for direct callers); an int takes the top N.

- [x] **Step 1: Update the failing/changing tests**

In `tests/test_resume_tailor.py`, rename every `included_ids` fixture key and expected-value key to `ranked_ids` (a mechanical find/replace across the file — every existing test's *semantics* are unchanged, only the key name). Then add:

```python
    def test_include_count_takes_only_the_top_n_ranked_ids(self):
        tailoring_result = {
            "ranked_ids": ["acme-1", "globex-1"],
            "bullets_by_id": {"acme-1": ["x"], "globex-1": ["y"]},
        }
        tailored, _ = apply_tailoring(_MASTER, tailoring_result, include_count=1)
        self.assertEqual([e["id"] for e in tailored["work_experience"]], ["acme-1"])

    def test_include_count_zero_yields_no_work_experience(self):
        tailoring_result = {"ranked_ids": ["acme-1", "globex-1"], "bullets_by_id": {}}
        tailored, _ = apply_tailoring(_MASTER, tailoring_result, include_count=0)
        self.assertEqual(tailored["work_experience"], [])

    def test_include_count_none_uses_every_ranked_id(self):
        tailoring_result = {
            "ranked_ids": ["acme-1", "globex-1"],
            "bullets_by_id": {"acme-1": ["x"], "globex-1": ["y"]},
        }
        tailored, _ = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual([e["id"] for e in tailored["work_experience"]], ["acme-1", "globex-1"])
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_resume_tailor.py -v`
Expected: FAIL — `tailor_resume`/`apply_tailoring` still use `included_ids` and `apply_tailoring` doesn't accept `include_count`.

- [x] **Step 3: Implement**

In `_SYSTEM_PROMPT`, change rule 2 to ask for a full ranking (every id, most-to-least relevant) instead of a subset, and change the output-shape example to `ranked_ids: [most_relevant_id, id2, ..., least_relevant_id]`. In `tailor_resume()`, change the shape check from `"included_ids" not in parsed` to `"ranked_ids" not in parsed`. In `apply_tailoring()`, add `include_count: int | None = None`, compute `ranked_ids = tailoring_result.get("ranked_ids") or []` and `ids_to_include = ranked_ids if include_count is None else ranked_ids[:include_count]`, and iterate `ids_to_include` instead of `tailoring_result.get("included_ids")`.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_resume_tailor.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add resume_manager/tailor.py tests/test_resume_tailor.py
git commit -m "feat(resume_manager): tailor.py ranks all entries instead of a binary include/exclude"
```

---

### Task 4: `validate.py` — validate the reconstructed tailored resume, not the raw LLM response

**Files:**
- Modify: `resume_manager/validate.py`
- Modify: `resume_manager/tailor_resume.py:111` (call site: `validate_tailored(master, tailoring_result)` → `validate_tailored(master, tailored)`)
- Test: `tests/test_resume_validate.py`

**Why this task exists (not explicitly called out in spec §13, found during planning):** After Task 3, `tailoring_result["ranked_ids"]` can contain *every* Work Experience entry, most of which never make it into the final tailored resume (only the top `include_count` do, per Task 5). If `validate_tailored` kept reading `ranked_ids`/`bullets_by_id` directly, it would run its metric-preservation checks against entries that were never actually included in the rendered PDF — the wrong entry set. The fix: validate against `tailored["work_experience"]` (already-reconstructed, already-trimmed) instead of the raw candidate pool. This also fully decouples `validate.py` from `tailor.py`'s exact response field names.

**Interfaces:**
- Consumes: `tailored: dict` (the reconstructed resume dict — `apply_tailoring`'s first return value).
- Produces: `validate_tailored(master: dict, tailored: dict) -> list[str]` (signature changed from `validate_tailored(master: dict, tailoring_result: dict)`).

- [x] **Step 1: Update the tests for the new signature**

Replace `tests/test_resume_validate.py` in full — same test cases, but each now builds a `tailored = {"work_experience": [...]}` dict directly (with `id` and already-rewritten `bullets` per entry) instead of a `tailoring_result` with `included_ids`/`bullets_by_id`. Add one new test:

```python
    def test_entry_with_no_matching_master_source_does_not_crash(self):
        tailored = {"work_experience": [{"id": "nonexistent", "bullets": ["Some bullet"]}]}
        self.assertEqual(validate_tailored(_MASTER, tailored), [])
```

(Full rewritten file already applied — see `tests/test_resume_validate.py`.)

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_resume_validate.py -v`
Expected: FAIL — `validate_tailored` still reads `included_ids`/`bullets_by_id` from its second argument.

- [x] **Step 3: Implement**

```python
def validate_tailored(master: dict, tailored: dict) -> list[str]:
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    problems: list[str] = []
    openings: dict[str, int] = {}
    for entry in tailored.get("work_experience") or []:
        entry_id = entry["id"]
        source = master_by_id.get(entry_id) or {}
        original_text = "\n".join(source.get("bullets") or [])
        rewritten_bullets = entry.get("bullets") or []
        rewritten_text = "\n".join(rewritten_bullets)
        for metric in metrics_not_traceable(rewritten_text, original_text):
            problems.append(f"{entry_id}: possible invented metric '{metric}' not found in original bullets")
        for metric in metrics_not_traceable(original_text, rewritten_text):
            problems.append(f"{entry_id}: possible dropped metric '{metric}' from original bullets not found in rewritten bullets")
        for bullet in rewritten_bullets:
            opening = _opening_phrase(bullet)
            if len(opening.split()) == _OPENING_WORD_COUNT:
                openings[opening] = openings.get(opening, 0) + 1
    for opening, count in openings.items():
        if count > 1:
            problems.append(
                f"repeated bullet opening: {count} bullets start with \"{opening}...\" -- vary the phrasing"
            )
    return problems
```

Note the dropped "unknown id" branch: `apply_tailoring` already guarantees every entry in `tailored["work_experience"]` resolves to a real master source (an unresolvable id is skipped and reported in `apply_tailoring`'s own return value, which `tailor_resume.py` already merges with this function's problems) — so that check is now dead code and is removed rather than kept as inert cruft. Update the call site in `tailor_resume.py` from `validate_tailored(master, tailoring_result)` to `validate_tailored(master, tailored)` (this line moves after `apply_tailoring` is called, which it already is positionally).

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_resume_validate.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add resume_manager/validate.py resume_manager/tailor_resume.py tests/test_resume_validate.py
git commit -m "fix(resume_manager): validate the actually-included tailored entries, not the raw ranked pool"
```

---

### Task 5: `tailor_resume.py` — greedy render-measure-retry fill loop

**Files:**
- Modify: `resume_manager/tailor_resume.py`
- Test: `tests/test_tailor_resume_cli.py`

**Interfaces:**
- Consumes: `render_resume_pdf(resume, output_path, target_pages) -> int` (Task 2), `apply_tailoring(master, tailoring_result, include_count) -> tuple[dict, list[str]]` (Task 3).
- Produces: `_select_work_experience_count(master, tailoring_result, target_pages, scratch_pdf_path) -> int`. `run_tailoring(...)` gains a `target_pages: int = 2` parameter.

- [x] **Step 1: Write the failing tests**

```python
class TestSelectWorkExperienceCount(unittest.TestCase):
    _MULTI_ENTRY_MASTER = {
        "work_experience": [
            {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
             "start_date": "2020", "end_date": "Present", "bullets": ["a"]},
            {"id": "globex-1", "org": "Globex", "role": "Analyst", "location": "LA",
             "start_date": "2015", "end_date": "2018", "bullets": ["b"]},
            {"id": "initech-1", "org": "Initech", "role": "Consultant", "location": "Austin",
             "start_date": "2010", "end_date": "2014", "bullets": ["c"]},
        ],
        "education": [], "awards": [], "publications": [], "skills": [],
    }

    def test_no_ranked_ids_returns_zero(self):
        tailoring_result = {"ranked_ids": [], "bullets_by_id": {}}
        count = _select_work_experience_count(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(count, 0)

    @patch("resume_manager.tailor_resume.render_resume_pdf", side_effect=[1, 1, 3])
    def test_stops_at_the_last_count_that_still_fits(self, mock_render):
        tailoring_result = {
            "ranked_ids": ["acme-1", "globex-1", "initech-1"],
            "bullets_by_id": {"acme-1": ["x"], "globex-1": ["y"], "initech-1": ["z"]},
        }
        count = _select_work_experience_count(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(count, 2)
        self.assertEqual(mock_render.call_count, 3)

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1)
    def test_uses_every_ranked_id_when_all_fit(self, mock_render):
        tailoring_result = {
            "ranked_ids": ["acme-1", "globex-1", "initech-1"],
            "bullets_by_id": {"acme-1": ["x"], "globex-1": ["y"], "initech-1": ["z"]},
        }
        count = _select_work_experience_count(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(count, 3)

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=5)
    def test_a_single_entry_that_overflows_is_still_included(self, mock_render):
        tailoring_result = {"ranked_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["x"]}}
        count = _select_work_experience_count(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(count, 1)
```

Also update `TestRunTailoring`'s existing mocked-`render_resume_pdf` tests to pass `return_value=1` (the mock is now used numerically by the fill loop) and rename their `included_ids` fixtures to `ranked_ids`. `test_writes_all_application_outputs` additionally asserts:

```python
            self.assertEqual(mock_render.call_count, 2)
            final_call = mock_render.call_args_list[-1]
            self.assertEqual(final_call.args[1], os.path.join(app_dir, "Tailored_Resume.pdf"))
```

(One call from the fill-loop search against the scratch path, one for the final authoritative render.)

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tailor_resume_cli.py -v`
Expected: FAIL — `_select_work_experience_count` doesn't exist yet; existing mocks return a `MagicMock` where an `int` is now required.

- [x] **Step 3: Implement**

```python
import tempfile
# ... (existing imports)

def _select_work_experience_count(
    master: dict, tailoring_result: dict, target_pages: int, scratch_pdf_path: str,
) -> int:
    ranked_ids = tailoring_result.get("ranked_ids") or []
    if not ranked_ids:
        return 0
    best_count = 1
    for count in range(1, len(ranked_ids) + 1):
        candidate, _ = apply_tailoring(master, tailoring_result, include_count=count)
        page_count = render_resume_pdf(candidate, scratch_pdf_path, target_pages=target_pages)
        if page_count <= target_pages:
            best_count = count
        else:
            break
    return best_count
```

In `run_tailoring`, after the `if tailoring_result is None: raise ...` block and before building `tailored`, add:

```python
    with tempfile.TemporaryDirectory() as scratch_dir:
        include_count = _select_work_experience_count(
            master, tailoring_result, target_pages, os.path.join(scratch_dir, "scratch.pdf"),
        )

    tailored, reconstruction_problems = apply_tailoring(master, tailoring_result, include_count=include_count)
```

(replacing the old `tailored, reconstruction_problems = apply_tailoring(master, tailoring_result)` line), add `target_pages: int = 2` to `run_tailoring`'s signature, and pass `target_pages=target_pages` to the final `render_resume_pdf(tailored, pdf_path, ...)` call.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_tailor_resume_cli.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add resume_manager/tailor_resume.py tests/test_tailor_resume_cli.py
git commit -m "feat(resume_manager): greedy render-measure-retry fill loop for Work Experience selection"
```

---

### Task 6: Full regression pass + real end-to-end verification

**Files:** none (verification only)

- [x] **Step 1: Run the full resume_manager test suite**

Run: `python -m pytest tests/test_resume_extract.py tests/test_resume_manager_package.py tests/test_resume_fact_diff.py tests/test_convert_resume.py tests/test_resume_llm_yaml.py tests/test_resume_schema.py tests/test_resume_normalize.py tests/test_resume_render.py tests/test_resume_validate.py tests/test_resume_tailor.py tests/test_tailor_resume_cli.py -q`
Expected: PASS, 141 tests.

- [x] **Step 2: Real end-to-end run against Ollama**

Run: `python -m resume_manager.tailor_resume --jd-file <a real job description> --application-name <name>`
Expected: succeeds, produces a PDF with (a) Education/Awards/Publications/Skills never split across a page, and (b) more Work Experience entries included than before this revision, filling available page-1 space.

- [x] **Step 3: Visually inspect the resulting PDF**

Read the generated `Tailored_Resume.pdf` and confirm both effects are visible in the actual layout, not just in test assertions.
