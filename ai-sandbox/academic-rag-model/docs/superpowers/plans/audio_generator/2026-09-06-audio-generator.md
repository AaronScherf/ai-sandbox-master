# Audio Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status (2026-09-07):** Tasks 1-5 below are complete and shipped (commits
`d3adf7a`, `834a528`, `89ce42b`, `2b064a3`, `e3822c1`, `7cccb14`, all on
`main`, pushed to `origin`) — kept here as the historical record of v1.
**Task 6 onward is new work** for the spec's LLM-based LaTeX narration
revision (§3.1), added after real-corpus testing showed v1's regex
`Equation: <raw LaTeX>` wrap passes literal, unpronounceable LaTeX command
syntax straight through on real equation-dense notes.

**Goal:** Build `audio_generator/`, a subproject that converts a course's Markdown notes and converted textbooks into local, offline-playable MP3 narration, writing each `.mp3` as a sibling of its source `.md` in the hub so a student's own sync tooling picks it up for passive/commute listening.

**Architecture:** Four independent modules feeding one orchestrator: `cleaner.py` (Markdown → narration-ready prose), `discovery.py` (finds source `.md` files across the `notes`/`textbook` content types), `state.py` (SHA-256 content-hash idempotency, so a re-run only regenerates what changed), and `engine.py` (Piper primary / Kokoro-ONNX secondary TTS, converted to MP3 via pydub+ffmpeg). `pipeline.py` ties these together and is both the library entry point (`run_pipeline()`) and the CLI (`main()`), matching `video_notes/pipeline.py`'s convention rather than the spec's separate `cli.py` sketch — this project's actual most-recent precedent keeps CLI parsing in the same file as orchestration, and `discovery.py`/`state.py` are split out the same way `video_notes/pipeline_state.py` is split from `video_notes/pipeline.py`, rather than folded into one large `pipeline.py`. `discovery.py` yields one `SourceFile` per source `.md` (never per-chapter), so a later chapter-aware pipeline (explicitly deferred, not part of this plan) only has to change what `state.py` tracks and how many `.mp3`s get written per source — not how sources are found. **Revision (Task 6+):** a fifth module, `narrate.py`, runs *before* `cleaner.py` on the raw `.md`, chunking it and rewriting LaTeX math into natural language via a local Ollama call (`common/ollama_utils.py`, already shared by `viz/`/`problem_gen/`) — deliberately with zero dependency on `cleaner.py` in either direction (§3.1's design rationale below), so `cleaner.py` needs no code or test changes at all. A chunk `narrate.py` can't successfully rewrite is returned unmodified, and `cleaner.py`'s existing (unchanged) regex wrap catches whatever raw LaTeX survives downstream — the pre-revision behavior, now reached only by narration failures instead of every equation.

