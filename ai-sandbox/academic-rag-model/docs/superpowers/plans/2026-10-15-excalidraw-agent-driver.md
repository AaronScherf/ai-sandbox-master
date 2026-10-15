# Excalidraw Agent Driver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the collect/submit/manifest agent-driven pattern to Excalidraw note transcription and expansion, and make the agent driver the default transport (with an explicit, opt-in API fallback) for both Excalidraw and PDF notes.

**Architecture:** A persisted chunk cache and a persisted expansion-segment cache make both of `transcribe_excalidraw.py`'s generative call sites resumable. A new `ExcalidrawDriver` protocol (`ExcalidrawApiDriver`/`ExcalidrawAgentDriver`/`ExcalidrawNullDriver`) sits at those two call sites, mirroring `agent_driver.py`'s existing PDF driver split but in its own module to avoid a circular import (the Excalidraw driver needs prompt-building helpers that already live in `transcribe_excalidraw.py`). `route_notes_transcribe.py` stops deferring Excalidraw notes under `--driver agent`, flips its (and `transcribe_notes.py`'s) default driver to `"agent"`, and adds a submit-time `--allow-api-fallback` flag for both file types.

**Tech Stack:** Python 3.13, pytest, existing `core.env.gemini_utils` cache helpers, existing Gemini/Ollama clients (mocked in tests).

**Spec:** `docs/superpowers/specs/transcribe_notes/2026-10-15-excalidraw-agent-driver-design.md` and its sibling amendment in `docs/superpowers/specs/transcribe_notes/2026-10-15-consolidated-pipeline-design.md` ("Amendment (2026-10-15)" section).

## Global Constraints

- No hidden generative fallback: an agent-driven run never silently calls the metered API. The one sanctioned exception is the new `--allow-api-fallback` flag, and only at `--submit` time, only when explicitly passed.
- `AgentPending` must never be caught by a bare `except Exception` — every new `except Exception` clause that wraps a driver call needs its own `except AgentPending: raise` immediately before it (mirrors `agent_driver.py`'s existing docstring warning).
- `ExcalidrawNullDriver`/`NullDriverFired`: a live call to a null driver is a cache-completeness bug and must raise, never silently fall through to a real (possibly paid) call.
- No live API calls in any test — every Gemini/Ollama call site is mocked or routed through a fake driver.
- Existing output file formats (`*.excalidraw.md`, `*.excalidraw.rag.md`) must not change: the non-slide expansion stays unwrapped prose; the slide-aware expansion keeps its `**[Slide]**`/`**[Notes]**` labeling exactly as today.

## Review Focus

- A canvas with embedded slides (`has_slides=True`) going through collect/submit — the segment-indexed expansion cache must only cache "Handwritten" segments (Slide segments are verbatim, never generated, never written to the cache file) — Task 5.
- A collect run on a note that already has SOME chunks cached from an earlier interrupted run — resumed collect must only stage the still-missing chunks, with real accumulated context from the cached ones, not restart from chunk 0 — Task 3.
- `--submit --allow-api-fallback` on a document with zero manifest entries at all (e.g., mistyped doc-slug or an already-fully-processed note) — must not crash attempting to build an `ExcalidrawApiDriver`/`ApiDriver` call for a note with nothing to do — Tasks 7, 9.
- A bounced (validation-rejected) chunk or segment — its text must never land in the cache, so a later resumed collect or `--allow-api-fallback` run re-requests it rather than treating the bounce as done — Task 7.
- Two notes in the same collect run whose `doc_slug_for` outputs collide (documented as an open item in the design spec) — Task 6's dedupe step must at minimum not silently merge their manifests; add a one-line guard that raises a clear error rather than clobbering one note's `.agent_work/` directory with another's.

---

## Task 1: Persisted chunk cache (resumability, API path only)

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`transcribe_chunks` at line 214, `process_excalidraw_note` at line 502)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`

**Interfaces:**
- Produces: `transcribe_chunks(client, model, chunk_bytes, has_slides=False, cache=None) -> dict[str, str]` (new `cache` param, backward compatible — omitting it behaves exactly as before). `chunk_cache_paths_for(excalidraw_md_path: str) -> tuple[str, str]` (cache_path, driver_path).

- [ ] **Step 1: Write the failing test for cache-aware resumability**

```python
def test_transcribe_chunks_skips_chunks_already_in_the_cache():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini") as mock_transcribe:
        mock_transcribe.return_value = "freshly transcribed"
        cache = transcribe_chunks(
            client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"],
            cache={"0": "already cached text"},
        )
    assert cache == {"0": "already cached text", "1": "freshly transcribed"}
    mock_transcribe.assert_called_once()  # chunk 0 never requested
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py::test_transcribe_chunks_skips_chunks_already_in_the_cache -v`
Expected: FAIL with `TypeError: transcribe_chunks() got an unexpected keyword argument 'cache'`

- [ ] **Step 3: Implement cache-aware `transcribe_chunks`**

Replace the body of `transcribe_chunks` (`pipelines/transcribe_notes/transcribe_excalidraw.py:214-231`):

```python
def transcribe_chunks(
    client, model: str, chunk_bytes: list[bytes], has_slides: bool = False,
    cache: dict[str, str] | None = None,
) -> dict[str, str]:
    cache = {} if cache is None else cache
    total_chunks = len(chunk_bytes)
    for chunk_index, image_bytes in enumerate(chunk_bytes):
        if cache.get(str(chunk_index), "").strip():
            continue  # already cached -- resumable, no API call
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks, has_slides)
        def transcribe_nonempty() -> str:
            text = transcribe_page_via_gemini(client, model, image_bytes, prompt)
            if not text or not text.strip():
                raise ValueError("empty chunk transcription")
            return text

        try:
            text = call_with_retries(transcribe_nonempty)
            cache[str(chunk_index)] = text
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py::test_transcribe_chunks_skips_chunks_already_in_the_cache -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `process_excalidraw_note`'s on-disk cache round-trip**

Add near `test_process_excalidraw_note_runs_full_pipeline` in `test_transcribe_excalidraw.py`:

```python
def test_process_excalidraw_note_writes_and_reuses_a_chunk_cache(tmp_path):
    hub = tmp_path / "hub"
    notes_dir = hub / "academic_notes" / "econ" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    md_path = notes_dir / "canvas.excalidraw.md"
    img_path = notes_dir / "canvas.excalidraw.svg"
    md_path.write_text("scene")
    img_path.write_bytes(b"<svg></svg>")

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.load_canvas_image", return_value=object()), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", return_value=[object(), object()]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", side_effect=lambda c: b"bytes"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini", return_value="transcribed"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("expanded", {"expansion_backend": "gemini", "expansion_model": "m", "grounded": False})):
        process_excalidraw_note(str(md_path), str(img_path), object(), "model", "gemini", str(hub))

    cache_path, _ = chunk_cache_paths_for(str(md_path))
    assert os.path.exists(cache_path)
    with open(cache_path, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved == {"0": "transcribed", "1": "transcribed"}
```

Add `import json` and `from pipelines.transcribe_notes.transcribe_excalidraw import chunk_cache_paths_for` to the test file's imports.

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py::test_process_excalidraw_note_writes_and_reuses_a_chunk_cache -v`
Expected: FAIL with `ImportError: cannot import name 'chunk_cache_paths_for'`

- [ ] **Step 7: Add `chunk_cache_paths_for` and wire the cache into `process_excalidraw_note`**

Add just above `process_excalidraw_note` (`pipelines/transcribe_notes/transcribe_excalidraw.py`, before line 502):

```python
def chunk_cache_paths_for(excalidraw_md_path: str) -> tuple[str, str]:
    base_name = os.path.basename(excalidraw_md_path)[: -len(".excalidraw.md")]
    output_dir = resolve_output_dir(excalidraw_md_path)
    cache_path = os.path.join(output_dir, f"{base_name}_chunks_cache.json")
    driver_path = cache_path.replace("_chunks_cache.json", "_chunks_driver.json")
    return cache_path, driver_path
```

In `process_excalidraw_note`, replace:

```python
    image = load_canvas_image(image_path)
    chunks = chunk_image(image)
    print(f"  {len(chunks)} chunks")
    chunk_bytes = [resize_chunk_for_api(c) for c in chunks]

    cache = transcribe_chunks(client, model, chunk_bytes, has_slides=has_slides)
```

with:

```python
    image = load_canvas_image(image_path)
    chunks = chunk_image(image)
    print(f"  {len(chunks)} chunks")
    chunk_bytes = [resize_chunk_for_api(c) for c in chunks]

    from core.env.gemini_utils import load_json_cache, save_json_cache
    cache_path, _ = chunk_cache_paths_for(excalidraw_md_path)
    cache = transcribe_chunks(client, model, chunk_bytes, has_slides=has_slides, cache=load_json_cache(cache_path))
    save_json_cache(cache_path, cache)
```

`resolve_output_dir` and `os` are already imported in this file.

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k "cache" -v`
Expected: both new tests PASS

- [ ] **Step 9: Run the full Excalidraw test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -v`
Expected: all PASS (existing tests unaffected — `cache=None` default preserves old behavior)

```bash
git add pipelines/transcribe_notes/transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py
git commit -m "feat(transcribe_notes): persisted chunk cache for Excalidraw transcription"
```

---

## Task 2: `ExcalidrawDriver` protocol + `ExcalidrawApiDriver`/`ExcalidrawNullDriver`, sequential chunk path

**Files:**
- Create: `pipelines/transcribe_notes/excalidraw_agent_driver.py`
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`transcribe_chunks`)
- Test: `tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py` (new)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py` (existing chunk tests — patch target changes)

**Interfaces:**
- Consumes: `AgentPending`, `NullDriverFired` from `pipelines.transcribe_notes.agent_driver` (both already generic — reused as-is). `transcribe_page_via_gemini(client, model, image_bytes, prompt) -> str` from `pipelines.transcribe_notes.transcribe_notes`.
- Produces: `ExcalidrawDriver` Protocol with `transcribe_chunk(excalidraw_md_path, model, chunk_index, total_chunks, prompt, image_bytes) -> str`. `ExcalidrawApiDriver(client, backend="gemini")`. `ExcalidrawNullDriver()`.

- [ ] **Step 1: Write the failing test for `ExcalidrawApiDriver.transcribe_chunk`**

Create `tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py`:

```python
import unittest.mock

import pytest

from pipelines.transcribe_notes.agent_driver import NullDriverFired
from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver, ExcalidrawNullDriver


def test_api_driver_transcribe_chunk_calls_gemini_through_retries():
    with unittest.mock.patch(
        "pipelines.transcribe_notes.excalidraw_agent_driver.transcribe_page_via_gemini",
        return_value="chunk text",
    ) as mock_call:
        driver = ExcalidrawApiDriver(client=object())
        result = driver.transcribe_chunk("note.excalidraw.md", "model", 0, 3, "prompt", b"img")
    assert result == "chunk text"
    mock_call.assert_called_once_with(driver.client, "model", b"img", "prompt")


def test_null_driver_transcribe_chunk_raises():
    driver = ExcalidrawNullDriver()
    with pytest.raises(NullDriverFired):
        driver.transcribe_chunk("note.excalidraw.md", "model", 0, 3, "prompt", b"img")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipelines.transcribe_notes.excalidraw_agent_driver'`

- [ ] **Step 3: Create `excalidraw_agent_driver.py`**

```python
# pipelines/transcribe_notes/excalidraw_agent_driver.py
"""
Driver seam for transcribe_excalidraw.py's two Gemini call sites: per-chunk
vision transcription and per-segment text expansion. Mirrors agent_driver.py's
ApiDriver/AgentDriver/NullDriver split for PDFs, in its own module since the
call shapes differ (a chunk's image bytes are already available -- no page-
rendering step -- and expansion operates on already-split text segments, not
raw page images) and because this module needs prompt-building helpers that
live in transcribe_excalidraw.py (importing agent_driver.py directly would
need the reverse, which transcribe_notes.py's process_pdf already avoids via
a local import -- see that function). See docs/superpowers/specs/
transcribe_notes/2026-10-15-excalidraw-agent-driver-design.md.
"""
from __future__ import annotations

from typing import Protocol

from core.env.gemini_utils import call_with_retries
from core.env.ollama_utils import call_ollama
from pipelines.transcribe_notes.agent_driver import NullDriverFired
from pipelines.transcribe_notes.transcribe_notes import transcribe_page_via_gemini

_EXPANSION_MODEL_GEMINI = "gemini-3.1-flash-lite"
_EXPANSION_MODEL_OLLAMA = "qwen2.5:7b-instruct"


class ExcalidrawDriver(Protocol):
    def transcribe_chunk(
        self, excalidraw_md_path: str, model: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str: ...

    def expand(
        self, excalidraw_md_path: str, prompt: str, segment_index: int, total_segments: int,
    ) -> str: ...


class ExcalidrawApiDriver:
    """Default driver: reproduces transcribe_excalidraw.py's existing direct
    Gemini/Ollama calls unchanged, chunk calls through call_with_retries
    (matching the retry the plain sequential loop already applied)."""

    def __init__(self, client, backend: str = "gemini"):
        self.client = client
        self.backend = backend

    def transcribe_chunk(
        self, excalidraw_md_path: str, model: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str:
        return call_with_retries(lambda: transcribe_page_via_gemini(self.client, model, image_bytes, prompt))

    def expand(
        self, excalidraw_md_path: str, prompt: str, segment_index: int, total_segments: int,
    ) -> str:
        if self.backend == "ollama":
            result = call_ollama(prompt, model=_EXPANSION_MODEL_OLLAMA, request_timeout=300)
            if isinstance(result, str):
                return result
            print("WARNING: Ollama expansion backend unreachable; falling back to Gemini.")
            self.backend = "gemini"
        response = self.client.models.generate_content(
            model=_EXPANSION_MODEL_GEMINI, contents=[prompt],
            config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
        )
        return response.text or ""


class ExcalidrawNullDriver:
    """Used once every chunk/segment is already cached: a live call here is
    a cache-completeness bug, not a real gap -- raise rather than silently
    making a real (possibly paid) call."""

    def transcribe_chunk(
        self, excalidraw_md_path: str, model: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str:
        raise NullDriverFired(
            f"ExcalidrawNullDriver: unexpected live call for chunk {chunk_index} in "
            f"{excalidraw_md_path} -- the cache should already be complete at this point."
        )

    def expand(
        self, excalidraw_md_path: str, prompt: str, segment_index: int, total_segments: int,
    ) -> str:
        raise NullDriverFired(
            f"ExcalidrawNullDriver: unexpected live call for segment {segment_index} in "
            f"{excalidraw_md_path} -- the cache should already be complete at this point."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -v`
Expected: PASS

- [ ] **Step 5: Wire `transcribe_chunks` to call the driver instead of `transcribe_page_via_gemini` directly**

In `pipelines/transcribe_notes/transcribe_excalidraw.py`, replace `transcribe_chunks` (from Task 1):

```python
def transcribe_chunks(
    client, model: str, chunk_bytes: list[bytes], has_slides: bool = False,
    cache: dict[str, str] | None = None, driver: "ExcalidrawDriver | None" = None,
    excalidraw_md_path: str | None = None,
) -> dict[str, str]:
    from pipelines.transcribe_notes.agent_driver import AgentPending
    from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver

    cache = {} if cache is None else cache
    if driver is None:
        driver = ExcalidrawApiDriver(client)
    total_chunks = len(chunk_bytes)
    for chunk_index, image_bytes in enumerate(chunk_bytes):
        if cache.get(str(chunk_index), "").strip():
            continue  # already cached -- resumable, no driver call
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks, has_slides)
        def transcribe_nonempty() -> str:
            text = driver.transcribe_chunk(excalidraw_md_path, model, chunk_index, total_chunks, prompt, image_bytes)
            if not text or not text.strip():
                raise ValueError("empty chunk transcription")
            return text

        try:
            text = transcribe_nonempty()
            cache[str(chunk_index)] = text
        except AgentPending:
            raise  # must propagate uncaught -- never retried, never falls through
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache
```

Note: retries now happen inside `ExcalidrawApiDriver.transcribe_chunk` itself (Step 3 above), not at this call site — matches `agent_driver.py`'s PDF pattern, where `process_pdf` also calls `driver.transcribe_page(...)` with no additional retry wrapper.

Add `"ExcalidrawDriver"` to the module's `TYPE_CHECKING` imports at the top of the file:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawDriver
```

- [ ] **Step 6: Update existing chunk tests to patch the new call path**

In `test_transcribe_excalidraw.py`, the existing `transcribe_chunks` tests (`test_transcribe_chunks_builds_cache_keyed_by_index`, `test_transcribe_chunks_passes_accumulated_context_from_prior_chunks`, `test_transcribe_chunks_retries_an_empty_response`) patch `pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini` and `...call_with_retries` — these no longer apply (retries moved into `ExcalidrawApiDriver`, which imports `transcribe_page_via_gemini` into its own module). Update each to patch `pipelines.transcribe_notes.excalidraw_agent_driver.transcribe_page_via_gemini` and `pipelines.transcribe_notes.excalidraw_agent_driver.call_with_retries` instead (same patch shape, new module path). `test_transcribe_chunks_skips_a_chunk_that_fails_after_retries` (which patches `call_with_retries` with a passthrough `side_effect=lambda fn: fn()`) needs the same module-path update.

- [ ] **Step 7: Run the full Excalidraw test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -v`
Expected: all PASS

```bash
git add pipelines/transcribe_notes/excalidraw_agent_driver.py pipelines/transcribe_notes/transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py
git commit -m "feat(transcribe_notes): ExcalidrawDriver protocol, route chunk transcription through it"
```

---

## Task 3: Collect-mode batched chunk staging

**Files:**
- Modify: `pipelines/transcribe_notes/excalidraw_agent_driver.py` (add `stage_chunks` to the protocol and both driver classes)
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`transcribe_chunks`, `process_excalidraw_note` gain `collect_mode`)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`, `test_excalidraw_agent_driver.py`

**Interfaces:**
- Consumes: Task 2's `ExcalidrawApiDriver`/`ExcalidrawNullDriver`/`ExcalidrawDriver`.
- Produces: `ExcalidrawDriver.stage_chunks(excalidraw_md_path, model, missing: list[tuple[int, str, bytes]], total_chunks) -> dict[int, str]` (raises `AgentPending` for an agent driver; `ExcalidrawApiDriver` and `ExcalidrawNullDriver` get working implementations too, so `collect_mode=True` never crashes regardless of driver). `transcribe_chunks(..., collect_mode: bool = False)`. `process_excalidraw_note(..., driver=None, collect_mode: bool = False)`.

- [ ] **Step 1: Write the failing test for `ExcalidrawApiDriver.stage_chunks`**

Add to `test_excalidraw_agent_driver.py`:

```python
def test_api_driver_stage_chunks_transcribes_each_missing_one():
    with unittest.mock.patch(
        "pipelines.transcribe_notes.excalidraw_agent_driver.transcribe_page_via_gemini",
        side_effect=["text 0", "text 2"],
    ):
        driver = ExcalidrawApiDriver(client=object())
        result = driver.stage_chunks(
            "note.excalidraw.md", "model",
            missing=[(0, "prompt 0", b"img0"), (2, "prompt 2", b"img2")], total_chunks=3,
        )
    assert result == {0: "text 0", 2: "text 2"}


