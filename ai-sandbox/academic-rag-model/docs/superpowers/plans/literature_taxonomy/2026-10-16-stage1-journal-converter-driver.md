# Stage 1: Journal Converter Driver Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `convert_journal_articles.py` transcribe on the Antigravity subscription by default (task cards, no API), fit the defect heuristic to journal prose, and stamp OpenAlex identity from the discovery sidecar onto each paper's index card.

**Architecture:** The journal CLI gains the same `--driver/--collect/--submit/--run-id/--allow-api-fallback/--bootstrap` surface the notes CLI already has, reusing `AgentDriver` and `submit_doc` unchanged except for two additive passthroughs (`known_doc_types`, `check_math_notation`) that `submit_doc` needs so its rerun routes a paper exactly as collect did. Work directory is `<index-root>/.agent_work/` (`research/.agent_work/`), which must be gitignored because cards hold paper text. A measured audit tool replaces guesswork for the defect profile. Identity is attached after the card exists, by a small additive `set_card_fields` in the indexer, and is idempotent so a `--backfill-identity` pass can stamp the ~107 papers already converted.

**Tech Stack:** Python 3.13, pytest/unittest + `unittest.mock`, pypdf, existing `core/indexer`, `pipelines/transcribe_notes`.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md` (section 6, Stage 1; section 8 for the cost/guardrail rules; section 7 for identity).

**Landed prerequisite:** the Excalidraw agent-driver work is on `main` (`b43cb09`): `--allow-api-fallback` on `submit_doc`, `transcribe_notes.py`'s own `--driver` default flipped to `agent`. This plan mirrors that CLI contract.

## Global Constraints

- Default to the subscription route: bare invocation must never make a paid transcription call. `--driver api` is the explicit opt-in and keeps the over-$1 warning rule from `CLAUDE.md`.
- "No hidden generative fallback": a card that is pending or bounced stays pending unless `--allow-api-fallback` is given at submit time. Never automatic.
- Index-card generation and embedding at submit/finish time still use the Gemini API (spec section 8: accepted, small calls). Agent-mode output must say so; it is separate from transcription.
- Do not edit any existing test. New behavior gets new test files. `agent_submit.submit_doc` and `process_pdf` changes are additive keyword parameters whose defaults reproduce today's behavior byte-for-byte.
- Card/work paths hold copyrighted paper text: `research/.agent_work/` must be gitignored before any card is ever written. Never commit PDFs, cards, page caches, or page images. Test fixtures are synthetic text only.
- Stage explicit paths only; never `git add -A`. Work in the `claude/journal-agent-driver` worktree. Do not land on `main`; the owner does.
- Run scripts as modules from `ai-sandbox/academic-rag-model/` using the main checkout's interpreter: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe`.
- `core/indexer/` is shared: the one change there (`set_card_fields`) needs tests for existing callers' behavior (Task 4 runs the indexer suite).

## Review Focus

Failure modes the spec implies but a straightforward implementation would miss, most likely first. Each has a pinning test in the task that owns the code.

1. **Submit reroutes a paper differently from collect.** `submit_doc` calls `process_pdf` without `known_doc_types` or the journal defect profile, so a paper staged under the journal profile is re-routed (or classified as a notes doc type) at submit and the agent's text is discarded or mis-typed. Expected: submit uses exactly the collect-time settings. (Task 2, Task 3)
2. **Clean papers never get written in agent mode.** Collect never writes (tier-1 local papers have no cards), and the notes submit loop only visits documents that have a run directory, so born-digital papers would silently never be converted. Expected: submit finishes card-less papers locally with 0 transcription calls, and says which papers still need `--collect`. (Task 3)
3. **Re-running submit rewrites or re-links already-converted papers.** The local finish must skip any paper whose `.md` already exists. (Task 3)
4. **Agent work directory ends up in git.** `research/.agent_work/` is not covered by any current `.gitignore` rule (only `academic-hub/.agent_work/` is). (Task 3, first step)
5. **Identity fields lost or wrong.** Missing/partial/corrupt sidecar must be a no-op, never a crash; stamping must not clobber unrelated card fields; re-stamping is idempotent; a card that does not exist yet reports `False`. (Task 4)

---

### Task 1: Defect audit tool (measure before tuning)

Spec section 6, stage 1 item 2 requires acceptance "measured, not asserted". This task builds the measuring instrument and records the baseline. It changes no pipeline behavior.

**Files:**
- Create: `pipelines/convert_journal_articles/defect_audit.py`
- Test: `tests/pipelines/convert_journal_articles/test_defect_audit.py`

**Interfaces:**
- Consumes: `transcribe_notes.page_looks_defective`, `_has_collapsed_prose_run`, `_has_suspicious_repeated_char_run`, `_has_lost_exponent_outside_scripts`, `_MAX_UNEXPECTED_CHARS`, `is_expected_char` (import location: wherever `transcribe_notes.py` imports `is_expected_char` from; confirm with `grep -n "is_expected_char" pipelines/transcribe_notes/transcribe_notes.py`), `extract_all_page_texts`, `has_reliable_pagination`.
- Produces: `SIGNALS: tuple[str, ...]`; `signals_for(text: str) -> set[str]`; `audit_pdf(pdf_path: str, check_math_notation: bool = True) -> dict` with keys `pages`, `reliable`, `defective_pages`, `by_signal` (signal → page count); `summarize(rows: list[dict]) -> dict` with keys `documents`, `pages`, `defective_pages`, `defect_rate`, `by_signal`, `docs_over_hybrid_threshold`. Aggregates only, never page text.

- [ ] **Step 1: Write the failing tests**

