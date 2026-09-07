# Audio Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `audio_generator/`, a subproject that converts a course's Markdown notes and converted textbooks into local, offline-playable MP3 narration, writing each `.mp3` as a sibling of its source `.md` in the hub so a student's own sync tooling picks it up for passive/commute listening.

**Architecture:** Four independent modules feeding one orchestrator: `cleaner.py` (Markdown → narration-ready prose), `discovery.py` (finds source `.md` files across the `notes`/`textbook` content types), `state.py` (SHA-256 content-hash idempotency, so a re-run only regenerates what changed), and `engine.py` (Piper primary / Kokoro-ONNX secondary TTS, converted to MP3 via pydub+ffmpeg). `pipeline.py` ties these together and is both the library entry point (`run_pipeline()`) and the CLI (`main()`), matching `video_notes/pipeline.py`'s convention rather than the spec's separate `cli.py` sketch — this project's actual most-recent precedent keeps CLI parsing in the same file as orchestration, and `discovery.py`/`state.py` are split out the same way `video_notes/pipeline_state.py` is split from `video_notes/pipeline.py`, rather than folded into one large `pipeline.py`. `discovery.py` yields one `SourceFile` per source `.md` (never per-chapter), so a later chapter-aware pipeline (explicitly deferred, not part of this plan) only has to change what `state.py` tracks and how many `.mp3`s get written per source — not how sources are found.