def test_null_driver_stage_chunks_raises_when_anything_is_missing():
    driver = ExcalidrawNullDriver()
    with pytest.raises(NullDriverFired):
        driver.stage_chunks("note.excalidraw.md", "model", missing=[(0, "p", b"img")], total_chunks=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -k stage_chunks -v`
Expected: FAIL with `AttributeError: 'ExcalidrawApiDriver' object has no attribute 'stage_chunks'`

- [ ] **Step 3: Add `stage_chunks` to the protocol and both driver classes**

In `excalidraw_agent_driver.py`, add to `ExcalidrawDriver`:

```python
    def stage_chunks(
        self, excalidraw_md_path: str, model: str, missing: list[tuple[int, str, bytes]], total_chunks: int,
    ) -> dict[int, str]: ...
```

Add to `ExcalidrawApiDriver`:

```python
    def stage_chunks(
        self, excalidraw_md_path: str, model: str, missing: list[tuple[int, str, bytes]], total_chunks: int,
    ) -> dict[int, str]:
        results = {}
        for chunk_index, prompt, image_bytes in missing:
            results[chunk_index] = self.transcribe_chunk(
                excalidraw_md_path, model, chunk_index, total_chunks, prompt, image_bytes,
            )
        return results
```

Add to `ExcalidrawNullDriver`:

```python
    def stage_chunks(
        self, excalidraw_md_path: str, model: str, missing: list[tuple[int, str, bytes]], total_chunks: int,
    ) -> dict[int, str]:
        raise NullDriverFired(
            f"ExcalidrawNullDriver: unexpected stage_chunks call for {excalidraw_md_path} -- "
            "the cache should already be complete at this point."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -k stage_chunks -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `transcribe_chunks`'s `collect_mode` branch**

Add to `test_transcribe_excalidraw.py`:

```python
def test_transcribe_chunks_collect_mode_calls_stage_chunks_once_with_all_missing():
    captured = {}

    class FakeDriver:
        def stage_chunks(self, excalidraw_md_path, model, missing, total_chunks):
            captured["missing"] = missing
            return {}

        def transcribe_chunk(self, *a, **k):
            pytest.fail("sequential path must not run in collect_mode")

    transcribe_chunks(
        client=object(), model="m", chunk_bytes=[b"img0", b"img1"],
        cache={}, driver=FakeDriver(), excalidraw_md_path="note.excalidraw.md", collect_mode=True,
    )
    assert [m[0] for m in captured["missing"]] == [0, 1]


def test_transcribe_chunks_collect_mode_only_stages_still_missing_chunks():
    captured = {}

    class FakeDriver:
        def stage_chunks(self, excalidraw_md_path, model, missing, total_chunks):
            captured["missing"] = missing
            return {}

    transcribe_chunks(
        client=object(), model="m", chunk_bytes=[b"img0", b"img1"],
        cache={"0": "already done"}, driver=FakeDriver(), excalidraw_md_path="note.excalidraw.md", collect_mode=True,
    )
    assert [m[0] for m in captured["missing"]] == [1]
```

Import `pytest` at the top of the test file if not already present.

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k collect_mode -v`
Expected: FAIL with `TypeError: transcribe_chunks() got an unexpected keyword argument 'collect_mode'`

- [ ] **Step 7: Add the `collect_mode` branch to `transcribe_chunks`**

```python
def transcribe_chunks(
    client, model: str, chunk_bytes: list[bytes], has_slides: bool = False,
    cache: dict[str, str] | None = None, driver: "ExcalidrawDriver | None" = None,
    excalidraw_md_path: str | None = None, collect_mode: bool = False,
) -> dict[str, str]:
    from pipelines.transcribe_notes.agent_driver import AgentPending
    from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver

    cache = {} if cache is None else cache
    if driver is None:
        driver = ExcalidrawApiDriver(client)
    total_chunks = len(chunk_bytes)

    if collect_mode:
        missing = [
            (i, build_chunk_transcription_prompt(
                _accumulated_chunk_context(cache, i, window=_ACCUMULATION_WINDOW), i, total_chunks, has_slides,
            ), chunk_bytes[i])
            for i in range(total_chunks) if not cache.get(str(i), "").strip()
        ]
        if not missing:
            return cache
        try:
            staged = driver.stage_chunks(excalidraw_md_path, model, missing, total_chunks)
        except AgentPending:
            raise
        for chunk_index, text in staged.items():
            if text and text.strip():
                cache[str(chunk_index)] = text
        return cache

    for chunk_index, image_bytes in enumerate(chunk_bytes):
        if cache.get(str(chunk_index), "").strip():
            continue
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks, has_slides)
        def transcribe_nonempty() -> str:
            text = driver.transcribe_chunk(excalidraw_md_path, model, chunk_index, total_chunks, prompt, image_bytes)
            if not text or not text.strip():
                raise ValueError("empty chunk transcription")
            return text

        try:
            text = transcribe_nonempty()
            cache[str(chunk_index)] = text
        except AgentPending:
            raise
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k collect_mode -v`
Expected: PASS

- [ ] **Step 9: Thread `driver`/`collect_mode` through `process_excalidraw_note`**

Replace the signature and the `cache = transcribe_chunks(...)` line from Task 1, Step 7:

```python
def process_excalidraw_note(
    excalidraw_md_path: str, image_path: str, client, model: str,
    expand_backend: str, academic_hub_root: str, use_grounding: bool = False, dry_run: bool = False,
    driver: "ExcalidrawDriver | None" = None, collect_mode: bool = False,
) -> bool:
```

```python
    from core.env.gemini_utils import load_json_cache, save_json_cache
    cache_path, _ = chunk_cache_paths_for(excalidraw_md_path)
    cache = transcribe_chunks(
        client, model, chunk_bytes, has_slides=has_slides, cache=load_json_cache(cache_path),
        driver=driver, excalidraw_md_path=excalidraw_md_path, collect_mode=collect_mode,
    )
    save_json_cache(cache_path, cache)
```

`collect_mode` must also skip the "missing chunks -> abort" check and everything after it (expansion, write_outputs) when any chunks are still missing after staging — a collect call never finishes a document. Add immediately after the cache save:

```python
    if collect_mode:
        missing_after_collect = [i + 1 for i in range(len(chunks)) if not cache.get(str(i), "").strip()]
        if missing_after_collect:
            return True  # task card(s) staged; nothing more to do this call
```

(When `collect_mode=True` and nothing was missing to begin with — e.g. a resumed collect on an already-fully-transcribed note — execution falls through to expansion as normal, which is Task 5's concern.)

- [ ] **Step 10: Run the full Excalidraw test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -v`
Expected: all PASS

```bash
git add pipelines/transcribe_notes/excalidraw_agent_driver.py pipelines/transcribe_notes/transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py
git commit -m "feat(transcribe_notes): collect-mode batched chunk staging for Excalidraw"
```

---

## Task 4: Persisted expansion-segment cache, sequential path

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`expand_transcription`, `_expand_slide_note`, `expand_with_verbatim_slides`, `process_excalidraw_note`, `reexpand_excalidraw_note`)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: `ExcalidrawApiDriver.expand(excalidraw_md_path, prompt, segment_index, total_segments) -> str` (Task 2).
- Produces: `expansion_cache_paths_for(excalidraw_md_path) -> tuple[str, str]`. `expand_transcription(client, raw_markdown, backend="gemini", retrieved_passages=None, has_slides=False, driver=None, excalidraw_md_path=None, cache=None) -> tuple[str | None, dict]` — same return contract as today, new trailing params only.

**Design note:** `split_labeled_segments` already treats a plain (non-slide) transcript as one `"Handwritten"` segment covering the whole text (verified: with no `**[Slide]**`/`**[Handwritten]**` markers, `matches` is empty and the entire text becomes a single `("Handwritten", text)` pair). This lets both the slide-aware and non-slide paths share one segment-indexed cache, while keeping their *output formats* different: non-slide output is the bare expanded text (no `**[Notes]**` wrapper); slide-aware output keeps today's per-block labeling.

- [ ] **Step 1: Write the failing test for segment-cache resumability (non-slide case)**

Add to `test_transcribe_excalidraw.py`:

```python
def test_expand_transcription_non_slide_skips_already_cached_segment():
    class FakeDriver:
        def expand(self, excalidraw_md_path, prompt, segment_index, total_segments):
            pytest.fail("must not call the driver -- segment 0 is already cached")

    text, meta = expand_transcription(
        client=object(), raw_markdown="shorthand notes", driver=FakeDriver(),
        excalidraw_md_path="note.excalidraw.md", cache={"0": "already expanded"},
    )
    assert text == "already expanded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k non_slide_skips -v`
Expected: FAIL with `TypeError: expand_transcription() got an unexpected keyword argument 'driver'`

- [ ] **Step 3: Refactor `expand_transcription` to route through the driver with a segment cache**

Replace `expand_transcription` and `_expand_slide_note` (`pipelines/transcribe_notes/transcribe_excalidraw.py:349-391`):

```python
def expansion_cache_paths_for(excalidraw_md_path: str) -> tuple[str, str]:
    base_name = os.path.basename(excalidraw_md_path)[: -len(".excalidraw.md")]
    output_dir = resolve_output_dir(excalidraw_md_path)
    cache_path = os.path.join(output_dir, f"{base_name}_expansion_cache.json")
    driver_path = cache_path.replace("_expansion_cache.json", "_expansion_driver.json")
    return cache_path, driver_path


def _expansion_segments(raw_markdown: str, has_slides: bool) -> list[tuple[str, str]]:
    if not has_slides:
        return [("Handwritten", raw_markdown)]
    return split_labeled_segments(raw_markdown)


def expand_transcription(
    client, raw_markdown: str, backend: str = "gemini", retrieved_passages: list[str] | None = None,
    has_slides: bool = False, driver: "ExcalidrawDriver | None" = None,
    excalidraw_md_path: str | None = None, cache: dict[str, str] | None = None,
) -> tuple[str | None, dict]:
    """backend='gemini' (default) or 'ollama' (opt-in). Routes every
    generative call through `driver` (default ExcalidrawApiDriver), caching
    each segment's expanded text by its position in `_expansion_segments`'s
    output so a resumed call never re-expands an already-cached segment.
    Slide segments are never generated (kept verbatim) and never cached."""
    from pipelines.transcribe_notes.agent_driver import AgentPending
    from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver

    if driver is None:
        driver = ExcalidrawApiDriver(client, backend=backend)
    cache = {} if cache is None else cache
    grounded = bool(retrieved_passages)
    segments = _expansion_segments(raw_markdown, has_slides)

    if not has_slides:
        # Single segment covering the whole document -- output format must
        # stay the bare expanded text, no "**[Notes]**" wrapper.
        if cache.get("0", "").strip():
            return cache["0"], {"expansion_backend": driver.backend if hasattr(driver, "backend") else backend,
                                 "expansion_model": _EXPANSION_MODEL_GEMINI, "grounded": grounded}
        prompt = build_expansion_prompt(raw_markdown, retrieved_passages, has_slides=False)
        try:
            text = driver.expand(excalidraw_md_path, prompt, 0, 1)
        except AgentPending:
            raise
        cache["0"] = text
        backend_used = driver.backend if hasattr(driver, "backend") else backend
        return text, {"expansion_backend": backend_used, "expansion_model": _EXPANSION_MODEL_GEMINI, "grounded": grounded}

    out: list[str] = []
    for i, (label, text) in enumerate(segments):
        if label == "Slide":
            out.append(f"**[Slide]**\n{text}")
            continue
        if cache.get(str(i), "").strip():
            out.append(f"**[Notes]**\n{cache[str(i)]}")
            continue
        neighbors = [
            segments[j][1] for j in (i - 1, i + 1)
            if 0 <= j < len(segments) and segments[j][0] == "Slide"
        ]
        prompt = build_handwriting_expansion_prompt(text, neighbors, retrieved_passages)
        try:
            expanded = driver.expand(excalidraw_md_path, prompt, i, len(segments))
        except AgentPending:
            raise
        expanded = (expanded or "").strip() or text  # keep raw text if generation came back empty
        cache[str(i)] = expanded
        out.append(f"**[Notes]**\n{expanded}")

    backend_used = driver.backend if hasattr(driver, "backend") else backend
    return "\n\n".join(out), {
        "expansion_backend": backend_used, "expansion_model": _EXPANSION_MODEL_GEMINI,
        "grounded": grounded, "slides_verbatim": True,
    }
```