```python
# tests/pipelines/convert_journal_articles/test_defect_audit.py
import unittest

from pipelines.convert_journal_articles.defect_audit import SIGNALS, signals_for, summarize
from pipelines.transcribe_notes.transcribe_notes import page_looks_defective

PUA_RUN = "Results \ue000\ue001\ue002\ue003\ue004 table"
LIGATURE_RUN = "significant \ufb01\ufb01\ufb01\ufb01\ufb01 effect"
COLLAPSED = "Thecoefficientonprogramparticipationispositiveandsignificantacrossspecifications."
LOST_EXPONENT = "The fit is R2 = 0.43 and hypothesis H1 holds."
CLEAN = "We estimate the effect of the program on household income using a difference-in-differences design."


class TestSignalsFor(unittest.TestCase):
    def test_each_defect_fixture_trips_its_own_signal(self):
        self.assertIn("unexpected_chars", signals_for(PUA_RUN))
        self.assertIn("repeated_char_run", signals_for(LIGATURE_RUN))
        self.assertIn("collapsed_prose", signals_for(COLLAPSED))
        self.assertIn("lost_exponent", signals_for(LOST_EXPONENT))

    def test_clean_prose_trips_nothing(self):
        self.assertEqual(signals_for(CLEAN), set())

    def test_signals_agree_with_page_looks_defective(self):
        # Drift guard: if page_looks_defective gains or loses a signal, this audit must follow.
        for text in (PUA_RUN, LIGATURE_RUN, COLLAPSED, LOST_EXPONENT, CLEAN):
            with self.subTest(text=text[:30]):
                self.assertEqual(bool(signals_for(text)), page_looks_defective(text))
                self.assertEqual(
                    bool(signals_for(text) - {"lost_exponent"}),
                    page_looks_defective(text, check_math_notation=False),
                )

    def test_signal_names_are_the_four_known(self):
        self.assertEqual(set(SIGNALS), {"collapsed_prose", "unexpected_chars", "repeated_char_run", "lost_exponent"})


class TestSummarize(unittest.TestCase):
    def test_rate_and_hybrid_threshold_count(self):
        rows = [
            {"pages": 10, "reliable": True, "defective_pages": 0, "by_signal": {}},
            {"pages": 10, "reliable": True, "defective_pages": 2, "by_signal": {"lost_exponent": 2}},
            {"pages": 10, "reliable": False, "defective_pages": 0, "by_signal": {}},
        ]
        s = summarize(rows)
        self.assertEqual(s["documents"], 3)
        self.assertEqual(s["pages"], 30)
        self.assertEqual(s["defective_pages"], 2)
        self.assertAlmostEqual(s["defect_rate"], 2 / 20)  # only reliably-paginated docs are scored
        self.assertEqual(s["by_signal"], {"lost_exponent": 2})
        self.assertEqual(s["docs_over_hybrid_threshold"], 1)  # 2/10 = 20% > 10%


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/pipelines/convert_journal_articles/test_defect_audit.py -q`
Expected: FAIL, `ModuleNotFoundError: pipelines.convert_journal_articles.defect_audit`.

- [ ] **Step 3: Implement**

```python
# pipelines/convert_journal_articles/defect_audit.py
"""Measures how often page_looks_defective() flags journal-article pages, per signal.

Prints aggregates only (never page text), so it is safe to run on copyrighted PDFs. Used to calibrate the
journal-prose defect profile (see docs/superpowers/plans/literature_taxonomy/2026-10-16-stage1-*.md)."""
from __future__ import annotations

import argparse
import json
import sys

from pipelines.convert_journal_articles.convert_journal_articles import discover_pdf_files
from pipelines.transcribe_notes import transcribe_notes as tn

SIGNALS = ("collapsed_prose", "unexpected_chars", "repeated_char_run", "lost_exponent")


def signals_for(text: str) -> set[str]:
    """Which of page_looks_defective's four signals fire on this page (mirrors its checks one for one)."""
    out: set[str] = set()
    if tn._has_collapsed_prose_run(text):
        out.add("collapsed_prose")
    if sum(1 for c in text if not c.isspace() and not tn.is_expected_char(c)) > tn._MAX_UNEXPECTED_CHARS:
        out.add("unexpected_chars")
    if tn._has_suspicious_repeated_char_run(text):
        out.add("repeated_char_run")
    if tn._has_lost_exponent_outside_scripts(text):
        out.add("lost_exponent")
    return out


def audit_pdf(pdf_path: str, check_math_notation: bool = True) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    reliable = tn.has_reliable_pagination(reader.metadata)
    by_signal: dict[str, int] = {}
    defective = 0
    if reliable:
        for text in tn.extract_all_page_texts(pdf_path, total):
            fired = signals_for(text)
            if not check_math_notation:
                fired.discard("lost_exponent")
            if fired:
                defective += 1
            for s in fired:
                by_signal[s] = by_signal.get(s, 0) + 1
    return {"pages": total, "reliable": reliable, "defective_pages": defective, "by_signal": by_signal}


def summarize(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["reliable"]]
    scored_pages = sum(r["pages"] for r in scored)
    by_signal: dict[str, int] = {}
    for r in scored:
        for s, n in r["by_signal"].items():
            by_signal[s] = by_signal.get(s, 0) + n
    over = sum(1 for r in scored if r["pages"] and r["defective_pages"] / r["pages"] > tn._MAX_DEFECT_RATIO_FOR_HYBRID)
    defective = sum(r["defective_pages"] for r in scored)
    return {
        "documents": len(rows), "pages": sum(r["pages"] for r in rows), "defective_pages": defective,
        "defect_rate": (defective / scored_pages) if scored_pages else 0.0,
        "by_signal": by_signal, "docs_over_hybrid_threshold": over,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Aggregate defect-heuristic rates over a PDF folder (no text output).")
    p.add_argument("--articles-dir", required=True)
    p.add_argument("--no-math-notation", action="store_true", help="Score as the journal profile would.")
    args = p.parse_args()
    rows = []
    for path in discover_pdf_files(args.articles_dir):
        try:
            rows.append(audit_pdf(path, check_math_notation=not args.no_math_notation))
        except Exception as err:  # unreadable PDF: count it, do not abort the audit
            print(f"skip (unreadable): {type(err).__name__}", file=sys.stderr)
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify pass**

Run: `python -m pytest tests/pipelines/convert_journal_articles/test_defect_audit.py -q`
Expected: PASS (4 tests). If `signals_agree_with_page_looks_defective` fails on a fixture, the fixture is wrong, not the guard: adjust the fixture string until it trips its intended signal.

- [ ] **Step 5: Record the baseline (local, not committed output)**

Run against the real corpus in the main checkout (read-only; PDFs are gitignored and stay there):
`python -m pipelines.convert_journal_articles.defect_audit --articles-dir C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\journal-articles`
then again with `--no-math-notation`.
Expected: two JSON summaries. Write both into the Task 5 status doc under "Baseline" (numbers only). Decision rule used in Task 2: if the `--no-math-notation` `defect_rate` is at most 0.10, the profile is "math notation off" and nothing else changes. If it is above 0.10, **stop and report to the owner** with the per-signal breakdown instead of tuning further; which signal to relax is a quality/recall tradeoff the owner decides.

- [ ] **Step 6: Commit**

```bash
git add pipelines/convert_journal_articles/defect_audit.py tests/pipelines/convert_journal_articles/test_defect_audit.py
git commit -m "feat(convert_journal_articles): defect_audit tool for measuring the heuristic per signal"
```

---

### Task 2: Journal defect profile and `submit_doc` passthroughs

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_notes.py` (`process_pdf` signature and its one `page_looks_defective(...)` call, near line 1210)
- Modify: `pipelines/transcribe_notes/agent_submit.py` (`submit_doc` signature and its two `process_pdf` calls)
- Test: `tests/pipelines/transcribe_notes/test_process_pdf_check_math.py` (new), `tests/pipelines/transcribe_notes/test_submit_passthrough.py` (new)