**Tech Stack:** Python 3, `unittest` + `unittest.mock` (this project's existing test stack, run via `pytest` or `python -m unittest`), `markdown` + `beautifulsoup4` (new deps, Markdown→prose), `piper-tts` (new dep, default TTS engine), `kokoro-onnx` + `soundfile` (new deps, secondary TTS engine), `pydub` (new dep, WAV→MP3, requires `ffmpeg` on `PATH`).

**Spec:** `docs/superpowers/specs/2026-09-06-audio-generator-design.md`

## Global Constraints

- Local-only TTS (Piper default, Kokoro-ONNX secondary) — no cloud API, no GPU requirement (spec §1).
- Exactly two content types in v1: `notes` (`academic_notes/<course>/`, every category, including `video_notes`'s `lecture-notes/`) and `textbook` (`academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/`) — journal-articles are explicitly out of scope, not partially supported (spec §1 non-goal).
- No `indexer/index_search.py` changes of any kind — an MP3 is a derived rendering of an already-indexed `.md`, never itself indexed (spec §1 non-goal).
- No auto-triggering from other pipelines — `audio_generator` is invoked manually via its own CLI only (spec §1 non-goal).
- Every generated `.mp3` is written as a sibling of its source `.md` (same directory, same basename) inside the hub content repo — never inside `academic-rag-model`'s own gitignored cache (spec §2, §5).
- Idempotency state (`audio_generator/.cache/state.json`) and downloaded TTS model files (`audio_generator/models/`) are code-repo-local and gitignored — bookkeeping and large binaries, not deliverables (spec §2).
- `video_notes`-style inline timestamp citations (`([04:12](https://youtu.be/...))`) are stripped before narration, never read aloud (spec §3).
- Images/figures are silently skipped, not narrated — `textbook/describe_images.py`'s output is not read in v1 (spec §1 non-goal).
- No length cap on generated audio, and no chapter-splitting in this plan — flagged as a genuinely separate, larger follow-on for the broader project (spec §9; the user's explicit note for this planning pass). `discovery.py`'s one-`SourceFile`-per-source-`.md` design must not be built in a way that would need to be ripped out if chapter-splitting is added later.
- The textbook folder-name alias (`textbooks` vs. `textbooks-and-papers`) is checked exactly the way `indexer/index_search.py:213`'s `_TEXTBOOK_FOLDER_NAMES` already does, duplicated locally rather than imported (this project's existing pattern: each subproject owns its own small pieces of hub-layout knowledge, e.g. `video_notes`'s own `DEFAULT_ACADEMIC_HUB_ROOT`, rather than a shared hub-layout module).
- A textbook's `.rag.md` sibling (confirmed present alongside every real `<name>.md` under `processed_outputs/<book>/`, e.g. `Axler_Linear_Algebra_Done_Right_2026.rag.md`) must never be picked up as a second source file.
- Tests mirror the project's existing flat `tests/` convention (package-qualified imports via the root `conftest.py`) and mock every external boundary — no real Piper/Kokoro model files, no real `ffmpeg` invocation, no real network access in tests (spec §8).
- Two module names collide with existing subprojects' own generically-named modules in the flat `tests/` directory: `discovery.py` (`journal_discovery` already has one, tested by `tests/test_discovery.py`) and `pipeline.py` (`video_notes` already has one, tested by `tests/test_pipeline.py`). This was caught during execution after `tests/test_discovery.py` was accidentally overwritten and had to be restored from git history — the corrected, disambiguated names used throughout this plan are `tests/test_audio_generator_discovery.py` and `tests/test_audio_generator_pipeline.py`.

---

### Task 1: Package scaffolding, Markdown-to-prose dependencies, and `cleaner.py`

**Files:**
- Create: `audio_generator/__init__.py`
- Create: `audio_generator/cleaner.py`
- Modify: `requirements.txt`
- Test: `tests/test_cleaner.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: the `audio_generator` package; `clean_markdown_for_speech(md_text: str) -> str`. Every later task that turns a `.md` file's content into narration text calls this exact function.

- [ ] **Step 1: Add the Markdown-to-prose dependencies to `requirements.txt`**

In `requirements.txt`, add a new section:

```
# Audio Generator
markdown
beautifulsoup4
```

- [ ] **Step 2: Install the new dependencies**

Run: `./.venv/Scripts/python.exe -m pip install markdown beautifulsoup4`
Expected: both install successfully.

- [ ] **Step 3: Write the failing tests**

Create `tests/test_cleaner.py`:

```python
import unittest

from audio_generator.cleaner import clean_markdown_for_speech


class TestCleanMarkdownForSpeech(unittest.TestCase):
    def test_strips_fenced_code_blocks(self):
        md = "Before.\n```python\nprint('hi')\n```\nAfter."
        result = clean_markdown_for_speech(md)
        self.assertNotIn("print", result)
        self.assertIn("Code snippet omitted", result)
        self.assertIn("Before.", result)
        self.assertIn("After.", result)

    def test_unwraps_inline_code(self):
        result = clean_markdown_for_speech("Call `foo()` to start.")
        self.assertIn("foo()", result)
        self.assertNotIn("`", result)

    def test_converts_block_latex_to_equation_prose(self):
        result = clean_markdown_for_speech("$$x^2 + y^2 = z^2$$")
        self.assertIn("Equation:", result)
        self.assertIn("x^2", result)

    def test_converts_inline_latex(self):
        result = clean_markdown_for_speech("The value is $x = 3$ here.")
        self.assertIn("x = 3", result)
        self.assertNotIn("$", result)

    def test_strips_video_notes_style_citations(self):
        md = "The eigenvalue of the matrix is 3 ([04:12](https://youtu.be/abc123&t=252s))."
        result = clean_markdown_for_speech(md)
        self.assertNotIn("04:12", result)
        self.assertNotIn("youtu.be", result)
        self.assertIn("The eigenvalue of the matrix is 3", result)

    def test_strips_remaining_markdown_syntax(self):
        result = clean_markdown_for_speech("# Heading\n\n- item one\n- item two")
        self.assertIn("Heading", result)
        self.assertIn("item one", result)
        self.assertIn("item two", result)
        self.assertNotIn("#", result)
        self.assertNotIn("- item", result)

    def test_image_markup_is_silently_dropped(self):
        result = clean_markdown_for_speech("See ![a diagram](images/fig1.png) below.")
        self.assertNotIn("fig1.png", result)
        self.assertIn("See", result)
        self.assertIn("below.", result)

    def test_normalizes_whitespace(self):
        result = clean_markdown_for_speech("Too    much\n\n\nwhitespace.")
        self.assertNotIn("  ", result)

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(clean_markdown_for_speech(""), "")

    def test_whitespace_only_input_returns_empty_string(self):
        self.assertEqual(clean_markdown_for_speech("   \n\n  "), "")
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cleaner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator'`

- [ ] **Step 5: Create the package**

Create `audio_generator/__init__.py` (empty file).

- [ ] **Step 6: Implement `cleaner.py`**

Create `audio_generator/cleaner.py`:

```python
"""
cleaner.py
Markdown-to-prose conversion for TTS narration: strips code blocks, LaTeX
delimiters, video_notes-style inline timestamp citations, and remaining
markdown syntax so the result reads as natural prose. Spec §3.
"""
from __future__ import annotations

import re

import markdown
from bs4 import BeautifulSoup

_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
_LATEX_BLOCK_PATTERN = re.compile(r"\$\$([^\$]+)\$\$")
_LATEX_INLINE_PATTERN = re.compile(r"\$([^\$]+)\$")
# Matches a video_notes-style citation attached to a sentence, e.g.
# "([04:12](https://youtu.be/abc123&t=252s))" -- only has value as a
# clickable link, meaningless read aloud (spec §3).
_CITATION_PATTERN = re.compile(r"\(\[[\d:]+\]\([^)]+\)\)")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_markdown_for_speech(md_text: str) -> str:
    """Converts raw Markdown into narration-ready prose (spec §3, steps 1-5,
    applied in this exact order)."""
    text = _CODE_BLOCK_PATTERN.sub(" [Code snippet omitted.] ", md_text)
    text = _INLINE_CODE_PATTERN.sub(r"\1", text)
    text = _LATEX_BLOCK_PATTERN.sub(r" Equation: \1. ", text)
    text = _LATEX_INLINE_PATTERN.sub(r" \1 ", text)
    text = _CITATION_PATTERN.sub("", text)
    html = markdown.markdown(text)
    soup = BeautifulSoup(html, "html.parser")
    clean_text = soup.get_text(separator=" ")
    return _WHITESPACE_PATTERN.sub(" ", clean_text).strip()
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_cleaner.py -v`
Expected: PASS (10 tests)

- [ ] **Step 8: Commit**

```bash
git add audio_generator/__init__.py audio_generator/cleaner.py requirements.txt tests/test_cleaner.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): scaffold package, add Markdown-to-prose cleaner

First piece of the audio_generator pipeline: converts raw Markdown into
narration-ready prose, including stripping video_notes's dense inline
timestamp citations (meaningless read aloud) before the general
markdown-stripping pass.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01N77F8Q3KtxtyKjUu7rtud7
EOF
)"
```

---

### Task 2: `discovery.py` — source file discovery across `notes` and `textbook`

**Files:**
- Create: `audio_generator/discovery.py`
- Test: `tests/test_audio_generator_discovery.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `CONTENT_TYPES = ("notes", "textbook")`; `SourceFile` (dataclass: `course: str, content_type: str, rel_md_path: str, abs_md_path: str, rel_mp3_path: str, abs_mp3_path: str`); `discover_source_files(academic_hub_root: str, course: str, content_types: list[str]) -> list[SourceFile]`. Every later task that needs "what should get audio" uses this exact `SourceFile` shape and function.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_generator_discovery.py`:

```python
import os
import tempfile
import unittest

from audio_generator.discovery import discover_source_files


def _touch(path: str, content: str = "content") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestDiscoverNotes(unittest.TestCase):
    def test_finds_md_directly_in_a_category(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture-notes", "real-analysis.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].content_type, "notes")
            self.assertEqual(sources[0].rel_md_path, "academic_notes/math-camp/lecture-notes/real-analysis.md")
            self.assertEqual(sources[0].rel_mp3_path, "academic_notes/math-camp/lecture-notes/real-analysis.mp3")

    def test_finds_md_in_a_category_processed_outputs_subfolder(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "ta_notes", "processed_outputs", "Aug 17 Analysis.md"))
            _touch(os.path.join(hub, "academic_notes", "math-camp", "ta_notes", "LN1-Analysis.pdf"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].rel_md_path.endswith("Aug 17 Analysis.md"))

    def test_ignores_non_md_sidecar_files(self):
        with tempfile.TemporaryDirectory() as hub:
            base = os.path.join(hub, "academic_notes", "math-camp", "handwritten_notes", "processed_outputs")
            _touch(os.path.join(base, "Aug 17 Analysis.md"))
            _touch(os.path.join(base, "Aug 17 Analysis_pages_cache.json"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)

    def test_missing_course_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as hub:
            self.assertEqual(discover_source_files(hub, "nonexistent-course", ["notes"]), [])


class TestDiscoverTextbooks(unittest.TestCase):
    def test_finds_book_md_matching_its_own_folder_name(self):
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "Axler_2026")
            _touch(os.path.join(book_dir, "Axler_2026.md"))
            _touch(os.path.join(book_dir, "Axler_2026_metadata.json"))
            sources = discover_source_files(hub, "math-camp", ["textbook"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].content_type, "textbook")

    def test_excludes_the_rag_md_variant(self):
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "Axler_2026")
            _touch(os.path.join(book_dir, "Axler_2026.md"))
            _touch(os.path.join(book_dir, "Axler_2026.rag.md"))
            sources = discover_source_files(hub, "math-camp", ["textbook"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].abs_md_path.endswith("Axler_2026.md"))
            self.assertFalse(sources[0].abs_md_path.endswith(".rag.md"))

    def test_recognizes_both_textbook_folder_aliases(self):
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(
                hub, "academic_resources", "econometrics", "textbooks-and-papers", "processed_outputs", "Wooldridge_2020",
            )
            _touch(os.path.join(book_dir, "Wooldridge_2020.md"))
            sources = discover_source_files(hub, "econometrics", ["textbook"])
            self.assertEqual(len(sources), 1)


class TestDiscoverSourceFilesContentTypeFilter(unittest.TestCase):
    def test_defaults_can_combine_both_types(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture-notes", "a.md"))
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "B")
            _touch(os.path.join(book_dir, "B.md"))
            sources = discover_source_files(hub, "math-camp", ["notes", "textbook"])
            self.assertEqual({s.content_type for s in sources}, {"notes", "textbook"})

    def test_rejects_unknown_content_type(self):
        with tempfile.TemporaryDirectory() as hub:
            with self.assertRaises(ValueError):
                discover_source_files(hub, "math-camp", ["journal-article"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_audio_generator_discovery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator.discovery'`

- [ ] **Step 3: Implement `discovery.py`**

Create `audio_generator/discovery.py`:

```python
"""
discovery.py
Finds every source .md file audio_generator should (re)generate audio for,
across the two in-scope content types (spec §5, §1): a course's own notes
(academic_notes/<course>/, all categories -- this already includes
video_notes's synthesized lecture notes, since those live in
academic_notes/<course>/lecture-notes/) and its converted textbooks
(academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/).

Returns one SourceFile per source .md -- not per chapter/section -- so a
future chapter-aware pipeline (spec §9's deferred follow-on) can change what
state.py tracks and how many .mp3s pipeline.py writes per source, without
needing to change discovery itself.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Mirrors indexer/index_search.py's _TEXTBOOK_FOLDER_NAMES (spec §5) --
# duplicated locally rather than imported, matching this project's existing
# pattern of each subproject owning its own small pieces of hub-layout
# knowledge (e.g. video_notes's own DEFAULT_ACADEMIC_HUB_ROOT) rather than a
# shared hub-layout module.
_TEXTBOOK_FOLDER_NAMES = ("textbooks", "textbooks-and-papers")

CONTENT_TYPES = ("notes", "textbook")


@dataclass
class SourceFile:
    course: str
    content_type: str  # "notes" | "textbook"
    rel_md_path: str  # hub-relative, e.g. "academic_notes/math-camp/ta_notes/processed_outputs/Aug 17 Analysis.md"
    abs_md_path: str
    rel_mp3_path: str  # same directory and basename, .mp3 extension (spec §5)
    abs_mp3_path: str


def _is_real_md_file(name: str) -> bool:
    """True for a real source .md -- excludes the textbook pipeline's
    `.rag.md` sibling variant (a separate, differently-formatted file that
    happens to also end in ".md")."""
    lower = name.lower()
    return lower.endswith(".md") and not lower.endswith(".rag.md")


def _make_source_file(academic_hub_root: str, course: str, content_type: str, abs_md_path: str) -> SourceFile:
    rel_md_path = os.path.relpath(abs_md_path, academic_hub_root).replace(os.sep, "/")
    abs_mp3_path = os.path.splitext(abs_md_path)[0] + ".mp3"
    rel_mp3_path = os.path.splitext(rel_md_path)[0] + ".mp3"
    return SourceFile(
        course=course, content_type=content_type,
        rel_md_path=rel_md_path, abs_md_path=abs_md_path,
        rel_mp3_path=rel_mp3_path, abs_mp3_path=abs_mp3_path,
    )


def _discover_notes(academic_hub_root: str, course: str) -> list:
    course_dir = os.path.join(academic_hub_root, "academic_notes", course)
    if not os.path.isdir(course_dir):
        return []
    sources = []
    for category in sorted(os.listdir(course_dir)):
        category_dir = os.path.join(course_dir, category)
        if not os.path.isdir(category_dir):
            continue
        # A category holds its .md files either directly (plain markdown
        # notes, e.g. "markdown"/"lecture-notes") or under its own
        # processed_outputs/ (OCR'd/converted notes, e.g. "ta_notes") --
        # both are checked, non-recursively (spec §5).
        for scan_dir in (category_dir, os.path.join(category_dir, "processed_outputs")):
            if not os.path.isdir(scan_dir):
                continue
            for name in sorted(os.listdir(scan_dir)):
                candidate = os.path.join(scan_dir, name)
                if _is_real_md_file(name) and os.path.isfile(candidate):
                    sources.append(_make_source_file(academic_hub_root, course, "notes", candidate))
    return sources


def _discover_textbooks(academic_hub_root: str, course: str) -> list:
    sources = []
    for folder_name in _TEXTBOOK_FOLDER_NAMES:
        processed_outputs_dir = os.path.join(
            academic_hub_root, "academic_resources", course, folder_name, "processed_outputs",
        )
        if not os.path.isdir(processed_outputs_dir):
            continue
        for book_folder in sorted(os.listdir(processed_outputs_dir)):
            book_dir = os.path.join(processed_outputs_dir, book_folder)
            if not os.path.isdir(book_dir):
                continue
            md_path = os.path.join(book_dir, f"{book_folder}.md")
            if os.path.isfile(md_path):
                sources.append(_make_source_file(academic_hub_root, course, "textbook", md_path))
    return sources


def discover_source_files(academic_hub_root: str, course: str, content_types: list) -> list:
    for content_type in content_types:
        if content_type not in CONTENT_TYPES:
            raise ValueError(f"Unknown content type {content_type!r}, expected one of {CONTENT_TYPES}")
    sources = []
    if "notes" in content_types:
        sources.extend(_discover_notes(academic_hub_root, course))
    if "textbook" in content_types:
        sources.extend(_discover_textbooks(academic_hub_root, course))
    return sources
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_audio_generator_discovery.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add audio_generator/discovery.py tests/test_audio_generator_discovery.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): add source-file discovery for notes and textbooks

Walks academic_notes/<course>/ (all categories) and
academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/
(both folder-name aliases) for real source .md files, explicitly excluding
the textbook pipeline's .rag.md sibling variant. Yields one SourceFile per
source file, keeping later chapter-level splitting additive rather than a
rewrite.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01N77F8Q3KtxtyKjUu7rtud7
EOF
)"
```

---

### Task 3: `state.py` — content-hash idempotency tracking

**Files:**
- Create: `audio_generator/state.py`
- Modify: `.gitignore`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `audio_generator.discovery.SourceFile` (Task 2).
- Produces: `compute_content_hash(md_path: str) -> str`; `load_state(audio_generator_root: str) -> dict`; `save_state(audio_generator_root: str, state: dict) -> None`; `needs_regeneration(state: dict, source: SourceFile, current_hash: str) -> bool`. `pipeline.py` (Task 5) calls all four.

- [ ] **Step 1: Add the idempotency cache dir to `.gitignore`**

In `.gitignore`, add:

```
audio_generator/.cache/
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_state.py`:

```python
import os
import tempfile
import unittest

from audio_generator.discovery import SourceFile
from audio_generator.state import compute_content_hash, load_state, needs_regeneration, save_state


def _source(hub_dir: str, rel_md: str = "academic_notes/math-camp/lecture-notes/a.md") -> SourceFile:
    abs_md = os.path.join(hub_dir, rel_md.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_md), exist_ok=True)
    return SourceFile(
        course="math-camp", content_type="notes",
        rel_md_path=rel_md, abs_md_path=abs_md,
        rel_mp3_path=rel_md[:-3] + ".mp3", abs_mp3_path=abs_md[:-3] + ".mp3",
    )


class TestComputeContentHash(unittest.TestCase):
    def test_same_content_same_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("hello")
            self.assertEqual(compute_content_hash(path), compute_content_hash(path))

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path_a, path_b = os.path.join(tmp, "a.md"), os.path.join(tmp, "b.md")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write("hello")
            with open(path_b, "w", encoding="utf-8") as f:
                f.write("hello there")
            self.assertNotEqual(compute_content_hash(path_a), compute_content_hash(path_b))


class TestStateRoundTrip(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_state(tmp, {"academic_notes/math-camp/lecture-notes/a.md": "abc123"})
            self.assertEqual(load_state(tmp), {"academic_notes/math-camp/lecture-notes/a.md": "abc123"})

    def test_missing_state_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_state(tmp), {})


class TestNeedsRegeneration(unittest.TestCase):
    def test_true_when_no_prior_record(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            self.assertTrue(needs_regeneration({}, source, "somehash"))

    def test_false_when_hash_matches_and_mp3_exists(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            state = {source.rel_md_path: "somehash"}
            self.assertFalse(needs_regeneration(state, source, "somehash"))

    def test_true_when_hash_matches_but_mp3_is_missing(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            state = {source.rel_md_path: "somehash"}
            self.assertTrue(needs_regeneration(state, source, "somehash"))

    def test_true_when_hash_differs(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            state = {source.rel_md_path: "oldhash"}
            self.assertTrue(needs_regeneration(state, source, "newhash"))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator.state'`

- [ ] **Step 4: Implement `state.py`**

Create `audio_generator/state.py`:

```python
"""
state.py
Content-hash idempotency tracking for audio_generator: which source .md
files already have up-to-date audio, so a re-run only (re)generates what
changed. Spec §2, §5 -- code-repo-local, gitignored (a flat file, since
there's no per-item pipeline stage to track here beyond "is this .mp3
current", unlike video_notes's richer per-video/per-group state).
"""
from __future__ import annotations

import hashlib
import json
import os


def _state_dir(audio_generator_root: str) -> str:
    return os.path.join(audio_generator_root, ".cache")


def _state_path(audio_generator_root: str) -> str:
    return os.path.join(_state_dir(audio_generator_root), "state.json")


def compute_content_hash(md_path: str) -> str:
    with open(md_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_state(audio_generator_root: str) -> dict:
    """Maps a source's rel_md_path to the content hash it had when its
    .mp3 was last (re)generated."""
    path = _state_path(audio_generator_root)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(audio_generator_root: str, state: dict) -> None:
    path = _state_path(audio_generator_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def needs_regeneration(state: dict, source, current_hash: str) -> bool:
    """True if source's .mp3 is missing, or its .md content hash has
    changed since the .mp3 was last (re)generated (spec §5)."""
    if not os.path.exists(source.abs_mp3_path):
        return True
    return state.get(source.rel_md_path) != current_hash
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_state.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add audio_generator/state.py .gitignore tests/test_state.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): add SHA-256 content-hash idempotency state

A re-run only regenerates a source's .mp3 when its .md content hash has
changed, or the .mp3 is missing entirely -- state.json is code-repo-local
and gitignored, matching video_notes's .state//.cache split.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01N77F8Q3KtxtyKjUu7rtud7
EOF
)"
```

---

### Task 4: `engine.py` — Piper / Kokoro-ONNX synthesis wrapper

**Files:**
- Create: `audio_generator/engine.py`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `ENGINES = ("piper", "kokoro")`; `synthesize_speech(text: str, output_mp3_path: str, engine: str = "piper") -> None`. `pipeline.py` (Task 5) calls this exact function.

**Note on API accuracy:** the brainstorm source material's script called `voice.synthesize(text, wav_file)` for Piper — verified against the current `piper-tts`/`piper1-gpl` API docs, that method actually streams audio chunks rather than writing to a wave file object; the correct call for writing directly to an open `wave.Wave_write` is `voice.synthesize_wav(text, wav_file, syn_config=None)`. This task uses the verified, correct method name. Likewise, `kokoro-onnx`'s real API (verified against its own repo example) is `Kokoro(model_path, voices_path).create(text, voice=..., speed=..., lang=...) -> (samples, sample_rate)`, saved via `soundfile.write(path, samples, sample_rate)` — not guessed from the engine-comparison table alone.

- [ ] **Step 1: Add the TTS dependencies to `requirements.txt`**

In `requirements.txt`, under the "# Audio Generator" section added in Task 1, add:

```
piper-tts
kokoro-onnx
soundfile
pydub
audioop-lts  # pydub needs this on Python 3.13+, whose stdlib dropped audioop (PEP 594)
```

- [ ] **Step 2: Install the new dependencies**

Run: `./.venv/Scripts/python.exe -m pip install piper-tts kokoro-onnx soundfile pydub audioop-lts`
Expected: all install successfully. (Actual Piper/Kokoro model files are not downloaded here — see Task 5's final manual-verification step for where real model files matter; this task's tests mock both engines entirely. `audioop-lts` was discovered as a real, necessary dependency during execution, not anticipated when this plan was written: `pydub` imports the stdlib `audioop` module, removed from Python 3.13's standard library — without this backport, `import pydub` itself raises `ModuleNotFoundError: No module named 'pyaudioop'`. Verified against the actually-installed `piper-tts`/`kokoro-onnx` packages that `PiperVoice.load`/`synthesize_wav` and `Kokoro`/`create` match the signatures `engine.py` below uses.)

- [ ] **Step 3: Add the downloaded-model directory to `.gitignore`**

In `.gitignore`, add:

```
audio_generator/models/
```

- [ ] **Step 4: Write the failing tests**

Create `tests/test_engine.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from audio_generator.engine import synthesize_speech


class TestSynthesizeSpeech(unittest.TestCase):
    @patch("audio_generator.engine.AudioSegment")
    @patch("audio_generator.engine._synthesize_piper_wav")
    def test_piper_engine_receives_the_given_text(self, mock_piper, mock_audio_segment):
        mock_audio_segment.from_wav.return_value = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.mp3")
            synthesize_speech("hello world", output_path, engine="piper")
        mock_piper.assert_called_once()
        self.assertEqual(mock_piper.call_args[0][0], "hello world")

    @patch("audio_generator.engine.AudioSegment")
    @patch("audio_generator.engine._synthesize_kokoro_wav")
    def test_kokoro_engine_receives_the_given_text(self, mock_kokoro, mock_audio_segment):
        mock_audio_segment.from_wav.return_value = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.mp3")
            synthesize_speech("hello world", output_path, engine="kokoro")
        mock_kokoro.assert_called_once()
        self.assertEqual(mock_kokoro.call_args[0][0], "hello world")

    def test_unknown_engine_raises_before_synthesizing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                synthesize_speech("hello", os.path.join(tmp, "out.mp3"), engine="not-a-real-engine")

    @patch("audio_generator.engine.AudioSegment")
    @patch("audio_generator.engine._synthesize_piper_wav")
    def test_exports_mp3_at_the_given_path(self, mock_piper, mock_audio_segment):
        exported_paths = []
        mock_audio_segment.from_wav.return_value.export.side_effect = (
            lambda path, **kw: exported_paths.append(path)
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.mp3")
            synthesize_speech("hello", output_path, engine="piper")
        self.assertEqual(exported_paths, [output_path])
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `python -m pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator.engine'`

- [ ] **Step 6: Implement `engine.py`**

Create `audio_generator/engine.py`:

```python
"""
engine.py
Wraps the two local TTS engines (spec §4): Piper (default, fast) and
Kokoro-ONNX (secondary, higher quality). Both synthesize to a temporary WAV;
pydub/ffmpeg then encodes the final .mp3 -- one shared conversion step
regardless of engine.
"""
from __future__ import annotations

import os
import tempfile
import wave

from pydub import AudioSegment

ENGINES = ("piper", "kokoro")

_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

DEFAULT_PIPER_MODEL_PATH = os.environ.get(
    "AUDIOGEN_PIPER_MODEL_PATH", os.path.join(_MODELS_DIR, "en_US-lessac-medium.onnx"),
)
DEFAULT_PIPER_CONFIG_PATH = os.environ.get(
    "AUDIOGEN_PIPER_CONFIG_PATH", os.path.join(_MODELS_DIR, "en_US-lessac-medium.onnx.json"),
)
DEFAULT_KOKORO_MODEL_PATH = os.environ.get(
    "AUDIOGEN_KOKORO_MODEL_PATH", os.path.join(_MODELS_DIR, "kokoro-v1.0.onnx"),
)
DEFAULT_KOKORO_VOICES_PATH = os.environ.get(
    "AUDIOGEN_KOKORO_VOICES_PATH", os.path.join(_MODELS_DIR, "voices-v1.0.bin"),
)
DEFAULT_KOKORO_VOICE = os.environ.get("AUDIOGEN_KOKORO_VOICE", "af_sarah")


def _synthesize_piper_wav(text: str, wav_path: str, model_path: str, config_path: str) -> None:
    from piper import PiperVoice

    voice = PiperVoice.load(model_path, config_path=config_path)
    with wave.open(wav_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)


def _synthesize_kokoro_wav(text: str, wav_path: str, model_path: str, voices_path: str, voice: str) -> None:
    import soundfile as sf
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(model_path, voices_path)
    samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
    sf.write(wav_path, samples, sample_rate)


def synthesize_speech(text: str, output_mp3_path: str, engine: str = "piper") -> None:
    """Synthesizes `text` to `output_mp3_path` using the given engine.
    Raises ValueError up front for an unknown engine name, before any
    synthesis work starts."""
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine {engine!r}, expected one of {ENGINES}")

    os.makedirs(os.path.dirname(output_mp3_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        wav_path = tmp_wav.name
    try:
        if engine == "piper":
            _synthesize_piper_wav(text, wav_path, DEFAULT_PIPER_MODEL_PATH, DEFAULT_PIPER_CONFIG_PATH)
        else:
            _synthesize_kokoro_wav(
                text, wav_path, DEFAULT_KOKORO_MODEL_PATH, DEFAULT_KOKORO_VOICES_PATH, DEFAULT_KOKORO_VOICE,
            )
        audio = AudioSegment.from_wav(wav_path)
        audio.export(output_mp3_path, format="mp3", bitrate="128k")
    finally:
        os.unlink(wav_path)
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_engine.py -v`
Expected: PASS (4 tests)

- [ ] **Step 8: Commit**

```bash
git add audio_generator/engine.py requirements.txt .gitignore tests/test_engine.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): add Piper/Kokoro-ONNX synthesis wrapper

Verified the real piper-tts and kokoro-onnx Python APIs before writing
this rather than trusting the brainstorm source's script as-is --
Piper's correct wave-file-writing call is synthesize_wav(), not
synthesize() (which streams chunks instead). Both engines synthesize to
a temp WAV; pydub/ffmpeg encodes the shared MP3 output.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01N77F8Q3KtxtyKjUu7rtud7
EOF
)"
```

---

### Task 5: `pipeline.py` — orchestration, CLI, and README

**Files:**
- Create: `audio_generator/pipeline.py`
- Create: `audio_generator/README.md`
- Test: `tests/test_audio_generator_pipeline.py`

**Interfaces:**
- Consumes: `clean_markdown_for_speech` (Task 1), `discover_source_files`/`CONTENT_TYPES` (Task 2), `compute_content_hash`/`load_state`/`save_state`/`needs_regeneration` (Task 3), `synthesize_speech`/`ENGINES` (Task 4).
- Produces: `run_pipeline(course: str, academic_hub_root: str, audio_generator_root: str, content_types: list, engine: str = "piper") -> dict` (summary dict with `generated`/`skipped_unchanged`/`skipped_empty`/`failed` counts); `main()` (CLI entry point).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_generator_pipeline.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

from audio_generator.discovery import SourceFile
from audio_generator.pipeline import run_pipeline
from audio_generator.state import load_state


def _make_source(hub: str, rel_md: str = "academic_notes/math-camp/lecture-notes/a.md", content: str = "hello world") -> SourceFile:
    abs_md = os.path.join(hub, rel_md.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_md), exist_ok=True)
    with open(abs_md, "w", encoding="utf-8") as f:
        f.write(content)
    return SourceFile(
        course="math-camp", content_type="notes",
        rel_md_path=rel_md, abs_md_path=abs_md,
        rel_mp3_path=rel_md[:-3] + ".mp3", abs_mp3_path=abs_md[:-3] + ".mp3",
    )


class TestRunPipeline(unittest.TestCase):
    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_generates_audio_for_a_new_source(self, mock_discover, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["generated"], 1)
            mock_synthesize.assert_called_once()
            self.assertEqual(mock_synthesize.call_args[0][1], source.abs_mp3_path)
            state = load_state(audio_generator_root)
            self.assertIn(source.rel_md_path, state)

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_skips_a_source_whose_mp3_is_already_up_to_date(self, mock_discover, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")

            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")
            mock_synthesize.reset_mock()
            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_unchanged"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_source_with_no_speakable_text_is_skipped_not_failed(self, mock_discover, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            # A bare image reference has no text node for BeautifulSoup's
            # get_text() to return -- unlike a code block, which cleaner.py
            # deliberately replaces with a non-empty "[Code snippet
            # omitted.]" placeholder (see test_cleaner.py). Caught during
            # execution: the original fixture here used a code-block-only
            # source, which never actually produces empty text.
            source = _make_source(hub, content="![diagram](img.png)")
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_empty"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech", side_effect=RuntimeError("engine crashed"))
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_failed_synthesis_is_recorded_and_does_not_raise(self, mock_discover, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["failed"], 1)
            state = load_state(audio_generator_root)
            self.assertNotIn(source.rel_md_path, state)

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_changed_source_is_regenerated(self, mock_discover, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="version one")
            mock_discover.return_value = [source]
            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            with open(source.abs_md_path, "w", encoding="utf-8") as f:
                f.write("version two, changed")
            mock_synthesize.reset_mock()

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")
            self.assertEqual(summary["generated"], 1)
            mock_synthesize.assert_called_once()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_audio_generator_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator.pipeline'`

- [ ] **Step 3: Implement `pipeline.py`**

Create `audio_generator/pipeline.py`:

```python
"""
pipeline.py
CLI entry point + orchestration for audio_generator: discover source .md
files for a course -> skip ones already up to date -> clean -> synthesize ->
write the sibling .mp3 -> update state. Spec:
docs/superpowers/specs/2026-09-06-audio-generator-design.md.

Run as a module from academic-rag-model/:
    python -m audio_generator.pipeline --course math-camp
    python -m audio_generator.pipeline --course math-camp --content-type textbook --engine kokoro
    python -m audio_generator.pipeline --course math-camp --dry-run
"""
from __future__ import annotations

import argparse
import os
import shutil

from audio_generator.cleaner import clean_markdown_for_speech
from audio_generator.discovery import CONTENT_TYPES, discover_source_files
from audio_generator.engine import ENGINES, synthesize_speech
from audio_generator.state import compute_content_hash, load_state, needs_regeneration, save_state

DEFAULT_ACADEMIC_HUB_ROOT = "../academic-hub"


def run_pipeline(
    course: str, academic_hub_root: str, audio_generator_root: str, content_types: list, engine: str = "piper",
) -> dict:
    sources = discover_source_files(academic_hub_root, course, content_types)
    state = load_state(audio_generator_root)
    summary = {"generated": 0, "skipped_unchanged": 0, "skipped_empty": 0, "failed": 0}

    for source in sources:
        current_hash = compute_content_hash(source.abs_md_path)
        if not needs_regeneration(state, source, current_hash):
            summary["skipped_unchanged"] += 1
            continue

        with open(source.abs_md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        text = clean_markdown_for_speech(md_text)
        if not text:
            print(f"WARNING: {source.rel_md_path} has no speakable text after cleaning -- skipping.")
            summary["skipped_empty"] += 1
            continue

        try:
            synthesize_speech(text, source.abs_mp3_path, engine=engine)
        except Exception as err:
            print(f"WARNING: failed to synthesize {source.rel_md_path}: {err}")
            summary["failed"] += 1
            continue

        state[source.rel_md_path] = current_hash
        summary["generated"] += 1

    save_state(audio_generator_root, state)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a course's Markdown notes/textbooks into local TTS audio (MP3s).",
    )
    parser.add_argument("--course", required=True, help="Matches an existing academic_notes/<course>/ or academic_resources/<course>/ folder.")
    parser.add_argument("--academic-hub-root", default=DEFAULT_ACADEMIC_HUB_ROOT)
    parser.add_argument(
        "--content-type", default=",".join(CONTENT_TYPES),
        help=f"Comma-separated subset of {CONTENT_TYPES}. Defaults to both.",
    )
    parser.add_argument("--engine", choices=ENGINES, default="piper")
    parser.add_argument("--dry-run", action="store_true", help="List what would be (re)generated without synthesizing anything.")
    args = parser.parse_args()

    content_types = [c.strip() for c in args.content_type.split(",") if c.strip()]
    audio_generator_root = os.path.dirname(os.path.abspath(__file__))

    if shutil.which("ffmpeg") is None:
        print(
            "WARNING: ffmpeg not found on PATH -- MP3 encoding will fail for every file. "
            "Install ffmpeg (e.g. `winget install ffmpeg` or https://ffmpeg.org/download.html) and retry.",
        )

    if args.dry_run:
        sources = discover_source_files(args.academic_hub_root, args.course, content_types)
        state = load_state(audio_generator_root)
        for source in sources:
            current_hash = compute_content_hash(source.abs_md_path)
            status = "regenerate" if needs_regeneration(state, source, current_hash) else "up to date"
            print(f"{status}: {source.rel_md_path}")
        return

    summary = run_pipeline(args.course, args.academic_hub_root, audio_generator_root, content_types, args.engine)
    print(f"Done: {summary}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_audio_generator_pipeline.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Write the README**

Create `audio_generator/README.md`:

```markdown
# audio_generator

Converts a course's Markdown notes and converted textbooks into local,
offline MP3 narration for passive/commute listening — no cloud API, no GPU.

Spec: `docs/superpowers/specs/2026-09-06-audio-generator-design.md`

## Usage

```bash
python -m audio_generator.pipeline --course math-camp
python -m audio_generator.pipeline --course math-camp --content-type textbook --engine kokoro
python -m audio_generator.pipeline --course math-camp --dry-run
```

- `--course` (required): matches an existing `academic_notes/<course>/` or
  `academic_resources/<course>/` folder.
- `--academic-hub-root` (default `../academic-hub`): the sibling hub repo.
- `--content-type` (default `notes,textbook`): comma-separated subset.
- `--engine` (`piper` default, `kokoro`): Piper is faster; Kokoro is higher
  quality but slower.
- `--dry-run`: lists what would be (re)generated without synthesizing.

## Output

Each source `<name>.md` gets a sibling `<name>.mp3` in the same hub
directory — no new folder taxonomy, so any existing sync tool that already
watches the student's notes picks up the audio too.

## Setup

Requires `ffmpeg` on `PATH`, and the TTS engine's model files present under
`audio_generator/models/` (gitignored — not committed):

- Piper (default): `en_US-lessac-medium.onnx` + `.onnx.json`, from
  https://huggingface.co/rhasspy/piper-voices
- Kokoro-ONNX: `kokoro-v1.0.onnx` + `voices-v1.0.bin`, from the
  `kokoro-onnx` project's releases

Override any model path via `AUDIOGEN_PIPER_MODEL_PATH`,
`AUDIOGEN_PIPER_CONFIG_PATH`, `AUDIOGEN_KOKORO_MODEL_PATH`,
`AUDIOGEN_KOKORO_VOICES_PATH`, `AUDIOGEN_KOKORO_VOICE`.

## Non-goals (see spec for rationale)

Journal-articles, auto-triggering from other pipelines, reading
image/figure descriptions aloud, indexer/RAG registration, and
chapter-level audio splitting are all explicitly out of scope for this
version.
```

- [ ] **Step 6: Manual end-to-end verification against the real hub**

Run (no TTS model files or `ffmpeg` required for `--dry-run` — it only
exercises discovery + idempotency state, not synthesis):

```bash
python -m audio_generator.pipeline --course math-camp --dry-run
```

Expected: prints one `regenerate: academic_notes/math-camp/...` or
`regenerate: academic_resources/math-camp/textbooks/...` line per real
source file found in the actual hub corpus, with no tracebacks. This
confirms discovery.py's folder-walking logic actually matches the real,
current hub layout (not just the synthetic fixtures in Task 2's tests).

- [ ] **Step 7: Commit**

```bash
git add audio_generator/pipeline.py audio_generator/README.md tests/test_audio_generator_pipeline.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): add pipeline orchestration, CLI, and README

Ties discovery, idempotency state, cleaning, and synthesis together into
run_pipeline() + a CLI main() (matching video_notes's convention of CLI
parsing living alongside orchestration, not a separate cli.py). A failed
synthesis is recorded and skipped, never stops the batch; --dry-run lists
pending work without requiring TTS model files or ffmpeg.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01N77F8Q3KtxtyKjUu7rtud7
EOF
)"
```
