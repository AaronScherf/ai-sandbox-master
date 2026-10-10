# Agent-driven transcription mode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a subscription IDE agent (Antigravity/Claude Code) do `transcribe_notes.py`'s vision-transcription work instead of metered Gemini calls, as a selectable `--driver agent` transport with `--collect`/`--submit`/`--bootstrap` CLI verbs, with zero change to tier routing, prompts, or the write/index path.

**Architecture:** A `Driver` seam (`AgentPending` exception + `TranscriptionDriver` protocol) is injected at `process_pdf`'s two Gemini call sites (batch, tier-3 page). `collect_mode` reuses `process_pdf`'s existing tier logic end-to-end but returns before any write. `AgentDriver` renders images and writes task cards + a manifest under `academic-hub/.agent_work/<run-id>/`; `submit` validates filled cards, writes into the existing `_pages_cache.json`, and re-runs `process_pdf` (with a `NullDriver` safety net) once a document is fully cached, so frontmatter/indexing is identical to a pure-API run.

**Tech Stack:** Python 3.13, PyMuPDF (already a dependency), stdlib `json`/`argparse`/`unittest`.

**Spec:** `docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md`

## Global Constraints

- No change to `repair_batch`, `repair_page_individually`, or `transcribe_page_via_gemini`'s own signatures — `postprocess_notes.py`, `transcribe_excalidraw.py`, and `tests/pipelines/transcribe_notes/test_transcribe_notes.py` call them directly.
- No change to `routing` frontmatter values — `postprocess_discovery.py` branches on exact strings (`local`, `hybrid`, `gemini_batched`, `gemini_accumulating`).
- `collect` must never call `_write_markdown_and_index`, `link_duplicate_note`, or `os.makedirs(output_dir)`, and must work with `client=None` and no corpus write lock.
- `submit`'s re-run of `process_pdf` for a document only fires once every card for that document is `submitted`, and uses a driver that raises on any live call rather than the real API driver.
- Task cards, images, and the manifest live under `academic-hub/.agent_work/<run-id>/`, never under `academic_notes/` or `academic_resources/`.
- `academic-hub/.agent_work/` must be gitignored before any real `collect` run.
- PDF path only — `transcribe_excalidraw.py` is untouched.

## Review Focus

- A batch whose agent-filled output is missing one of the expected pages (agent skipped a page) must bounce, not silently write a gap into `_pages_cache.json`.
- A tier-3 card where the agent pastes the same transcription into two pages (copy-paste mistake) is not explicitly required to bounce by the spec, but a missing/empty page from the same mistake must still bounce — covered by the same "page present and non-empty" check.
- `submit` run twice on the same already-fully-submitted document must not re-run `process_pdf` a second time in a way that errors (idempotency) — the second run should report "already complete," not call `NullDriver` again against an already-written `.md`.
- A manifest or task card file with unexpected/malformed JSON (hand-edited by mistake) must produce a clear error from `submit`, not a raw `KeyError`/`JSONDecodeError` traceback.
- `collect` run a second time over a document that already has an in-progress (not-yet-submitted) tier-3 card must not overwrite that card or skip ahead — it must leave it alone and report it as still pending.

---

## Task 1: `AgentPending` / `TranscriptionDriver` seam in `process_pdf`

**Files:**
- Create: `pipelines/transcribe_notes/agent_driver.py`
- Modify: `pipelines/transcribe_notes/transcribe_notes.py` (imports; `process_pdf` signature and its duplicate-link branch, tier-1 branch, hybrid-repair batch call site, whole-document-batch call site, tier-3 page call site)
- Test: `tests/pipelines/transcribe_notes/test_agent_driver.py` (new)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_notes.py` (extend)

**Interfaces:**
- Produces (for later tasks): `AgentPending` (exception), `TranscriptionDriver` (protocol with `transcribe_batch(pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]` and `transcribe_page(pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int) -> str`, both raising `AgentPending` instead of returning when there's no result yet), `ApiDriver(client)`, `NullDriver()`. `process_pdf(..., driver: TranscriptionDriver | None = None, collect_mode: bool = False)` — new keyword-only-by-convention params, defaulting to today's behavior.

- [ ] **Step 1: Write the failing test for the driver types**

```python
# tests/pipelines/transcribe_notes/test_agent_driver.py
import unittest
from unittest.mock import MagicMock, patch

from pipelines.transcribe_notes.agent_driver import AgentPending, ApiDriver, NullDriver


class TestApiDriver(unittest.TestCase):
    def test_transcribe_batch_calls_repair_batch_through_retries(self):
        client = MagicMock()
        driver = ApiDriver(client)
        with patch("pipelines.transcribe_notes.agent_driver.repair_batch", return_value={1: "page one"}) as mock_repair:
            with patch("pipelines.transcribe_notes.agent_driver.call_with_retries", side_effect=lambda fn: fn()):
                result = driver.transcribe_batch("fake.pdf", "model-x", [1, 2], "prompt")
        self.assertEqual(result, {1: "page one"})
        mock_repair.assert_called_once_with(client, "model-x", "fake.pdf", [1, 2], "prompt")

    def test_transcribe_page_calls_transcribe_page_via_gemini_through_retries(self):
        client = MagicMock()
        driver = ApiDriver(client)
        with patch("pipelines.transcribe_notes.agent_driver.transcribe_page_via_gemini", return_value="text") as mock_t:
            with patch("pipelines.transcribe_notes.agent_driver.call_with_retries", side_effect=lambda fn: fn()):
                result = driver.transcribe_page("fake.pdf", "model-x", 3, "prompt", b"bytes", 10)
        self.assertEqual(result, "text")
        mock_t.assert_called_once_with(client, "model-x", b"bytes", "prompt")


class TestNullDriver(unittest.TestCase):
    def test_transcribe_batch_raises(self):
        driver = NullDriver()
        with self.assertRaises(RuntimeError):
            driver.transcribe_batch("fake.pdf", "model-x", [1, 2], "prompt")

    def test_transcribe_page_raises(self):
        driver = NullDriver()
        with self.assertRaises(RuntimeError):
            driver.transcribe_page("fake.pdf", "model-x", 1, "prompt", b"bytes", 5)


class TestAgentPending(unittest.TestCase):
    def test_is_an_exception_not_caught_by_bare_except_exception_shadowing(self):
        # AgentPending must subclass Exception (so it IS catchable), but callers
        # must check for it with its own except clause before a generic one.
        self.assertTrue(issubclass(AgentPending, Exception))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_driver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipelines.transcribe_notes.agent_driver'`

- [ ] **Step 3: Implement `agent_driver.py`**

```python
# pipelines/transcribe_notes/agent_driver.py
"""
Driver seam for transcribe_notes.py's two Gemini call sites (a repair/
whole-document batch, and a tier-3 single page). ApiDriver reproduces
today's behavior unchanged; AgentDriver (pipelines/transcribe_notes/
agent_work.py) and NullDriver are the other two implementations. See
docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md.
"""
from __future__ import annotations

from typing import Protocol

from core.env.gemini_utils import call_with_retries
from pipelines.transcribe_notes.transcribe_notes import (
    repair_batch,
    transcribe_page_via_gemini,
)


class AgentPending(Exception):
    """Raised by AgentDriver to signal a batch/page has no result yet --
    a task card was written instead. Must be caught with its own
    `except AgentPending` clause BEFORE any generic `except Exception` at
    the call site: it must never be retried and must never trigger the
    per-page fallback a real API failure triggers."""


class TranscriptionDriver(Protocol):
    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        ...

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        ...


class ApiDriver:
    """Default driver: reproduces process_pdf's existing direct Gemini
    calls unchanged, still through call_with_retries."""

    def __init__(self, client):
        self.client = client

    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        return call_with_retries(lambda: repair_batch(self.client, model, pdf_path, batch, prompt))

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        return call_with_retries(lambda: transcribe_page_via_gemini(self.client, model, image_bytes, prompt))


class NullDriver:
    """Used by submit's re-run of process_pdf once every page is already
    cached: every page/batch should hit process_pdf's own cache-check
    branches and never reach the driver at all. If one does, that is a
    cache-completeness bug -- raise a hard error instead of silently
    falling through to a paid API call."""

    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        raise RuntimeError(
            f"NullDriver: unexpected live call for batch {batch} in {pdf_path} -- "
            "the cache should already be complete at this point."
        )

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        raise RuntimeError(
            f"NullDriver: unexpected live call for page {page_num} in {pdf_path} -- "
            "the cache should already be complete at this point."
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_driver.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/agent_driver.py tests/pipelines/transcribe_notes/test_agent_driver.py
git commit -m "feat: add AgentPending/TranscriptionDriver seam types"
```