**Interfaces:**
- Consumes: Task 1's decision rule (profile = math notation off).
- Produces: `process_pdf(..., check_math_notation: bool = True)`; `submit_doc(..., known_doc_types=None, check_math_notation: bool = True)`; `known_doc_types=None` means "use `process_pdf`'s default", so existing callers are unchanged.

- [ ] **Step 1: Write the failing tests**

```python
# tests/pipelines/transcribe_notes/test_process_pdf_check_math.py
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

TN = "pipelines.transcribe_notes.transcribe_notes"


class TestCheckMathNotationPassthrough(unittest.TestCase):
    def _run(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "econ", "paper.pdf")
            os.makedirs(os.path.dirname(pdf))
            with open(pdf, "wb") as f:
                f.write(b"%PDF-1.4 mock")
            reader = MagicMock()
            reader.pages = [MagicMock()]
            reader.metadata = {"/Producer": "Apache FOP"}
            seen = []

            def fake_defective(text, check_math_notation=True):
                seen.append(check_math_notation)
                return False

            with patch("pypdf.PdfReader", return_value=reader), \
                    patch(f"{TN}.has_reliable_pagination", return_value=True), \
                    patch(f"{TN}.extract_all_page_texts", return_value=["Fit is R2 = 0.43."]), \
                    patch(f"{TN}.page_looks_defective", side_effect=fake_defective), \
                    patch(f"{TN}._write_markdown_and_index"):
                from pipelines.transcribe_notes.transcribe_notes import process_pdf
                process_pdf(pdf, None, None, tmp, **kw)
            return seen

    def test_default_keeps_math_notation_check(self):
        self.assertEqual(self._run(), [True])

    def test_false_is_forwarded_to_the_defect_check(self):
        self.assertEqual(self._run(check_math_notation=False), [False])


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/pipelines/transcribe_notes/test_submit_passthrough.py
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from pipelines.transcribe_notes.agent_submit import submit_doc
from pipelines.transcribe_notes.agent_work import AgentDriver, load_manifest

JOURNAL = frozenset({"journal_article"})


class TestSubmitForwardsCollectTimeSettings(unittest.TestCase):
    def test_final_rerun_gets_known_doc_types_and_check_math_notation(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "econ", "paper.pdf")
            os.makedirs(os.path.dirname(pdf))
            with open(pdf, "wb") as f:
                f.write(b"%PDF-1.4 mock")
            reader = MagicMock()
            reader.pages = [MagicMock()]
            reader.metadata = {"/Producer": "pdfTeX"}
            tn = "pipelines.transcribe_notes.transcribe_notes"
            with patch("pypdf.PdfReader", return_value=reader), \
                    patch(f"{tn}.has_reliable_pagination", return_value=True), \
                    patch(f"{tn}.extract_all_page_texts", return_value=["x"]), \
                    patch(f"{tn}.page_looks_defective", return_value=False), \
                    patch("pipelines.transcribe_notes.agent_work.render_page_to_image_bytes", return_value=b"png"):
                from pipelines.transcribe_notes.transcribe_notes import process_pdf
                driver = AgentDriver(tmp, "run-1")
                process_pdf(pdf, None, None, tmp, force_vision=True, driver=driver, collect_mode=True,
                            known_doc_types=JOURNAL, check_math_notation=False)
                slug = driver.last_doc_slug
                doc_dir = os.path.join(tmp, ".agent_work", "run-1", slug)
                card = os.path.join(doc_dir, f"{load_manifest(doc_dir)[0].task_id}.md")
                text = open(card, encoding="utf-8").read()
                open(card, "w", encoding="utf-8").write(text.replace(
                    "## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nAgent text.\n"))
                with patch("pipelines.transcribe_notes.agent_submit.process_pdf") as rerun, \
                        patch("pipelines.transcribe_notes.agent_submit.extract_page_text", return_value="hint"):
                    submit_doc(tmp, tmp, "run-1", slug, pdf, MagicMock(), None, force_vision=True,
                               known_doc_types=JOURNAL, check_math_notation=False)
            kwargs = rerun.call_args.kwargs
            self.assertEqual(kwargs["known_doc_types"], JOURNAL)
            self.assertIs(kwargs["check_math_notation"], False)

    def test_signature_defaults(self):
        import inspect
        sig = inspect.signature(submit_doc).parameters
        self.assertIsNone(sig["known_doc_types"].default)
        self.assertIs(sig["check_math_notation"].default, True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_process_pdf_check_math.py tests/pipelines/transcribe_notes/test_submit_passthrough.py -q`