**Tech Stack:** Python 3, `unittest` + `unittest.mock` (this project's existing test stack, run via `pytest` or `python -m unittest`), `markdown` + `beautifulsoup4` (new deps, Markdown→prose), `piper-tts` (new dep, default TTS engine), `kokoro-onnx` + `soundfile` (new deps, secondary TTS engine), `pydub` (new dep, WAV→MP3, requires `ffmpeg` on `PATH`). **Revision (Task 6+):** no new dependencies — `narrate.py` only needs `common/ollama_utils.py`, already installed.

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

**Revision constraints (Task 6+, spec §3.1):**
- `narrate.py` does not import from `cleaner.py`, and `cleaner.py` is not modified — zero code or test changes to `cleaner.py` in this revision. Confirmed before writing any code: no `tests/test_narrate.py` already exists in this repo (unlike `discovery.py`/`pipeline.py` above), but this revision still uses the same disambiguated-naming convention for consistency: `tests/test_audio_generator_narrate.py`.
- `pipeline.py` calls `narrate.narrate_for_speech(md_text)` **first**, on the raw `.md`, then feeds its output into the existing `cleaner.clean_markdown_for_speech()` exactly as before — this specific order is required; the reverse would let `cleaner.py`'s own LaTeX regex mangle the text before `narrate.py` ever saw it.
- Retry semantics follow `common/ollama_utils.py`'s own `OllamaTimeout` docstring exactly: `call_ollama` returning `None` (server unreachable) never retries — an immediate second call cannot succeed either — and returns that chunk's original text unmodified right away. `call_ollama` returning `OLLAMA_TIMEOUT` (slow-but-alive), or a real response that fails the length-ratio sanity check, retries exactly once; if the retry also fails, return the chunk's original text unmodified. `narrate.py` never invents its own fallback text.
- `call_ollama`'s real signature (verified against `common/ollama_utils.py` and its real call sites in `video_notes/synthesize.py:86`, `problem_gen/llm_gen.py:230`, `viz/llm_fallback.py:267`): `call_ollama(prompt: str, model: str, request_timeout: int, url: str = OLLAMA_URL, num_ctx: int | None = None) -> str | None | OllamaTimeout`, called positionally as `call_ollama(prompt, model, request_timeout)`.
- A fenced code block is never split internally and never sent to the LLM at all — `narrate.py` runs before `cleaner.py` has stripped code blocks, and dropping a code sample into a "rewrite as spoken prose" prompt would only confuse the model.
- The fully-cleaned narration text — `narrate_for_speech()`'s output *after* it has already been through `cleaner.clean_markdown_for_speech()`, i.e. exactly what gets handed to `engine.synthesize_speech()` — is written to a new sibling `<name>.narrated.md`, gated by the exact same source-content-hash check that already gates `<name>.mp3`. No new caching schema.
- `discovery.py`'s `_is_real_md_file()` must exclude `*.narrated.md` in addition to the existing `*.rag.md` exclusion, or the next pipeline run would rediscover it as a new source file.
- Model default `qwen2-math:7b` (math-specialized, matching `problem_gen`'s own choice), overridable via `AUDIOGEN_NARRATE_OLLAMA_MODEL` — same override pattern as `PROBLEMGEN_OLLAMA_MODEL`/`VIDEONOTES_OLLAMA_MODEL`. Timeout default follows `video_notes`'s env-var-overridable-constant pattern (`VIDEONOTES_OLLAMA_TIMEOUT_SECONDS`), not `problem_gen`'s/`viz`'s hardcoded constants, since per-chunk CPU timing here is a genuinely unmeasured unknown (Task 8's manual verification step) that may need real-world tuning without a code change.
- No real Ollama calls in tests — `call_ollama` is mocked throughout, matching this project's established testing philosophy (spec §8).

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

---

## Revision: LLM-based LaTeX narration (spec §3.1)

Real-corpus testing against `academic_notes/math-camp/ta_notes/processed_outputs/LN_Probability.md`
(997 `$`-delimited spans) showed Task 1's regex `Equation: <raw LaTeX>` wrap
— validated only against the brainstorm's trivial `$$x^2+y^2=z^2$$` example —
passes literal, unpronounceable LaTeX command syntax straight through, e.g.
`\mathbb{E}[X] = \sum_{x} x \mathbb{P}(X = x)` read verbatim. Tasks 6-8 below
replace that step with a chunked, LLM-based rewrite. See the Global
Constraints' "Revision constraints (Task 6+)" section above for the design
rules every task here follows.

### Task 6: `narrate.py` — chunked LLM-based LaTeX narration

**Files:**
- Create: `audio_generator/narrate.py`
- Test: `tests/test_audio_generator_narrate.py`

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama(prompt: str, model: str, request_timeout: int) -> str | None | OllamaTimeout`, `common.ollama_utils.OLLAMA_TIMEOUT`.
- Produces: `narrate_for_speech(md_text: str) -> str`. Task 8 (`pipeline.py`) calls this first, before `cleaner.clean_markdown_for_speech()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_generator_narrate.py`:

```python
import unittest
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT

from audio_generator.narrate import narrate_for_speech

_LONG_PARAGRAPH_A = "Consider the random variable X. " * 60  # ~2000 chars
_LONG_PARAGRAPH_B = "Its expectation is written as follows. " * 60  # ~2400 chars


class TestNarrateForSpeechChunking(unittest.TestCase):
    @patch("audio_generator.narrate.call_ollama")
    def test_calls_ollama_once_per_paragraph_when_short(self, mock_call):
        mock_call.return_value = "A rewritten sentence long enough to pass the sanity check easily here."
        md_text = "First short paragraph.\n\nSecond short paragraph."
        narrate_for_speech(md_text)
        self.assertEqual(mock_call.call_count, 1)  # both paragraphs fit in one ~2-3K chunk together

    @patch("audio_generator.narrate.call_ollama")
    def test_splits_into_multiple_chunks_when_content_is_large(self, mock_call):
        mock_call.return_value = "A rewritten passage, long enough to pass the sanity check easily. " * 30
        md_text = f"{_LONG_PARAGRAPH_A}\n\n{_LONG_PARAGRAPH_B}\n\n{_LONG_PARAGRAPH_A}"
        narrate_for_speech(md_text)
        self.assertGreater(mock_call.call_count, 1)

    @patch("audio_generator.narrate.call_ollama")
    def test_never_sends_a_code_block_to_the_llm(self, mock_call):
        mock_call.return_value = None  # doesn't matter -- assert it's never called with code content
        md_text = "Before the code.\n\n```python\nprint('should never reach the LLM')\n```\n\nAfter the code."
        result = narrate_for_speech(md_text)
        for call_args in mock_call.call_args_list:
            self.assertNotIn("print(", call_args[0][0])
        self.assertIn("print('should never reach the LLM')", result)  # passed through untouched


class TestNarrateForSpeechRetryAndFallback(unittest.TestCase):
    @patch("audio_generator.narrate.call_ollama")
    def test_successful_rewrite_is_used(self, mock_call):
        mock_call.return_value = "The expected value of X is written as follows, a nice long rewrite."
        result = narrate_for_speech("Short original text with $E[X]$ in it.")
        self.assertEqual(result, mock_call.return_value)
        self.assertEqual(mock_call.call_count, 1)

    @patch("audio_generator.narrate.call_ollama")
    def test_none_response_falls_back_immediately_with_no_retry(self, mock_call):
        mock_call.return_value = None
        original = "Some original text with $E[X]$ that the LLM can't reach."
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(mock_call.call_count, 1)  # no retry against an unreachable server

    @patch("audio_generator.narrate.call_ollama")
    def test_timeout_retries_once_then_succeeds(self, mock_call):
        mock_call.side_effect = [OLLAMA_TIMEOUT, "The rewritten version, long enough to pass the sanity check."]
        result = narrate_for_speech("Some original text with $E[X]$ in it, long enough for a ratio check.")
        self.assertEqual(result, "The rewritten version, long enough to pass the sanity check.")
        self.assertEqual(mock_call.call_count, 2)

    @patch("audio_generator.narrate.call_ollama")
    def test_timeout_retries_once_then_falls_back(self, mock_call):
        mock_call.side_effect = [OLLAMA_TIMEOUT, OLLAMA_TIMEOUT]
        original = "Some original text with $E[X]$ that keeps timing out on every attempt made."
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(mock_call.call_count, 2)

    @patch("audio_generator.narrate.call_ollama")
    def test_too_short_response_retries_once_then_falls_back(self, mock_call):
        original = "A" * 200  # long original
        mock_call.side_effect = ["no", "no"]  # both far too short relative to `original`
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(mock_call.call_count, 2)

    @patch("audio_generator.narrate.call_ollama")
    def test_too_short_response_retries_once_then_succeeds(self, mock_call):
        original = "A" * 200
        mock_call.side_effect = ["no", "B" * 150]  # second attempt passes the ratio check
        result = narrate_for_speech(original)
        self.assertEqual(result, "B" * 150)
        self.assertEqual(mock_call.call_count, 2)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_audio_generator_narrate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator.narrate'`

- [ ] **Step 3: Implement `narrate.py`**

Create `audio_generator/narrate.py`:

```python
"""
narrate.py
Chunked, holistic LaTeX-to-narration rewrite via a local LLM, running
before cleaner.py on the raw .md (spec §3.1). Deliberately has zero
dependency on cleaner.py in either direction: a chunk this module can't
successfully rewrite is returned unmodified, and cleaner.py's existing
(unchanged) regex wrap catches whatever raw LaTeX survives downstream.
"""
from __future__ import annotations

import os
import re

from common.ollama_utils import call_ollama

AUDIOGEN_NARRATE_OLLAMA_MODEL = os.environ.get("AUDIOGEN_NARRATE_OLLAMA_MODEL", "qwen2-math:7b")
AUDIOGEN_NARRATE_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("AUDIOGEN_NARRATE_OLLAMA_TIMEOUT", "300"))

_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
_PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")
_CHUNK_TARGET_SIZE = 2500
_MIN_LENGTH_RATIO = 0.5

_PROMPT_TEMPLATE = """Rewrite this passage as natural spoken prose for audio narration. \
Describe mathematical notation in words rather than symbols. Do not omit or summarize any \
content -- rewrite every sentence, changing only how notation is expressed.

--- PASSAGE START ---
{chunk}
--- PASSAGE END ---"""


def _split_into_pieces(md_text: str) -> list[str]:
    """Splits on paragraph boundaries, treating a fenced code block as one
    atomic piece regardless of blank lines inside it (spec §3.1)."""
    pieces = []
    pos = 0
    for match in _CODE_BLOCK_PATTERN.finditer(md_text):
        before = md_text[pos:match.start()]
        pieces.extend(p for p in _PARAGRAPH_SPLIT_PATTERN.split(before) if p.strip())
        pieces.append(match.group())
        pos = match.end()
    pieces.extend(p for p in _PARAGRAPH_SPLIT_PATTERN.split(md_text[pos:]) if p.strip())
    return pieces


def _group_into_chunks(pieces: list[str]) -> list[str]:
    """Groups paragraph pieces into ~_CHUNK_TARGET_SIZE-character chunks.
    A code-block piece is never merged with anything else -- it always
    becomes its own chunk (spec §3.1)."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for piece in pieces:
        if _CODE_BLOCK_PATTERN.fullmatch(piece):
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.append(piece)
            continue
        if current and current_len + len(piece) > _CHUNK_TARGET_SIZE:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(piece)
        current_len += len(piece)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _passes_sanity_check(original: str, rewritten) -> bool:
    """Cheap proxy for 'did the model drop/summarize content' (spec §3.1,
    §9 -- exact ratio flagged as needing real tuning, not a validated
    constant)."""
    if not isinstance(rewritten, str) or not rewritten.strip():
        return False
    return len(rewritten) >= _MIN_LENGTH_RATIO * len(original)


def _narrate_chunk(chunk: str) -> str:
    """Rewrites one chunk via the local LLM. Never raises; returns the
    chunk's original, unmodified text on any failure that survives a
    retry (spec §3.1) -- this module never invents its own fallback text."""
    prompt = _PROMPT_TEMPLATE.format(chunk=chunk)
    for _ in range(2):
        result = call_ollama(prompt, AUDIOGEN_NARRATE_OLLAMA_MODEL, AUDIOGEN_NARRATE_OLLAMA_TIMEOUT_SECONDS)
        if result is None:
            return chunk  # server unreachable -- not worth retrying
        if isinstance(result, str) and _passes_sanity_check(chunk, result):
            return result
        # OLLAMA_TIMEOUT, or a real response that failed the sanity check -- retry once
    return chunk


def narrate_for_speech(md_text: str) -> str:
    """Entry point pipeline.py calls first, on raw .md text, before
    cleaner.clean_markdown_for_speech() (spec §3.1)."""
    chunks = _group_into_chunks(_split_into_pieces(md_text))
    narrated = [
        chunk if _CODE_BLOCK_PATTERN.fullmatch(chunk) else _narrate_chunk(chunk)
        for chunk in chunks
    ]
    return "\n\n".join(narrated)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_audio_generator_narrate.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add audio_generator/narrate.py tests/test_audio_generator_narrate.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): add chunked LLM-based LaTeX narration

Real-corpus testing (LN_Probability.md, 997 LaTeX spans) showed the
regex Equation-wrap step passes raw, unpronounceable LaTeX command
syntax straight through. narrate_for_speech() chunks raw .md on paragraph
boundaries (never through a fenced code block, never sent to the LLM),
rewrites each chunk via a local Ollama call, and falls back to that
chunk's original text on any failure a retry doesn't resolve -- zero
dependency on cleaner.py in either direction; its existing regex wrap
catches whatever raw LaTeX survives downstream.

Retry semantics follow common/ollama_utils.py's own OllamaTimeout
docstring: None (server unreachable) never retries, OLLAMA_TIMEOUT
(slow-but-alive) retries once, matching problem_gen's established
pattern.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012utPaFRMX7eLAtcGdRJhcE
EOF
)"
```

---

### Task 7: `discovery.py` — exclude the new `.narrated.md` sibling

**Files:**
- Modify: `audio_generator/discovery.py:33-38` (`_is_real_md_file`)
- Test: `tests/test_audio_generator_discovery.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: no change to `discover_source_files`'s signature or behavior for existing content — only narrows what counts as a real source `.md`.

- [ ] **Step 1: Write the failing test**

In `tests/test_audio_generator_discovery.py`, add this test method to the
existing `TestDiscoverNotes` class (alongside `test_ignores_non_md_sidecar_files`):

```python
    def test_excludes_the_narrated_md_sibling(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture-notes", "real-analysis.md"))
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture-notes", "real-analysis.narrated.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].rel_md_path.endswith("real-analysis.md"))
            self.assertFalse(sources[0].rel_md_path.endswith(".narrated.md"))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_audio_generator_discovery.py -v -k narrated`
Expected: FAIL — `real-analysis.narrated.md` is currently discovered as a second source, so `len(sources)` is 2, not 1.

- [ ] **Step 3: Fix `_is_real_md_file`**

In `audio_generator/discovery.py`, change:

```python
def _is_real_md_file(name: str) -> bool:
    """True for a real source .md -- excludes the textbook pipeline's
    `.rag.md` sibling variant (a separate, differently-formatted file that
    happens to also end in ".md")."""
    lower = name.lower()
    return lower.endswith(".md") and not lower.endswith(".rag.md")
```

to:

```python
def _is_real_md_file(name: str) -> bool:
    """True for a real source .md -- excludes both the textbook pipeline's
    `.rag.md` sibling variant and audio_generator's own `.narrated.md`
    sibling (spec §3.1), each a separate, differently-formatted file that
    happens to also end in ".md"."""
    lower = name.lower()
    return lower.endswith(".md") and not lower.endswith((".rag.md", ".narrated.md"))
```

- [ ] **Step 4: Run the full discovery test suite to verify everything passes**

Run: `python -m pytest tests/test_audio_generator_discovery.py -v`
Expected: PASS (10 tests — the 9 already shipped, plus this new one)

- [ ] **Step 5: Commit**

```bash
git add audio_generator/discovery.py tests/test_audio_generator_discovery.py
git commit -m "$(cat <<'EOF'
fix(audio_generator): exclude .narrated.md from source discovery

Task 8 will write <name>.narrated.md as a sibling of every processed
source .md (spec §3.1). Without this exclusion, the next pipeline run
would discover that sibling as a brand-new source .md and generate audio
from it too -- the same class of bug the existing .rag.md exclusion
already guards against for the textbook pipeline.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012utPaFRMX7eLAtcGdRJhcE
EOF
)"
```

---

### Task 8: `pipeline.py` integration, README, and real CPU-timing measurement

**Files:**
- Modify: `audio_generator/pipeline.py`
- Modify: `audio_generator/README.md`
- Modify: `tests/test_audio_generator_pipeline.py`

**Interfaces:**
- Consumes: `narrate.narrate_for_speech(md_text: str) -> str` (Task 6).
- Produces: `run_pipeline()`'s existing signature is unchanged; it now also writes `<name>.narrated.md` as a sibling of `<name>.mp3` whenever it (re)generates audio.

- [ ] **Step 1: Update the existing tests to mock the new call, then add new coverage**

Replace `tests/test_audio_generator_pipeline.py` in full:

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
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_generates_audio_for_a_new_source(self, mock_discover, mock_narrate, mock_synthesize):
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
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_skips_a_source_whose_mp3_is_already_up_to_date(self, mock_discover, mock_narrate, mock_synthesize):
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
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_source_with_no_speakable_text_is_skipped_not_failed(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            # A bare image reference has no text node for BeautifulSoup's
            # get_text() to return -- unlike a code block, which cleaner.py
            # deliberately replaces with a non-empty "[Code snippet
            # omitted.]" placeholder (see test_cleaner.py).
            source = _make_source(hub, content="![diagram](img.png)")
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_empty"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech", side_effect=RuntimeError("engine crashed"))
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_failed_synthesis_is_recorded_and_does_not_raise(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["failed"], 1)
            state = load_state(audio_generator_root)
            self.assertNotIn(source.rel_md_path, state)
            self.assertFalse(os.path.exists(source.abs_md_path[:-3] + ".narrated.md"))

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_changed_source_is_regenerated(self, mock_discover, mock_narrate, mock_synthesize):
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

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_narrate_runs_before_clean_and_result_is_written_to_a_sibling_file(
        self, mock_discover, mock_narrate, mock_synthesize,
    ):
        mock_narrate.return_value = "# Heading\n\nThe expected value of X is three."
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="Some raw markdown with $E[X]$ in it.")
            mock_discover.return_value = [source]

            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            mock_narrate.assert_called_once_with("Some raw markdown with $E[X]$ in it.")
            narrated_path = source.abs_md_path[:-3] + ".narrated.md"
            self.assertTrue(os.path.exists(narrated_path))
            with open(narrated_path, "r", encoding="utf-8") as f:
                written = f.read()
            # The written file is cleaner.py's output (markup stripped),
            # not narrate.py's raw markdown-with-heading return value --
            # confirms clean_markdown_for_speech() ran on narrate.py's
            # output, in that order (spec §3.1).
            self.assertNotIn("#", written)
            self.assertIn("The expected value of X is three.", written)
            self.assertEqual(mock_synthesize.call_args[0][0], written)
```

- [ ] **Step 2: Run the tests to verify the new/changed ones fail as expected**

Run: `python -m pytest tests/test_audio_generator_pipeline.py -v`
Expected: the 5 pre-existing tests FAIL with
`AttributeError: <module 'audio_generator.pipeline'> does not have the attribute 'narrate_for_speech'`
(the `@patch` target doesn't exist yet); the new
`test_narrate_runs_before_clean_and_result_is_written_to_a_sibling_file`
fails the same way.

- [ ] **Step 3: Integrate `narrate_for_speech` into `run_pipeline`**

In `audio_generator/pipeline.py`, add the import and a small path helper,
and update `run_pipeline`:

```python
from audio_generator.cleaner import clean_markdown_for_speech
from audio_generator.discovery import CONTENT_TYPES, discover_source_files
from audio_generator.engine import ENGINES, synthesize_speech
from audio_generator.narrate import narrate_for_speech
from audio_generator.state import compute_content_hash, load_state, needs_regeneration, save_state

DEFAULT_ACADEMIC_HUB_ROOT = "../academic-hub"


def _narrated_md_path(abs_md_path: str) -> str:
    base, _ext = os.path.splitext(abs_md_path)
    return f"{base}.narrated.md"


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
        narrated_md = narrate_for_speech(md_text)
        text = clean_markdown_for_speech(narrated_md)
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

        with open(_narrated_md_path(source.abs_md_path), "w", encoding="utf-8") as f:
            f.write(text)

        state[source.rel_md_path] = current_hash
        summary["generated"] += 1

    save_state(audio_generator_root, state)
    return summary
```

(`main()` below `run_pipeline` in this file is unchanged — it already
just calls `run_pipeline()` and doesn't need to know about `narrate.py`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_audio_generator_pipeline.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Update the README**

In `audio_generator/README.md`, add a new subsection after `## Setup` (before
`## Non-goals`):

```markdown
## LaTeX narration

Math notation (`$...$`/`$$...$$`) is rewritten into natural spoken prose by
a local Ollama call before synthesis (`qwen2-math:7b` by default), chunked
per-file. Requires `ollama serve` running with that model pulled
(`ollama pull qwen2-math:7b`) for full-quality narration; if Ollama is
unreachable, or a chunk's rewrite fails a sanity check twice, that chunk
degrades to the old literal-LaTeX-wrapped narration instead of failing the
file.

The final narration text (after all cleaning) is written to a sibling
`<name>.narrated.md` next to `<name>.md`/`<name>.mp3` — useful for spot-
checking translation quality without listening to the audio.

Override the model or its per-chunk timeout via `AUDIOGEN_NARRATE_OLLAMA_MODEL`
/ `AUDIOGEN_NARRATE_OLLAMA_TIMEOUT` (seconds, default `300`).
```

- [x] **Step 6: Measure real CPU timing against the actual equation-dense file (spec §9's flagged unknown)**

**Status: measured (2026-09-09). Real result: 21,758.5s (362.6 min, ~6h 2m)
for one file (121,637 input chars -> 127,558 output chars).**

This is the headline finding for spec §9: **narrating one equation-dense
notes file takes roughly six hours** on this machine's CPU-only
`qwen2-math:7b` setup. 42 separate "timed out after 300s" warnings fired
during the run (`common/ollama_utils.py`'s `OLLAMA_TIMEOUT` path, retried
once each per `narrate.py`'s retry semantics) -- a large fraction of the
~50 chunks needed at least one retry against the 300s-per-chunk timeout.
Output being longer than input (not shrunk) indicates most chunks were
genuinely rewritten rather than falling back to unmodified text. At this
rate, a full course's worth of notes/textbook files is not practical to
narrate serially on hardware like this -- a real, now-measured constraint
(not a guess) worth flagging for anyone scoping a batch run, exactly the
kind of finding `problem_gen`/`video_notes` have recorded after their own
first real timing runs.

The three prior attempts below were superseded once the measurement was
run outside the Claude Code harness's background-task supervision (a
plain terminal window the user ran directly) -- confirming the harness's
own memory-safety guard, not genuine resource exhaustion, was what killed
attempts 2 and 3. `ollama`/`llama-server` were never touched in any
attempt.

**Prior attempts (history, all superseded):**

**Attempt 1 (2026-09-07, primary dev machine):** OOM-killed before
completing. With IDEA (~2GB), several Chrome tabs, and Obsidian already
open on a 16GB-RAM machine, under ~500MB was free when `qwen2-math:7b`
(4.4GB) needed to load — the process was killed for low memory, not just
slow.

**Attempt 2 (2026-09-08/09, same machine, ~9.7GB free at start):** killed
again, but for a different reason. Free memory was comfortably above
`qwen2-math:7b`'s 4.4GB footprint when the run started, `ollama serve` and
the model loaded fine, and the run proceeded without error for **~76
minutes** — well past attempt 1's near-instant failure — before free
memory had drifted down to ~3.6GB (unrelated background activity:
Windows Update's `TiWorker`, rising memory-compression pressure) and the
process was killed defensively. `ollama`/`llama-server` themselves stayed
up throughout; only the Python driver process was killed. The run never
printed its timing line, so still no real elapsed-time number for the
full file.

**Attempt 3 (2026-09-09, same machine, ~8.2GB free at start, `TiWorker`
confirmed not running, IDE/Obsidian confirmed closed):** killed again.
Free memory dropped faster than attempt 2 at first (8.2GB -> ~3.9GB within
~10 minutes) with no single process visibly ballooning (`llama-server`'s
own working set stayed ~760MB the whole time — most of the model appears
memory-mapped rather than fully resident), then plateaued around
3.5-3.6GB for the next ~40 minutes before finally being killed at ~3.37GB
free, ~65 minutes in. Only the Python driver processes were killed;
`ollama`/`llama-server` survived again.

All three kills were issued by the Claude Code harness's own background-
task memory-safety guard (the task notification says so explicitly), not
a Windows-native OOM condition -- Windows itself pages to disk under
memory pressure rather than killing processes outright, unless its
commit limit is truly exhausted, which was never observed here (`ollama`/
`llama-server` were never touched). The three kills landed at free-memory
readings of <500MB, ~3.6GB, and ~3.37GB respectively -- consistent with a
harness-side threshold somewhere around 20% of this machine's 16.6GB
total, triggered on the absolute reading rather than the trend (attempt 3
had plateaued for ~40 minutes before still getting killed).

Updated finding (spec §9): on this machine, a full-file run of
`narrate_for_speech()` reliably drives free memory down into a range that
trips the harness's own safety guard well before the narration finishes,
regardless of what else is or isn't running. The next attempt should run
outside the harness's background-task supervision entirely (a plain
terminal window the harness isn't monitoring) so only Windows' own memory
management applies -- or run on a machine with meaningfully more RAM.
Watching free memory through the run (as below) is still useful for
diagnosis, but has not by itself been enough to avoid the kill:

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize
```

Expected several GB free (comfortably more than `qwen2-math:7b`'s 4.4GB)
before proceeding — close other heavy applications first if not. Requires
`ollama serve` running with `qwen2-math:7b` pulled:

```bash
ollama pull qwen2-math:7b   # skip if already pulled
```

```python
# Run via: ./.venv/Scripts/python.exe -c "<paste below>"
import time

from audio_generator.narrate import narrate_for_speech

with open("../academic-hub/academic_notes/math-camp/ta_notes/processed_outputs/LN_Probability.md", "r", encoding="utf-8") as f:
    md_text = f.read()

start = time.monotonic()
result = narrate_for_speech(md_text)
elapsed = time.monotonic() - start
print(f"Input: {len(md_text)} chars. Output: {len(result)} chars. Elapsed: {elapsed:.1f}s ({elapsed / 60:.1f} min).")
```

**Result (2026-09-09, run directly in a plain terminal, outside harness
supervision):** `Input: 121637 chars. Output: 127558 chars. Elapsed:
21758.5s (362.6 min).` See the summary above this script for the full
finding and its implications.

- [ ] **Step 7: Commit**

```bash
git add audio_generator/pipeline.py audio_generator/README.md tests/test_audio_generator_pipeline.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): wire LLM-based LaTeX narration into the pipeline

run_pipeline() now calls narrate_for_speech() on the raw .md before
clean_markdown_for_speech(), and writes the final (post-cleaning)
narration text to a new <name>.narrated.md sibling -- gated by the same
content-hash check that already gates <name>.mp3, no new caching schema.
README documents the new env var overrides and the Ollama-unreachable
degrade-gracefully behavior.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012utPaFRMX7eLAtcGdRJhcE
EOF
)"
```

---

### Task 9: Replace local Ollama narration with tiered Gemini API calls (spec §3.1 v3)

**Why:** Task 8 Step 6's real measurement came back at ~6h for one
equation-dense file on local CPU-only `qwen2-math:7b` — impractical for
any real batch. This task swaps `narrate.py`'s LLM backend to the Gemini
Developer API, reusing `common/gemini_utils.py` exactly as
`viz/llm_fallback.py`/`indexer/index_card.py` already do (no new
dependency — `google-genai` and `python-dotenv` are already in
`requirements.txt` via those subprojects). Adds per-chunk complexity
tiering (skip/light/heavy) so plain-prose content costs nothing. Drops the
local-Ollama fallback tier entirely — see spec §3.1 v3 for full rationale.

**Files:**
- Modify: `audio_generator/narrate.py`
- Modify: `audio_generator/README.md`
- Test: `tests/test_audio_generator_narrate.py` (rewritten)

**Interfaces:**
- Consumes: `common.gemini_utils.get_gemini_client`/`call_with_retries`/`load_dotenv_override`.
- Produces: `narrate_for_speech(md_text: str) -> str` — **signature
  unchanged from v2**, so `pipeline.py` needs zero code changes; it already
  calls this exact function first, before `cleaner.clean_markdown_for_speech()`.

- [ ] **Step 1: Write the failing classifier tests**

Add to `tests/test_audio_generator_narrate.py` (new import:
`from audio_generator.narrate import _classify_chunk`):

```python
class TestClassifyChunk(unittest.TestCase):
    def test_pure_prose_is_skip(self):
        self.assertEqual(_classify_chunk("Just plain prose, no math at all here."), "skip")

    def test_stray_greek_letter_outside_dollar_signs_is_not_skip(self):
        self.assertNotEqual(_classify_chunk("The parameter α controls the rate."), "skip")

    def test_sparse_simple_inline_math_is_light(self):
        chunk = "Consider the random variable X. " * 20 + "Its mean is $E[X]$."
        self.assertEqual(_classify_chunk(chunk), "light")

    def test_dense_dollar_spans_is_heavy(self):
        chunk = "$" + "x^2 + y^2 = z^2 " * 40 + "$"
        self.assertEqual(_classify_chunk(chunk), "heavy")

    def test_many_backslash_commands_is_heavy(self):
        chunk = "Short text. $\\mathbb{E}[X] = \\sum_{x} x \\mathbb{P}(X = x) \\cdot \\int f(x)$."
        self.assertEqual(_classify_chunk(chunk), "heavy")

    def test_begin_environment_is_always_heavy_regardless_of_ratio(self):
        chunk = "Short lead-in. $\\begin{align} x &= 1 \\end{align}$"
        self.assertEqual(_classify_chunk(chunk), "heavy")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_audio_generator_narrate.py -k Classify -v`
Expected: FAIL with `ImportError: cannot import name '_classify_chunk'`.

- [ ] **Step 3: Implement the classifier**

In `audio_generator/narrate.py`, add (near the existing pattern constants):

```python
_LATEX_SPAN_PATTERN = re.compile(r"\$\$[^\$]+\$\$|\$[^\$]+\$")
_LATEX_COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+")
_LATEX_ENV_PATTERN = re.compile(r"\\begin\{[^}]+\}")
# Greek letters + common math-operator/arrow ranges, for notation typed as
# literal Unicode rather than LaTeX (e.g. "the parameter α" in prose).
_MATH_UNICODE_PATTERN = re.compile("[\u0370-\u03ff\u2190-\u21ff\u2200-\u22ff]")

AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD = float(os.environ.get("AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD", "0.15"))
AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD = int(os.environ.get("AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD", "3"))


def _classify_chunk(chunk: str) -> str:
    """Returns "skip" | "light" | "heavy" (spec §3.1 v3) -- thresholds are
    a starting guess, flagged in spec §9 for empirical tuning."""
    spans = _LATEX_SPAN_PATTERN.findall(chunk)
    if not spans and not _MATH_UNICODE_PATTERN.search(chunk):
        return "skip"
    if _LATEX_ENV_PATTERN.search(chunk):
        return "heavy"
    ratio = sum(len(s) for s in spans) / len(chunk) if chunk else 0.0
    command_count = len(_LATEX_COMMAND_PATTERN.findall(chunk))
    if ratio >= AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD or command_count >= AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD:
        return "heavy"
    return "light"
```

- [ ] **Step 4: Run to verify the classifier tests pass**

Run: `python -m pytest tests/test_audio_generator_narrate.py -k Classify -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Write the failing `_call_gemini` tests**

Add to `tests/test_audio_generator_narrate.py` (new imports:
`from unittest.mock import MagicMock, patch` (extend existing import),
`from audio_generator.narrate import _call_gemini`):

```python
class TestCallGemini(unittest.TestCase):
    def test_returns_response_text_on_success(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="A rewritten passage.")
        result = _call_gemini("prompt", "gemini-3.1-flash-lite", client)
        self.assertEqual(result, "A rewritten passage.")

    def test_passes_the_given_model_and_prompt(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="response")
        _call_gemini("my specific prompt", "gemini-2.5-flash", client)
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-2.5-flash")
        self.assertEqual(kwargs["contents"], "my specific prompt")

    def test_returns_none_when_call_with_retries_raises(self):
        client = MagicMock()
        with patch("audio_generator.narrate.call_with_retries", side_effect=Exception("quota exceeded")):
            result = _call_gemini("prompt", "gemini-3.1-flash-lite", client)
        self.assertIsNone(result)
```

- [ ] **Step 6: Run to verify they fail, then implement `_call_gemini`**

Run: `python -m pytest tests/test_audio_generator_narrate.py -k CallGemini -v`
Expected: FAIL with `ImportError`.

In `audio_generator/narrate.py`, replace the `common.ollama_utils` import
and add:

```python
from common.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override

AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL = os.environ.get("AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL", "gemini-3.1-flash-lite")
AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL = os.environ.get("AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL", "gemini-2.5-flash")
_TIER_MODELS = {"light": AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL, "heavy": AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL}


def _call_gemini(prompt: str, model: str, client) -> str | None:
    """Mirrors viz/llm_fallback.py's _call_gemini exactly -- relies on
    common.gemini_utils.call_with_retries for transient-failure retry/
    backoff, the same mechanism every other Gemini call in this project
    already uses. Returns None only once retries are exhausted, never
    raises."""
    try:
        response = call_with_retries(lambda: client.models.generate_content(
            model=model, contents=prompt, config={"temperature": 0.2},
        ))
        return (response.text or "").strip()
    except Exception as err:
        print(f"WARNING: Gemini call to model '{model}' failed after retries ({err})")
        return None
```

Run: `python -m pytest tests/test_audio_generator_narrate.py -k CallGemini -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Update the existing chunking/retry tests for the Gemini backend**

Replace every `@patch("audio_generator.narrate.call_ollama")` test in
`TestNarrateForSpeechChunking`/`TestNarrateForSpeechRetryAndFallback` with
the Gemini-client-shaped equivalent. Pattern for each (illustrated on two
representative cases -- apply the same shape to the rest):

```python
from unittest.mock import MagicMock, patch

class TestNarrateForSpeechChunking(unittest.TestCase):
    @patch("audio_generator.narrate.get_gemini_client")
    @patch("audio_generator.narrate.load_dotenv_override")
    def test_calls_gemini_once_per_paragraph_when_short(self, mock_dotenv, mock_get_client):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="A rewritten sentence long enough to pass the sanity check easily here.",
        )
        mock_get_client.return_value = client
        md_text = "First short paragraph with $x$.\n\nSecond short paragraph with $y$."
        narrate_for_speech(md_text)
        self.assertEqual(client.models.generate_content.call_count, 1)

    @patch("audio_generator.narrate.get_gemini_client")
    @patch("audio_generator.narrate.load_dotenv_override")
    def test_no_client_falls_back_to_unmodified_text(self, mock_dotenv, mock_get_client):
        mock_get_client.return_value = None  # missing/invalid GEMINI_API_KEY
        original = "Some text with $E[X]$ in it that needs a client to rewrite."
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
```

Notes for the remaining cases:
- The old "code block never reaches the LLM" test still applies unchanged
  (that check happens before `_narrate_chunk` is ever called) — just
  update its `@patch` target the same way.
- The old `OLLAMA_TIMEOUT`-retry-then-succeed/-then-fall-back tests
  **do not have a direct v3 equivalent** — `call_with_retries` (Step 6)
  now owns all transient-failure retries internally, so `narrate.py`
  itself no longer retries. Replace those two tests with: (a) a
  `_narrate_chunk`-level test that a too-short response is *not* retried a
  second time by `narrate.py` (`client.models.generate_content.call_count == 1`
  even though the sanity check fails), and (b) keep one success-path test
  and one `_call_gemini`-raises-so-narrate-falls-back test (already
  covered by Step 5's `TestCallGemini`, but add one at the
  `narrate_for_speech` level too for end-to-end coverage).
- Every test's input text must contain at least one `$...$` span (or
  Greek-letter Unicode) — otherwise `_classify_chunk` returns `"skip"` and
  `generate_content` is never called at all, which would make these tests
  assert the wrong thing.

- [ ] **Step 8: Implement the tiered `_narrate_chunk` and updated `narrate_for_speech`**

In `audio_generator/narrate.py`:

```python
def _narrate_chunk(chunk: str, client) -> str:
    """Rewrites one chunk via the tier-appropriate Gemini model (spec
    §3.1 v3). No local fallback if client is None or the call fails --
    just the chunk's original, unmodified text, exactly as v2 behaved on
    an unreachable server."""
    tier = _classify_chunk(chunk)
    if tier == "skip" or client is None:
        return chunk
    prompt = _PROMPT_TEMPLATE.format(chunk=chunk)
    result = _call_gemini(prompt, _TIER_MODELS[tier], client)
    if result is not None and _passes_sanity_check(chunk, result):
        return result
    return chunk


def narrate_for_speech(md_text: str) -> str:
    """Entry point pipeline.py calls first, on raw .md text, before
    cleaner.clean_markdown_for_speech() (spec §3.1). Builds one Gemini
    client per file (not per chunk) -- get_gemini_client() is cheap
    (no network call itself), and this keeps pipeline.py's call site
    completely unchanged from v2."""
    load_dotenv_override()
    client = get_gemini_client()
    chunks = _group_into_chunks(_split_into_pieces(md_text))
    narrated = [
        chunk if _CODE_BLOCK_PATTERN.fullmatch(chunk) else _narrate_chunk(chunk, client)
        for chunk in chunks
    ]
    return "\n\n".join(narrated)
```

Remove the old `AUDIOGEN_NARRATE_OLLAMA_MODEL`/
`AUDIOGEN_NARRATE_OLLAMA_TIMEOUT_SECONDS` constants and the
`from common.ollama_utils import call_ollama` import entirely -- v3 has
no local-Ollama code path (spec §3.1 v3, dropped by design).

- [ ] **Step 9: Run the full narrate test suite**

Run: `python -m pytest tests/test_audio_generator_narrate.py -v`
Expected: PASS (all tests, updated + new).

- [ ] **Step 10: Update the README's LaTeX narration section**

In `audio_generator/README.md`, replace the existing "LaTeX narration"
subsection (added in Task 8 Step 5) with one documenting: the three tiers
and their default models (`gemini-3.1-flash-lite`/`gemini-2.5-flash`),
that `GEMINI_API_KEY` must be set in `ai-sandbox/.env` (point to
`../.env.example`, matching every other Gemini-calling subproject's own
README convention), that a missing/invalid key degrades gracefully to
raw-LaTeX-passthrough rather than failing the batch, and the four
overridable env vars (`AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD`,
`AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD`,
`AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL`, `AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL`).

- [ ] **Step 11: Real verification against the actual equation-dense file**

Same file as Task 8 Step 6
(`../academic-hub/academic_notes/math-camp/ta_notes/processed_outputs/LN_Probability.md`),
but timing the Gemini-backed path this time -- expected to be dramatically
faster than v2's measured ~6h, but that's an expectation, not yet a
number (spec §9). Requires `GEMINI_API_KEY` set in `ai-sandbox/.env`.

```python
# Run via: PYTHONPATH=<academic-rag-model dir> ./.venv/Scripts/python.exe this_script.py
import time

from audio_generator.narrate import narrate_for_speech

with open("../academic-hub/academic_notes/math-camp/ta_notes/processed_outputs/LN_Probability.md", "r", encoding="utf-8") as f:
    md_text = f.read()

start = time.monotonic()
result = narrate_for_speech(md_text)
elapsed = time.monotonic() - start
print(f"Input: {len(md_text)} chars. Output: {len(result)} chars. Elapsed: {elapsed:.1f}s ({elapsed / 60:.1f} min).")
```

Report the real elapsed time, and record it in spec §9 (the "NEW (v3):
real API timing and per-file cost are unmeasured" bullet) alongside a
rough cost estimate from the actual input/output character counts at
`gemini-3.1-flash-lite`/`gemini-2.5-flash`'s per-token pricing.

- [ ] **Step 12: Commit**

```bash
git add audio_generator/narrate.py audio_generator/README.md tests/test_audio_generator_narrate.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): replace local Ollama narration with tiered Gemini API

v2's local qwen2-math:7b rewrite measured at ~6h for one equation-dense
file (Task 8 Step 6) -- impractical for real batch use. narrate.py now
classifies each chunk (skip/light/heavy by LaTeX density) and routes
light chunks to gemini-3.1-flash-lite, heavy chunks to gemini-2.5-flash,
via this project's existing common/gemini_utils.py (already used by
indexer/, viz/, textbook/) -- no new dependency. No-math chunks make zero
API calls. narrate_for_speech()'s signature is unchanged, so pipeline.py
needed no code changes. Drops the local-Ollama fallback entirely: a
missing/invalid GEMINI_API_KEY now degrades straight to cleaner.py's
regex wrap, same as any other failed rewrite.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BaWkFCR7CdMinG5BxgB6uu
EOF
)"
```

---

### Task 10: Section-aware episode splitting for `notes` (spec §3.2)

**Why:** running v3 end-to-end against the real `LN_Probability.md`
(outside this plan's tests, as a manual demo) produced a correct but
impractical 3h22m single MP3. This task splits a long note into multiple
episodes targeting 10-20 minutes each, using a real measured
chars-per-minute calibration (969, from that same 202.5-minute run)
rather than a fixed header depth. Scoped to `notes` only — `textbook`
chapter-reuse (`chapter_index.py`) is a separate, unstarted investigation
(spec §9).

**Files:**
- Create: `audio_generator/sections.py`
- Modify: `audio_generator/pipeline.py`
- Modify: `audio_generator/state.py`
- Modify: `audio_generator/README.md`
- Test: `tests/test_sections.py` (new — no existing `test_sections.py` in
  the flat `tests/` dir, confirmed before picking this name)

**Interfaces:**
- Produces: `Section`/`NarratedSection`/`Episode` dataclasses;
  `split_into_sections(md_text: str) -> list[Section]`;
  `narrate_sections(sections: list[Section]) -> list[NarratedSection]`
  (thin wrapper reusing `narrate.narrate_for_speech`/
  `cleaner.clean_markdown_for_speech`, unchanged);
  `group_sections_into_episodes(narrated_sections, chars_per_minute=..., target_min_minutes=10, target_max_minutes=20) -> list[Episode]`.
- Consumes (in `pipeline.py`): all of the above, plus the existing
  `state.py` functions (extended, see Step 6).

- [ ] **Step 1: Write the failing `split_into_sections` tests**

Create `tests/test_sections.py`:

```python
import unittest