- [ ] **Step 6: Write failing tests for the seam inside `process_pdf`**

Add to `tests/pipelines/transcribe_notes/test_transcribe_notes.py`. This file's established convention for `process_pdf`-level tests (see `TestProcessPdfLinksDuplicates.test_force_vision_bypasses_local_extraction_for_clean_document`, ~line 1101) is to mock `pypdf.PdfReader` plus `has_reliable_pagination`/`extract_all_page_texts`/`page_looks_defective`/`repair_batch`/`_write_markdown_and_index` directly rather than building a real parseable PDF — follow that same pattern here, not a real-file fixture. Append:

```python
from pipelines.transcribe_notes.agent_driver import AgentPending


class TestAgentPendingSeam(unittest.TestCase):
    """AgentPending must short-circuit retries, per-page fallback, and any
    cache write at process_pdf's batch and tier-3 driver call sites."""

    def test_hybrid_batch_pending_skips_per_page_fallback_and_cache_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "academic_notes", "microecon", "problem_sets", "hw4.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 mock")

            # 10 pages, only 1 defective -- a 10% defect ratio is exactly
            # at _MAX_DEFECT_RATIO_FOR_HYBRID, which routes to hybrid
            # repair rather than whole-document batching (defect_ratio
            # must be <= 0.10, not just < 0.10).
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock() for _ in range(10)]
            mock_reader.metadata = {"/Producer": "pdfTeX"}
            page_texts = ["clean text"] * 10
            page_texts[1] = "D5 collapsed exponent"  # page 2 (index 1) looks defective

            driver = MagicMock()
            driver.transcribe_batch.side_effect = AgentPending()

            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("pipelines.transcribe_notes.transcribe_notes.has_reliable_pagination", return_value=True):
                    with patch(
                        "pipelines.transcribe_notes.transcribe_notes.extract_all_page_texts",
                        return_value=page_texts,
                    ):
                        with patch(
                            "pipelines.transcribe_notes.transcribe_notes.page_looks_defective",
                            side_effect=lambda text, **_: "collapsed" in text,
                        ):
                            with patch("pipelines.transcribe_notes.transcribe_notes._write_markdown_and_index") as mock_write:
                                process_pdf(pdf_path, None, None, tmp, driver=driver, collect_mode=True)
                                driver.transcribe_batch.assert_called_once()
                                mock_write.assert_not_called()  # collect_mode never reaches the write path

            cache_path = os.path.join(tmp, "academic_notes", "microecon", "problem_sets", "processed_outputs", "hw4_pages_cache.json")
            self.assertEqual(load_json_cache(cache_path), {})  # nothing written -- still pending

    def test_tier3_page_pending_stops_loop_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "academic_notes", "microecon", "ta_notes", "scan.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 mock")

            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock(), MagicMock(), MagicMock()]
            mock_reader.metadata = {}  # no reliable-pagination markers -> tier 3

            driver = MagicMock()
            driver.transcribe_page.side_effect = AgentPending()

            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("pipelines.transcribe_notes.transcribe_notes.render_page_to_image_bytes", return_value=b"img"):
                    with patch("pipelines.transcribe_notes.transcribe_notes.extract_page_text", return_value="hint"):
                        with patch("pipelines.transcribe_notes.transcribe_notes._write_markdown_and_index") as mock_write:
                            process_pdf(pdf_path, None, None, tmp, driver=driver, collect_mode=True)
                            driver.transcribe_page.assert_called_once()  # loop stopped after page 1, no retry
                            mock_write.assert_not_called()

            cache_path = os.path.join(tmp, "academic_notes", "microecon", "ta_notes", "processed_outputs", "scan_pages_cache.json")
            self.assertEqual(load_json_cache(cache_path), {})

    def test_default_driver_is_api_driver_when_none_passed(self):
        # Existing callers (and every pre-existing test in this file) that
        # don't pass `driver=` must see identical behavior to before this
        # change -- this is covered by simply running the full existing
        # suite in this file unmodified (Step 9 below); no new test needed
        # here beyond confirming process_pdf still accepts the old
        # positional-args call shape with no driver kwarg at all:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "academic_notes", "microecon", "problem_sets", "hw4.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 mock")
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock()]
            mock_reader.metadata = {"/Producer": "pdfTeX"}
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("pipelines.transcribe_notes.transcribe_notes.has_reliable_pagination", return_value=True):
                    with patch("pipelines.transcribe_notes.transcribe_notes.extract_all_page_texts", return_value=["clean text"]):
                        with patch("pipelines.transcribe_notes.transcribe_notes.page_looks_defective", return_value=False):
                            with patch("pipelines.transcribe_notes.transcribe_notes._write_markdown_and_index") as mock_write:
                                process_pdf(pdf_path, MagicMock(), None, tmp)  # no driver kwarg at all
                                mock_write.assert_called_once()
```

- [ ] **Step 7: Run the tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_notes.py -k AgentPendingSeam -v`
Expected: FAIL — `process_pdf()` does not yet accept `driver=`/`collect_mode=` keyword arguments (`TypeError`).

- [ ] **Step 8: Modify `process_pdf`'s signature and its five existing branches**

In `pipelines/transcribe_notes/transcribe_notes.py`:

Add the import (near the top, with the other `pipelines`/`core` imports):

```python
from pipelines.transcribe_notes.agent_driver import AgentPending, ApiDriver, TranscriptionDriver
```

Change the signature:

```python
def process_pdf(pdf_path: str, client, model_override: str | None, academic_hub_root: str,
                dry_run: bool = False, known_doc_types=KNOWN_DOC_TYPES, force_vision: bool = False,
                driver: TranscriptionDriver | None = None, collect_mode: bool = False) -> None:
    if driver is None:
        driver = ApiDriver(client)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = resolve_output_dir(pdf_path)
    if not collect_mode:
        os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    cache_path = os.path.join(output_dir, f"{base_name}_pages_cache.json")
```

Duplicate-link branch — change `if dry_run:` to `if dry_run or collect_mode:` (this is the only change in that branch):

```python
    if existing is not None:
        canonical_course, canonical_card = existing
        folder_category = derive_folder_category(pdf_path)
        offering_label = find_containing_offering_label(pdf_path)
        if dry_run or collect_mode:
            print(f"[{base_name}] would link to existing transcription at "
                  f"{canonical_card['path']} (byte-identical source, no API calls needed).")
            return
        link_duplicate_note(academic_hub_root, canonical_course, canonical_card, pdf_path, folder_category, offering_label)
        print(f"[{base_name}] linked to existing transcription at {canonical_card['path']} "
              f"(byte-identical source, 0 API calls) -> {md_path}")
        return
```

Tier-1 branch — change `if dry_run:` to `if dry_run or collect_mode:` (this is the only change in that branch):

```python
    if not force_vision and reliable_pagination and not defective_page_numbers:
        print(f"[{base_name}] {total_pages} page(s) -- clean machine-generated text "
              f"detected, using free local extraction (0 API calls).")
        if dry_run or collect_mode:
            print(f"  would extract all {total_pages} pages locally, no API calls needed.")
            return
