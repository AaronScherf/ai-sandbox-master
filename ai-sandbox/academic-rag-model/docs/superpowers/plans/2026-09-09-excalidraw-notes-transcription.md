# Excalidraw Notes Transcription & Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `notes/transcribe_excalidraw.py` (+ a new `notes/excalidraw_chunking.py` helper module) that turns an Excalidraw handwritten-notes canvas (`.excalidraw.md` + its plugin-auto-exported `.png`) into two RAG-corpus artifacts: a raw shorthand transcription and an expanded, cohesive-prose version, replacing the OneNote capture workflow that baked redundant content onto the page.

**Architecture:** Five stages -- chunk the tall canvas PNG at whitespace gaps (pure, no API), transcribe each chunk via Gemini vision with a trailing-context window (mirrors `transcribe_notes.py`'s Tier 3 accumulation), assemble the raw transcript, expand it into prose via a configurable backend (Gemini default, Ollama opt-in) optionally grounded in retrieved textbook passages, then write `<name>.md` (raw) + `<name>.rag.md` (expanded) with frontmatter and register the expanded doc with the source indexer under a new `excalidraw_notes` doc type.

**Tech Stack:** Python, Pillow + numpy (chunking), `google-genai` (Gemini vision + text), local Ollama HTTP API (optional expansion backend), pytest + `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md`

## Global Constraints

- No `torch`/`marker`/network call at module import time -- match `common/gemini_utils.py`'s existing convention (only `get_gemini_client()` touches `google-genai`, only when called).
- Every function that doesn't touch the network, the filesystem beyond simple reads, or PIL/numpy image data must be independently unit-testable with no mocking -- match this project's existing pure/impure split (e.g. `transcribe_notes.py`'s `build_accumulated_context`, `build_frontmatter` are pure; `render_page_to_image_bytes` is not and isn't locally unit-tested).
- Network calls (Gemini, Ollama) are mocked in the test suite -- no real API calls in `pytest`. Real-corpus validation is a separate, explicit manual task (Task 11), not part of the automated suite.
- `.excalidraw.md`/`.png` source files live in `academic-hub/academic_notes/<course>/lecture_notes/`, a **separate git repo** (`academic-notes-vault`, private) nested inside the main project and gitignored from it. This is a plain filesystem-path concern for this code -- the nested repo boundary is irrelevant to any function written here.
- Naming trap: `academic_notes/<course>/lecture_notes/` (underscored, Excalidraw tablet sync) is not `academic_notes/math-camp/lecture-notes/` (hyphenated, `video_notes`' synthesized output). Do not conflate them in code, tests, or docs.
- Reuse existing helpers rather than re-implementing: `common/gemini_utils.py`'s `call_with_retries`/`get_gemini_client`/`load_dotenv_override`/`load_json_cache`/`save_json_cache`; `common/ollama_utils.py`'s `call_ollama`; `notes/transcribe_notes.py`'s `transcribe_page_via_gemini`/`build_frontmatter`/`_yaml_scalar`; `indexer/index_card.py`'s `compute_file_id`/`compute_content_hash`/`derive_course`/`reconcile_and_write`; `indexer/index_search.py`'s `search_passages`. **Not** `build_accumulated_context` -- Task 6 found its 1-based assumption doesn't compose with 0-based chunk indices; a small local equivalent was written instead.

---

## File Structure

- `notes/excalidraw_chunking.py` (new) -- Stage 1 (chunking) and the chunk-resize/compression step. Pure image processing, no API calls, no filesystem writes beyond what's handed to it. One responsibility: "given a canvas image, produce API-ready chunk images."
- `notes/transcribe_excalidraw.py` (new) -- discovery, Stages 2-5 (transcribe, assemble, expand, write), and the CLI. Mirrors `notes/transcribe_notes.py`'s existing shape (one module per subproject, discovery + processing + `main()` together) rather than splitting further -- this project's established pattern for a subproject this size.
- `indexer/index_card.py` (modified) -- add `EXCALIDRAW_DOC_TYPES = frozenset({"excalidraw_notes"})` alongside the existing `LECTURE_NOTE_DOC_TYPES`, same pattern.
- `tests/test_excalidraw_chunking.py` (new) -- pure unit tests, synthetic images generated in-test, no fixtures on disk, no mocking.
- `tests/test_transcribe_excalidraw.py` (new) -- mirrors `tests/test_transcribe_notes.py`'s mocking conventions for the network-touching pieces.

---

### Task 1: Gap detection

**Files:**
- Create: `notes/excalidraw_chunking.py`
- Test: `tests/test_excalidraw_chunking.py`

**Interfaces:**
- Produces: `find_gaps(gray: "numpy.ndarray", ink_row_threshold: int = 245, min_gap_rows: int = 8) -> list[tuple[int, int]]` -- returns `(start_row, end_row)` for every contiguous blank-row run of at least `min_gap_rows` rows. `gray` is a 2D array, one row per image row, values 0-255 (darker = more ink).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_excalidraw_chunking.py
import numpy as np

from notes.excalidraw_chunking import find_gaps


def _rows(*specs):
    """Build a tiny grayscale array from a list of (row_count, min_value) pairs."""
    rows = []
    for count, value in specs:
        rows.extend([value] * count)
    return np.array([[v] * 3 for v in rows], dtype=np.uint8)


def test_find_gaps_finds_a_single_blank_band():
    # 5 ink rows (dark), 10 blank rows (white), 5 ink rows
    gray = _rows((5, 50), (10, 255), (5, 50))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == [(5, 15)]


def test_find_gaps_ignores_short_blank_runs():
    # a 3-row blank run is below min_gap_rows=8 -- not a real gap
    gray = _rows((5, 50), (3, 255), (5, 50))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == []


def test_find_gaps_handles_trailing_blank_run():
    gray = _rows((5, 50), (10, 255))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == [(5, 15)]


def test_find_gaps_no_gaps_in_solid_ink():
    gray = _rows((20, 50))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_excalidraw_chunking.py -v` (from `academic-rag-model/`)
Expected: FAIL with `ModuleNotFoundError: No module named 'notes.excalidraw_chunking'`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/excalidraw_chunking.py
"""
excalidraw_chunking.py
Turns a tall Excalidraw canvas PNG (unbounded height, unlike a fixed-size
PDF page) into API-ready chunks by cutting at whitespace gaps rather than
a fixed pixel interval -- spiked and validated against two real canvases
(785x13,860px and 786x7,049px) before this module existed; see
docs/status/2026-08-24-notes-transcription-status.md's "2026-09-09"
section and docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md.
No network calls, no filesystem writes -- pure image processing.
"""
from __future__ import annotations

import numpy as np


def find_gaps(gray: np.ndarray, ink_row_threshold: int = 245, min_gap_rows: int = 8) -> list[tuple[int, int]]:
    """Returns (start, end) row ranges that are blank -- every pixel in
    the row is >= ink_row_threshold. A run shorter than min_gap_rows is
    not returned; it's too small to safely cut inside without risking a
    near-miss on real ink (e.g. the gap between two lines of the same
    sentence)."""
    row_min = gray.min(axis=1)
    is_blank = row_min >= ink_row_threshold
    gaps = []
    start = None
    for y, blank in enumerate(is_blank):
        if blank and start is None:
            start = y
        elif not blank and start is not None:
            if y - start >= min_gap_rows:
                gaps.append((start, y))
            start = None
    if start is not None and len(is_blank) - start >= min_gap_rows:
        gaps.append((start, len(is_blank)))
    return gaps
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_excalidraw_chunking.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add notes/excalidraw_chunking.py tests/test_excalidraw_chunking.py
git commit -m "feat(excalidraw): add whitespace-gap detection for canvas chunking"
```

---

### Task 2: Cut selection and full-image chunking

**Files:**
- Modify: `notes/excalidraw_chunking.py`
- Test: `tests/test_excalidraw_chunking.py`

**Interfaces:**
- Consumes: `find_gaps` (Task 1).
- Produces:
  - `choose_cuts(height: int, gaps: list[tuple[int, int]], target_chunk_height: int = 3000, max_chunk_height: int = 4500) -> list[tuple[int, bool]]` -- ordered list of `(cut_row, is_hard_cut)`, not including the final implicit cut at `height`.
  - `chunk_image(image: "PIL.Image.Image", target_chunk_height: int = 3000, max_chunk_height: int = 4500, ink_row_threshold: int = 245, min_gap_rows: int = 8) -> list["PIL.Image.Image"]` -- the full canvas, cropped into ordered chunk images.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_excalidraw_chunking.py (add to existing file)
from PIL import Image

from notes.excalidraw_chunking import choose_cuts, chunk_image


def test_choose_cuts_picks_gap_nearest_target_height():
    # gaps at 100-110 and 2990-3010 and 6000-6010, height 8000,
    # target 3000 -> first cut should land in the 2990-3010 gap (midpoint 3000)
    gaps = [(100, 110), (2990, 3010), (6000, 6010)]
    cuts = choose_cuts(8000, gaps, target_chunk_height=3000, max_chunk_height=4500)
    assert cuts[0] == (3000, False)


def test_choose_cuts_hard_cuts_when_no_gap_available():
    # no gaps at all -- must still produce a cut, flagged as hard
    cuts = choose_cuts(10000, [], target_chunk_height=3000, max_chunk_height=4500)
    assert cuts[0] == (4500, True)


def test_choose_cuts_no_cuts_needed_under_target():
    cuts = choose_cuts(2000, [], target_chunk_height=3000, max_chunk_height=4500)
    assert cuts == []


def _make_canvas(height: int, ink_rows: set[int]) -> Image.Image:
    """White canvas, width 10, with the given rows painted dark (ink)."""
    img = Image.new("RGB", (10, height), color=(255, 255, 255))
    pixels = img.load()
    for y in ink_rows:
        for x in range(10):
            pixels[x, y] = (30, 30, 30)
    return img


def test_chunk_image_splits_at_a_real_gap_not_through_ink():
    # ink rows 0-4 and 20-24, blank 5-19 (15 rows, a real gap) and 25-29
    ink_rows = set(range(0, 5)) | set(range(20, 25))
    canvas = _make_canvas(30, ink_rows)
    chunks = chunk_image(canvas, target_chunk_height=10, max_chunk_height=20, min_gap_rows=8)
    assert len(chunks) == 2
    assert chunks[0].size == (10, 12)  # cut at gap midpoint (5+19)//2+1=12ish -- see step 3
    total_height = sum(c.size[1] for c in chunks)
    assert total_height == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_excalidraw_chunking.py -v`
Expected: FAIL with `ImportError: cannot import name 'choose_cuts'`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/excalidraw_chunking.py (append)
from PIL import Image


def choose_cuts(
    height: int, gaps: list[tuple[int, int]],
    target_chunk_height: int = 3000, max_chunk_height: int = 4500,
) -> list[tuple[int, bool]]:
    """Walks down the image picking a gap-midpoint cut near every
    target_chunk_height, falling back to a hard cut at max_chunk_height
    only when no gap is available in that window -- never observed on
    the two real canvases this was spiked against, but must still be
    handled rather than assumed impossible."""
    cuts: list[tuple[int, bool]] = []
    last_cut = 0
    while last_cut + target_chunk_height < height:
        want = last_cut + target_chunk_height
        window_end = min(last_cut + max_chunk_height, height)
        candidates = [g for g in gaps if last_cut < (g[0] + g[1]) // 2 <= window_end]
        if candidates:
            best = min(candidates, key=lambda g: abs((g[0] + g[1]) // 2 - want))
            cut = (best[0] + best[1]) // 2
            hard = False
        else:
            cut = last_cut + max_chunk_height
            hard = True
        if cut >= height:
            # No room for another cut before the end of the image -- the
            # final segment (handled by chunk_image's own trailing
            # `height` boundary) runs long instead. Without this guard,
            # a hard cut that lands exactly on `height` would produce a
            # spurious zero-height final chunk.
            break
        cuts.append((cut, hard))
        last_cut = cut
    return cuts


def chunk_image(
    image: Image.Image,
    target_chunk_height: int = 3000, max_chunk_height: int = 4500,
    ink_row_threshold: int = 245, min_gap_rows: int = 8,
) -> list[Image.Image]:
    """Crops `image` into ordered, top-to-bottom chunks cut at whitespace
    gaps. Full width is preserved on every chunk -- only height is cut."""
    import numpy as np

    gray = np.array(image.convert("L"))
    height, width = gray.shape
    gaps = find_gaps(gray, ink_row_threshold=ink_row_threshold, min_gap_rows=min_gap_rows)
    cuts = choose_cuts(height, gaps, target_chunk_height=target_chunk_height, max_chunk_height=max_chunk_height)

    rgb = image.convert("RGB")
    chunks = []
    prev = 0
    for cut, _hard in cuts + [(height, False)]:
        chunks.append(rgb.crop((0, prev, width, cut)))
        prev = cut
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_excalidraw_chunking.py -v`
Expected: PASS. If the exact expected height in `test_chunk_image_splits_at_a_real_gap_not_through_ink` doesn't match your gap-midpoint arithmetic, fix the assertion to the actual computed value -- the important invariant is "2 chunks, total height 30, cut falls inside rows 5-19," not the exact midpoint pixel.

- [ ] **Step 5: Commit**

```bash
git add notes/excalidraw_chunking.py tests/test_excalidraw_chunking.py
git commit -m "feat(excalidraw): add cut selection and full-canvas chunking"
```

---

### Task 3: Chunk resize/compression -- real experiment, then implement

This task is empirical, not TDD in the usual sense: the spec explicitly defers the compression setting to a real measurement (both canvases are only 785-786px wide already, narrower than Tier 3's ~1700px+ textbook-page renders, so the generic "always downscale" advice may not even apply here). Do the experiment first; the constants below are starting points to adjust from what you measure, not the final answer.

**Files:**
- Create (throwaway, not committed): a scratch script, e.g. `academic-rag-model/scratch_resize_experiment.py`
- Modify: `notes/excalidraw_chunking.py`
- Test: `tests/test_excalidraw_chunking.py`

**Interfaces:**
- Produces: `resize_chunk_for_api(image: "PIL.Image.Image", max_width: int = 1200, jpeg_quality: int = 85) -> bytes` -- returns JPEG-encoded bytes, width capped at `max_width` (height scaled proportionally), no-op resize if already narrower.

- [ ] **Step 1: Run the real experiment**

Using two or three real chunks from `academic-hub/academic_notes/math_methods/lecture_notes/` (produced by pulling the tablet-sync repo and running `chunk_image` interactively, or reusing the Task 2 spike approach), write and run a throwaway script that sends each of 3 variants of the same chunk to Gemini and prints `usage_metadata`:

```python
# scratch_resize_experiment.py (throwaway -- do not commit)
import io
import sys

from PIL import Image

sys.path.insert(0, ".")
from common.gemini_utils import get_gemini_client, load_dotenv_override

load_dotenv_override()
client = get_gemini_client()

chunk_path = sys.argv[1]  # path to one real chunk PNG
image = Image.open(chunk_path)

variants = {
    "original_png": lambda im: (io.BytesIO(im.tobytes()) and _to_bytes(im, "PNG")),
    "original_jpeg_q85": lambda im: _to_bytes(im, "JPEG", quality=85),
    "width_1200_jpeg_q85": lambda im: _to_bytes(_resize(im, 1200), "JPEG", quality=85),
}


def _to_bytes(im, fmt, **kwargs):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def _resize(im, max_width):
    if im.width <= max_width:
        return im
    ratio = max_width / im.width
    return im.resize((max_width, int(im.height * ratio)))


from google.genai import types

for name, fn in variants.items():
    data = fn(image)
    mime = "image/png" if "png" in name else "image/jpeg"
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[types.Part.from_bytes(data=data, mime_type=mime),
                  "Transcribe all handwritten text and math notation on this image into markdown with LaTeX."],
        config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
    )
    usage = response.usage_metadata
    print(f"{name}: bytes={len(data)} input_tokens={usage.prompt_token_count} "
          f"output_tokens={usage.candidates_token_count}")
    print(f"  transcription preview: {response.text[:200]!r}")
```

Run: `.venv/Scripts/python.exe scratch_resize_experiment.py "../academic-hub/academic_notes/math_methods/lecture_notes/processed_outputs_scratch/chunk_00.png"` (or wherever you saved a real chunk from Task 2's manual verification).

Record, in `docs/status/2026-08-24-notes-transcription-status.md`, a new dated entry: bytes/tokens per variant, and a manual read of whether the transcription preview looks equally accurate across variants. Pick `max_width` and `jpeg_quality` from what you observe -- if narrower width or JPEG compression measurably hurts transcription of small handwriting or dense matrices, keep the original PNG and skip resizing entirely (a valid outcome, not a failure of this task).

- [ ] **Step 2: Delete the scratch script**

```bash
rm scratch_resize_experiment.py
```

- [ ] **Step 3: Write the failing test for the chosen implementation**

```python
# tests/test_excalidraw_chunking.py (add to existing file)
import io

from PIL import Image

from notes.excalidraw_chunking import resize_chunk_for_api


def test_resize_chunk_for_api_caps_width_and_returns_jpeg_bytes():
    wide = Image.new("RGB", (2000, 500), color=(255, 255, 255))
    data = resize_chunk_for_api(wide, max_width=1200, jpeg_quality=85)
    result = Image.open(io.BytesIO(data))
    assert result.format == "JPEG"
    assert result.width == 1200
    assert result.height == 300  # 500 * (1200/2000)


def test_resize_chunk_for_api_no_op_when_already_narrow():
    narrow = Image.new("RGB", (785, 3000), color=(255, 255, 255))
    data = resize_chunk_for_api(narrow, max_width=1200, jpeg_quality=85)
    result = Image.open(io.BytesIO(data))
    assert result.size == (785, 3000)
```

Adjust `max_width`/`jpeg_quality` defaults in both the test and Step 4's implementation to whatever Step 1's experiment concluded -- 1200/85 above are starting points, not the measured answer.

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_excalidraw_chunking.py -v -k resize`
Expected: FAIL with `ImportError: cannot import name 'resize_chunk_for_api'`

- [ ] **Step 5: Write minimal implementation**

```python
# notes/excalidraw_chunking.py (append)
import io


def resize_chunk_for_api(image: Image.Image, max_width: int = 1200, jpeg_quality: int = 85) -> bytes:
    """Encodes a chunk for the Gemini API call -- caps width (height
    scaled proportionally) and re-encodes as JPEG. Defaults come from a
    real experiment (see docs/status/2026-08-24-notes-transcription-status.md,
    the dated entry for this task), not a guess -- update them there and
    here together if a later experiment says otherwise."""
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
    return buf.getvalue()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_excalidraw_chunking.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 7: Commit**

```bash
git add notes/excalidraw_chunking.py tests/test_excalidraw_chunking.py docs/status/2026-08-24-notes-transcription-status.md
git commit -m "feat(excalidraw): add chunk resize/compression, tuned from a real experiment"
```

---

### Task 4: Discovery

**Files:**
- Create: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Produces: `discover_excalidraw_files(notes_dir: str, file_filter: str | None = None) -> list[tuple[str, str]]` -- list of `(excalidraw_md_path, png_path)` pairs, sorted by filename. Skips any `.excalidraw.md` with no matching `.png` sibling (auto-export may not have run yet), printing a warning rather than raising.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py
import os

from notes.transcribe_excalidraw import discover_excalidraw_files


def test_discover_excalidraw_files_pairs_md_and_png(tmp_path):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing A.excalidraw.png").write_bytes(b"fake-png")
    (tmp_path / "Drawing B.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing B.excalidraw.png").write_bytes(b"fake-png")

    pairs = discover_excalidraw_files(str(tmp_path))

    assert pairs == [
        (str(tmp_path / "Drawing A.excalidraw.md"), str(tmp_path / "Drawing A.excalidraw.png")),
        (str(tmp_path / "Drawing B.excalidraw.md"), str(tmp_path / "Drawing B.excalidraw.png")),
    ]


def test_discover_excalidraw_files_skips_md_with_no_png(tmp_path, capsys):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    # no matching PNG

    pairs = discover_excalidraw_files(str(tmp_path))

    assert pairs == []
    assert "no matching .png" in capsys.readouterr().out.lower()


def test_discover_excalidraw_files_respects_file_filter(tmp_path):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing A.excalidraw.png").write_bytes(b"fake-png")
    (tmp_path / "Drawing B.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing B.excalidraw.png").write_bytes(b"fake-png")

    pairs = discover_excalidraw_files(str(tmp_path), file_filter="Drawing A.excalidraw.md")

    assert len(pairs) == 1
    assert pairs[0][0].endswith("Drawing A.excalidraw.md")


def test_discover_excalidraw_files_missing_dir_returns_empty():
    assert discover_excalidraw_files("/no/such/dir") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'notes.transcribe_excalidraw'`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py
"""
transcribe_excalidraw.py
Turns an Excalidraw handwritten-notes canvas (.excalidraw.md + its
plugin-auto-exported .png) into RAG-corpus markdown: chunk -> transcribe
-> assemble -> expand -> write. Replaces the OneNote capture workflow
(see docs/status/2026-08-24-notes-transcription-status.md's "2026-09-07"
section for why). Spec: docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def discover_excalidraw_files(notes_dir: str, file_filter: str | None = None) -> list[tuple[str, str]]:
    """Finds every `.excalidraw.md` directly under notes_dir with a
    matching `.excalidraw.png` sibling (the plugin's auto-export) --
    skips (with a warning, not an error) any .md whose PNG hasn't been
    written yet."""
    if not os.path.isdir(notes_dir):
        return []
    pairs = []
    for name in sorted(os.listdir(notes_dir)):
        if not name.lower().endswith(".excalidraw.md"):
            continue
        if file_filter is not None and name != file_filter:
            continue
        md_path = os.path.join(notes_dir, name)
        png_path = md_path[: -len(".md")] + ".png"
        if not os.path.exists(png_path):
            print(f"WARNING: {name} has no matching .png (auto-export may not have run yet) -- skipping.")
            continue
        pairs.append((md_path, png_path))
    return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): add .excalidraw.md/.png discovery"
```

---

### Task 5: Chunk transcription prompt and raw-transcript assembly

**Files:**
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Produces:
  - `build_chunk_transcription_prompt(accumulated_context: str, chunk_index: int, total_chunks: int) -> str`
  - `assemble_raw_markdown(cache: dict, total_chunks: int) -> str` -- same shape as `transcribe_notes.py`'s `build_final_markdown(cache, total_pages)`, keyed by chunk index (0-based) instead of page number (1-based).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py (add to existing file)
from notes.transcribe_excalidraw import assemble_raw_markdown, build_chunk_transcription_prompt


def test_build_chunk_transcription_prompt_mentions_chunk_position():
    prompt = build_chunk_transcription_prompt("", chunk_index=0, total_chunks=5)
    assert "chunk 1 of 5" in prompt.lower()


def test_build_chunk_transcription_prompt_includes_accumulated_context():
    prompt = build_chunk_transcription_prompt("--- Chunk 1 ---\nEarlier text", chunk_index=1, total_chunks=5)
    assert "Earlier text" in prompt
    assert "continuity" in prompt.lower()


def test_build_chunk_transcription_prompt_omits_context_block_when_empty():
    prompt = build_chunk_transcription_prompt("", chunk_index=0, total_chunks=1)
    assert "already-transcribed" not in prompt.lower()


def test_assemble_raw_markdown_joins_chunks_in_order():
    cache = {"0": "first chunk text", "1": "second chunk text"}
    result = assemble_raw_markdown(cache, total_chunks=2)
    assert result == "<!-- chunk 1 -->\n\nfirst chunk text\n\n<!-- chunk 2 -->\n\nsecond chunk text"


def test_assemble_raw_markdown_skips_missing_chunks():
    cache = {"0": "first chunk text"}  # chunk 1 never transcribed (failed)
    result = assemble_raw_markdown(cache, total_chunks=2)
    assert result == "<!-- chunk 1 -->\n\nfirst chunk text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k "prompt or assemble"`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py (append)
def build_chunk_transcription_prompt(accumulated_context: str, chunk_index: int, total_chunks: int) -> str:
    context_block = (
        f"Already-transcribed content from earlier chunks of this same canvas, for continuity "
        f"(a chunk boundary can split a derivation or sentence mid-thought):\n{accumulated_context}\n\n"
        if accumulated_context else ""
    )
    return (
        f"This is chunk {chunk_index + 1} of {total_chunks} from a single tall, continuous "
        "handwritten-notes canvas (an Excalidraw drawing, cropped at a whitespace gap -- not a "
        "page boundary). Transcribe everything on this chunk into clean markdown: preserve "
        "problem/part numbering, mathematical notation (LaTeX-style, e.g. $...$ or $$...$$), "
        "and reading order. Keep this transcription terse and faithful to the shorthand as "
        "written -- do not expand abbreviations or add explanation; that happens in a later "
        "pass.\n\n"
        f"{context_block}"
        "Respond with ONLY the transcribed markdown for THIS chunk -- no commentary, no code "
        "fence, no repetition of earlier chunks' content.\n"
    )


def assemble_raw_markdown(cache: dict, total_chunks: int) -> str:
    parts = []
    for chunk_index in range(total_chunks):
        text = cache.get(str(chunk_index))
        if text is None:
            continue
        parts.append(f"<!-- chunk {chunk_index + 1} -->\n\n{text}")
    return "\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): add chunk transcription prompt and raw-transcript assembly"
```

---

### Task 6: Per-chunk transcription with cross-chunk accumulation

**Files:**
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: `notes.transcribe_notes.transcribe_page_via_gemini(client, model, image_bytes, prompt) -> str` (reused as-is -- it's already generic over "an image and a prompt," not PDF-specific), `common.gemini_utils.call_with_retries`.
- Produces: `_accumulated_chunk_context(cache, chunk_index, window) -> str` (**not** a reuse of `transcribe_notes.py`'s `build_accumulated_context` -- real testing found that function's hardcoded 1-based floor silently drops chunk 0 from a 0-based scheme; see Step 3), `transcribe_chunks(client, model: str, chunk_bytes: list[bytes]) -> dict[str, str]` -- cache dict keyed by chunk index as a string, one entry per successfully-transcribed chunk. A chunk that raises after retries is logged and skipped, not fatal to the whole document (matches `process_pdf`'s per-page resilience).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py (add to existing file)
from unittest.mock import patch

from notes.transcribe_excalidraw import transcribe_chunks


def test_transcribe_chunks_builds_cache_keyed_by_index():
    with patch("notes.transcribe_excalidraw.transcribe_page_via_gemini") as mock_transcribe:
        mock_transcribe.side_effect = ["first chunk text", "second chunk text"]
        cache = transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"])
    assert cache == {"0": "first chunk text", "1": "second chunk text"}


def test_transcribe_chunks_passes_accumulated_context_from_prior_chunks():
    captured_prompts = []

    def fake_transcribe(client, model, image_bytes, prompt):
        captured_prompts.append(prompt)
        return f"text for chunk with prompt len {len(prompt)}"

    with patch("notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake_transcribe):
        transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"])

    # second call's prompt must include the first chunk's already-transcribed text
    assert "text for chunk with prompt len" in captured_prompts[1]


def test_transcribe_chunks_skips_a_chunk_that_fails_after_retries():
    def fake_transcribe(client, model, image_bytes, prompt):
        if image_bytes == b"img1":
            raise ValueError("simulated repetition-loop failure")
        return "ok text"

    with patch("notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake_transcribe):
        with patch("notes.transcribe_excalidraw.call_with_retries", side_effect=lambda fn: fn()):
            cache = transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1", b"img2"])

    assert cache == {"0": "ok text", "2": "ok text"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k transcribe_chunks`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py (add imports near the top, then append)
from common.gemini_utils import call_with_retries
from notes.transcribe_notes import transcribe_page_via_gemini

_ACCUMULATION_WINDOW = 3  # same value as transcribe_notes.py's Tier 3 -- see that
                          # module's _ACCUMULATION_WINDOW docstring for why a
                          # trailing window (not full-document accumulation) is used


def _accumulated_chunk_context(cache: dict, chunk_index: int, window: int) -> str:
    """0-based equivalent of transcribe_notes.py's build_accumulated_context.
    Not reused directly: that function assumes 1-based page numbers (its
    start-page floor is hardcoded to 1), which silently drops chunk 0's
    context when called with 0-based chunk indices -- caught by a real
    failing test, not assumed in advance. Same trailing-window behavior,
    just 0-based."""
    start = max(0, chunk_index - window)
    parts = []
    for i in range(start, chunk_index):
        text = cache.get(str(i))
        if text:
            parts.append(f"--- Chunk {i + 1} ---\n{text}")
    return "\n\n".join(parts)


def transcribe_chunks(client, model: str, chunk_bytes: list[bytes]) -> dict[str, str]:
    cache: dict[str, str] = {}
    total_chunks = len(chunk_bytes)
    for chunk_index, image_bytes in enumerate(chunk_bytes):
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks)
        try:
            text = call_with_retries(lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt))
            cache[str(chunk_index)] = text
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache
```

**Real deviation from the original plan, caught by Step 4's test run, not assumed in advance:** the plan originally called for reusing `transcribe_notes.py`'s `build_accumulated_context` directly. Running the tests below found it drops chunk 0 from a 0-based scheme (its start-page floor is hardcoded to 1, assuming pages start at 1). Wrote a small local 0-based equivalent instead of forcing an interface mismatch.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): transcribe chunks via Gemini with cross-chunk accumulation"
```

---

### Task 7: Expansion prompt and Gemini expansion backend

**Files:**
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: `common.gemini_utils.call_with_retries`.
- Produces:
  - `build_expansion_prompt(raw_markdown: str, retrieved_passages: list[str] | None = None) -> str`
  - `expand_via_gemini(client, model: str, raw_markdown: str, retrieved_passages: list[str] | None = None) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py (add to existing file)
from notes.transcribe_excalidraw import build_expansion_prompt, expand_via_gemini


def test_build_expansion_prompt_includes_raw_text():
    prompt = build_expansion_prompt("$$x + y = z$$")
    assert "$$x + y = z$$" in prompt
    assert "cohesive" in prompt.lower() or "prose" in prompt.lower()


def test_build_expansion_prompt_includes_retrieved_passages_when_given():
    prompt = build_expansion_prompt("shorthand notes", retrieved_passages=["Textbook passage about norms."])
    assert "Textbook passage about norms." in prompt


def test_build_expansion_prompt_omits_grounding_block_when_none():
    prompt = build_expansion_prompt("shorthand notes", retrieved_passages=None)
    assert "textbook" not in prompt.lower()


def test_expand_via_gemini_returns_response_text():
    class FakeResponse:
        text = "Expanded prose explaining the shorthand."
        usage_metadata = None

    class FakeModels:
        def generate_content(self, model, contents, config):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    result = expand_via_gemini(FakeClient(), model="gemini-3.1-flash-lite", raw_markdown="shorthand")
    assert result == "Expanded prose explaining the shorthand."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k expansion`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py (append)
def build_expansion_prompt(raw_markdown: str, retrieved_passages: list[str] | None = None) -> str:
    grounding_block = ""
    if retrieved_passages:
        joined = "\n\n".join(retrieved_passages)
        grounding_block = (
            "Relevant passages from the course's own textbook material, for grounding and "
            f"terminology consistency (cite/connect to these where genuinely relevant, don't "
            f"force a connection that isn't there):\n{joined}\n\n"
        )
    return (
        "The following is a terse, shorthand transcription of a student's handwritten math/"
        "economics lecture notes -- LaTeX-heavy, abbreviated, written for the student's own "
        "quick reference, not for someone else to read. Rewrite it into a cohesive, "
        "self-contained prose explanation: expand abbreviations, spell out the reasoning "
        "between steps, and preserve every piece of mathematical content (do not drop or "
        "simplify any equation) while making it directly understandable to someone who "
        "wasn't in the room. Keep LaTeX notation ($...$, $$...$$) for all math.\n\n"
        f"{grounding_block}"
        f"Shorthand transcription:\n{raw_markdown}\n\n"
        "Respond with ONLY the expanded markdown -- no commentary, no code fence.\n"
    )


def expand_via_gemini(client, model: str, raw_markdown: str, retrieved_passages: list[str] | None = None) -> str:
    prompt = build_expansion_prompt(raw_markdown, retrieved_passages)
    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
    )
    return (response.text or "").strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): add expansion prompt and Gemini expansion backend"