from audio_generator.sections import Section, split_into_sections


class TestSplitIntoSections(unittest.TestCase):
    def test_no_headers_produces_one_titleless_section(self):
        sections = split_into_sections("Just plain prose, no headers here at all.")
        self.assertEqual(len(sections), 1)
        self.assertIsNone(sections[0].title)
        self.assertIn("Just plain prose", sections[0].body)

    def test_splits_at_every_header_level(self):
        md = "# Chapter One\nBody one.\n\n## 1.1 Subsection\nBody two.\n\n# Chapter Two\nBody three."
        sections = split_into_sections(md)
        self.assertEqual([s.title for s in sections], ["Chapter One", "1.1 Subsection", "Chapter Two"])

    def test_content_before_first_header_becomes_titleless_leading_section(self):
        md = "Some preamble text.\n\n# First Real Header\nBody."
        sections = split_into_sections(md)
        self.assertEqual(len(sections), 2)
        self.assertIsNone(sections[0].title)
        self.assertIn("preamble", sections[0].body)
        self.assertEqual(sections[1].title, "First Real Header")

    def test_body_excludes_the_header_line_itself(self):
        md = "# A Title\nThe body text."
        sections = split_into_sections(md)
        self.assertNotIn("# A Title", sections[0].body)
        self.assertIn("The body text.", sections[0].body)

    def test_a_section_body_runs_up_to_but_not_into_the_next_header(self):
        md = "# One\nBody one.\n\n# Two\nBody two."
        sections = split_into_sections(md)
        self.assertNotIn("Two", sections[0].body)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_sections.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio_generator.sections'`.