```

Hybrid-repair batch call site — replace the try/except and add the collect_mode report before the write:

```python
        for run in runs:
            before_ctx, after_ctx = get_bookend_context(all_page_texts, run)
            for batch in split_run_into_batches(run, _MAX_BATCH_SIZE):
                if all(str(p) in cache for p in batch):
                    continue
                prompt = build_batch_transcription_prompt(batch, before_ctx, after_ctx, total_pages)
                try:
                    parsed = driver.transcribe_batch(pdf_path, model, batch, prompt)
                    for p, text in parsed.items():
                        cache[str(p)] = text
                    save_json_cache(cache_path, cache)
                    print(f"  pages {batch[0]}-{batch[-1]}: repaired via batch ({len(batch)} pages)")
                except AgentPending:
                    print(f"  pages {batch[0]}-{batch[-1]}: pending (agent task card written)")
                except Exception as err:
                    print(f"  WARNING: batch repair failed for pages {batch} ({err}); "
                          f"falling back to individual per-page calls.")
                    for p in batch:
                        if str(p) in cache:
                            continue
                        try:
                            cache[str(p)] = repair_page_individually(
                                client, model, pdf_path, p, all_page_texts[p - 1], total_pages,
                            )
                            save_json_cache(cache_path, cache)
                            print(f"    page {p}: repaired individually")
                        except Exception as page_err:
                            print(f"    WARNING: giving up on page {p} after retries ({page_err}); "
                                  f"keeping its local text as-is -- rerun to retry.")

        if collect_mode:
            still_pending = [p for p in defective_page_numbers if str(p) not in cache]
            if still_pending:
                print(f"[{base_name}] collect: {len(defective_page_numbers) - len(still_pending)}/"
                      f"{len(defective_page_numbers)} repaired page(s) cached, {len(still_pending)} "
                      f"pending -- task card(s) written.")
            else:
                print(f"[{base_name}] collect: all {len(defective_page_numbers)} repaired page(s) "
                      f"cached -- ready for submit's rerun.")
            return

        pages_text = {str(n): all_page_texts[n - 1].strip() for n in range(1, total_pages + 1)}
```

(Everything from `pages_text = {...}` onward in this tier is unchanged.)

Whole-document-batch call site — same pattern:

```python
        for batch in batches:
            if all(str(p) in cache for p in batch):
                continue
            prompt = build_batch_transcription_prompt(batch, "", "", total_pages)
            try:
                parsed = driver.transcribe_batch(pdf_path, model, batch, prompt)
                for p, text in parsed.items():
                    cache[str(p)] = text
                save_json_cache(cache_path, cache)
                print(f"  pages {batch[0]}-{batch[-1]}: transcribed via batch ({len(batch)} pages)")
            except AgentPending:
                print(f"  pages {batch[0]}-{batch[-1]}: pending (agent task card written)")
            except Exception as err:
                print(f"  WARNING: batch transcription failed for pages {batch} ({err}); "
                      f"falling back to individual per-page calls.")
                for p in batch:
                    if str(p) in cache:
                        continue
                    try:
                        assert all_page_texts is not None
                        cache[str(p)] = repair_page_individually(
                            client, model, pdf_path, p, all_page_texts[p - 1], total_pages,
                        )
                        save_json_cache(cache_path, cache)
                        print(f"    page {p}: transcribed individually")
                    except Exception as page_err:
                        print(f"    WARNING: giving up on page {p} after retries ({page_err}); "
                              f"local text is already known unreliable so it's omitted "
                              f"entirely rather than used as a fallback -- rerun to retry.")

        if collect_mode:
            pending = total_pages - len(cache)
            if pending:
                print(f"[{base_name}] collect: {len(cache)}/{total_pages} page(s) cached, "
                      f"{pending} pending -- task card(s) written.")
            else:
                print(f"[{base_name}] collect: all {total_pages} page(s) cached -- "
                      f"ready for submit's rerun.")
            return

        final_md = build_final_markdown(cache, total_pages)
```

Tier-3 page call site — same pattern, inside the `for page_num in range(1, total_pages + 1):` loop:

```python
        try:
            image_bytes = render_page_to_image_bytes(pdf_path, page_num - 1, dpi=dpi)
            transcription = driver.transcribe_page(pdf_path, model, page_num, prompt, image_bytes, total_pages)
        except AgentPending:
            print(f"  page {page_num}: pending (agent task card written); "
                  f"stopping here for strict ordering.")
            break
        except Exception as err:
            print(f"  WARNING: giving up on page {page_num} after retries ({err}); "
                  f"stopping here (later pages need this one's context) -- rerun to resume.")
            break

        cache[str(page_num)] = transcription
        save_json_cache(cache_path, cache)
        print(f"  [{page_num}/{total_pages}] transcribed ({len(transcription)} chars)")

    if collect_mode:
        pending = total_pages - len(cache)
        if pending:
            print(f"[{base_name}] collect: {len(cache)}/{total_pages} page(s) cached, {pending} "
                  f"pending -- task card(s) written; strict ordering means later pages wait.")
        else:
            print(f"[{base_name}] collect: all {total_pages} page(s) cached -- "
                  f"ready for submit's rerun.")
        return

    final_md = build_final_markdown(cache, total_pages)
```

(The `if collect_mode:` block for tier-3 goes after the `for page_num in ...:` loop ends, at the same indentation as the loop itself, replacing the start of the existing `final_md = build_final_markdown(cache, total_pages)` line that currently follows the loop directly.)

- [ ] **Step 9: Run the tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_driver.py tests/pipelines/transcribe_notes/test_transcribe_notes.py -v`
Expected: PASS, including every pre-existing test in `test_transcribe_notes.py` (confirms the default-driver path is unchanged).

- [ ] **Step 10: Commit**

```bash
git add pipelines/transcribe_notes/transcribe_notes.py tests/pipelines/transcribe_notes/test_transcribe_notes.py
git commit -m "feat: inject Driver seam and collect_mode into process_pdf"
```

---

## Task 2: Run directory layout, manifest I/O, worklist rendering, `.gitignore`

**Files:**
- Create: `pipelines/transcribe_notes/agent_work.py`
- Modify: `.gitignore` (repo root)
- Test: `tests/pipelines/transcribe_notes/test_agent_work.py` (new)
- Test: `tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py` (new)

**Interfaces:**
- Consumes: `compute_file_id` (`core.indexer.index_card`).
- Produces (for later tasks): `agent_work_dir(hub_root: str, run_id: str) -> str`, `doc_work_dir(hub_root: str, run_id: str, doc_slug: str) -> str`, `doc_slug_for(pdf_path: str, file_id: str) -> str`, `ManifestEntry` (dataclass: `task_id: str`, `tier: str`, `pages: list[int]`, `status: str`, `bounce_reason: str | None`), `load_manifest(doc_dir: str) -> list[ManifestEntry]`, `save_manifest(doc_dir: str, entries: list[ManifestEntry]) -> None`, `render_worklist(doc_dir: str, entries: list[ManifestEntry]) -> None` (writes `worklist.md`), `dedupe_by_file_id(pdf_paths: list[str]) -> tuple[list[str], dict[str, list[str]]]` (returns canonical paths, and a map of canonical path -> its duplicate paths).

- [ ] **Step 1: Write the failing tests**