```

---

### Task 8: Ollama expansion backend and backend dispatcher

**Files:**
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama(prompt, model, request_timeout, url, num_ctx) -> str | None | OllamaTimeout`, `expand_via_gemini` (Task 7).
- Produces:
  - `expand_via_ollama(raw_markdown: str, model: str, request_timeout: int = 300, retrieved_passages: list[str] | None = None) -> str | None`
  - `expand_transcription(client, raw_markdown: str, backend: str, retrieved_passages: list[str] | None = None) -> tuple[str | None, dict]` -- returns `(expanded_text, metadata)` where `metadata` is `{"expansion_backend": ..., "expansion_model": ..., "grounded": bool}`; falls back to Gemini if Ollama is requested but unreachable (matches `viz`/`problem_gen`'s existing degrade-to-Gemini-or-warn pattern).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py (add to existing file)
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT
from notes.transcribe_excalidraw import expand_transcription, expand_via_ollama


def test_expand_via_ollama_returns_response_text():
    with patch("notes.transcribe_excalidraw.call_ollama", return_value="Expanded via Ollama."):
        result = expand_via_ollama("shorthand", model="qwen2.5:7b-instruct")
    assert result == "Expanded via Ollama."


def test_expand_via_ollama_returns_none_on_timeout():
    with patch("notes.transcribe_excalidraw.call_ollama", return_value=OLLAMA_TIMEOUT):
        result = expand_via_ollama("shorthand", model="qwen2.5:7b-instruct")
    assert result is None


def test_expand_transcription_gemini_backend():
    with patch("notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="gemini")
    assert text == "Gemini prose"
    assert meta["expansion_backend"] == "gemini"
    assert meta["grounded"] is False


def test_expand_transcription_ollama_backend_success():
    with patch("notes.transcribe_excalidraw.expand_via_ollama", return_value="Ollama prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="ollama")
    assert text == "Ollama prose"
    assert meta["expansion_backend"] == "ollama"


def test_expand_transcription_ollama_falls_back_to_gemini_when_unreachable():
    with patch("notes.transcribe_excalidraw.expand_via_ollama", return_value=None), \
         patch("notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini fallback prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="ollama")
    assert text == "Gemini fallback prose"
    assert meta["expansion_backend"] == "gemini"


def test_expand_transcription_marks_grounded_when_passages_given():
    with patch("notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini prose"):
        _text, meta = expand_transcription(
            client=object(), raw_markdown="shorthand", backend="gemini",
            retrieved_passages=["some textbook passage"],
        )
    assert meta["grounded"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k "ollama or dispatcher or expand_transcription"`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py (add imports near the top, then append)
from common.ollama_utils import call_ollama

_EXPANSION_MODEL_GEMINI = "gemini-3.1-flash-lite"  # text-only reasoning task, matches
                                                     # problem_gen's/viz's own default tier
_EXPANSION_MODEL_OLLAMA = "qwen2.5:7b-instruct"     # general-purpose, not qwen2-math --
                                                     # expansion spans math AND econ notes,
                                                     # same reasoning video_notes used for
                                                     # its own synthesis model choice


def expand_via_ollama(
    raw_markdown: str, model: str = _EXPANSION_MODEL_OLLAMA, request_timeout: int = 300,
    retrieved_passages: list[str] | None = None,
) -> str | None:
    prompt = build_expansion_prompt(raw_markdown, retrieved_passages)
    result = call_ollama(prompt, model=model, request_timeout=request_timeout)
    if isinstance(result, str):
        return result.strip()
    return None  # unreachable server or timeout -- caller decides whether to fall back


def expand_transcription(
    client, raw_markdown: str, backend: str = "gemini", retrieved_passages: list[str] | None = None,
) -> tuple[str | None, dict]:
    """backend='gemini' (default) or 'ollama' (opt-in, matches
    VIZ_BACKEND/PROBLEMGEN_BACKEND's existing env-var pattern at the CLI
    layer -- see main()). Falls back to Gemini if Ollama is requested but
    unreachable, printing a warning, rather than failing the whole
    document."""
    grounded = bool(retrieved_passages)
    if backend == "ollama":
        text = expand_via_ollama(raw_markdown, retrieved_passages=retrieved_passages)
        if text is not None:
            return text, {"expansion_backend": "ollama", "expansion_model": _EXPANSION_MODEL_OLLAMA, "grounded": grounded}
        print("WARNING: Ollama expansion backend unreachable; falling back to Gemini.")
    text = expand_via_gemini(client, _EXPANSION_MODEL_GEMINI, raw_markdown, retrieved_passages)
    return text, {"expansion_backend": "gemini", "expansion_model": _EXPANSION_MODEL_GEMINI, "grounded": grounded}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): add Ollama expansion backend with Gemini fallback"
```

---

### Task 9: Output writing, frontmatter, and indexer registration

**Files:**
- Modify: `indexer/index_card.py`
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: `notes.transcribe_notes.build_frontmatter(metadata: dict) -> str` (reused as-is), `indexer.index_card.compute_file_id`, `compute_content_hash`, `derive_course`, `reconcile_and_write` (reused exactly as `transcribe_notes.py`'s `_write_markdown_and_index` uses them), the new `EXCALIDRAW_DOC_TYPES`.
- Produces: `write_outputs(excalidraw_md_path: str, png_path: str, raw_markdown: str, expanded_markdown: str, transcription_model: str, expansion_meta: dict, num_chunks: int, academic_hub_root: str, client) -> tuple[str, str]` -- writes `<name>.md` and `<name>.rag.md` under a sibling `processed_outputs/` directory, returns their paths. Only the `.rag.md` is registered with the source indexer (it's the RAG-canonical artifact per the spec).

- [ ] **Step 1: Add the new doc type**

In `indexer/index_card.py`, right after the existing `LECTURE_NOTE_DOC_TYPES` line:

```python
# indexer/index_card.py (modify near line 39)
LECTURE_NOTE_DOC_TYPES = frozenset({"lecture_notes"})
EXCALIDRAW_DOC_TYPES = frozenset({"excalidraw_notes"})
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py (add to existing file)
import os
from unittest.mock import patch

from notes.transcribe_excalidraw import write_outputs


def test_write_outputs_creates_both_files_with_frontmatter(tmp_path):
    course_dir = tmp_path / "academic-hub" / "academic_notes" / "math_methods" / "lecture_notes"
    course_dir.mkdir(parents=True)
    md_path = course_dir / "Drawing 2026-09-08.excalidraw.md"
    png_path = course_dir / "Drawing 2026-09-08.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")

    with patch("notes.transcribe_excalidraw.reconcile_and_write") as mock_reconcile:
        raw_path, rag_path = write_outputs(
            excalidraw_md_path=str(md_path), png_path=str(png_path),
            raw_markdown="raw shorthand text", expanded_markdown="expanded prose text",
            transcription_model="gemini-3.6-flash",
            expansion_meta={"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False},
            num_chunks=3, academic_hub_root=str(tmp_path / "academic-hub"), client=object(),
        )

    assert os.path.basename(raw_path) == "Drawing 2026-09-08.excalidraw.md"
    assert os.path.basename(rag_path) == "Drawing 2026-09-08.excalidraw.rag.md"
    assert os.path.dirname(raw_path).endswith("processed_outputs")

    raw_content = open(raw_path, encoding="utf-8").read()
    assert "routing: excalidraw_chunked" in raw_content
    assert "raw shorthand text" in raw_content

    rag_content = open(rag_path, encoding="utf-8").read()
    assert "expansion_backend: gemini" in rag_content
    assert "expanded prose text" in rag_content

    mock_reconcile.assert_called_once()  # only the .rag.md gets indexed
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k write_outputs`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py (add imports near the top, then append)
from indexer.index_card import (
    EXCALIDRAW_DOC_TYPES,
    compute_content_hash,
    compute_file_id,
    derive_course,
    reconcile_and_write,
)
from notes.transcribe_notes import build_frontmatter


def write_outputs(
    excalidraw_md_path: str, png_path: str, raw_markdown: str, expanded_markdown: str,
    transcription_model: str, expansion_meta: dict, num_chunks: int, academic_hub_root: str, client,
) -> tuple[str, str]:
    base_name = os.path.basename(excalidraw_md_path)[: -len(".excalidraw.md")]
    output_dir = os.path.join(os.path.dirname(excalidraw_md_path), "processed_outputs")
    os.makedirs(output_dir, exist_ok=True)

    common_meta = {
        "source_excalidraw": os.path.basename(excalidraw_md_path),
        "source_png": os.path.basename(png_path),
        "folder_category": "excalidraw_notes",
        "routing": "excalidraw_chunked",
        "chunks": num_chunks,
        "model": transcription_model,
        "tags": [],
    }

    raw_path = os.path.join(output_dir, f"{base_name}.excalidraw.md")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(build_frontmatter(common_meta) + raw_markdown)

    rag_meta = dict(common_meta)
    rag_meta.update(expansion_meta)
    rag_path = os.path.join(output_dir, f"{base_name}.excalidraw.rag.md")
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(build_frontmatter(rag_meta) + expanded_markdown)

    try:
        file_id = compute_file_id(excalidraw_md_path)
        rel_rag_path = os.path.relpath(rag_path, academic_hub_root).replace(os.sep, "/")
        rel_source_path = os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/")
        course = derive_course(rel_source_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_rag_path, source_pdf_path=rel_source_path,
            course=course, folder_category="excalidraw_notes", content_sample=expanded_markdown,
            page_count=num_chunks, client=client, content_hash=compute_content_hash(rag_path),
            known_doc_types=EXCALIDRAW_DOC_TYPES,
        )
    except Exception as err:
        print(f"WARNING: source-indexer update failed for {rag_path} ({err}); "
              f"rerun `python -m indexer.index_search rebuild` later to catch it up.")

    return raw_path, rag_path
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add indexer/index_card.py notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): write raw+expanded outputs and register with the source indexer"
```

---

### Task 10: End-to-end orchestration and CLI

**Files:**
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: everything from Tasks 1-9 (`chunk_image`, `resize_chunk_for_api`, `discover_excalidraw_files`, `transcribe_chunks`, `assemble_raw_markdown`, `expand_transcription`, `write_outputs`), plus `indexer.index_search.search_passages` (optional grounding) and `PIL.Image.open`.
- Produces: `process_excalidraw_note(excalidraw_md_path: str, png_path: str, client, model: str, expand_backend: str, academic_hub_root: str, use_grounding: bool = False, dry_run: bool = False) -> None`, `main()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py (add to existing file)
from unittest.mock import MagicMock, patch

from notes.transcribe_excalidraw import process_excalidraw_note


def test_process_excalidraw_note_dry_run_does_not_call_apis(tmp_path):
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")

    with patch("notes.transcribe_excalidraw.transcribe_chunks") as mock_transcribe, \
         patch("notes.transcribe_excalidraw.expand_transcription") as mock_expand:
        process_excalidraw_note(
            str(md_path), str(png_path), client=None, model="gemini-3.6-flash",
            expand_backend="gemini", academic_hub_root=str(tmp_path), dry_run=True,
        )

    mock_transcribe.assert_not_called()
    mock_expand.assert_not_called()


def test_process_excalidraw_note_runs_full_pipeline(tmp_path):
    from PIL import Image
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(png_path)

    with patch("notes.transcribe_excalidraw.chunk_image", return_value=["chunk_image_1", "chunk_image_2"]), \
         patch("notes.transcribe_excalidraw.resize_chunk_for_api", side_effect=[b"bytes1", b"bytes2"]), \
         patch("notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "raw text 0", "1": "raw text 1"}), \
         patch("notes.transcribe_excalidraw.expand_transcription", return_value=("expanded text", {"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False})), \
         patch("notes.transcribe_excalidraw.write_outputs", return_value=("raw.md", "raw.rag.md")) as mock_write:
        process_excalidraw_note(
            str(md_path), str(png_path), client=object(), model="gemini-3.6-flash",
            expand_backend="gemini", academic_hub_root=str(tmp_path), dry_run=False,
        )

    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args.kwargs
    assert call_kwargs["raw_markdown"] == "<!-- chunk 1 -->\n\nraw text 0\n\n<!-- chunk 2 -->\n\nraw text 1"
    assert call_kwargs["expanded_markdown"] == "expanded text"
    assert call_kwargs["num_chunks"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k process_excalidraw_note`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/transcribe_excalidraw.py (add import near the top, then append)
from PIL import Image

from notes.excalidraw_chunking import chunk_image, resize_chunk_for_api

_TRANSCRIBE_MODEL = "gemini-3.6-flash"  # same tier as transcribe_notes.py's
                                         # _MODEL_HANDWRITING -- these are all
                                         # handwriting-heavy vision transcription


def process_excalidraw_note(
    excalidraw_md_path: str, png_path: str, client, model: str,
    expand_backend: str, academic_hub_root: str, use_grounding: bool = False, dry_run: bool = False,
) -> None:
    print(f"Processing {os.path.basename(excalidraw_md_path)}...")
    if dry_run:
        print("  (dry run -- would chunk, transcribe, expand, and write outputs)")
        return

    image = Image.open(png_path)
    chunks = chunk_image(image)
    print(f"  {len(chunks)} chunks")
    chunk_bytes = [resize_chunk_for_api(c) for c in chunks]

    cache = transcribe_chunks(client, model, chunk_bytes)
    raw_markdown = assemble_raw_markdown(cache, total_chunks=len(chunks))

    retrieved_passages = None
    if use_grounding:
        from indexer.index_search import search_passages
        course = derive_course(os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/"))
        results = search_passages([academic_hub_root], query=raw_markdown[:500], client=client, course=course, top_k=3)
        retrieved_passages = [r.text for r in results] if results else None

    expanded_markdown, expansion_meta = expand_transcription(client, raw_markdown, expand_backend, retrieved_passages)

    write_outputs(
        excalidraw_md_path=excalidraw_md_path, png_path=png_path,
        raw_markdown=raw_markdown, expanded_markdown=expanded_markdown or "",
        transcription_model=model, expansion_meta=expansion_meta,
        num_chunks=len(chunks), academic_hub_root=academic_hub_root, client=client,
    )
    print(f"  wrote outputs to {os.path.dirname(excalidraw_md_path)}/processed_outputs/")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe and expand Excalidraw handwritten-notes canvases into markdown."
    )
    parser.add_argument(
        "--notes-subdir", required=True,
        help="Path, relative to the academic-hub/ folder next to this project, e.g. "
             "'academic_notes/math_methods/lecture_notes'.",
    )
    parser.add_argument("--file", default=None, help="Only process this one .excalidraw.md filename.")
    parser.add_argument("--model", default=_TRANSCRIBE_MODEL, help=f"Gemini vision model. Default: {_TRANSCRIBE_MODEL}.")
    parser.add_argument(
        "--expand-backend", default="gemini", choices=("gemini", "ollama"),
        help="Expansion backend (default: gemini). 'ollama' falls back to Gemini if unreachable.",
    )
    parser.add_argument("--grounding", action="store_true", help="Retrieve textbook passages to ground the expansion.")
    parser.add_argument("--dry-run", action="store_true", help="List files that would be processed without calling any API.")
    args = parser.parse_args()

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent / "academic-hub"
    notes_dir = academic_hub_dir / args.notes_subdir
    pairs = discover_excalidraw_files(str(notes_dir), args.file)
    if not pairs:
        print(f"No .excalidraw.md/.png pairs found under {notes_dir}.")
        sys.exit(1)

    client = None
    if not args.dry_run:
        client = get_gemini_client()
        if client is None:
            sys.exit(1)

    for md_path, png_path in pairs:
        process_excalidraw_note(
            md_path, png_path, client, args.model, args.expand_backend,
            str(academic_hub_dir), use_grounding=args.grounding, dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS (full file)

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (all tests, including every other subproject's)

- [ ] **Step 6: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): add end-to-end orchestration and CLI"
```

---

### Task 11: Real-corpus validation (manual, not automated)

Every subproject in this project gets validated against real data before being called done -- unit tests with mocked APIs prove the code paths work, not that the output is actually good. This task has no failing-test cycle; its deliverable is a documented, honest result.

**Files:**
- Modify: `docs/status/2026-08-24-notes-transcription-status.md`

- [ ] **Step 1: Run for real against both real tablet files**

```bash
cd academic-rag-model
.venv/Scripts/python.exe -m notes.transcribe_excalidraw --notes-subdir academic_notes/math_methods/lecture_notes
.venv/Scripts/python.exe -m notes.transcribe_excalidraw --notes-subdir academic_notes/microecon/lecture_notes
```

- [ ] **Step 2: Spot-check both `.rag.md` outputs against the source PNGs**

Open each `<name>.excalidraw.rag.md` next to its source `.png` and confirm: every equation/concept visible in the image appears in the expanded text, nothing was invented that isn't on the canvas, and the prose is genuinely more useful as a standalone explanation than the raw `.md` (not just the same text reworded).

- [ ] **Step 3: Record real findings**

Add a new dated section to `docs/status/2026-08-24-notes-transcription-status.md` (following the existing "2026-09-07"/"2026-09-09" section style): chunk counts observed, any transcription errors found, whether the expansion felt accurate vs. over-confident, actual token/cost numbers from `_log_token_usage`-style output if you wire that in, and whether the Gemini-vs-Ollama expansion backend choice held up (if you also test `--expand-backend ollama` for comparison -- worth doing once, given the spec left this genuinely undetermined).

- [ ] **Step 4: Update the tracker and reflections docs**

Update `docs/trackers/2026-08-30-academic-hub-status.md`'s notes-transcription bullet and `docs/brainstorms/Academic Hub Progress Reflections.md`'s handwritten-notes sub-bullet from "spec written, not yet planned/built" to "shipped, real-corpus validated" (or, honestly, whatever the Step 3 findings actually support -- if real testing surfaces a blocking gap, say so instead of overclaiming, matching this project's own established pattern).

- [ ] **Step 5: Commit**

```bash
git add docs/status/2026-08-24-notes-transcription-status.md docs/trackers/2026-08-30-academic-hub-status.md "docs/brainstorms/Academic Hub Progress Reflections.md"
git commit -m "docs(excalidraw): record real-corpus validation results"
```