Expected: FAIL, `TypeError: process_pdf() got an unexpected keyword argument 'check_math_notation'` / `submit_doc() ... 'known_doc_types'`.

- [ ] **Step 3: Implement**

In `process_pdf`: add `check_math_notation: bool = True` after `collect_mode`; at the single `page_looks_defective(all_page_texts[n - 1])` call pass `check_math_notation=check_math_notation`.

In `submit_doc`: add `known_doc_types=None, check_math_notation: bool = True`. Build once:

```python
extra = {"check_math_notation": check_math_notation}
if known_doc_types is not None:
    extra["known_doc_types"] = known_doc_types
```

and add `**extra` to both `process_pdf(...)` calls (the tier-3 `next_driver` restage call and the final write call).

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/pipelines/transcribe_notes -q`
Expected: all existing notes tests plus the new ones pass (existing count unchanged, nothing edited).

- [ ] **Step 5: Mutation check**

Temporarily delete `**extra` from the final-write `process_pdf` call in `submit_doc`; Expected: `test_final_rerun_gets_known_doc_types_and_check_math_notation` fails. Restore; it passes.

- [ ] **Step 6: Commit**

```bash
git add pipelines/transcribe_notes/transcribe_notes.py pipelines/transcribe_notes/agent_submit.py tests/pipelines/transcribe_notes/test_process_pdf_check_math.py tests/pipelines/transcribe_notes/test_submit_passthrough.py
git commit -m "feat(transcribe_notes): process_pdf check_math_notation and submit_doc passthroughs for collect-time settings"
```

---

### Task 3: Journal CLI driver wiring

**Files:**
- Modify: `pipelines/convert_journal_articles/convert_journal_articles.py`
- Modify: `.gitignore` (repo root: add `ai-sandbox/research/.agent_work/` beside the existing `academic-hub/.agent_work/` rule at line ~77)
- Test: `tests/pipelines/convert_journal_articles/test_cli_driver.py` (new)

**Interfaces:**
- Consumes: Task 2's `process_pdf(..., check_math_notation)` and `submit_doc(..., known_doc_types, check_math_notation)`; `AgentDriver(hub_root, run_id)`, `dedupe_by_file_id`, `agent_work_dir`, `doc_slug_for`, `NullDriver`, `NullDriverFired`, `corpus_write_lock`, `compute_file_id`.
- Produces: module constants `_CHECK_MATH_NOTATION = False`; functions `_eligible_pdfs(paths, max_pages) -> list[str]`, `_collect(pdf_paths, args) -> None`, `_submit(pdf_paths, args) -> None`, `_finish_locally(pdf_path, client, args) -> str`, `_bootstrap_text(run_id) -> str`; CLI flags `--driver {agent,api}` (default `agent`), `--collect`, `--submit RUN_ID`, `--run-id`, `--allow-api-fallback`, `--bootstrap RUN_ID`. Flag names and semantics match `transcribe_notes.py`'s CLI exactly.

- [ ] **Step 1: Gitignore the work directory first**

Add `ai-sandbox/research/.agent_work/` to the root `.gitignore` next to the academic-hub rule, with a one-line comment that cards hold paper text. Verify: `git check-ignore -v ai-sandbox/research/.agent_work/r/doc/task-0001.md` prints the new rule. Commit alone: `git add .gitignore && git commit -m "chore: ignore research/.agent_work (task cards hold paper text)"`.

- [ ] **Step 2: Write the failing tests** (`unittest.mock`, patching names in the converter module namespace; no real PDFs, no network)

```python
# tests/pipelines/convert_journal_articles/test_cli_driver.py
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pipelines.convert_journal_articles.convert_journal_articles as cja

M = "pipelines.convert_journal_articles.convert_journal_articles"