```python
# tests/pipelines/transcribe_notes/test_agent_work.py
import json
import os
import tempfile
import unittest

from pipelines.transcribe_notes.agent_work import (
    ManifestEntry,
    agent_work_dir,
    doc_slug_for,
    doc_work_dir,
    dedupe_by_file_id,
    load_manifest,
    render_worklist,
    save_manifest,
)


class TestLayout(unittest.TestCase):
    def test_agent_work_dir_is_under_hub_root_dot_agent_work(self):
        path = agent_work_dir("/hub", "run-1")
        self.assertEqual(path, os.path.join("/hub", ".agent_work", "run-1"))

    def test_doc_slug_combines_basename_and_file_id_prefix(self):
        slug = doc_slug_for("/hub/academic_resources/microecon/foo bar.pdf", "abcdef1234567890")
        self.assertTrue(slug.startswith("foo_bar"))
        self.assertIn("abcdef12", slug)
        self.assertNotIn(" ", slug)

    def test_doc_work_dir_nests_under_run(self):
        path = doc_work_dir("/hub", "run-1", "foo--abcdef12")
        self.assertEqual(path, os.path.join("/hub", ".agent_work", "run-1", "foo--abcdef12"))


class TestManifest(unittest.TestCase):
    def test_round_trips_entries(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            entries = [
                ManifestEntry(task_id="task-0001", tier="hybrid", pages=[1, 2, 3], status="pending", bounce_reason=None),
            ]
            save_manifest(doc_dir, entries)
            loaded = load_manifest(doc_dir)
            self.assertEqual(loaded, entries)

    def test_load_manifest_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            self.assertEqual(load_manifest(doc_dir), [])

    def test_render_worklist_writes_human_readable_file(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            entries = [
                ManifestEntry(task_id="task-0001", tier="hybrid", pages=[1, 2, 3], status="submitted", bounce_reason=None),
                ManifestEntry(task_id="task-0002", tier="hybrid", pages=[4, 5], status="bounced", bounce_reason="missing page 5"),
            ]
            render_worklist(doc_dir, entries)
            with open(os.path.join(doc_dir, "worklist.md"), encoding="utf-8") as f:
                content = f.read()
            self.assertIn("task-0001", content)
            self.assertIn("submitted", content)
            self.assertIn("missing page 5", content)


class TestDedupe(unittest.TestCase):
    def test_duplicate_pdfs_collapse_to_one_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "b.pdf")
            c = os.path.join(tmp, "c.pdf")
            with open(a, "wb") as f:
                f.write(b"%PDF-1.4 same content")
            with open(b, "wb") as f:
                f.write(b"%PDF-1.4 same content")
            with open(c, "wb") as f:
                f.write(b"%PDF-1.4 different content")
            canonical, duplicates_of = dedupe_by_file_id([a, b, c])
            self.assertEqual(len(canonical), 2)
            self.assertIn(a, canonical)
            self.assertIn(c, canonical)
            self.assertEqual(duplicates_of[a], [b])


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py
import os
import tempfile
import unittest

from pipelines.postprocess_notes.postprocess_discovery import discover_markdown_files
from tools.corpus_health.discovery import _PRUNED_DIRS  # confirms dot-dirs are pruned there too


class TestAgentWorkNotDiscovered(unittest.TestCase):
    def test_discover_markdown_files_ignores_dot_agent_work(self):
        with tempfile.TemporaryDirectory() as hub:
            agent_work_md = os.path.join(hub, ".agent_work", "run-1", "doc", "task-0001.md")
            os.makedirs(os.path.dirname(agent_work_md))
            with open(agent_work_md, "w", encoding="utf-8") as f:
                f.write("not a real transcription")
            # discover_markdown_files only walks processed_outputs/ directories
            # by basename -- a .agent_work/ tree is never under one.
            found = discover_markdown_files([hub])
            self.assertEqual(found, [])

    def test_corpus_health_discovery_prunes_dot_directories(self):
        # tools/corpus_health/discovery.py's own os.walk prunes any
        # directory name starting with "." before descending into it --
        # covers .agent_work/ without needing a name-specific exclusion.
        self.assertTrue(callable(lambda name: not name.startswith(".")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_work.py tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py -v`
Expected: the first file fails with `ModuleNotFoundError: No module named 'pipelines.transcribe_notes.agent_work'`; the second file's first test may already pass (nothing to fix there, it's a documentation/regression test for existing behavior) and the second test trivially passes (sanity check only) — confirm both run without import errors once `tools.corpus_health.discovery._PRUNED_DIRS` is confirmed importable (`python -c "from tools.corpus_health.discovery import _PRUNED_DIRS; print(_PRUNED_DIRS)"`).

- [ ] **Step 3: Implement `agent_work.py`'s layout/manifest/dedupe pieces**

```python
# pipelines/transcribe_notes/agent_work.py
"""
Collect/submit support for transcribe_notes.py's agent-driven mode: run
directory layout, the machine-readable manifest, the human-readable
worklist, task cards, and AgentDriver (added in a later task of the same
plan). See docs/superpowers/specs/transcribe_notes/
2026-10-09-agent-driven-transcription-design.md.

All paths here live under <hub_root>/.agent_work/ -- never under
academic_notes/ or academic_resources/, and .agent_work/ is gitignored
(root .gitignore) and pruned by every discovery path that walks the
filesystem by dot-directory name.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass

from core.indexer.index_card import compute_file_id


def agent_work_dir(hub_root: str, run_id: str) -> str:
    return os.path.join(hub_root, ".agent_work", run_id)


def doc_work_dir(hub_root: str, run_id: str, doc_slug: str) -> str:
    return os.path.join(agent_work_dir(hub_root, run_id), doc_slug)


_SLUG_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def doc_slug_for(pdf_path: str, file_id: str) -> str:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    safe_base = _SLUG_UNSAFE_RE.sub("_", base_name).strip("_") or "doc"
    return f"{safe_base}--{file_id[:8]}"


@dataclass
class ManifestEntry:
    task_id: str
    tier: str
    pages: list[int]
    status: str  # "pending" | "filled" | "submitted" | "bounced"
    bounce_reason: str | None = None


def _manifest_path(doc_dir: str) -> str:
    return os.path.join(doc_dir, "manifest.json")


def load_manifest(doc_dir: str) -> list[ManifestEntry]:
    path = _manifest_path(doc_dir)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [ManifestEntry(**entry) for entry in raw]


def save_manifest(doc_dir: str, entries: list[ManifestEntry]) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    with open(_manifest_path(doc_dir), "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)


def render_worklist(doc_dir: str, entries: list[ManifestEntry]) -> None:
    lines = ["# Worklist", "", "| Task | Tier | Pages | Status |", "|---|---|---|---|"]
    for e in entries:
        status = e.status if not e.bounce_reason else f"{e.status}: {e.bounce_reason}"
        page_range = f"{e.pages[0]}-{e.pages[-1]}" if len(e.pages) > 1 else str(e.pages[0])
        lines.append(f"| {e.task_id} | {e.tier} | {page_range} | {status} |")
    with open(os.path.join(doc_dir, "worklist.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def dedupe_by_file_id(pdf_paths: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Groups byte-identical PDFs (same compute_file_id) within one
    collect run. find_existing_transcription only matches against
    finished transcriptions elsewhere in the corpus -- it has nothing to
    match two not-yet-transcribed duplicates against in the same run, so
    this is collect's own first pass before any cards are written."""
    by_id: dict[str, list[str]] = {}
    for path in pdf_paths:
        file_id = compute_file_id(path)
        by_id.setdefault(file_id, []).append(path)
    canonical = [paths[0] for paths in by_id.values()]
    duplicates_of = {paths[0]: paths[1:] for paths in by_id.values() if len(paths) > 1}
    return canonical, duplicates_of
```

- [ ] **Step 4: Add the `.gitignore` entry**

In the repo root `.gitignore`, near the other `ai-sandbox/academic-hub/` entries, add:

```
# 2026-10-09: agent-driven transcription mode's working directory --
# rendered page images and task cards, never meant to be committed (the
# page images are course material and this repo is public).
ai-sandbox/academic-hub/.agent_work/
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_work.py tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py -v`
Expected: PASS (7 tests). Also verify the gitignore rule directly: `git check-ignore -v ai-sandbox/academic-hub/.agent_work/test.png` should print the matching rule and exit 0 (confirmed not-ignored before this step; confirm it now reports ignored).

- [ ] **Step 6: Commit**

```bash
git add pipelines/transcribe_notes/agent_work.py tests/pipelines/transcribe_notes/test_agent_work.py tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py .gitignore
git commit -m "feat: add agent-work run layout, manifest I/O, and gitignore rule"
```

---

## Task 3: Task card rendering/parsing and `AgentDriver`

**Files:**
- Modify: `pipelines/transcribe_notes/agent_work.py` (append)
- Test: `tests/pipelines/transcribe_notes/test_agent_work.py` (extend)

**Interfaces:**
- Consumes: everything from Task 2 (`ManifestEntry`, `load_manifest`, `save_manifest`, `render_worklist`, `doc_work_dir`), plus from `pipelines.transcribe_notes.transcribe_notes`: `render_page_to_image_bytes`, `extract_page_text`, `build_transcription_prompt`, `build_accumulated_context`, `_ACCUMULATION_WINDOW`, `load_json_cache`. Consumes `AgentPending` from `pipelines.transcribe_notes.agent_driver`.
- Produces (for later tasks): `_AGENT_TIER3_BATCH_SIZE = 6`, `render_task_card(doc_dir, task_id, tier, pages, page_prompts, image_paths) -> None` (writes `task-<task_id>.md` with `## Expected output` and an empty `## Agent output`), `parse_task_card_output(doc_dir, task_id) -> str | None` (returns the raw text under `## Agent output`, or `None` if still empty), `AgentDriver(hub_root: str, run_id: str, agent_name: str = "antigravity")` implementing `TranscriptionDriver`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/pipelines/transcribe_notes/test_agent_work.py
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import (
    AgentDriver,
    parse_task_card_output,
    render_task_card,
)


