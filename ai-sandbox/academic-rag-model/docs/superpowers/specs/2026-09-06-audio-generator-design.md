# Audio Generator — Design Spec

Date: 2026-09-06
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

The academic-hub corpus is entirely text/image-based (markdown notes, textbooks, journal articles, synthesized lecture notes). This limits study opportunities to sedentary scenarios (sitting at a desk, viewing a screen). Students need to consume study material passively (during commutes, exercise, etc.).

This spec designs **`audio_generator`**: a new subproject that converts hub markdown content into high-quality, locally-generated audio MP3 files, optimized for passive listening.

**Goals**
- Locally generated on commodity CPUs (no GPU, no external APIs).
- High performance (Piper TTS for speed, Kokoro-ONNX for audiobook-grade quality).
- Markdown-to-prose conversion: smart stripping of LaTeX, code blocks, and markdown structure to ensure the audio sounds natural, not like a machine reading raw syntax.
- Covers three content types, all of which live under `academic_hub_root` and are addressable by `--course` (§5): the student's own notes (`academic_notes/<course>/`, all categories — this already includes `video_notes`'s synthesized lecture notes, since those are written to `academic_notes/<course>/lecture-notes/`), and converted textbooks (`academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/`, both folder-name aliases, matching the indexer's existing handling of the same rename — `indexer/index_search.py:206-213`).
- Idempotent batch pipeline: only re-generates audio when the underlying `.md` file changes (tracked by content hash).
- Output MP3s land in the hub content repo, next to the source note they were generated from, so a folder-sync tool (Syncthing, a phone's file-sync app, etc.) picks them up the same way it already picks up the student's markdown notes — never inside `academic-rag-model`'s own gitignored caches.
- Integration: invoked manually per course via CLI (§6) — not auto-triggered as a follow-on of other pipelines in v1 (see Non-goals).

**Non-goals**
- Cloud TTS APIs (ElevenLabs, OpenAI).
- Real-time/GPU-heavy model training.
- Interactive audio features (e.g., in-audio navigation markers beyond standard MP3 seeking).
- **Indexer/RAG registration.** Unlike `video_notes`'s synthesized lecture notes (which are new, otherwise-unindexed content and so need a new `index_search.py` discovery path), an MP3 here is a derived, downstream rendering of a `.md` file that's already indexed. The source `.md` remains the single retrieval unit; the tutor never needs to know an audio version exists. No `indexer/index_search.py` changes.
- **Journal articles.** `research/journal-articles/<field>/processed_outputs/` is a genuinely different shape from the other three content types: it lives in a separate sibling repo (`../research`, not `../academic-hub`) and is organized by academic field, not by `--course`. Rather than bolt on a second, mutually-exclusive scoping key (`--field` alongside `--course`) before the core pipeline is proven, this is deferred as a follow-on (§9).
- **Auto-triggering as a follow-on pass.** `postprocessing`/`viz` hook into other pipelines' completion; `audio_generator` v1 is manual-CLI-only (§6) to keep the first version simple. Revisit once the manual flow is proven (§9).
- **Reading image/figure descriptions aloud.** `textbook/describe_images.py` already generates descriptions for diagrams in converted textbook markdown, but wiring `cleaner.py` to find and narrate them is deferred (§9) — v1 silently skips images/figures the same way it skips code blocks.
- **A length cap on generated audio.** A full textbook chapter or long article becomes one MP3 with no length limit — matches the existing 1:1 sibling-file design (§5). Chapter-splitting is already a deferred follow-on (§9), not a v1 concern.

## 2. Architecture

A new package `audio_generator/`, sitting alongside `rag/`/`indexer/`/`problem_gen/`/`video_notes/` in `academic-rag-model/`:

```
academic-rag-model/
  audio_generator/
    __init__.py
    README.md
    cleaner.py       # Markdown-to-prose logic (from brainstorm)
    engine.py        # Wrapper for Piper / Kokoro-ONNX engines
    pipeline.py       # Batch orchestration, discovery, idempotency
    cli.py            # CLI entry point
```

Like every other subproject that touches hub content, `pipeline.py` takes an
`academic_hub_root` argument and defaults it the same way `video_notes/pipeline.py`
does (`DEFAULT_ACADEMIC_HUB_ROOT = "../academic-hub"`, `video_notes/pipeline.py:31`)
— the hub is a sibling repo to `academic-rag-model/`, never assumed to be a local
folder inside this project.

**Where the code looks for source content vs. where it writes output differs by
design, matching two different existing precedents:**
- *Idempotency state* (which files have already been converted, keyed by content
  hash) is code-repo-local and gitignored, matching `video_notes/.state/` +
  `video_notes/.cache/` (`.gitignore:5-6`): `audio_generator/.cache/state.json`.
  This is bookkeeping, not a deliverable, so it stays out of the hub and out of
  git, exactly like `video_notes`'s per-video/per-group state files.
- *Generated MP3 output* is **not** treated as a disposable cache the way
  `viz/`'s generated images are (`viz/viz_agent.py:60` writes to
  `academic_hub_root/.viz`, a hub-root-level, regenerate-on-demand directory a
  student never browses directly). Audio is the actual deliverable a student
  listens to on a commute, so it needs to live somewhere a student's own
  sync tooling reaches — see §5.

## 3. Markdown-to-prose logic (`cleaner.py`)

Reuses the logic validated in the brainstorm, plus one addition driven by
`video_notes` content now being in scope:

1. **Remove code blocks:** Completely omitted or summarized as "[Code snippet omitted.]"
2. **Handle LaTeX:** Convert `$$...$$` and `$...$` into natural prose ("Equation: X").
3. **Strip inline timestamp citations:** `video_notes`-synthesized notes attach a
   citation like `([04:12](https://youtu.be/abc123&t=252s))` to nearly every
   sentence, by design (`2026-09-06-video-lecture-notes-design.md` §7's own
   example: `"The eigenvalue of the matrix is 3 ([04:12](https://youtu.be/abc123&t=252s))."`).
   A citation only has value as a clickable link; read aloud it's meaningless
   noise on every sentence. `cleaner.py` strips the whole parenthetical
   `(\[[\d:]+\]\([^)]+\))` pattern before the general markdown-stripping pass
   below — the source `.md` remains the citable reference (matching the
   indexer non-goal, §1).
4. **Strip remaining Markup:** Parse markdown via `markdown`/`BeautifulSoup` to
   strip remaining syntax (including images/figures, silently — §1 non-goal).
5. **Normalize:** Strip excessive whitespace.

## 4. Synthesis Engines (`engine.py`)

- **Piper TTS (Primary):** ~20–60MB, ~10× real-time on CPU. Best for batch processing.
- **Kokoro-ONNX (Secondary/Advanced):** ~82M params (~300MB), real-time to 3× real-time. Better inflection, near-human quality.

The pipeline will default to Piper but allow switching engines via CLI flag.

## 5. Pipeline, discovery, output location & idempotency (`pipeline.py`)

- **Source discovery**, scoped by `--content-type` (§6):
  - `notes`: walks `academic_hub_root/academic_notes/<course>/<category>/` for
    all `.md` files, across every category subfolder that exists for that
    course (`markdown`, `latex`, `articles`, `briefings`, `handwritten_notes`,
    `lecture-notes`, etc. — whatever subfolders the course actually has).
  - `textbook`: walks `academic_hub_root/academic_resources/<course>/<alias>/processed_outputs/`
    for `_metadata.json` + `.md` pairs, checking both folder-name aliases
    (`textbooks`, `textbooks-and-papers`) the same way
    `indexer/index_search.py:213`'s `_TEXTBOOK_FOLDER_NAMES` does.
- **Output location:** for each discovered `<name>.md`, writes `<name>.mp3` as a
  sibling file — same directory, same basename. This is a deliberate 1:1
  choice (unlike `video_notes`, which synthesizes *many* videos into *one* new
  note and so needs a new destination folder, `audio_generator` renders exactly
  one source file into exactly one audio file, so no new folder taxonomy is
  needed and the MP3 naturally sits where a sync tool already watches).
- **Idempotency:** Computes a SHA-256 content hash of the input `.md` file,
  stored in `audio_generator/.cache/state.json` (code-repo-local, gitignored —
  see §2) keyed by the file's hub-relative path. If the stored hash for that
  path matches the current file's hash and the sibling `.mp3` already exists,
  skip regeneration.
- **Batch Processing:** Iterates over the discovered `.md` files for the given
  course and content-type(s), (re-)generating audio only for those whose
  content hash changed or that have no sibling `.mp3` yet.

## 6. Integration & CLI

```bash
python -m audio_generator.pipeline --course math-camp \
  [--academic-hub-root ../academic-hub] [--content-type notes,textbook] \
  [--engine piper] [--dry-run]
```

- `--academic-hub-root` defaults to `../academic-hub` (§2).
- `--course` is required, matching every other subproject's CLI
  (`video_notes/pipeline.py:166`, `problem_corpus`).
- `--content-type` accepts a comma-separated subset of `notes`, `textbook`;
  omitting it means both (§5). (`journal-article` is not a valid value in
  v1 — see the journal-articles non-goal, §1.)

## 7. Edge cases

| Situation | Behavior |
|---|---|
| LaTeX-heavy file | Handled by `cleaner.py` (Equation-read conversion). |
| File with no speakable text | `cleaner.py` returns empty/whitespace; pipeline skips and logs a warning. |
| `ffmpeg` missing | Pipeline pre-flight check fails gracefully, logs instructions to install `ffmpeg`. |
| Image-heavy textbook page / figure | Images and their surrounding markup are silently skipped by `cleaner.py` (§1 non-goal) — no attempt to narrate `describe_images.py` output in v1. |
| `video_notes` note with dense inline citations | Citations stripped before narration (§3); no per-sentence "at timestamp X" clutter. |
| Very long source file (full textbook chapter, long article) | No length cap in v1 — produces one correspondingly long MP3 (§1 non-goal). |
| Source `.md` deleted after its `.mp3` was generated | Out of scope for this spec's first pass — orphaned MP3s are not auto-pruned (no orphan-sweep like the indexer's, since this pipeline doesn't own an index). Flagged in §9 as a candidate follow-on if it turns out to matter in practice. |

## 8. Testing

Mirrors the project's existing flat `tests/` convention (package-qualified
imports via the root `conftest.py` — `tests/test_audio_download.py`,
`tests/test_grouping.py`, etc. are all siblings at the repo root, not nested
inside their subproject packages): `tests/test_cleaner.py`,
`tests/test_engine.py`, `tests/test_pipeline.py`.