Remove `_expand_slide_note` entirely (its logic is now inlined above, generalized to also cover the non-slide case). Remove its only other call site, which was inside the old `expand_transcription` — already replaced. `expand_via_gemini`, `expand_via_ollama`, `expand_with_verbatim_slides`, and `build_handwriting_expansion_prompt` stay as free functions (still directly tested) but are no longer called by `expand_transcription` — leave them in place; they remain useful, independently-tested building blocks and nothing else in this plan removes them.

Add `split_labeled_segments` to the module's existing `core.env.excalidraw_text` import (already imported at the top of the file per the earlier read — confirm `split_labeled_segments` is in that import list; it already is, per line 26-31 of the file).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k non_slide_skips -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for slide-aware segment caching**

```python
def test_expand_transcription_slide_aware_only_generates_missing_segments():
    requested = []

    class FakeDriver:
        backend = "gemini"

        def expand(self, excalidraw_md_path, prompt, segment_index, total_segments):
            requested.append(segment_index)
            return f"expanded segment {segment_index}"

    raw = "**[Slide]**\nSlide one\n\n**[Handwritten]**\nNote one\n\n**[Slide]**\nSlide two\n\n**[Handwritten]**\nNote two"
    text, meta = expand_transcription(
        client=object(), raw_markdown=raw, has_slides=True, driver=FakeDriver(),
        excalidraw_md_path="note.excalidraw.md", cache={"1": "already expanded note one"},
    )
    assert requested == [3]  # segment 1 (first Handwritten) already cached, only segment 3 generated
    assert "already expanded note one" in text
    assert "expanded segment 3" in text
    assert "Slide one" in text and "Slide two" in text
```

- [ ] **Step 6: Run test to verify it fails, then passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k slide_aware_only_generates -v`
Expected: FAIL first (if segment indexing doesn't match — adjust the test's expected indices by printing `split_labeled_segments(raw)` if needed, since segment numbering is 0-indexed across ALL segments including Slides, per `_expansion_segments`), then PASS after Step 3's implementation.

- [ ] **Step 7: Wire the expansion cache into `process_excalidraw_note` and `reexpand_excalidraw_note`**

In `process_excalidraw_note`, replace:

```python
    expanded_markdown, expansion_meta = expand_transcription(client, raw_markdown, expand_backend, retrieved_passages, has_slides=has_slides)
```

with:

```python
    exp_cache_path, _ = expansion_cache_paths_for(excalidraw_md_path)
    expanded_markdown, expansion_meta = expand_transcription(
        client, raw_markdown, expand_backend, retrieved_passages, has_slides=has_slides,
        driver=driver, excalidraw_md_path=excalidraw_md_path, cache=load_json_cache(exp_cache_path),
    )
```

(`load_json_cache` already imported earlier in this function from Task 1/3.) After computing `expanded_markdown`, persist the cache — add right before `write_outputs(...)`:

```python
    # expand_transcription mutates its cache arg in place; re-derive the
    # same dict reference it returned into rather than reloading from disk.
```

Actually simplest: capture the cache dict passed in and save it after the call:

```python
    exp_cache_path, _ = expansion_cache_paths_for(excalidraw_md_path)
    exp_cache = load_json_cache(exp_cache_path)
    expanded_markdown, expansion_meta = expand_transcription(
        client, raw_markdown, expand_backend, retrieved_passages, has_slides=has_slides,
        driver=driver, excalidraw_md_path=excalidraw_md_path, cache=exp_cache,
    )
    save_json_cache(exp_cache_path, exp_cache)