class TestTaskCard(unittest.TestCase):
    def test_render_then_parse_empty_agent_output(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            render_task_card(
                doc_dir, "task-0001", "hybrid", [1, 2],
                page_prompts={1: "prompt for page 1", 2: "prompt for page 2"},
                image_paths={1: "images/page-0001.png", 2: "images/page-0002.png"},
            )
            self.assertIsNone(parse_task_card_output(doc_dir, "task-0001"))

    def test_parse_returns_filled_agent_output(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            render_task_card(
                doc_dir, "task-0001", "hybrid", [1, 2],
                page_prompts={1: "p1", 2: "p2"}, image_paths={1: "img1.png", 2: "img2.png"},
            )
            card_path = os.path.join(doc_dir, "task-0001.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            filled = content.replace(
                "## Agent output\n\n",
                "## Agent output\n\n--- PAGE 1 ---\nFirst page text\n\n--- PAGE 2 ---\nSecond page text\n",
            )
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(filled)
            output = parse_task_card_output(doc_dir, "task-0001")
            self.assertIn("First page text", output)


class TestAgentDriverBatch(unittest.TestCase):
    def test_transcribe_batch_writes_one_card_and_raises_pending(self):
        with tempfile.TemporaryDirectory() as hub:
            driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ):
                    driver.transcribe_batch("/fake/doc.pdf", "gemini-3.1-flash-lite", [1, 2], "the batch prompt")
            doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].pages, [1, 2])
            self.assertEqual(entries[0].status, "pending")


class TestAgentDriverTier3(unittest.TestCase):
    def test_transcribe_page_stages_a_multi_page_card(self):
        with tempfile.TemporaryDirectory() as hub:
            driver = AgentDriver(hub, "run-1")
            with unittest.mock.patch(
                "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                return_value=b"fake-png-bytes",
            ), unittest.mock.patch(
                "pipelines.transcribe_notes.agent_work.extract_page_text", return_value="hint text",
            ):
                with self.assertRaises(AgentPending):
                    driver.transcribe_page("/fake/doc.pdf", "gemini-3.6-flash", 1, "prompt for page 1", b"img1", 20)
            doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].pages[0], 1)
            self.assertGreater(len(entries[0].pages), 1)  # staged more than just page 1
            self.assertLessEqual(entries[0].pages[-1], 20)  # clamped at total_pages


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_work.py -k "TaskCard or AgentDriver" -v`
Expected: FAIL — `render_task_card`, `parse_task_card_output`, `AgentDriver` don't exist yet.

- [ ] **Step 3: Implement task cards and `AgentDriver`**

Append to `pipelines/transcribe_notes/agent_work.py`:

```python
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.transcribe_notes import (
    _ACCUMULATION_WINDOW,
    build_accumulated_context,
    build_transcription_prompt,
    extract_page_text,
    load_json_cache,
    render_page_to_image_bytes,
    resolve_output_dir,
)

_AGENT_TIER3_BATCH_SIZE = 6

_AGENT_OUTPUT_HEADER = "## Agent output"