def _pdf(root, rel="economics/a.pdf"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4 mock " + rel.encode())
    return path


def _run(argv):
    with patch.object(sys, "argv", ["convert_journal_articles"] + argv):
        cja.main()


class TestDriverFlags(unittest.TestCase):
    def test_bare_run_does_not_spend_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5):
                with self.assertRaises(SystemExit) as ctx:
                    _run(["--articles-dir", tmp, "--index-root", tmp])
            self.assertNotEqual(ctx.exception.code, 0)
            client.assert_not_called()
            proc.assert_not_called()

    def test_collect_uses_agent_driver_collect_mode_and_journal_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--collect", "--run-id", "r1"])
            client.assert_not_called()
            kw = proc.call_args.kwargs
            self.assertTrue(kw["collect_mode"])
            self.assertEqual(kw["known_doc_types"], cja._JOURNAL_DOC_TYPES)
            self.assertIs(kw["check_math_notation"], False)
            self.assertEqual(type(kw["driver"]).__name__, "AgentDriver")
            self.assertEqual(kw["driver"].hub_root, tmp)

    def test_api_driver_keeps_the_existing_client_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()) as client, \
                    patch(f"{M}.process_pdf") as proc, patch(f"{M}._page_count", return_value=5):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--driver", "api"])
            client.assert_called_once()
            self.assertIs(proc.call_args.kwargs["check_math_notation"], False)
            self.assertNotIn("driver", proc.call_args.kwargs)

    def test_dry_run_needs_no_driver_flag_and_no_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--dry-run"])
            client.assert_not_called()
            self.assertTrue(proc.call_args.kwargs["dry_run"])

    def test_oversize_paper_is_never_staged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.process_pdf") as proc, patch(f"{M}._page_count", return_value=400):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--collect", "--run-id", "r1"])
            proc.assert_not_called()

    def test_bootstrap_prints_contract_without_touching_anything(self):
        with patch(f"{M}.process_pdf") as proc, patch(f"{M}.discover_pdf_files") as disc:
            _run(["--bootstrap", "r9"])
        proc.assert_not_called()
        disc.assert_not_called()
        self.assertIn("r9", cja._bootstrap_text("r9"))


class TestSubmit(unittest.TestCase):
    def _slug(self, path):
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_work import doc_slug_for
        return doc_slug_for(path, compute_file_id(path))

    def test_submit_forwards_collect_time_settings_and_fallback_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1", self._slug(pdf)))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.submit_doc", return_value="incomplete: 1 card(s) still pending/bounced") as sub, \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1", "--allow-api-fallback"])
            first, second = sub.call_args_list
            self.assertFalse(first.kwargs["allow_api_fallback"])
            self.assertTrue(second.kwargs["allow_api_fallback"])
            self.assertEqual(first.kwargs["known_doc_types"], cja._JOURNAL_DOC_TYPES)
            self.assertIs(first.kwargs["check_math_notation"], False)

    def test_card_less_paper_is_finished_locally_with_a_null_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}.submit_doc") as sub, \
                    patch(f"{M}.process_pdf") as proc, patch(f"{M}._page_count", return_value=5), \
                    patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            sub.assert_not_called()
            self.assertEqual(type(proc.call_args.kwargs["driver"]).__name__, "NullDriver")

    def test_card_less_paper_that_needs_the_agent_is_reported_not_crashed(self):
        from pipelines.transcribe_notes.agent_driver import NullDriverFired
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.process_pdf", side_effect=NullDriverFired("x")), \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"), \
                    patch("builtins.print") as out:
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            self.assertTrue(any("--collect" in " ".join(map(str, c.args)) for c in out.call_args_list))

    def test_already_converted_paper_is_not_touched_by_the_local_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            open(os.path.splitext(pdf)[0] + ".md", "w", encoding="utf-8").write("done")
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            proc.assert_not_called()

    def test_unknown_run_id_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}._page_count", return_value=5):
                with self.assertRaises(SystemExit):
                    _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "nope"])


if __name__ == "__main__":
    unittest.main()
```

Note for the implementer: the converted `.md` sits next to the PDF only if `resolve_output_dir(pdf_path)` returns the PDF's folder for journal papers; confirm with `grep -n "def resolve_output_dir" -A14 pipelines/transcribe_notes/transcribe_notes.py` and make `_finish_locally` check the path `resolve_output_dir` actually gives (import it), adjusting the fixture in `test_already_converted_...` to match.

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/pipelines/convert_journal_articles/test_cli_driver.py -q`
Expected: FAIL (unrecognized arguments `--collect`, missing `_bootstrap_text`, etc.). The existing `test_convert_journal_articles.py` must still pass untouched.

- [ ] **Step 4: Implement**

In `convert_journal_articles.py`:

```python
_CHECK_MATH_NOTATION = False  # journal prose: a bare "R2" or "H1" is a statistic or hypothesis label, not a lost exponent
```

Replace the parser tail and `main()` body with: new flags copied from `transcribe_notes.main` (same help text, `--driver` default `agent`); then