- [ ] **Step 3: Implement `split_into_sections`**

Create `audio_generator/sections.py`:

```python
"""
sections.py
Section-aware episode splitting for audio_generator (spec §3.2): splits a
raw .md at every header level, narrates/cleans each section independently
(reusing narrate.py/cleaner.py completely unchanged), then groups
consecutive sections into episodes targeting a real, measured listening
length instead of one unbounded MP3 per source file. notes content type
only -- textbook has its own separate, PDF-anchored chapter-boundary
system (textbook/chapter_index.py) worth investigating for reuse instead
of duplicating this header-based approach (spec §9).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from audio_generator.cleaner import clean_markdown_for_speech
from audio_generator.narrate import narrate_for_speech

AUDIOGEN_SECTIONS_CHARS_PER_MINUTE = int(os.environ.get("AUDIOGEN_SECTIONS_CHARS_PER_MINUTE", "969"))
AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES = int(os.environ.get("AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES", "10"))
AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES = int(os.environ.get("AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES", "20"))

_HEADER_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+)$", re.MULTILINE)


@dataclass
class Section:
    title: str | None  # None for content before the first header
    body: str  # raw markdown, header line itself excluded


@dataclass
class NarratedSection:
    title: str  # already narrated+cleaned; "" if the section had no title
    text: str  # already narrated+cleaned body


@dataclass
class Episode:
    text: str  # concatenated title+body for every section in this episode
    section_titles: list[str] = field(default_factory=list)


def split_into_sections(md_text: str) -> list[Section]:
    """Splits raw markdown at every ATX header line, any depth (spec
    §3.2 -- grouping, not header depth, controls final output length)."""
    matches = list(_HEADER_PATTERN.finditer(md_text))
    if not matches:
        return [Section(title=None, body=md_text)]

    sections: list[Section] = []
    if matches[0].start() > 0 and md_text[:matches[0].start()].strip():
        sections.append(Section(title=None, body=md_text[:matches[0].start()]))

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        sections.append(Section(title=match.group(2).strip(), body=md_text[start:end]))
    return sections
```