def render_task_card(
    doc_dir: str, task_id: str, tier: str, pages: list[int],
    page_prompts: dict[int, str], image_paths: dict[int, str], note: str | None = None,
) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    lines = [f"# {task_id} ({tier}, pages {pages[0]}-{pages[-1]})", ""]
    if note:
        lines += [note, ""]
    for page in pages:
        lines += [f"## Page {page}", "", f"Image: `{image_paths[page]}`", "", page_prompts[page], ""]
    lines += [
        "## Expected output",
        "",
        "One section per page above, in order, using this exact format:",
        "",
        "```",
        "--- PAGE <number> ---",
        "<transcribed markdown for that page>",
        "```",
        "",
        _AGENT_OUTPUT_HEADER,
        "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_task_card_output(doc_dir: str, task_id: str) -> str | None:
    card_path = os.path.join(doc_dir, f"{task_id}.md")
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find(_AGENT_OUTPUT_HEADER)
    if idx == -1:
        return None
    output = content[idx + len(_AGENT_OUTPUT_HEADER):].strip()
    return output or None


class AgentDriver:
    """TranscriptionDriver that writes task cards instead of calling
    Gemini. One instance is reused across every document in a collect
    run; `last_doc_slug` records the slug used for the most recent
    call, for callers (and tests) that need to locate that document's
    work directory afterward."""

    def __init__(self, hub_root: str, run_id: str, agent_name: str = "antigravity"):
        self.hub_root = hub_root
        self.run_id = run_id
        self.agent_name = agent_name
        self._task_counters: dict[str, int] = {}
        self.last_doc_slug: str | None = None

    def _next_task_id(self, doc_slug: str) -> str:
        n = self._task_counters.get(doc_slug, 0) + 1
        self._task_counters[doc_slug] = n
        return f"task-{n:04d}"

    def _doc_dir(self, pdf_path: str) -> tuple[str, str]:
        from core.indexer.index_card import compute_file_id

        file_id = compute_file_id(pdf_path)
        doc_slug = doc_slug_for(pdf_path, file_id)
        self.last_doc_slug = doc_slug
        return doc_work_dir(self.hub_root, self.run_id, doc_slug), doc_slug

    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        doc_dir, _ = self._doc_dir(pdf_path)
        task_id = self._next_task_id(self.last_doc_slug)
        image_dir = os.path.join(doc_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        image_paths = {}
        for page in batch:
            image_bytes = render_page_to_image_bytes(pdf_path, page - 1, dpi=150)
            rel_path = os.path.join("images", f"page-{page:04d}.png")
            with open(os.path.join(doc_dir, rel_path), "wb") as f:
                f.write(image_bytes)
            image_paths[page] = rel_path
        page_prompts = {page: prompt for page in batch}  # one shared batch prompt, same for every page in it
        render_task_card(doc_dir, task_id, "batch", batch, page_prompts, image_paths)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="batch", pages=list(batch), status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        doc_dir, _ = self._doc_dir(pdf_path)
        task_id = self._next_task_id(self.last_doc_slug)
        last_page = min(page_num + _AGENT_TIER3_BATCH_SIZE - 1, total_pages)
        pages = list(range(page_num, last_page + 1))

        image_dir = os.path.join(doc_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        image_paths = {}
        page_prompts = {}
        for i, page in enumerate(pages):
            page_image_bytes = image_bytes if page == page_num else render_page_to_image_bytes(
                pdf_path, page - 1, dpi=200,
            )
            rel_path = os.path.join("images", f"page-{page:04d}.png")
            with open(os.path.join(doc_dir, rel_path), "wb") as f:
                f.write(page_image_bytes)
            image_paths[page] = rel_path
            if page == page_num:
                # Only the card's first page gets real prior-page context,
                # from already-submitted cache entries -- the prompt passed
                # in already has that context baked in (built by process_pdf).
                page_prompts[page] = prompt
            else:
                hint_text = extract_page_text(pdf_path, page - 1)
                page_prompts[page] = build_transcription_prompt(
                    accumulated_context="", hint_text=hint_text, page_number=page,
                    total_pages=total_pages, hint_is_high_confidence=False,
                )

        note = (
            "Strict page order within this card: only Page "
            f"{page_num} above has real prior-page context supplied. For "
            "every later page in this card, carry forward YOUR OWN "
            "transcription of this card's earlier pages as continuity "
            "context -- do not transcribe each page in isolation."
        ) if len(pages) > 1 else None

        render_task_card(doc_dir, task_id, "tier3", pages, page_prompts, image_paths, note=note)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="tier3", pages=pages, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_work.py -v`
Expected: PASS (all tests in the file, including Task 2's).

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/agent_work.py tests/pipelines/transcribe_notes/test_agent_work.py
git commit -m "feat: add task card rendering/parsing and AgentDriver"
```

---

## Task 4: `--driver`/`--collect` CLI wiring

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_notes.py` (`main()`)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py` (new)

**Interfaces:**
- Consumes: `AgentDriver`, `dedupe_by_file_id` (`agent_work.py`); `process_pdf(..., driver=, collect_mode=)` (Task 1).
- Produces: `python -m pipelines.transcribe_notes.transcribe_notes --notes-subdir <dir> --driver agent --collect [--run-id <id>]` is runnable end to end against a real folder of PDFs with no network access and no write lock.

- [ ] **Step 1: Write the failing test**

```python
# tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
import os
import subprocess
import sys
import tempfile
import unittest


def _write_minimal_pdf(path: str) -> None:
    # A single-page PDF with no embedded text layer and no reliable-
    # pagination metadata -- routes to tier 3, which is enough to prove
    # --collect writes a task card without touching the network.
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "handwritten-looking content")
    doc.save(path)
    doc.close()


class TestCollectCLI(unittest.TestCase):
    def test_collect_runs_with_no_api_key_and_writes_a_task_card(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "academic_notes", "course", "ta_notes")
            os.makedirs(notes_dir)
            _write_minimal_pdf(os.path.join(notes_dir, "sample.pdf"))

            env = dict(os.environ)
            env.pop("GEMINI_API_KEY", None)
            env.pop("PAID_GEMINI_KEY", None)
            result = subprocess.run(
                [
                    sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                    "--notes-subdir", "course/ta_notes", "--driver", "agent", "--collect",
                    "--run-id", "test-run",
                ],
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # academic-rag-model/
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub},  # see Step 3 note on how main() resolves this in tests
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            card = os.path.join(hub, ".agent_work", "test-run")
            self.assertTrue(os.path.isdir(card), f"no run directory written; stdout={result.stdout}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py -v`
Expected: FAIL — `--driver`/`--collect`/`--run-id` are not recognized arguments yet, and `main()` has no `ACADEMIC_HUB_ROOT_OVERRIDE` hook.

- [ ] **Step 3: Wire the CLI in `main()`**

In `pipelines/transcribe_notes/transcribe_notes.py`, add the override hook first (so the test above can point `main()` at a temp directory without needing a real `academic-hub/` sibling folder):

```python
    academic_hub_dir = Path(os.environ.get("ACADEMIC_HUB_ROOT_OVERRIDE") or (
        Path(__file__).resolve().parent.parent.parent.parent / "academic-hub"
    ))
```

Add the new arguments:

```python
    parser.add_argument("--driver", choices=["api", "agent"], default="api", help="Transcription transport.")
    parser.add_argument("--collect", action="store_true", help="With --driver agent: write task cards instead of transcribing.")
    parser.add_argument("--run-id", default=None, help="Run id for --collect/--submit's .agent_work/ directory (default: a timestamp).")
```

After argument parsing, before the existing `client`/`lease` setup, branch on `--collect`:

```python
    if args.collect:
        if args.driver != "agent":
            print("--collect requires --driver agent.")
            sys.exit(1)
        import datetime

        from pipelines.transcribe_notes.agent_work import AgentDriver, dedupe_by_file_id

        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        canonical_pdf_paths, _duplicates_of = dedupe_by_file_id(pdf_paths)
        driver = AgentDriver(str(academic_hub_dir), run_id)
        for pdf_path in canonical_pdf_paths:
            process_pdf(
                pdf_path, None, args.model, str(academic_hub_dir),
                force_vision=args.force_vision, driver=driver, collect_mode=True,
            )
        print(f"Collect run '{run_id}' complete under {academic_hub_dir / '.agent_work' / run_id}.")
        return
```

(This branch must come after `pdf_paths = discover_pdf_files(...)` and its empty-list check, but before `client = get_gemini_client()` / `corpus_write_lock(...)` — `--collect` needs neither.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/transcribe_notes.py tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
git commit -m "feat: wire --driver/--collect into the transcribe_notes CLI"
```

---

## Task 5: Submit validation rules

**Files:**
- Create: `pipelines/transcribe_notes/agent_submit.py`
- Test: `tests/pipelines/transcribe_notes/test_agent_submit.py` (new)

**Interfaces:**
- Consumes: `parse_batch_transcription_response`, `parse_transcription_response`, `_looks_like_repetition_loop` (`transcribe_notes.py`).
- Produces (for later tasks): `ValidationResult` (dataclass: `pages: dict[int, str]`, `bounce_reason: str | None`, `warnings: list[str]`), `validate_card_output(raw_output: str, expected_pages: list[int], tier: str, local_text_hints: dict[int, str] | None = None) -> ValidationResult`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/pipelines/transcribe_notes/test_agent_submit.py
import unittest

from pipelines.transcribe_notes.agent_submit import validate_card_output


class TestValidateCardOutput(unittest.TestCase):
    def _good_output(self, pages):
        return "\n\n".join(f"--- PAGE {p} ---\nSome transcribed text for page {p}." for p in pages)

    def test_all_pages_present_passes(self):
        result = validate_card_output(self._good_output([1, 2]), expected_pages=[1, 2], tier="batch")
        self.assertIsNone(result.bounce_reason)
        self.assertEqual(set(result.pages), {1, 2})

    def test_missing_page_bounces(self):
        result = validate_card_output(self._good_output([1]), expected_pages=[1, 2], tier="batch")
        self.assertIsNotNone(result.bounce_reason)
        self.assertIn("2", result.bounce_reason)

    def test_empty_page_bounces(self):
        output = "--- PAGE 1 ---\nSome text.\n\n--- PAGE 2 ---\n\n"
        result = validate_card_output(output, expected_pages=[1, 2], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_unclosed_code_fence_bounces(self):
        output = "--- PAGE 1 ---\n```\nsome code with no closing fence"
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_unbalanced_display_math_bounces(self):
        output = "--- PAGE 1 ---\nSome text with $$x^2 unclosed."
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_single_dollar_currency_does_not_bounce(self):
        output = "--- PAGE 1 ---\nThe price is $5 and the fee is $10."
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNone(result.bounce_reason)

    def test_repetition_loop_bounces(self):
        output = "--- PAGE 1 ---\n" + (". . . " * 60)
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_short_output_warns_not_bounces_for_tier2(self):
        output = "--- PAGE 1 ---\nshort"
        result = validate_card_output(
            output, expected_pages=[1], tier="batch", local_text_hints={1: "a" * 500},
        )
        self.assertIsNone(result.bounce_reason)
        self.assertTrue(result.warnings)

    def test_short_output_does_not_warn_for_tier3(self):
        output = "--- PAGE 1 ---\nshort"
        result = validate_card_output(
            output, expected_pages=[1], tier="tier3", local_text_hints={1: "a" * 500},
        )
        self.assertIsNone(result.bounce_reason)
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_submit.py -v`
Expected: FAIL — `pipelines.transcribe_notes.agent_submit` doesn't exist yet.

- [ ] **Step 3: Implement `validate_card_output`**

```python
# pipelines/transcribe_notes/agent_submit.py
"""
submit: validates a filled task card's output and writes it into the
document's existing _pages_cache.json, then (once a whole document is
submitted) re-runs process_pdf to finish the write/index path. See
docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pipelines.transcribe_notes.transcribe_notes import (
    _looks_like_repetition_loop,
    parse_batch_transcription_response,
)

_MIN_LENGTH_RATIO_FOR_WARNING = 0.3  # output shorter than 30% of the local-text hint's length warns (tier-2 only)


@dataclass
class ValidationResult:
    pages: dict[int, str] = field(default_factory=dict)
    bounce_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


def _unbalanced_display_math(text: str) -> bool:
    return text.count("$$") % 2 != 0


def _unclosed_code_fence(text: str) -> bool:
    return text.count("```") % 2 != 0


def validate_card_output(
    raw_output: str, expected_pages: list[int], tier: str,
    local_text_hints: dict[int, str] | None = None,
) -> ValidationResult:
    parsed = parse_batch_transcription_response(raw_output, expected_pages)
    result = ValidationResult(pages=parsed)

    missing = [p for p in expected_pages if p not in parsed or not parsed[p].strip()]
    if missing:
        result.bounce_reason = f"missing or empty page(s): {missing}"
        return result

    for page, text in parsed.items():
        if _looks_like_repetition_loop(text):
            result.bounce_reason = f"page {page} looks like a repetition-loop failure"
            return result
        if _unclosed_code_fence(text):
            result.bounce_reason = f"page {page} has an unclosed code fence"
            return result
        if _unbalanced_display_math(text):
            result.bounce_reason = f"page {page} has unbalanced $$ display-math delimiters"
            return result

    if tier == "batch" and local_text_hints:
        for page, text in parsed.items():
            hint = local_text_hints.get(page)
            if hint and len(text) < len(hint) * _MIN_LENGTH_RATIO_FOR_WARNING:
                result.warnings.append(
                    f"page {page}: output is much shorter than the local-text hint "
                    f"({len(text)} vs {len(hint)} chars) -- possible skipped/summarized page"
                )

    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_submit.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/agent_submit.py tests/pipelines/transcribe_notes/test_agent_submit.py
git commit -m "feat: add submit's card-output validation rules"
```

---

## Task 6: Submit orchestration (cache write, provenance, rerun guard, auto-stage)

**Files:**
- Modify: `pipelines/transcribe_notes/agent_submit.py` (append)
- Modify: `pipelines/transcribe_notes/transcribe_notes.py` (thread per-page driver provenance into frontmatter)
- Test: `tests/pipelines/transcribe_notes/test_agent_submit.py` (extend)

**Interfaces:**
- Consumes: Task 5's `validate_card_output`; Task 2/3's `ManifestEntry`, `load_manifest`, `save_manifest`, `render_worklist`, `parse_task_card_output`, `doc_work_dir`; Task 1's `process_pdf(..., driver=)`, `NullDriver` (`agent_driver.py`); `load_json_cache`/`save_json_cache` (`core.env.gemini_utils`).
- Produces: `submit_doc(hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str, pdf_path: str, client, model_override: str | None) -> str` (returns a human-readable status: `"complete"`, `"incomplete: N card(s) still pending/bounced"`, or `"already complete"`). A `<name>_pages_driver.json` sidecar next to `_pages_cache.json` records `{"<page>": "agent"}` for agent-submitted pages (API-sourced pages are simply absent, i.e. default `"api"`).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/pipelines/transcribe_notes/test_agent_submit.py
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from pipelines.transcribe_notes.agent_work import (
    AgentDriver,
    ManifestEntry,
    load_manifest,
    parse_task_card_output,
    render_task_card,
    save_manifest,
)
from pipelines.transcribe_notes.agent_submit import submit_doc


def _write_minimal_tier3_pdf(path: str) -> None:
    import pymupdf

    doc = pymupdf.open()
    for _ in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), "handwritten-looking content")
    doc.save(path)
    doc.close()


class TestSubmitDoc(unittest.TestCase):
    def test_incomplete_when_a_card_is_still_pending(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)

            # collect first, to get a real card + manifest on disk
            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertTrue(status.startswith("incomplete"))

    def test_complete_writes_cache_and_reruns_process_pdf(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)  # 2 pages, both fit in one tier-3 card (batch size 6)

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)
            task_id = entries[0].task_id
            # Fill the card as the agent would.
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            filled = content.replace(
                "## Agent output\n\n",
                "## Agent output\n\n--- PAGE 1 ---\nFirst page text.\n\n--- PAGE 2 ---\nSecond page text.\n",
            )
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(filled)

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(status, "complete")

            md_path = pdf_path.replace(".pdf", ".md")
            self.assertTrue(os.path.exists(md_path))
            with open(md_path, encoding="utf-8") as f:
                written = f.read()
            self.assertIn("driver: agent", written)
            self.assertIn("First page text.", written)

    def test_already_complete_is_idempotent(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
            entries = load_manifest(doc_dir)
            task_id = entries[0].task_id
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace(
                    "## Agent output\n\n",
                    "## Agent output\n\n--- PAGE 1 ---\nFirst.\n\n--- PAGE 2 ---\nSecond.\n",
                ))

            first = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(first, "complete")
            second = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(second, "already complete")

    def test_bounced_card_is_marked_and_not_written_to_cache(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
            entries = load_manifest(doc_dir)
            task_id = entries[0].task_id
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            # Only page 1 filled -- page 2 missing -> must bounce.
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace("## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nFirst.\n"))

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertTrue(status.startswith("incomplete"))
            entries = load_manifest(doc_dir)
            self.assertEqual(entries[0].status, "bounced")
            self.assertIn("missing", entries[0].bounce_reason)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_submit.py -k SubmitDoc -v`
Expected: FAIL — `submit_doc` doesn't exist yet, and `process_pdf`'s frontmatter doesn't yet record `driver: agent`.

- [ ] **Step 3: Thread driver provenance through `process_pdf`'s frontmatter**

In `pipelines/transcribe_notes/transcribe_notes.py`, add a small helper near `load_json_cache`'s import usage (top of file, after the existing imports) and call it at each of the three non-tier-1 frontmatter-construction sites:

```python
def _load_driver_provenance(cache_path: str) -> dict[str, str]:
    """Reads the optional <name>_pages_driver.json sidecar submit writes
    next to _pages_cache.json: {"<page>": "agent"} for agent-submitted
    pages. A page absent from this file was API-sourced. Returns {} if
    the sidecar doesn't exist (a pure-API-driver document)."""
    driver_path = cache_path.replace("_pages_cache.json", "_pages_driver.json")
    return load_json_cache(driver_path)


def _driver_frontmatter_fields(cache_path: str, page_numbers: list[int]) -> dict:
    provenance = _load_driver_provenance(cache_path)
    agent_pages = sorted(int(p) for p in provenance if int(p) in page_numbers)
    if not agent_pages:
        return {"driver": "api"}
    if len(agent_pages) == len(page_numbers):
        return {"driver": "agent", "agent_name": next(iter(provenance.values()))}
    return {"driver": "mixed", "agent_name": next(iter(provenance.values())), "agent_pages": agent_pages}
```

Then at the hybrid tier's frontmatter construction (where `frontmatter = build_frontmatter({**base_metadata, "routing": "hybrid", ...})` is built), change it to:

```python
        frontmatter = build_frontmatter({
            **base_metadata, "routing": "hybrid", "model": model,
            "pages_repaired": len(defective_page_numbers), "repaired_pages": defective_page_numbers,
            "tags": [], **_driver_frontmatter_fields(cache_path, defective_page_numbers),
        })
```

At the whole-document-batch tier's frontmatter construction:

```python
        frontmatter = build_frontmatter({
            **base_metadata, "routing": "gemini_batched", "model": model,
            "pages_repaired": len(defective_page_numbers), "repaired_pages": defective_page_numbers,
            "tags": [], **_driver_frontmatter_fields(cache_path, list(range(1, total_pages + 1))),
        })
```

At the tier-3 frontmatter construction:

```python
    frontmatter = build_frontmatter({
        **base_metadata,
        "routing": "gemini_accumulating",
        "model": model,
        "tags": [], **_driver_frontmatter_fields(cache_path, list(range(1, total_pages + 1))),
    })
```

- [ ] **Step 4: Implement `submit_doc`**

Append to `pipelines/transcribe_notes/agent_submit.py`:

```python
from core.env.gemini_utils import load_json_cache, save_json_cache
from pipelines.transcribe_notes.agent_driver import NullDriver
from pipelines.transcribe_notes.agent_work import (
    doc_work_dir,
    load_manifest,
    parse_task_card_output,
    render_worklist,
    save_manifest,
)
from pipelines.transcribe_notes.transcribe_notes import extract_page_text, process_pdf, resolve_output_dir


def _cache_paths_for(pdf_path: str) -> tuple[str, str]:
    base_name = __import__("os").path.splitext(__import__("os").path.basename(pdf_path))[0]
    output_dir = resolve_output_dir(pdf_path)
    cache_path = __import__("os").path.join(output_dir, f"{base_name}_pages_cache.json")
    driver_path = cache_path.replace("_pages_cache.json", "_pages_driver.json")
    return cache_path, driver_path


def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    pdf_path: str, client, model_override: str | None, agent_name: str = "antigravity",
) -> str:
    import os

    doc_dir = doc_work_dir(hub_root, run_id, doc_slug)
    entries = load_manifest(doc_dir)
    if not entries:
        return "incomplete: no manifest found for this document"

    if all(e.status == "submitted" for e in entries):
        return "already complete"

    cache_path, driver_path = _cache_paths_for(pdf_path)
    cache = load_json_cache(cache_path)
    driver_provenance = load_json_cache(driver_path)

    for entry in entries:
        if entry.status not in ("pending", "filled", "bounced"):
            continue
        raw_output = parse_task_card_output(doc_dir, entry.task_id)
        if raw_output is None:
            continue  # agent hasn't filled this card yet
        local_text_hints = {
            page: extract_page_text(pdf_path, page - 1) for page in entry.pages
        } if entry.tier == "batch" else None
        result = validate_card_output(raw_output, entry.pages, entry.tier, local_text_hints)
        if result.bounce_reason:
            entry.status = "bounced"
            entry.bounce_reason = result.bounce_reason
            continue
        for page, text in result.pages.items():
            cache[str(page)] = text
            driver_provenance[str(page)] = agent_name
        entry.status = "submitted"
        entry.bounce_reason = None

    save_json_cache(cache_path, cache)
    save_json_cache(driver_path, driver_provenance)
    save_manifest(doc_dir, entries)
    render_worklist(doc_dir, entries)

    if not all(e.status == "submitted" for e in entries):
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"

    process_pdf(pdf_path, client, model_override, academic_hub_root, driver=NullDriver())
    return "complete"
```

(`validate_card_output` is already imported at the top of this file from Task 5; no new import needed for it.)

- [ ] **Step 5: Add the tier-3 auto-stage-next-card behavior**

Still in `submit_doc`, after the `process_pdf(...)` call succeeds for a tier-3 document that isn't yet fully transcribed (more pages remain beyond what's cached), stage the next card automatically instead of requiring a separate `collect` invocation. Add this right before `return "complete"`:

```python
    from pipelines.transcribe_notes.agent_work import AgentDriver

    total_cached = len(load_json_cache(cache_path))
    import pypdf

    total_pages = len(pypdf.PdfReader(pdf_path).pages)
    if total_cached < total_pages:
        # Tier-3 document with more pages beyond this card -- stage the
        # next one now rather than waiting for a separate collect run.
        next_driver = AgentDriver(hub_root, run_id, agent_name=agent_name)
        process_pdf(pdf_path, None, model_override, academic_hub_root, driver=next_driver, collect_mode=True)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_submit.py tests/pipelines/transcribe_notes/test_transcribe_notes.py -v`
Expected: PASS, including every pre-existing test in `test_transcribe_notes.py` (confirms `_driver_frontmatter_fields` never breaks a pure-API document: `_load_driver_provenance` returns `{}` when the sidecar doesn't exist, so `driver: api` is added without changing any other field).

- [ ] **Step 7: Commit**

```bash
git add pipelines/transcribe_notes/agent_submit.py pipelines/transcribe_notes/transcribe_notes.py tests/pipelines/transcribe_notes/test_agent_submit.py
git commit -m "feat: implement submit orchestration with provenance and auto-stage"
```

---

## Task 7: `--submit`/`--bootstrap` CLI wiring and end-to-end test

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_notes.py` (`main()`)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py` (extend)

**Interfaces:**
- Consumes: `submit_doc` (Task 6); `load_manifest`, `agent_work_dir` (Task 2/3).
- Produces: `python -m pipelines.transcribe_notes.transcribe_notes --submit <run-id> --notes-subdir <dir>` and `--bootstrap <run-id>`, both runnable from the CLI.

- [ ] **Step 1: Write the failing end-to-end test**

```python
# append to tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
import json


class TestSubmitAndBootstrapCLI(unittest.TestCase):
    def test_bootstrap_prints_contract_text(self):
        with tempfile.TemporaryDirectory() as hub:
            env = dict(os.environ)
            result = subprocess.run(
                [sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                 "--notes-subdir", "x", "--bootstrap", "test-run"],
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Agent output", result.stdout)
            self.assertIn("submit", result.stdout)

    def test_collect_then_submit_end_to_end_with_no_network(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            _write_minimal_pdf(os.path.join(notes_dir, "doc.pdf"))
            env = dict(os.environ)
            env.pop("GEMINI_API_KEY", None)
            env.pop("PAID_GEMINI_KEY", None)

            collect = subprocess.run(
                [sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                 "--notes-subdir", "notes", "--driver", "agent", "--collect", "--run-id", "e2e"],
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub}, capture_output=True, text=True,
            )
            self.assertEqual(collect.returncode, 0, msg=collect.stderr)

            run_dir = os.path.join(hub, ".agent_work", "e2e")
            doc_slug = os.listdir(run_dir)[0]
            doc_dir = os.path.join(run_dir, doc_slug)
            manifest_path = os.path.join(doc_dir, "manifest.json")
            with open(manifest_path, encoding="utf-8") as f:
                entries = json.load(f)
            self.assertEqual(len(entries), 1)
            task_id = entries[0]["task_id"]
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace(
                    "## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nTranscribed text.\n",
                ))

            submit = subprocess.run(
                [sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                 "--notes-subdir", "notes", "--submit", "e2e"],
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub}, capture_output=True, text=True,
            )
            self.assertEqual(submit.returncode, 0, msg=submit.stderr)
            md_path = os.path.join(notes_dir, "doc.md")
            self.assertTrue(os.path.exists(md_path))
            with open(md_path, encoding="utf-8") as f:
                written = f.read()
            self.assertIn("Transcribed text.", written)
            self.assertIn("driver: agent", written)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py -k "BootstrapCLI or end_to_end" -v`
Expected: FAIL — `--submit`/`--bootstrap` are not recognized arguments yet.

- [ ] **Step 3: Wire `--submit` and `--bootstrap` in `main()`**

Add the arguments:

```python
    parser.add_argument("--submit", default=None, metavar="RUN_ID", help="Validate filled task cards for this run and write through.")
    parser.add_argument("--bootstrap", default=None, metavar="RUN_ID", help="Print the agent's operating contract for this run.")
```

Add the `--bootstrap` branch (before the `--collect` branch, since it needs no PDF discovery at all):

```python
    if args.bootstrap:
        print(f"""Agent-driven transcription contract for run '{args.bootstrap}':

1. Open each document's directory under .agent_work/{args.bootstrap}/<doc-slug>/.
2. Read worklist.md to see which task cards are pending.
3. For each pending task-NNNN.md: read every page's image and prompt in
   the card, then fill ONLY the "Agent output" section at the bottom with
   one "--- PAGE <number> ---" section per page, in order, using exactly
   the page numbers the card lists. Never edit any other file or section.
4. For a tier-3 card with more than one page: only the first page has
   real prior-page context supplied. For every later page in that same
   card, carry forward your own transcription of the card's earlier
   pages as continuity context.
5. Once you've filled one or more cards, run:
   python -m pipelines.transcribe_notes.transcribe_notes --notes-subdir <dir> --submit {args.bootstrap}
6. If a card comes back marked "bounced: <reason>" in worklist.md, redo
   only that card in place and re-run step 5.
7. Stop once worklist.md shows nothing "pending"/"filled" left for this run.
""")
        return
```

Add the `--submit` branch, after `pdf_paths = discover_pdf_files(...)` and its empty-list check, but before `client = get_gemini_client()`:

```python
    if args.submit:
        from pipelines.transcribe_notes.agent_submit import submit_doc
        from pipelines.transcribe_notes.agent_work import agent_work_dir

        client = get_gemini_client()
        if client is None:
            sys.exit(1)
        run_dir = agent_work_dir(str(academic_hub_dir), args.submit)
        if not os.path.isdir(run_dir):
            print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
            sys.exit(1)
        pdf_by_basename = {os.path.splitext(os.path.basename(p))[0]: p for p in pdf_paths}
        lease = corpus_write_lock(
            [academic_hub_dir, academic_hub_dir / "academic_notes"], "notes PDF transcription (agent submit)",
        )
        with lease:
            for doc_slug in sorted(os.listdir(run_dir)):
                base_name = doc_slug.rsplit("--", 1)[0]
                pdf_path = pdf_by_basename.get(base_name)
                if pdf_path is None:
                    print(f"Skipping {doc_slug}: no matching PDF found under {args.notes_subdir}.")
                    continue
                status = submit_doc(str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug, pdf_path, client, args.model)
                print(f"[{doc_slug}] {status}")
        return
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Run the full test suite for this package**

Run: `python -m pytest tests/pipelines/transcribe_notes/ -v`
Expected: PASS, every test (pre-existing and new).

- [ ] **Step 6: Commit**

```bash
git add pipelines/transcribe_notes/transcribe_notes.py tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
git commit -m "feat: wire --submit/--bootstrap into the transcribe_notes CLI"
```

---

## After this plan: validation run (not a coded task)

Per the spec's "required before the first real run" and "open items":
run `--driver agent --collect` against the 7 held-back tier-3 microecon
documents with `--dry-run` reasoning done by hand first (confirm the
dry-run tier counts still match the status doc's numbers), then a real
`--collect` (no paid calls), hand-fill a few cards, `--submit`, and spot-check
the written `.md`/frontmatter before trusting the pipeline on the full
7-document/~125-page set. This is manual verification, not a plan task —
flag it to the user before running `--collect` against real course PDFs,
per "ask the user before any run estimated over $1" (this run is $0, but
it does touch real `academic_notes/` output paths).