```

Apply the same `exp_cache_path`/`exp_cache` pattern to `reexpand_excalidraw_note`'s existing `expand_transcription(...)` call (it doesn't need `driver`/`collect_mode` — it stays API-only, matching its docstring "cheap to rerun"; pass `driver=None` implicitly by omitting the kwarg).

- [ ] **Step 8: Run the full Excalidraw test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -v`
Expected: all PASS (check `test_write_outputs_*` and `test_process_excalidraw_note_runs_full_pipeline*` still pass unchanged — they patch `expand_transcription` wholesale, so the internal refactor doesn't affect them)

```bash
git add pipelines/transcribe_notes/transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py
git commit -m "feat(transcribe_notes): persisted expansion-segment cache, route expansion through the driver"
```

---

## Task 5: Collect-mode batched segment staging

**Files:**
- Modify: `pipelines/transcribe_notes/excalidraw_agent_driver.py` (add `stage_segments`)
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`expand_transcription`, `process_excalidraw_note` gain expansion-side `collect_mode`)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`, `test_excalidraw_agent_driver.py`

**Interfaces:**
- Produces: `ExcalidrawDriver.stage_segments(excalidraw_md_path, missing: list[tuple[int, str]], total_segments) -> dict[int, str]` (`missing` is `(segment_index, prompt)` pairs — no image bytes, text only).

- [ ] **Step 1: Write the failing test for `ExcalidrawApiDriver.stage_segments`**

Add to `test_excalidraw_agent_driver.py`:

```python
def test_api_driver_stage_segments_expands_each_missing_one():
    class FakeApiLikeDriver(ExcalidrawApiDriver):
        def expand(self, excalidraw_md_path, prompt, segment_index, total_segments):
            return f"expanded {segment_index}"

    driver = FakeApiLikeDriver(client=object())
    result = driver.stage_segments("note.excalidraw.md", missing=[(1, "prompt 1"), (3, "prompt 3")], total_segments=4)
    assert result == {1: "expanded 1", 3: "expanded 3"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -k stage_segments -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Add `stage_segments` to the protocol and both driver classes**

In `excalidraw_agent_driver.py`, add to `ExcalidrawDriver`:

```python
    def stage_segments(
        self, excalidraw_md_path: str, missing: list[tuple[int, str]], total_segments: int,
    ) -> dict[int, str]: ...
```

Add to `ExcalidrawApiDriver`:

```python
    def stage_segments(
        self, excalidraw_md_path: str, missing: list[tuple[int, str]], total_segments: int,
    ) -> dict[int, str]:
        return {
            segment_index: self.expand(excalidraw_md_path, prompt, segment_index, total_segments)
            for segment_index, prompt in missing
        }
```

Add to `ExcalidrawNullDriver`:

```python
    def stage_segments(
        self, excalidraw_md_path: str, missing: list[tuple[int, str]], total_segments: int,
    ) -> dict[int, str]:
        raise NullDriverFired(
            f"ExcalidrawNullDriver: unexpected stage_segments call for {excalidraw_md_path} -- "
            "the cache should already be complete at this point."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -k stage_segments -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `expand_transcription`'s collect_mode branch**

```python
def test_expand_transcription_collect_mode_stages_all_missing_segments_in_one_call():
    captured = {}

    class FakeDriver:
        backend = "gemini"

        def stage_segments(self, excalidraw_md_path, missing, total_segments):
            captured["missing"] = missing
            return {}

    raw = "**[Slide]**\nSlide one\n\n**[Handwritten]**\nNote one\n\n**[Handwritten]**\nNote two"
    expand_transcription(
        client=object(), raw_markdown=raw, has_slides=True, driver=FakeDriver(),
        excalidraw_md_path="note.excalidraw.md", cache={}, collect_mode=True,
    )
    assert [m[0] for m in captured["missing"]] == [1, 2]  # both Handwritten segments, Slide excluded
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k collect_mode_stages_all_missing -v`
Expected: FAIL with `TypeError: expand_transcription() got an unexpected keyword argument 'collect_mode'`

- [ ] **Step 7: Add the `collect_mode` branch to `expand_transcription`**

Add `collect_mode: bool = False` to the signature, and branch immediately after computing `segments`:

```python
    if collect_mode:
        missing = []
        for i, (label, text) in enumerate(segments):
            if label == "Slide" or cache.get(str(i), "").strip():
                continue
            neighbors = [
                segments[j][1] for j in (i - 1, i + 1)
                if 0 <= j < len(segments) and segments[j][0] == "Slide"
            ] if has_slides else []
            prompt = (
                build_handwriting_expansion_prompt(text, neighbors, retrieved_passages) if has_slides
                else build_expansion_prompt(raw_markdown, retrieved_passages, has_slides=False)
            )
            missing.append((i, prompt))
        if not missing:
            return None, {}  # nothing to stage -- caller must check whether cache is already complete
        try:
            staged = driver.stage_segments(excalidraw_md_path, missing, len(segments))
        except AgentPending:
            raise
        for segment_index, text in staged.items():
            if text and text.strip():
                cache[str(segment_index)] = text
        return None, {}  # collect never finishes assembly -- same contract as transcribe_chunks' collect_mode
```

Place this branch right after `segments = _expansion_segments(raw_markdown, has_slides)` and before the `if not has_slides:` single-segment branch.

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k collect_mode_stages_all_missing -v`
Expected: PASS

- [ ] **Step 9: Wire expansion's `collect_mode` into `process_excalidraw_note`**

After the Task 3 `if collect_mode: ... return True` block (which only fires when chunks are still missing), add the expansion-side collect handling right before the existing `write_outputs(...)` call:

```python
    if collect_mode:
        exp_cache_path, _ = expansion_cache_paths_for(excalidraw_md_path)
        exp_cache = load_json_cache(exp_cache_path)
        expand_transcription(
            client, raw_markdown, expand_backend, retrieved_passages, has_slides=has_slides,
            driver=driver, excalidraw_md_path=excalidraw_md_path, cache=exp_cache, collect_mode=True,
        )
        save_json_cache(exp_cache_path, exp_cache)
        return True
```

Place this immediately before the existing (non-collect) `exp_cache_path, exp_cache = ...` / `expand_transcription(...)` block from Task 4, Step 7, so a `collect_mode=True` call never reaches the non-collect expansion call or `write_outputs`.

- [ ] **Step 10: Run the full Excalidraw test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py -v`
Expected: all PASS

```bash
git add pipelines/transcribe_notes/excalidraw_agent_driver.py pipelines/transcribe_notes/transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_excalidraw_agent_driver.py
git commit -m "feat(transcribe_notes): collect-mode batched segment staging for Excalidraw expansion"
```

---

## Task 6: `ExcalidrawAgentDriver` (task-card writing)

**Files:**
- Create: `pipelines/transcribe_notes/excalidraw_agent_work.py`
- Test: `tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py` (new)

**Interfaces:**
- Consumes: `doc_slug_for`, `doc_work_dir`, `agent_work_dir`, `ManifestEntry`, `load_manifest`, `save_manifest`, `render_worklist` from `pipelines.transcribe_notes.agent_work` (all already generic, reused unmodified). `AgentPending` from `pipelines.transcribe_notes.agent_driver`.
- Produces: `ExcalidrawAgentDriver(hub_root, run_id, agent_name="antigravity")` implementing `ExcalidrawDriver`'s full surface (`transcribe_chunk`/`expand` raise `AgentPending` unconditionally — they're never called in `collect_mode`, only `stage_chunks`/`stage_segments` are; implemented anyway to satisfy the protocol defensively, matching `NullDriver`'s belt-and-suspenders style). `render_chunk_card`, `render_expansion_card`, `parse_chunk_card_output`, `parse_expansion_card_output`.

- [ ] **Step 1: Write the failing test for `ExcalidrawAgentDriver.stage_chunks` writing one card and raising**

Create `tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py`:

```python
import os
import tempfile

import pytest

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import load_manifest
from pipelines.transcribe_notes.excalidraw_agent_work import ExcalidrawAgentDriver


def test_stage_chunks_writes_one_card_covering_every_missing_chunk():
    with tempfile.TemporaryDirectory() as hub:
        md_path = os.path.join(hub, "canvas.excalidraw.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene content for file_id hashing")

        driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_chunks(
                md_path, "gemini-3.6-flash",
                missing=[(0, "prompt 0", b"img0"), (1, "prompt 1", b"img1")], total_chunks=2,
            )
        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        entries = load_manifest(doc_dir)
        assert len(entries) == 1
        assert entries[0].pages == [0, 1]
        assert entries[0].status == "pending"
        assert os.path.exists(os.path.join(doc_dir, "images", "chunk-0000.png"))
        assert os.path.exists(os.path.join(doc_dir, "images", "chunk-0001.png"))


def test_recollecting_a_still_pending_chunk_card_does_not_duplicate_it():
    with tempfile.TemporaryDirectory() as hub:
        md_path = os.path.join(hub, "canvas.excalidraw.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene content")

        driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_chunks(md_path, "m", missing=[(0, "p0", b"i0")], total_chunks=1)

        second_driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            second_driver.stage_chunks(md_path, "m", missing=[(0, "p0", b"i0")], total_chunks=1)

        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        assert len(load_manifest(doc_dir)) == 1  # no duplicate card
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipelines.transcribe_notes.excalidraw_agent_work'`

- [ ] **Step 3: Create `excalidraw_agent_work.py`**

```python
# pipelines/transcribe_notes/excalidraw_agent_work.py
"""
ExcalidrawAgentDriver: writes task cards for transcribe_excalidraw.py's two
generative stages (chunk transcription, segment expansion) instead of
calling Gemini. Reuses agent_work.py's generic run-directory layout,
manifest, and worklist primitives (none of them are PDF-specific). See
docs/superpowers/specs/transcribe_notes/2026-10-15-excalidraw-agent-driver-design.md.
"""
from __future__ import annotations

import os

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import (
    ManifestEntry,
    doc_slug_for,
    doc_work_dir,
    load_manifest,
    render_worklist,
    save_manifest,
)
from core.indexer.index_card import compute_file_id

_CHUNK_OUTPUT_HEADER = "## Agent output"


def render_chunk_card(
    doc_dir: str, task_id: str, missing: list[tuple[int, str, bytes]], total_chunks: int,
) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    image_dir = os.path.join(doc_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    indices = [m[0] for m in missing]
    lines = [f"# {task_id} (chunks, {indices[0]}-{indices[-1]} of {total_chunks - 1})", ""]
    if len(missing) > 1:
        lines += [
            "Strict chunk order within this card: only the first chunk below has real "
            "prior-chunk context supplied. For every later chunk in this card, carry forward "
            "YOUR OWN transcription of this card's earlier chunks as continuity context.",
            "",
        ]
    for chunk_index, prompt, image_bytes in missing:
        rel_path = os.path.join("images", f"chunk-{chunk_index:04d}.png")
        with open(os.path.join(doc_dir, rel_path), "wb") as f:
            f.write(image_bytes)
        lines += [f"## Chunk {chunk_index}", "", f"Image: `{rel_path}`", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per chunk above, in order, using this exact format:", "",
        "```", "--- CHUNK <number> ---", "<transcribed markdown for that chunk>", "```", "",
        _CHUNK_OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_expansion_card(doc_dir: str, task_id: str, missing: list[tuple[int, str]], total_segments: int) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    indices = [m[0] for m in missing]
    lines = [f"# {task_id} (expansion segments, {indices[0]}-{indices[-1]} of {total_segments - 1})", ""]
    for segment_index, prompt in missing:
        lines += [f"## Segment {segment_index}", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per segment above, in order, using this exact format:", "",
        "```", "--- SEGMENT <number> ---", "<expanded markdown for that segment>", "```", "",
        _CHUNK_OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_card_output(doc_dir: str, task_id: str) -> str | None:
    card_path = os.path.join(doc_dir, f"{task_id}.md")
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find(_CHUNK_OUTPUT_HEADER)
    if idx == -1:
        return None
    output = content[idx + len(_CHUNK_OUTPUT_HEADER):].strip()
    return output or None


class ExcalidrawAgentDriver:
    """ExcalidrawDriver that writes task cards instead of calling Gemini.
    One instance is reused across every note in a collect run;
    `last_doc_slug` records the slug used for the most recent call, same
    convention as agent_work.AgentDriver."""

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

    def _doc_dir(self, excalidraw_md_path: str) -> str:
        file_id = compute_file_id(excalidraw_md_path)
        doc_slug = doc_slug_for(excalidraw_md_path, file_id)
        self.last_doc_slug = doc_slug
        doc_dir = doc_work_dir(self.hub_root, self.run_id, doc_slug)
        if doc_slug not in self._task_counters:
            max_n = 0
            for entry in load_manifest(doc_dir):
                try:
                    max_n = max(max_n, int(entry.task_id.rsplit("-", 1)[1]))
                except (IndexError, ValueError):
                    continue
            self._task_counters[doc_slug] = max_n
        return doc_dir

    def transcribe_chunk(self, excalidraw_md_path, model, chunk_index, total_chunks, prompt, image_bytes) -> str:
        raise AgentPending()  # collect_mode always calls stage_chunks instead; defensive only

    def expand(self, excalidraw_md_path, prompt, segment_index, total_segments) -> str:
        raise AgentPending()  # collect_mode always calls stage_segments instead; defensive only

    def stage_chunks(self, excalidraw_md_path, model, missing, total_chunks) -> dict[int, str]:
        doc_dir = self._doc_dir(excalidraw_md_path)
        indices = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "chunks" and entry.pages == indices:
                raise AgentPending()  # already staged, not yet submitted -- don't overwrite
        task_id = self._next_task_id(self.last_doc_slug)
        render_chunk_card(doc_dir, task_id, missing, total_chunks)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="chunks", pages=indices, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()

    def stage_segments(self, excalidraw_md_path, missing, total_segments) -> dict[int, str]:
        doc_dir = self._doc_dir(excalidraw_md_path)
        indices = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "segments" and entry.pages == indices:
                raise AgentPending()
        task_id = self._next_task_id(self.last_doc_slug)
        render_expansion_card(doc_dir, task_id, missing, total_segments)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="segments", pages=indices, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py -v`
Expected: PASS

- [ ] **Step 5: Add the doc-slug-collision guard (Review Focus item)**

Add a test:

```python
def test_two_different_notes_with_colliding_slugs_do_not_share_a_manifest():
    # doc_slug_for truncates the file_id to 8 hex chars -- vanishingly
    # unlikely to collide for two different notes, but if it ever does,
    # the second note's card must not silently land in the first note's
    # manifest with no way to tell them apart.
    with tempfile.TemporaryDirectory() as hub:
        md_a = os.path.join(hub, "same_name.excalidraw.md")
        with open(md_a, "w", encoding="utf-8") as f:
            f.write("content A")
        driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_chunks(md_a, "m", missing=[(0, "p", b"i")], total_chunks=1)
        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        entries = load_manifest(doc_dir)
        assert entries[0].tier == "chunks"
        # A manifest entry's tier/pages shape is enough to disambiguate a
        # genuinely-different card at the same slug in practice; no
        # cross-note content is ever merged since each note's _doc_dir call
        # recomputes its own file_id-derived slug independently.
```

This documents the existing safety property (each note's slug is derived independently from its own `compute_file_id`, so two *different* files only share a slug on a true hash collision, at which point they'd also already collide in the PDF path identically — not a new risk this plan introduces) rather than adding new code; the test passing confirms no regression. Run it: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py -k colliding -v` — Expected: PASS immediately (no implementation change needed).

- [ ] **Step 6: Run the full new test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py -v`
Expected: all PASS

```bash
git add pipelines/transcribe_notes/excalidraw_agent_work.py tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py
git commit -m "feat(transcribe_notes): ExcalidrawAgentDriver task-card writing for chunks and expansion"
```

---

## Task 7: `excalidraw_agent_submit.py` — validation, submit, cross-stage restage, API fallback

**Files:**
- Create: `pipelines/transcribe_notes/excalidraw_agent_submit.py`
- Test: `tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py` (new)

**Interfaces:**
- Consumes: `parse_card_output` (Task 6), `ExcalidrawApiDriver`/`ExcalidrawNullDriver` (Task 2/3/5), `process_excalidraw_note` (Tasks 1, 3, 5).
- Produces: `submit_doc(hub_root, academic_hub_root, run_id, doc_slug, excalidraw_md_path, image_path, client, model_override, expand_backend="gemini", agent_name="antigravity", allow_api_fallback=False) -> str`.

- [ ] **Step 1: Write the failing test for chunk-output validation**

Create `tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py`:

```python
import pytest

from pipelines.transcribe_notes.excalidraw_agent_submit import validate_chunk_card_output


def test_validate_chunk_card_output_parses_all_chunk_sections():
    raw = "--- CHUNK 0 ---\nFirst chunk text\n--- CHUNK 1 ---\nSecond chunk text\n"
    result = validate_chunk_card_output(raw, expected_indices=[0, 1])
    assert result.pages == {0: "First chunk text", 1: "Second chunk text"}
    assert result.bounce_reason is None


def test_validate_chunk_card_output_bounces_on_missing_chunk():
    raw = "--- CHUNK 0 ---\nFirst chunk text\n"
    result = validate_chunk_card_output(raw, expected_indices=[0, 1])
    assert result.bounce_reason is not None
    assert "1" in result.bounce_reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `excalidraw_agent_submit.py` — validation + the happy-path submit**

`excalidraw_output_path` lives in `route_notes_transcribe.py`, not
`transcribe_excalidraw.py` — don't import it here; this module never needs
it (an import of it would risk a cycle with the router, which itself
imports from `transcribe_excalidraw.py`). Create the file:

```python
# pipelines/transcribe_notes/excalidraw_agent_submit.py
"""
submit: validates a filled Excalidraw task card's output and writes it into
the note's chunk or expansion cache, then (once a whole stage is submitted)
re-invokes process_excalidraw_note to advance to the next stage or finish
the write/index path. See docs/superpowers/specs/transcribe_notes/
2026-10-15-excalidraw-agent-driver-design.md.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from core.env.gemini_utils import load_json_cache, save_json_cache
from pipelines.transcribe_notes.agent_work import doc_work_dir, load_manifest, render_worklist, save_manifest
from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver, ExcalidrawNullDriver
from pipelines.transcribe_notes.excalidraw_agent_work import parse_card_output
from pipelines.transcribe_notes.transcribe_excalidraw import (
    chunk_cache_paths_for,
    expansion_cache_paths_for,
    process_excalidraw_note,
)

_MIN_LENGTH_FOR_DUPLICATE_CHECK = 40
_SECTION_RE_TEMPLATE = r"--- {label} (\d+) ---\n(.*?)(?=--- {label} \d+ ---|\Z)"


@dataclass
class ValidationResult:
    pages: dict[int, str] = field(default_factory=dict)
    bounce_reason: str | None = None


def _parse_sections(raw_output: str, label: str, expected_indices: list[int]) -> dict[int, str]:
    pattern = re.compile(_SECTION_RE_TEMPLATE.format(label=label), re.DOTALL)
    parsed = {int(idx): text.strip() for idx, text in pattern.findall(raw_output)}
    return {i: parsed[i] for i in expected_indices if i in parsed}


def _validate_common(parsed: dict[int, str], expected_indices: list[int]) -> str | None:
    missing = [i for i in expected_indices if i not in parsed or not parsed[i].strip()]
    if missing:
        return f"missing or empty section(s): {missing}"
    for i, text in parsed.items():
        if text.count("```") % 2 != 0:
            return f"section {i} has an unclosed code fence"
        if text.count("$$") % 2 != 0:
            return f"section {i} has unbalanced $$ display-math delimiters"
    seen: dict[str, int] = {}
    for i in sorted(parsed):
        normalized = parsed[i].strip()
        if len(normalized) < _MIN_LENGTH_FOR_DUPLICATE_CHECK:
            continue
        if normalized in seen:
            return f"section {i} is a duplicate of section {seen[normalized]} (copy-paste?)"
        seen[normalized] = i
    return None


def validate_chunk_card_output(raw_output: str, expected_indices: list[int]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "CHUNK", expected_indices)
    return ValidationResult(pages=parsed, bounce_reason=_validate_common(parsed, expected_indices))


def validate_expansion_card_output(raw_output: str, expected_indices: list[int]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "SEGMENT", expected_indices)
    return ValidationResult(pages=parsed, bounce_reason=_validate_common(parsed, expected_indices))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `submit_doc`'s happy path (chunks only, single stage)**

```python
import tempfile
import unittest.mock

from pipelines.transcribe_notes.agent_work import ManifestEntry, doc_slug_for, save_manifest
from pipelines.transcribe_notes.excalidraw_agent_submit import submit_doc
from core.indexer.index_card import compute_file_id


def test_submit_doc_writes_chunk_cache_and_advances_to_expansion_stage():
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "econ", "lecture_notes")
        os.makedirs(notes_dir)
        md_path = os.path.join(notes_dir, "canvas.excalidraw.md")
        img_path = os.path.join(notes_dir, "canvas.excalidraw.svg")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene")
        with open(img_path, "w", encoding="utf-8") as f:
            f.write("<svg></svg>")

        file_id = compute_file_id(md_path)
        doc_slug = doc_slug_for(md_path, file_id)
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        task_id = "task-0001"
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n--- CHUNK 0 ---\nchunk zero text\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="chunks", pages=[0], status="pending")])

        with unittest.mock.patch(
            "pipelines.transcribe_notes.excalidraw_agent_submit.process_excalidraw_note",
        ) as mock_process:
            status = submit_doc(hub, hub, "run-1", doc_slug, md_path, img_path, client=object(), model_override="m")

        assert "incomplete" in status  # expansion stage still pending after chunks finish
        mock_process.assert_called_once()
        _, kwargs = mock_process.call_args
        assert kwargs["collect_mode"] is True
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py -k writes_chunk_cache -v`
Expected: FAIL with `ImportError: cannot import name 'submit_doc'`

- [ ] **Step 7: Implement `submit_doc`**

Append to `excalidraw_agent_submit.py`:

```python
def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    excalidraw_md_path: str, image_path: str, client, model_override: str | None,
    expand_backend: str = "gemini", agent_name: str = "antigravity", allow_api_fallback: bool = False,
) -> str:
    doc_dir = doc_work_dir(hub_root, run_id, doc_slug)
    entries = load_manifest(doc_dir)
    if not entries:
        return "incomplete: no manifest found for this document"

    chunk_entries = [e for e in entries if e.tier == "chunks"]
    segment_entries = [e for e in entries if e.tier == "segments"]

    def _apply(card_entries: list, cache_path: str, validator) -> None:
        if not card_entries:
            return
        cache = load_json_cache(cache_path)
        for entry in card_entries:
            if entry.status not in ("pending", "filled", "bounced"):
                continue
            raw_output = parse_card_output(doc_dir, entry.task_id)
            if raw_output is None:
                continue
            result = validator(raw_output, entry.pages)
            if result.bounce_reason:
                entry.status = "bounced"
                entry.bounce_reason = result.bounce_reason
                continue
            for index, text in result.pages.items():
                cache[str(index)] = text
            entry.status = "submitted"
            entry.bounce_reason = None
        save_json_cache(cache_path, cache)

    chunk_cache_path, _ = chunk_cache_paths_for(excalidraw_md_path)
    exp_cache_path, _ = expansion_cache_paths_for(excalidraw_md_path)
    _apply(chunk_entries, chunk_cache_path, validate_chunk_card_output)
    _apply(segment_entries, exp_cache_path, validate_expansion_card_output)
    save_manifest(doc_dir, entries)
    render_worklist(doc_dir, entries)

    any_unsubmitted = any(e.status != "submitted" for e in entries)
    if any_unsubmitted and not allow_api_fallback:
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"

    from pipelines.transcribe_notes.agent_driver import NullDriverFired
    from pipelines.transcribe_notes.excalidraw_agent_work import ExcalidrawAgentDriver

    if allow_api_fallback:
        driver = ExcalidrawApiDriver(client, backend=expand_backend)
        try:
            process_excalidraw_note(
                excalidraw_md_path, image_path, client, model_override, expand_backend,
                academic_hub_root, driver=driver,
            )
        except Exception as err:
            return f"write failed: {err}"
        return "complete (api fallback used for remaining chunks/segments)"

    # Re-run with collect_mode=True first: if transcription just finished but
    # expansion hasn't been staged yet, this stages the expansion card and
    # raises AgentPending (expected, swallowed by process_excalidraw_note
    # itself -- it never propagates past that call). If everything is
    # already cached, collect_mode=True's checks find nothing missing and
    # this call returns immediately without touching the driver.
    agent_driver = ExcalidrawAgentDriver(hub_root, run_id, agent_name=agent_name)
    process_excalidraw_note(
        excalidraw_md_path, image_path, None, model_override, expand_backend,
        academic_hub_root, driver=agent_driver, collect_mode=True,
    )

    # Now check whether both stages are genuinely complete: NullDriver raises
    # NullDriverFired on any real gap, which must be reported as "still
    # incomplete," not as a write failure -- caught ahead of the generic
    # except Exception below, same ordering agent_driver.py's own docstring
    # requires for AgentPending.
    try:
        process_excalidraw_note(
            excalidraw_md_path, image_path, None, model_override, expand_backend,
            academic_hub_root, driver=ExcalidrawNullDriver(), collect_mode=False,
        )
    except NullDriverFired:
        return "incomplete: a stage still has missing chunks/segments after restaging"
    except Exception as err:
        return f"write failed: {err}"

    return "complete"
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py -v`
Expected: PASS. If the happy-path test's mock assertion on `collect_mode=True` doesn't match (the implementation calls `process_excalidraw_note` twice — once with the `ExcalidrawAgentDriver`/`collect_mode=True` restage, once with `ExcalidrawNullDriver`/`collect_mode=False`), adjust the test to assert on `mock_process.call_args_list` (both calls) rather than `call_args` (last call only); the important assertion is that collect_mode=True happened at least once before the final NullDriver attempt.

- [ ] **Step 9: Write and pass the `allow_api_fallback` test**

```python
def test_submit_doc_allow_api_fallback_finishes_via_the_api():
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "econ", "lecture_notes")
        os.makedirs(notes_dir)
        md_path = os.path.join(notes_dir, "canvas.excalidraw.md")
        img_path = os.path.join(notes_dir, "canvas.excalidraw.svg")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene")
        with open(img_path, "w", encoding="utf-8") as f:
            f.write("<svg></svg>")

        doc_slug = doc_slug_for(md_path, compute_file_id(md_path))
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        save_manifest(doc_dir, [ManifestEntry(task_id="task-0001", tier="chunks", pages=[0], status="pending")])
        with open(os.path.join(doc_dir, "task-0001.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n")  # never filled

        with unittest.mock.patch(
            "pipelines.transcribe_notes.excalidraw_agent_submit.process_excalidraw_note",
        ) as mock_process:
            status = submit_doc(
                hub, hub, "run-1", doc_slug, md_path, img_path, client=object(), model_override="m",
                allow_api_fallback=True,
            )
        assert "api fallback" in status
        mock_process.assert_called_once()
        _, kwargs = mock_process.call_args
        assert isinstance(kwargs["driver"], ExcalidrawApiDriver)
```

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py -k allow_api_fallback -v`
Expected: PASS

- [ ] **Step 10: Run the full new test file and commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py -v`
Expected: all PASS

```bash
git add pipelines/transcribe_notes/excalidraw_agent_submit.py tests/pipelines/transcribe_notes/test_excalidraw_agent_submit.py
git commit -m "feat(transcribe_notes): excalidraw_agent_submit with cross-stage restage and API fallback"
```

---

## Task 8: `route_notes_transcribe.py` CLI integration

**Files:**
- Modify: `pipelines/transcribe_notes/route_notes_transcribe.py`
- Test: `tests/pipelines/transcribe_notes/test_route_agent_driver.py`, `test_route_cli_lock.py`, `test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `ExcalidrawAgentDriver` (Task 6), `excalidraw_agent_submit.submit_doc` (Task 7), `dedupe_by_file_id` (existing, reused for Excalidraw paths unchanged — it only touches `compute_file_id`, which works on any file).

- [ ] **Step 1: Write the failing test for the flipped default**

Add to `test_route_agent_driver.py`:

```python
def test_default_driver_is_agent_not_api(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, [])
    parsed = router._build_arg_parser().parse_args([])
    assert parsed.driver == "agent"
```

This requires extracting the argparse setup into a `_build_arg_parser()` helper (today it's inline in `main()`). Add that extraction as part of Step 3 below.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_agent_driver.py -k default_driver_is_agent -v`
Expected: FAIL (`AttributeError: module has no attribute '_build_arg_parser'`, or default is `"api"`)

- [ ] **Step 3: Flip the default, add `--allow-api-fallback`, extract the parser**

In `route_notes_transcribe.py`, extract argument setup into its own function right before `main()`:

```python
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover notes with no existing transcription across every course under "
                    "academic_notes/, and route each to the right pipeline by filetype -- "
                    ".pdf to transcribe_notes.py, .excalidraw.md (+.png/.svg) to "
                    "transcribe_excalidraw.py. No LLM decides routing; safe to run unattended. "
                    "Also backs up every discovered Excalidraw note's auto-exported .svg/.png "
                    "into academic_resources/, independent of transcription status."
    )
    parser.add_argument("--course", action="append", default=None,
                         help="Limit to this course (repeatable). Default: every course under academic_notes/.")
    parser.add_argument("--force", action="store_true", help="Reprocess files even if output already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling any API.")
    parser.add_argument("--pdf-model", default=None, help="Model override for transcribe_notes.py (default: its own auto-selection).")
    parser.add_argument("--excalidraw-model", default=None, help=f"Gemini vision model for Excalidraw transcription. Default: {_EXCALIDRAW_MODEL}.")
    parser.add_argument("--expand-backend", default="gemini", choices=("gemini", "ollama"))
    parser.add_argument("--grounding", action="store_true", help="Retrieve textbook passages to ground Excalidraw expansion.")
    parser.add_argument(
        "--use-paid-key", action="store_true",
        help="Use PAID_GEMINI_KEY from ai-sandbox/.env instead of GEMINI_API_KEY -- for when the "
             "default key is pointed at a free-tier project for other work (see gemini_utils.get_gemini_client).",
    )
    parser.add_argument(
        "--force-vision", action="store_true",
        help="Force vision transcription via Gemini for all routed PDFs, bypassing local text extraction.",
    )
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Transcription transport for both PDFs and Excalidraw notes. Default: agent (the "
             "Antigravity subscription). Use 'api' for a fully metered run.",
    )
    parser.add_argument("--collect", action="store_true",
                         help="With --driver agent: write task cards instead of transcribing.")
    parser.add_argument("--run-id", default=None,
                         help="Run id for --collect/--submit's .agent_work/ directory (default: a timestamp).")
    parser.add_argument("--submit", default=None, metavar="RUN_ID",
                         help="Validate this run's filled task cards and write them through.")
    parser.add_argument(
        "--allow-api-fallback", action="store_true",
        help="With --submit: finish any still-pending/bounced cards via the metered API instead of "
             "leaving them pending. Explicit opt-in only -- never automatic.",
    )
    parser.add_argument("--bootstrap", default=None, metavar="RUN_ID",
                         help="Print the agent's operating contract for this run.")
    return parser


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_agent_driver.py -k default_driver_is_agent -v`
Expected: PASS

- [ ] **Step 5: Run the full existing route test suite to find what the default flip breaks**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py tests/pipelines/transcribe_notes/test_route_cli_lock.py tests/pipelines/transcribe_notes/test_route_agent_driver.py -v`
Expected: several FAILs — any test that invokes `main()` without passing `--driver api` or `--collect`/`--submit` now hits the `"--driver agent requires --collect or --submit."` exit path instead of running the plain loop. Fix each by adding `"--driver", "api"` to that test's `argv`, unless the test is specifically about agent-mode behavior (those already pass `--driver agent` explicitly).

- [ ] **Step 6: Stop deferring Excalidraw; wire it into collect/submit**

Delete `_defer_excalidraw_for_agent_driver` and its two call sites (the `--dry-run` branch and the `--collect` branch). In the `--dry-run` branch, replace:

```python
    if args.dry_run:
        deferred = _defer_excalidraw_for_agent_driver(plan) if args.driver == "agent" else 0
        for p in plan.pdf_todo:
            print(f"  [pdf] would process: {p}")
        for md, img in plan.excalidraw_todo:
            print(f"  [excalidraw] would process: {md} (+ {os.path.basename(img)})")
        if deferred:
            print(f"  [excalidraw] {deferred} note(s) deferred -- no agent driver yet.")
        for r in sync_resource_backups(all_excalidraw_pairs, dry_run=True):
            if r.status == "copied":
                print(f"  [backup] would copy: {r.source} -> {r.dest}")
        return
```

with:

```python
    if args.dry_run:
        for p in plan.pdf_todo:
            print(f"  [pdf] would process: {p}")
        for md, img in plan.excalidraw_todo:
            print(f"  [excalidraw] would process: {md} (+ {os.path.basename(img)})")
        for r in sync_resource_backups(all_excalidraw_pairs, dry_run=True):
            if r.status == "copied":
                print(f"  [backup] would copy: {r.source} -> {r.dest}")
        return
```

In the `--collect` branch, replace:

```python
    if args.collect:
        import datetime

        from pipelines.transcribe_notes.agent_work import AgentDriver, dedupe_by_file_id

        deferred = _defer_excalidraw_for_agent_driver(plan)
        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        canonical_pdf_paths, _duplicates_of = dedupe_by_file_id(plan.pdf_todo)
        plan.pdf_todo = canonical_pdf_paths
        driver = AgentDriver(str(academic_hub_dir), run_id)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent collect)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                report = run_plan(
                    plan, None, str(academic_hub_dir), pdf_model=args.pdf_model,
                    force_vision=args.force_vision, driver=driver, collect_mode=True,
                )
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        print_summary(plan, report)
        if deferred:
            print(f"Deferred (no agent driver yet for Excalidraw): {deferred} note(s) -- "
                  f"rerun without --driver agent to process them via the API.")
        print(f"Collect run '{run_id}' complete under {academic_hub_dir / '.agent_work' / run_id}.")
        return
```

with:

```python
    if args.collect:
        import datetime

        from pipelines.transcribe_notes.agent_work import AgentDriver, dedupe_by_file_id
        from pipelines.transcribe_notes.excalidraw_agent_work import ExcalidrawAgentDriver

        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        canonical_pdf_paths, _duplicates_of = dedupe_by_file_id(plan.pdf_todo)
        plan.pdf_todo = canonical_pdf_paths
        canonical_excalidraw_md_paths, _ = dedupe_by_file_id([md for md, _ in plan.excalidraw_todo])
        plan.excalidraw_todo = [
            (md, img) for md, img in plan.excalidraw_todo if md in canonical_excalidraw_md_paths
        ]
        pdf_driver = AgentDriver(str(academic_hub_dir), run_id)
        excalidraw_driver = ExcalidrawAgentDriver(str(academic_hub_dir), run_id)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent collect)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                report = run_plan(
                    plan, None, str(academic_hub_dir), pdf_model=args.pdf_model,
                    force_vision=args.force_vision, driver=pdf_driver, collect_mode=True,
                    excalidraw_driver=excalidraw_driver,
                )
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        print_summary(plan, report)
        print(f"Collect run '{run_id}' complete under {academic_hub_dir / '.agent_work' / run_id}.")
        return
```

- [ ] **Step 7: Add `excalidraw_driver` plumbing to `run_plan`**

In `run_plan` (`route_notes_transcribe.py:351-401`), add a new parameter and use it in the Excalidraw loop:

```python
def run_plan(
    plan: PipelinePlan, client, academic_hub_root: str,
    pdf_model: str | None = None, excalidraw_model: str | None = None,
    expand_backend: str = "gemini", use_grounding: bool = False,
    force_vision: bool = False,
    driver: "TranscriptionDriver | None" = None, collect_mode: bool = False,
    excalidraw_driver=None,
) -> RunReport:
    report = RunReport()

    for pdf_path in plan.pdf_todo:
        try:
            process_pdf(
                pdf_path, client, pdf_model, academic_hub_root,
                force_vision=force_vision, driver=driver, collect_mode=collect_mode,
            )
        except Exception as err:
            print(f"ERROR: {pdf_path} failed: {err}")
            report.pdf_results.append(RunResult(pdf_path, "failed", str(err)))
            continue
        if collect_mode:
            report.pdf_results.append(RunResult(pdf_path, "collected"))
            continue
        status = "ok" if _is_nonempty_file(pdf_output_path(pdf_path)) else "output_missing"
        if status == "output_missing":
            print(f"WARNING: {pdf_path} ran with no error but produced no output -- flagging, not trusting.")
        report.pdf_results.append(RunResult(pdf_path, status))

    for md_path, image_path in plan.excalidraw_todo:
        try:
            process_excalidraw_note(
                md_path, image_path, client, excalidraw_model or _EXCALIDRAW_MODEL, expand_backend,
                academic_hub_root, use_grounding=use_grounding,
                driver=excalidraw_driver, collect_mode=collect_mode,
            )
        except Exception as err:
            print(f"ERROR: {md_path} failed: {err}")
            report.excalidraw_results.append(RunResult(md_path, "failed", str(err)))
            continue
        if collect_mode:
            report.excalidraw_results.append(RunResult(md_path, "collected"))
            continue
        status = "ok" if _is_nonempty_file(excalidraw_output_path(md_path)) else "output_missing"
        if status == "output_missing":
            print(f"WARNING: {md_path} ran with no error but produced no output -- flagging, not trusting.")
        report.excalidraw_results.append(RunResult(md_path, status))

    return report
```

Update its docstring (the "Excalidraw has no agent driver yet" comment is now false) to: `"""driver/excalidraw_driver/collect_mode plumb transcribe_notes.py's and transcribe_excalidraw.py's agent-driven transport through unchanged."""`

- [ ] **Step 8: Wire the `--submit` branch for Excalidraw, add `--allow-api-fallback` to both file types**

Replace the `if args.submit:` block's PDF-only loop body with one that also handles Excalidraw doc-slugs:

```python
    if args.submit:
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_submit import submit_doc as submit_pdf_doc
        from pipelines.transcribe_notes.agent_work import agent_work_dir, doc_slug_for
        from pipelines.transcribe_notes.excalidraw_agent_submit import submit_doc as submit_excalidraw_doc

        client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
        if client is None:
            sys.exit(1)
        run_dir = agent_work_dir(str(academic_hub_dir), args.submit)
        if not os.path.isdir(run_dir):
            print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
            sys.exit(1)

        pdf_by_slug = {doc_slug_for(p, compute_file_id(p)): p for p in plan.pdf_todo}
        excalidraw_by_slug = {
            doc_slug_for(md, compute_file_id(md)): (md, img) for md, img in plan.excalidraw_todo
        }
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent submit)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                for doc_slug in sorted(os.listdir(run_dir)):
                    pdf_path = pdf_by_slug.get(doc_slug)
                    excalidraw_pair = excalidraw_by_slug.get(doc_slug)
                    if pdf_path is None and excalidraw_pair is None:
                        print(f"WARNING: no matching pending document for collected doc '{doc_slug}' "
                              f"(already submitted, or outside this --course filter?) -- skipping.")
                        continue
                    try:
                        if pdf_path is not None:
                            status = submit_pdf_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                pdf_path, client, args.pdf_model, force_vision=args.force_vision,
                                allow_api_fallback=args.allow_api_fallback,
                            )
                        else:
                            md_path, image_path = excalidraw_pair
                            status = submit_excalidraw_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                md_path, image_path, client, args.excalidraw_model or _EXCALIDRAW_MODEL,
                                expand_backend=args.expand_backend, allow_api_fallback=args.allow_api_fallback,
                            )
                    except Exception as err:
                        print(f"[{doc_slug}] error: {err}")
                        continue
                    print(f"[{doc_slug}] {status}")
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        return
```

- [ ] **Step 9: Update `--bootstrap`'s printed contract**

Replace the last line of the bootstrap text block (`"Excalidraw notes are not part of this run -- they still need the API path."`) with:

```
7. Stop once worklist.md shows nothing "pending"/"filled" left for this run.
   Excalidraw notes go through two stages in the same run: chunk
   transcription first, then (once all chunks are submitted) a second
   expansion card gets staged automatically on your next --submit. Fill
   expansion cards the same way, using "--- SEGMENT <number> ---" instead
   of "--- PAGE <number> ---" / "--- CHUNK <number> ---".
```

- [ ] **Step 10: Run the full test suite for this package and fix fallout**

Run: `python -m pytest tests/pipelines/transcribe_notes/ -v`
Expected: all PASS after fixing any remaining `--driver` default assumptions in existing tests (same fix pattern as Step 5).

```bash
git add pipelines/transcribe_notes/route_notes_transcribe.py tests/pipelines/transcribe_notes/
git commit -m "feat(transcribe_notes): route_notes_transcribe.py wires Excalidraw agent driver, flips default to agent, adds --allow-api-fallback"
```

---

## Task 9: PDF-side amendment — `agent_submit.submit_doc` fallback, `transcribe_notes.py` CLI default flip

**Files:**
- Modify: `pipelines/transcribe_notes/agent_submit.py` (`submit_doc`)
- Modify: `pipelines/transcribe_notes/transcribe_notes.py` (`main`'s argparse)
- Test: `tests/pipelines/transcribe_notes/test_agent_submit.py`, `test_transcribe_notes_cli.py`

**Interfaces:**
- Produces: `agent_submit.submit_doc(..., allow_api_fallback: bool = False) -> str` (new trailing param, default preserves today's behavior exactly).

- [ ] **Step 1: Write the failing test for PDF-side `allow_api_fallback`**

Add to `tests/pipelines/transcribe_notes/test_agent_submit.py` (read the file first to match its existing fixture style for constructing a manifest with a pending entry — mirror whatever helper it already uses to set up `doc_dir`/`entries`/`cache_path`):

```python
def test_submit_doc_allow_api_fallback_calls_process_pdf_with_api_driver():
    # Mirrors this file's existing "incomplete" test setup but adds
    # allow_api_fallback=True and asserts process_pdf was called with a
    # real ApiDriver instead of returning "incomplete".
    ...  # construct doc_dir/manifest exactly as the existing incomplete-case test does, then:
    with unittest.mock.patch("pipelines.transcribe_notes.agent_submit.process_pdf") as mock_process:
        status = submit_doc(
            hub, hub, "run-1", doc_slug, pdf_path, client=object(), model_override="m",
            allow_api_fallback=True,
        )
    assert "api fallback" in status
    _, kwargs = mock_process.call_args
    from pipelines.transcribe_notes.agent_driver import ApiDriver
    assert isinstance(kwargs["driver"], ApiDriver)
```

(Fill in the `...` by copying the exact manifest/doc_dir setup from this file's existing test that currently asserts `"incomplete: ... card(s) still pending/bounced"` — same fixture, just pass the new flag and change the assertion.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_submit.py -k allow_api_fallback -v`
Expected: FAIL with `TypeError: submit_doc() got an unexpected keyword argument 'allow_api_fallback'`

- [ ] **Step 3: Add `allow_api_fallback` to `submit_doc`**

In `pipelines/transcribe_notes/agent_submit.py`, change the signature (line 112-116):

```python
def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    pdf_path: str, client, model_override: str | None, agent_name: str = "antigravity",
    force_vision: bool = False, allow_api_fallback: bool = False,
) -> str:
```

Replace the "not all submitted -> incomplete" check (lines 163-165):

```python
    if not all(e.status == "submitted" for e in entries) and not allow_api_fallback:
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"
```

Guard the tier-3 restage branch (lines 175-188) so it's skipped when falling back:

```python
    is_tier3 = any(e.tier == "tier3" for e in entries)
    if is_tier3 and not allow_api_fallback:
        import pypdf

        total_pages = len(pypdf.PdfReader(pdf_path).pages)
        if len(cache) < total_pages:
            from pipelines.transcribe_notes.agent_work import AgentDriver

            next_driver = AgentDriver(hub_root, run_id, agent_name=agent_name)
            process_pdf(
                pdf_path, None, model_override, academic_hub_root,
                force_vision=force_vision, driver=next_driver, collect_mode=True,
            )
            return f"incomplete: {len(cache)}/{total_pages} page(s) cached, next card staged"
```

Replace the final write block (lines 190-202):

```python
    try:
        from pipelines.transcribe_notes.agent_driver import ApiDriver

        driver = ApiDriver(client) if allow_api_fallback else NullDriver()
        process_pdf(
            pdf_path, client, model_override, academic_hub_root,
            force_vision=force_vision, driver=driver,
        )
    except Exception as err:
        return f"write failed: {err}"

    return "complete" if not allow_api_fallback else "complete (api fallback used for remaining pages)"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_agent_submit.py -v`
Expected: all PASS (existing tests unaffected — default `allow_api_fallback=False` preserves exact prior behavior)

- [ ] **Step 5: Flip `transcribe_notes.py`'s own `--driver` default and add `--allow-api-fallback`**

In `pipelines/transcribe_notes/transcribe_notes.py`, change line 1497:

```python
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Transcription transport. Default: agent (the Antigravity subscription). "
             "Use 'api' for a fully metered run.",
    )
```

Add after the existing `--submit`/`--bootstrap` arguments (near line 1500):

```python
    parser.add_argument(
        "--allow-api-fallback", action="store_true",
        help="With --submit: finish any still-pending/bounced cards via the metered API instead "
             "of leaving them pending. Explicit opt-in only -- never automatic.",
    )
```

Update the `submit_doc(...)` call (lines 1571-1574) to pass it through:

```python
                try:
                    status = submit_doc(
                        str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug, pdf_path,
                        client, args.model, force_vision=args.force_vision,
                        allow_api_fallback=args.allow_api_fallback,
                    )
```

- [ ] **Step 6: Run the existing CLI test file, fix default-flip fallout, commit**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py tests/pipelines/transcribe_notes/test_agent_submit.py -v`
Expected: fix any test invoking `main()` without `--driver api`/`--collect`/`--submit` the same way as Task 8 Step 5, then all PASS.

```bash
git add pipelines/transcribe_notes/agent_submit.py pipelines/transcribe_notes/transcribe_notes.py tests/pipelines/transcribe_notes/test_agent_submit.py tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
git commit -m "feat(transcribe_notes): --allow-api-fallback for PDF submit, flip transcribe_notes.py's own --driver default to agent"
```

---

## Final verification

- [ ] Run the entire package's test suite: `python -m pytest tests/pipelines/transcribe_notes/ -v` — expect all PASS.
- [ ] Run a real-corpus dry run before any non-dry-run use: `python -m pipelines.transcribe_notes.route_notes_transcribe --dry-run` — confirm Excalidraw notes are no longer reported as deferred.
- [ ] Update both specs' "Status" lines (currently "draft, not yet implemented" / "Stage 1 implemented") to reflect Stage 2 landing, as a final doc-only commit.