```python
def _bootstrap_text(run_id: str) -> str: ...  # same contract text as notes, with this module's --submit command

def _eligible_pdfs(pdf_paths, max_pages):
    keep = []
    for pdf_path in pdf_paths:
        page_count = _page_count(pdf_path)
        if page_count is None:
            print(f"WARNING: could not read {pdf_path}; skipping.")
        elif page_count > max_pages:
            print(f"FLAGGED: {pdf_path} has {page_count} pages (over --max-pages {max_pages}) -- "
                  f"likely a book or monograph, not a journal article. Skipping. If you want it "
                  f"processed, move it into academic-hub/ and run convert_textbook.py there.")
        else:
            keep.append(pdf_path)
    return keep

def _process_kwargs():
    return {"known_doc_types": _JOURNAL_DOC_TYPES, "check_math_notation": _CHECK_MATH_NOTATION}

def _collect(pdf_paths, args):
    run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    canonical, _ = dedupe_by_file_id(pdf_paths)
    driver = AgentDriver(args.index_root, run_id)
    for pdf_path in canonical:
        process_pdf(pdf_path, None, args.model, args.index_root, driver=driver, collect_mode=True, **_process_kwargs())
    print(f"Collect run '{run_id}' complete under {os.path.join(args.index_root, '.agent_work', run_id)}. "
          f"Papers that are clean machine text have no cards; --submit converts them locally.")

def _finish_locally(pdf_path, client, args) -> str:
    md = os.path.join(resolve_output_dir(pdf_path), os.path.splitext(os.path.basename(pdf_path))[0] + ".md")
    if os.path.exists(md):
        return "already converted"
    try:
        process_pdf(pdf_path, client, args.model, args.index_root, driver=NullDriver(), **_process_kwargs())
    except NullDriverFired:
        return "needs agent transcription: run --collect first"
    return "converted locally (0 transcription calls)"

def _submit(pdf_paths, args):
    client = get_gemini_client()
    if client is None:
        sys.exit(1)
    run_dir = agent_work_dir(args.index_root, args.submit)
    if not os.path.isdir(run_dir):
        print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
        sys.exit(1)
    print("Note: index cards and embeddings are generated through the Gemini API at this step "
          "(small calls); transcription itself is not.")
    by_slug = {doc_slug_for(p, compute_file_id(p)): p for p in pdf_paths}
    staged = set(os.listdir(run_dir))
    with corpus_write_lock([args.index_root], "journal PDF transcription (agent submit)"):
        for slug in sorted(staged):
            pdf_path = by_slug.get(slug)
            if pdf_path is None:
                print(f"Skipping {slug}: no matching PDF found under {args.articles_dir}.")
                continue
            try:
                status = submit_doc(args.index_root, args.index_root, args.submit, slug, pdf_path, client, args.model,
                                    allow_api_fallback=args.allow_api_fallback, **_process_kwargs())
            except Exception as err:  # one malformed document must not abort the rest
                print(f"[{slug}] error: {err}")
                continue
            print(f"[{slug}] {status}")
        for slug, pdf_path in sorted(by_slug.items()):
            if slug not in staged:
                print(f"[{slug}] {_finish_locally(pdf_path, client, args)}")
```