- `cleaner.py`: Unit tests against fixtures (complex LaTeX, nested code blocks,
  tables, and a `video_notes`-style fixture with dense inline timestamp
  citations to confirm they're stripped without mangling surrounding prose).
- `engine.py`: Integration test with a mocked engine to confirm input text passed to engine matches cleaned text.
- `pipeline.py`: Content-hash idempotency tested against a temp corpus (change
  file -> regen; don't change -> skip); discovery tested against both
  `academic_notes/` and both textbook-folder aliases; a test that output lands
  as a sibling `.mp3` at the expected hub-relative path for each content type.

## 9. Open questions / follow-on (not decided by this spec)

- **Journal-articles support** (§1 non-goal) — needs its own `--research-root`
  + `--field` scoping (`../research/journal-articles/<field>/`), distinct from
  the `--course` model the other three content types share. Revisit once the
  core pipeline is proven.
- **Auto-triggering** as a follow-on pass hooked into `postprocessing`/`textbook`/`video_notes`
  completion, instead of manual CLI invocation only (§1 non-goal).
- **Reading image/figure descriptions aloud**, reusing `textbook/describe_images.py`'s
  output where present, instead of silently skipping images (§1 non-goal) —
  first needs checking how/whether those descriptions are actually embedded in
  the `.md` today.
- **Chapter-level audio splitting:** Automatically splitting long notes/textbook
  chapters into per-chapter MP3s (using the chunking work already done),
  instead of one long MP3 per source file (§1 non-goal).
- **In-audio navigation:** Injecting chapter-titles/section-headings via silent-gap injection.
- **Advanced inflection:** Using a more capable local model for emphasis (if hardware allows).
- **Orphaned-MP3 cleanup:** if a source `.md` is deleted or renamed, decide whether/how to prune or rename its sibling `.mp3` (§7) — not designed here.