- [ ] **Step 4: Run to verify the section-splitting tests pass**

Run: `python -m pytest tests/test_sections.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Write the failing `group_sections_into_episodes` tests, then implement it**

Add to `tests/test_sections.py`:

```python
from audio_generator.sections import Episode, NarratedSection, group_sections_into_episodes


def _narrated(title: str, char_count: int) -> NarratedSection:
    return NarratedSection(title=title, text="x" * char_count)


class TestGroupSectionsIntoEpisodes(unittest.TestCase):
    def test_short_sections_are_grouped_into_one_episode(self):
        sections = [_narrated("A", 1000), _narrated("B", 1000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(len(episodes), 1)

    def test_stops_grouping_once_the_minimum_is_met_and_the_max_would_be_exceeded(self):
        # chars_per_minute=1000, min=10min (10000 chars), max=20min (20000 chars).
        # First section alone hits the minimum; a second big section would blow past the max.
        sections = [_narrated("A", 11000), _narrated("B", 15000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].section_titles, ["A"])
        self.assertEqual(episodes[1].section_titles, ["B"])

    def test_keeps_grouping_past_the_max_if_the_minimum_has_not_yet_been_met(self):
        # A single section far exceeding target-max, on its own, still becomes one episode
        # (never split inside a section -- spec §3.2).
        sections = [_narrated("Huge", 50000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].section_titles, ["Huge"])

    def test_preserves_section_order_within_and_across_episodes(self):
        sections = [_narrated("A", 500), _narrated("B", 500), _narrated("C", 30000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        all_titles = [t for ep in episodes for t in ep.section_titles]
        self.assertEqual(all_titles, ["A", "B", "C"])
```

Run: `python -m pytest tests/test_sections.py -k Group -v`
Expected: FAIL with `ImportError`.

In `audio_generator/sections.py`, add:

```python
def narrate_sections(sections: list[Section]) -> list[NarratedSection]:
    """Narrates and cleans each section's body independently, reusing
    narrate.py/cleaner.py completely unchanged (spec §3.2). A section's
    title is cleaned (regex-only, no LLM call -- titles are short and
    essentially never equation-dense) but never sent through
    narrate_for_speech(): headers must be resolved before any text reaches
    the LLM, not recovered from its output."""
    result = []
    for section in sections:
        title = clean_markdown_for_speech(section.title) if section.title else ""
        text = clean_markdown_for_speech(narrate_for_speech(section.body))
        result.append(NarratedSection(title=title, text=text))
    return result


def _episode_text(parts: list[NarratedSection]) -> str:
    pieces = [f"{p.title}. {p.text}".strip() if p.title else p.text for p in parts if p.title or p.text]
    return "\n\n".join(pieces)


def group_sections_into_episodes(
    narrated_sections: list[NarratedSection],
    chars_per_minute: int = AUDIOGEN_SECTIONS_CHARS_PER_MINUTE,
    target_min_minutes: int = AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES,
    target_max_minutes: int = AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES,
) -> list[Episode]:
    """Greedily groups consecutive sections (order preserved) into
    episodes targeting a [target_min_minutes, target_max_minutes] band of
    resulting audio, using chars_per_minute as the (real, measured --
    spec §3.2) conversion. A section already past target_min on its own
    is never merged with the next if that would exceed target_max; a
    section that hasn't yet reached target_min is merged regardless of
    target_max, so a single section longer than target_max on its own
    still becomes its own (over-length) episode -- this never splits
    inside one section (spec §3.2, flagged §9 as a known limitation)."""
    min_chars = chars_per_minute * target_min_minutes
    max_chars = chars_per_minute * target_max_minutes

    episodes: list[Episode] = []
    current: list[NarratedSection] = []
    current_len = 0
    for section in narrated_sections:
        section_len = len(section.title) + len(section.text)
        if current and current_len >= min_chars and current_len + section_len > max_chars:
            episodes.append(Episode(text=_episode_text(current), section_titles=[s.title for s in current if s.title]))
            current, current_len = [], 0
        current.append(section)
        current_len += section_len
    if current:
        episodes.append(Episode(text=_episode_text(current), section_titles=[s.title for s in current if s.title]))
    return episodes
```

- [ ] **Step 6: Run to verify all of `test_sections.py` passes**

Run: `python -m pytest tests/test_sections.py -v`
Expected: PASS (9 tests).

- [ ] **Step 7: Extend `state.py` for per-episode idempotency**

**Files:** Modify `audio_generator/state.py`, `tests/test_state.py`.

State keys change shape from `rel_md_path` to `f"{rel_md_path}::part{NN:02d}"`
(zero-padded), but the value is still just the *whole source file's*
content hash (spec §3.2's deliberate simplification — a change anywhere
in the source regenerates every part for that file, not just the changed
one). Add a small helper so `pipeline.py` doesn't hand-format this key
inline in two places:

```python
def episode_state_key(rel_md_path: str, part_number: int) -> str:
    """part_number is 1-indexed, matching the __partNN filename suffix."""
    return f"{rel_md_path}::part{part_number:02d}"
```

Add one test asserting the exact zero-padded format
(`episode_state_key("a/b.md", 1) == "a/b.md::part01"`,
`episode_state_key("a/b.md", 12) == "a/b.md::part12"`). `needs_regeneration()`
and `compute_content_hash()` need no changes — they're already generic
over whatever key/path is passed in.

- [ ] **Step 8: Update `pipeline.py`'s `run_pipeline()` for `notes` content**

This step only changes behavior for `content_type == "notes"` —
`textbook` sources keep today's exact one-file-one-MP3 path unchanged
(spec §3.2's scope).

```python
from audio_generator.sections import group_sections_into_episodes, narrate_sections, split_into_sections
from audio_generator.state import episode_state_key

def _run_notes_source(source, state, engine, summary):
    current_hash = compute_content_hash(source.abs_md_path)
    with open(source.abs_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = split_into_sections(md_text)
    narrated_sections = narrate_sections(sections)
    episodes = group_sections_into_episodes(narrated_sections)

    base, _ext = os.path.splitext(source.abs_md_path)
    for i, episode in enumerate(episodes, start=1):
        key = episode_state_key(source.rel_md_path, i)
        abs_mp3_path = f"{base}__part{i:02d}.mp3"
        # needs_regeneration() takes a SourceFile for its .abs_mp3_path check --
        # build a lightweight stand-in with this episode's actual output path.
        episode_source = replace(source, abs_mp3_path=abs_mp3_path, rel_md_path=key)
        if not needs_regeneration(state, episode_source, current_hash):
            summary["skipped_unchanged"] += 1
            continue
        if not episode.text:
            summary["skipped_empty"] += 1
            continue
        try:
            synthesize_speech(episode.text, abs_mp3_path, engine=engine)
        except Exception as err:
            print(f"WARNING: failed to synthesize {key}: {err}")
            summary["failed"] += 1
            continue
        with open(f"{base}__part{i:02d}.narrated.md", "w", encoding="utf-8") as f:
            f.write(episode.text)
        state[key] = current_hash
        summary["generated"] += 1

    _write_index_manifest(base, episodes)
```

(`replace` is `dataclasses.replace` — `SourceFile` is already a
`@dataclass`, Task 2. `_write_index_manifest(base, episodes)` writes
`f"{base}__index.md"`, a plain table of part number -> included section
titles -> estimated duration in minutes, from `len(episode.text) /
AUDIOGEN_SECTIONS_CHARS_PER_MINUTE`.) Wire `_run_notes_source` into
`run_pipeline()`'s existing loop, branching on `source.content_type ==
"notes"` vs. the unchanged `textbook` path.

- [ ] **Step 9: Write/update `tests/test_audio_generator_pipeline.py` for the new notes path**

Cover: a short single-section note still produces exactly one
`__part01.mp3` (no behavior change for short notes); a note with enough
header-delimited content to span two episodes produces `__part01.mp3` and
`__part02.mp3`; re-running with no source change skips all parts; editing
the source regenerates all parts (the documented simplification, spec
§3.2); `__index.md` lists the right section titles per part; `textbook`
sources are completely unaffected (still exactly one `<name>.mp3`, no
`__partNN` suffix).

- [ ] **Step 10: Update discovery.py's exclusion check if needed**

Confirm (test, don't just assume) that `_is_real_md_file()`'s existing
`.narrated.md` exclusion (Task 6) already covers `<name>__part01.narrated.md`
and `<name>__index.md` — both end in `.md` and need to stay excluded from
the next run's source discovery. Add a test if the existing suffix check
doesn't already generalize correctly.

- [ ] **Step 11: Update the README**

Document the `notes`-only episode-splitting behavior, the three new env
vars (`AUDIOGEN_SECTIONS_CHARS_PER_MINUTE`, `_TARGET_MIN_MINUTES`,
`_TARGET_MAX_MINUTES`), the `__partNN.mp3`/`__index.md` output shape, and
that existing single-file `<name>.mp3`/`<name>.narrated.md` outputs from
before this revision become orphaned (not auto-deleted or migrated).

- [x] **Step 12: Real verification against `LN_Probability.md`**

**Done, 2026-09-09.** Two real end-to-end runs were needed, not one — the
first surfaced a real concurrency bug (below), fixed before the second,
final run.

**Run 1 (pre-fix):** the initial `narrate_sections()` implementation
called `narrate_for_speech()` once per section in a sequential loop.
Real-world timing exposed why that's wrong: each call had its own
internal concurrency across that section's chunks, but sections were
processed one after another, confining parallelism to one section's
batch at a time — a document with many small sections (this file has 74)
ends up *slower* than the original whole-file design, not faster. Fixed
by exposing `narrate.chunk_for_narration()`/`narrate.narrate_chunks()` as
public functions and flattening every section's chunks into one list
before a single shared dispatch (commit `fb6fd8d`) — fully
backward-compatible, all 20 existing `narrate.py` tests passed unchanged.
Episode-level TTS synthesis was parallelized the same pass
(`AUDIOGEN_SECTIONS_SYNTH_MAX_WORKERS`, default 3).

**Run 2 (post-fix, final numbers):**
- Narration: **227.1s (3.8 min)** for 74 header-delimited sections (down
  from 777.3s/13.0 min for the old single-whole-file v3 measurement).
- Grouped into **9 episodes**.
- Synthesis: **1165.3s (19.4 min) wall-clock** across 3 concurrent Piper
  workers (vs. 3353.0s/55.9 min summed sequentially — ~2.9x speedup).
- **Total: 1392.5s (23.2 min) end to end.**
- `__index.md` correctly lists each part's real section titles.
- **One real limitation confirmed, not a regression:** Part 02 came out
  at 60,389 chars (~62 min), 3x the 20-minute target — source section
  "1.5 Probability measures" spans 711 raw lines with zero sub-headers,
  a genuinely undivided block the algorithm correctly refused to split
  (spec §3.2's documented "never split inside one section" rule). Spec
  §9 had flagged this as "expected to be rare" — confirmed real on the
  very first file tested. **Deliberately left unfixed** — the user wants
  to listen to the 9 real output files and compare against the source
  content first, before deciding whether to add paragraph-level fallback
  splitting for an over-long leaf section.

Full narrative, per-episode breakdown table, and the "this test exercised
the hard case, not the primary intended use case" scope note:
`docs/status/2026-09-09-audio-generator-status.md`.

- [ ] **Step 13: Commit**

```bash
git add audio_generator/sections.py audio_generator/pipeline.py audio_generator/state.py audio_generator/README.md tests/test_sections.py tests/test_state.py tests/test_audio_generator_pipeline.py
git commit -m "$(cat <<'EOF'
feat(audio_generator): add section-aware episode splitting for notes

Running v3's Gemini narration end-to-end against the real
LN_Probability.md produced a correct but impractical 3h22m single MP3.
notes sources now split at every header level, narrate/clean each
section independently, and greedily group consecutive sections into
10-20 minute episodes using a real measured calibration (969 chars/min,
from that same 202.5-minute run) -- not a fixed header depth, which real
inspection showed would still yield 30-60+ minute files for this corpus.

Idempotency tracks per-episode but hashes the whole source file, not
per-section -- a deliberate simplification (spec §3.2), not the finest-
grained possible design. textbook content is unaffected -- still one
MP3 per source file; reusing chapter_index.py's PDF-anchored chapter
boundaries for textbook is a separate, unstarted investigation.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BaWkFCR7CdMinG5BxgB6uu
EOF
)"
```