`main()` dispatch order: `--bootstrap` → return; discover (exit 1 if none); `load_dotenv_override()`; `pdf_paths = _eligible_pdfs(...)`; `--submit` → `_submit`; `--collect` (requires `--driver agent`, else message and exit 1) → `_collect`; if `--dry-run` → `process_pdf(..., dry_run=True, **_process_kwargs())` per paper with `client=None`; `--driver agent` with none of collect/submit/dry-run → print `--driver agent requires --collect or --submit (or --dry-run).` and `sys.exit(1)`; else the API loop (client required, `corpus_write_lock([index_root], ...)`, `process_pdf(..., **_process_kwargs())`). New imports: `datetime`, `AgentDriver`, `agent_work_dir`, `dedupe_by_file_id`, `doc_slug_for`, `NullDriver`, `NullDriverFired`, `submit_doc`, `corpus_write_lock`, `compute_file_id`, `resolve_output_dir`.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/pipelines/convert_journal_articles tests/pipelines/transcribe_notes -q`
Expected: all pass, including the untouched existing converter tests.

- [ ] **Step 6: Mutation checks**

(a) Drop `**_process_kwargs()` from the `submit_doc` call: `test_submit_forwards_collect_time_settings...` fails. (b) Remove the `os.path.exists(md)` guard: `test_already_converted_paper_...` fails. Restore both.

- [ ] **Step 7: Commit**

```bash
git add pipelines/convert_journal_articles/convert_journal_articles.py tests/pipelines/convert_journal_articles/test_cli_driver.py
git commit -m "feat(convert_journal_articles): agent driver by default with --collect/--submit, local finish for clean papers"
```

---

### Task 4: OpenAlex identity on index cards

**Files:**
- Modify: `core/indexer/index_card.py` (add `IDENTITY_FIELDS`, `set_card_fields`, next to `set_rag_md_path`)
- Create: `pipelines/convert_journal_articles/identity.py`
- Modify: `pipelines/convert_journal_articles/convert_journal_articles.py` (call `attach_identity` after each successful write; add `--backfill-identity`)
- Test: `tests/core/test_index_card_set_fields.py`, `tests/pipelines/convert_journal_articles/test_identity.py` (new)

**Interfaces:**
- Consumes: `find_card_by_file_id`, `load_shard`, `save_shard`, `_replace_card` (existing, same module as `set_rag_md_path`); `compute_file_id`.
- Produces: `IDENTITY_FIELDS = frozenset({"openalex_id", "doi", "openalex_topics", "publication_year"})`; `set_card_fields(academic_hub_root: str, file_id: str, fields: dict) -> bool` (False when no card; raises `ValueError` on any key outside `IDENTITY_FIELDS`; changes nothing else on the card); `identity_fields(pdf_path: str) -> dict | None`; `attach_identity(pdf_path: str, index_root: str) -> bool`.

Scope note: the sidecar carries no country data (spec section 7 names ISO-3166 codes). Study-country codes come from the stage-2 extraction record; author-affiliation countries would need discovery to request OpenAlex institution data and are out of scope here. Task 5 amends the spec accordingly.

- [ ] **Step 1: Check for card-schema validators**

Run: `grep -rn "CARD_FIELDS\|required_card\|card.*schema\|jsonschema" core/indexer/*.py | head`. Expected: no validator rejecting unknown keys (cards already carry optional keys like `rag_md_path`, `offering_label`). If one exists, extend it in this task rather than bypassing it.

- [ ] **Step 2: Write the failing tests**

```python
# tests/core/test_index_card_set_fields.py
import tempfile
import unittest

from core.indexer.index_card import IDENTITY_FIELDS, find_card_by_file_id, load_shard, save_shard, set_card_fields


def _seed(root, file_id="f1", course="economics"):
    save_shard(root, course, [{"file_id": file_id, "path": "a.md", "course": course, "summary": "keep me"}])


class TestSetCardFields(unittest.TestCase):
    def test_sets_identity_and_leaves_everything_else(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertTrue(set_card_fields(root, "f1", {"openalex_id": "https://openalex.org/W1", "doi": "10.1/x"}))
            card = find_card_by_file_id(root, "f1")[1]
            self.assertEqual(card["openalex_id"], "https://openalex.org/W1")
            self.assertEqual(card["summary"], "keep me")
            self.assertEqual(card["path"], "a.md")

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            set_card_fields(root, "f1", {"doi": "10.1/x"})
            first = load_shard(root, "economics")
            set_card_fields(root, "f1", {"doi": "10.1/x"})
            self.assertEqual(load_shard(root, "economics"), first)

    def test_missing_card_returns_false(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(set_card_fields(root, "nope", {"doi": "10.1/x"}))

    def test_non_identity_keys_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            with self.assertRaises(ValueError):
                set_card_fields(root, "f1", {"path": "evil.md"})
            self.assertEqual(find_card_by_file_id(root, "f1")[1]["path"], "a.md")

    def test_identity_field_set_is_the_documented_one(self):
        self.assertEqual(IDENTITY_FIELDS, {"openalex_id", "doi", "openalex_topics", "publication_year"})


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/pipelines/convert_journal_articles/test_identity.py
import json
import os
import tempfile
import unittest

from core.indexer.index_card import compute_file_id, find_card_by_file_id, save_shard
from pipelines.convert_journal_articles.identity import attach_identity, identity_fields

SIDECAR = {
    "title": "T", "authors": ["A"], "year": 2021, "doi": "10.1/x", "openalex_id": "https://openalex.org/W9",
    "concepts": ["Economics"], "topics": [{"id": "https://openalex.org/T1", "display_name": "Aid", "score": 0.9}],
    "source_tier": "oa", "relevance_score": 0.5, "page_count": 12,
}


def _paper(root, sidecar=None, raw=None):
    pdf = os.path.join(root, "economics", "a.pdf")
    os.makedirs(os.path.dirname(pdf))
    open(pdf, "wb").write(b"%PDF-1.4 mock")
    side = os.path.join(root, "economics", "a.meta.json")
    if sidecar is not None:
        json.dump(sidecar, open(side, "w", encoding="utf-8"))
    if raw is not None:
        open(side, "w", encoding="utf-8").write(raw)
    return pdf


class TestIdentityFields(unittest.TestCase):
    def test_maps_sidecar_to_card_fields(self):
        with tempfile.TemporaryDirectory() as root:
            f = identity_fields(_paper(root, SIDECAR))
        self.assertEqual(f["openalex_id"], "https://openalex.org/W9")
        self.assertEqual(f["doi"], "10.1/x")
        self.assertEqual(f["publication_year"], 2021)
        self.assertEqual(f["openalex_topics"], [{"id": "https://openalex.org/T1", "display_name": "Aid", "score": 0.9}])

    def test_missing_sidecar_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(identity_fields(_paper(root)))

    def test_corrupt_sidecar_is_none_not_a_crash(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(identity_fields(_paper(root, raw="{not json")))

    def test_partial_sidecar_drops_absent_keys(self):
        with tempfile.TemporaryDirectory() as root:
            f = identity_fields(_paper(root, {"title": "T", "openalex_id": "https://openalex.org/W9", "doi": None}))
        self.assertEqual(f, {"openalex_id": "https://openalex.org/W9"})

    def test_sidecar_name_matches_discovery(self):
        from discovery.discover_journal_articles.metadata_sidecar import sidecar_path
        from pipelines.convert_journal_articles.identity import _sidecar
        self.assertEqual(_sidecar("x/a.pdf"), sidecar_path("x/a.pdf"))


class TestAttachIdentity(unittest.TestCase):
    def test_stamps_the_card_for_this_pdf(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = _paper(root, SIDECAR)
            fid = compute_file_id(pdf)
            save_shard(root, "economics", [{"file_id": fid, "path": "economics/a.md", "course": "economics"}])
            self.assertTrue(attach_identity(pdf, root))
            self.assertEqual(find_card_by_file_id(root, fid)[1]["doi"], "10.1/x")

    def test_no_card_yet_is_false(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(attach_identity(_paper(root, SIDECAR), root))

    def test_no_sidecar_is_false_and_card_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = _paper(root)
            fid = compute_file_id(pdf)
            save_shard(root, "economics", [{"file_id": fid, "path": "p.md", "course": "economics"}])
            self.assertFalse(attach_identity(pdf, root))
            self.assertNotIn("doi", find_card_by_file_id(root, fid)[1])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/core/test_index_card_set_fields.py tests/pipelines/convert_journal_articles/test_identity.py -q`
Expected: FAIL (ImportError for `IDENTITY_FIELDS` / `identity`).

- [ ] **Step 4: Implement**

`core/indexer/index_card.py`, beside `set_rag_md_path`:

```python
IDENTITY_FIELDS = frozenset({"openalex_id", "doi", "openalex_topics", "publication_year"})


def set_card_fields(academic_hub_root: str, file_id: str, fields: dict) -> bool:
    """Stamps external-identity fields (see IDENTITY_FIELDS) onto an existing card without touching anything
    else. Returns False, never raises, when no card exists yet; raises ValueError for any other key so this
    cannot be used to rewrite paths or hashes."""
    extra = set(fields) - IDENTITY_FIELDS
    if extra:
        raise ValueError(f"not identity fields: {sorted(extra)}")
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    course, card = found
    updated = {**card, **fields}
    if updated != card:
        save_shard(academic_hub_root, course, _replace_card(load_shard(academic_hub_root, course), file_id, updated))
    return True
```

`pipelines/convert_journal_articles/identity.py`:

```python
"""Carries the discovery sidecar's OpenAlex identity onto a paper's index card (spec section 7)."""
from __future__ import annotations

import json
from pathlib import Path

from core.indexer.index_card import compute_file_id, set_card_fields


def _sidecar(pdf_path) -> Path:
    # Same rule as discovery's metadata_sidecar.sidecar_path (a test pins them equal); kept local so the
    # converter does not import the discovery package at runtime.
    return Path(pdf_path).with_suffix(".meta.json")


def identity_fields(pdf_path) -> dict | None:
    path = _sidecar(pdf_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    topics = [t for t in (data.get("topics") or []) if isinstance(t, dict) and t.get("id")]
    fields = {
        "openalex_id": data.get("openalex_id"), "doi": data.get("doi"),
        "publication_year": data.get("year"), "openalex_topics": topics or None,
    }
    fields = {k: v for k, v in fields.items() if v is not None}
    return fields or None


def attach_identity(pdf_path, index_root) -> bool:
    fields = identity_fields(pdf_path)
    if not fields:
        return False
    return set_card_fields(str(index_root), compute_file_id(str(pdf_path)), fields)
```

In `convert_journal_articles.py`: call `attach_identity(pdf_path, args.index_root)` after `process_pdf` returns in the API loop; in `_submit` after any status starting with `"complete"` and after `_finish_locally` returns a string starting with `"converted"`; add `--backfill-identity` (no client, no transcription; under `corpus_write_lock`; loops `_eligible_pdfs`, prints `stamped N, no card M, no sidecar K`).

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/core tests/pipelines/convert_journal_articles -q`
Expected: all pass, including every existing `tests/core` indexer test (nothing edited).

- [ ] **Step 6: Add a CLI test for the wiring and run it**

Append to `test_cli_driver.py` (new class, not editing the others): `--backfill-identity` calls `attach_identity` once per eligible paper and never calls `get_gemini_client`; a `--submit` with `submit_doc` returning `"complete"` triggers `attach_identity`, with `"incomplete: ..."` does not. Run it red first by temporarily omitting the call, then green.

- [ ] **Step 7: Commit**

```bash
git add core/indexer/index_card.py pipelines/convert_journal_articles/identity.py pipelines/convert_journal_articles/convert_journal_articles.py tests/core/test_index_card_set_fields.py tests/pipelines/convert_journal_articles/test_identity.py tests/pipelines/convert_journal_articles/test_cli_driver.py
git commit -m "feat(convert_journal_articles): stamp OpenAlex identity from the sidecar onto index cards, with backfill"
```

---

### Task 5: Docs, spec amendments, measured acceptance

**Files:**
- Modify: `pipelines/convert_journal_articles/README.md`
- Modify: `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md`
- Create: `docs/status/convert_journal_articles/2026-10-16-stage1-driver-wiring.md`

- [ ] **Step 1: README.** Replace the "no new code" framing with the new contract: default `agent`, the three-step flow (`--collect`, fill cards in Antigravity per `--bootstrap`, `--submit`), `--allow-api-fallback` semantics, `--driver api` and the over-$1 warning, `--backfill-identity`, the `research/.agent_work/` location and why it is gitignored, and the note that index-card and embedding calls still use the API at submit.

- [ ] **Step 2: Spec amendments** (dated 2026-10-16, in the amendments style already used in that file): (a) stage 1 item 3: the sidecar has no country data, ISO codes come from the stage-2 record, author-affiliation countries are deferred; (b) stage 1 item 4 (page images for result tables) is deferred to stage 2, where `Task.attachments` consumes them; (c) add the finding that collect never writes so card-less papers are finished at submit; (d) mark stage 1 built, link the status doc.

- [ ] **Step 3: Measured acceptance (local, numbers only into the status doc).** With the profile active, rerun the Task 1 audit with `--no-math-notation` over the real corpus. Acceptance: `defect_rate` at most 0.10 and the share of documents above the hybrid threshold reported. Then run a real agent-mode check on **two** papers: `--collect --run-id stage1-check --file <one paper>` on a mixed pair, confirm cards exist only for papers that need them and nothing appears under `git status` (the work directory is ignored), fill nothing, run `--submit stage1-check` and confirm the clean paper converts locally and the carded paper reports `incomplete`. Record outcomes in the status doc. Do **not** run `--driver api`.

- [ ] **Step 4: Full verification.** Run the suite in per-directory chunks (the single full run was killed once for memory): `agent`, `audio_generator`, `core`, `discovery`, `pipelines`, `resume_manager`, `tools`. Expected: everything passes except the three `tests/tools/` website-sync collection errors from the missing `jsonschema` in the shared venv (pre-existing).

- [ ] **Step 5: Commit**

```bash
git add pipelines/convert_journal_articles/README.md docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md docs/status/convert_journal_articles/2026-10-16-stage1-driver-wiring.md
git commit -m "docs(convert_journal_articles): stage 1 usage, spec amendments, measured baseline"
```

## Self-review notes

- **Spec coverage:** item 1 (driver flags, default agent, no hidden fallback, explicit API cost note) → Task 3 plus Task 2 passthroughs; item 2 (journal defect profile, measured) → Tasks 1, 2, 5 step 3; item 3 (identity) → Task 4, with the country-code correction in Task 5; item 4 (page images) → explicitly deferred in Task 5.
- **Open decision for the owner (not blocking):** if the Task 1 baseline shows the rate above 10% even with math notation off, the plan stops for an owner decision rather than tuning other signals.
- **Not in this plan:** corpus-wide re-conversion of the ~107 existing papers (only identity backfill); moving journals into the academic-hub index; any extraction work (stage 2).
