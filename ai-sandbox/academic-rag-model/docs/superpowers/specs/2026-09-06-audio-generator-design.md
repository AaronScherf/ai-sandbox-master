# Audio Generator — Design Spec

Date: 2026-09-06 (revised 2026-09-07: LLM-based LaTeX narration)
Status: v1 implemented and shipped (commits d3adf7a..7cccb14, on `main`).
This revision (§3.1, replacing the naive regex LaTeX-to-prose step) is
approved in brainstorming, not yet planned/implemented.

## 1. Problem & goals

The academic-hub corpus is entirely text/image-based (markdown notes, textbooks, journal articles, synthesized lecture notes). This limits study opportunities to sedentary scenarios (sitting at a desk, viewing a screen). Students need to consume study material passively (during commutes, exercise, etc.).

This spec designs **`audio_generator`**: a new subproject that converts hub markdown content into high-quality, locally-generated audio MP3 files, optimized for passive listening.

**Goals**
- Locally generated on commodity CPUs (no GPU, no external APIs) — a local
  Ollama call (§3.1) is still "local," not an external API, same posture as
  `problem_gen`'s and `video_notes`'s existing Ollama dependencies.
- High performance (Piper TTS for speed, Kokoro-ONNX for audiobook-grade quality).
- Markdown-to-prose conversion: smart stripping of code blocks and markdown
  structure, plus LLM-based narration of LaTeX math (§3.1), to ensure the
  audio sounds natural, not like a machine reading raw syntax. **Real-corpus
  finding (2026-09-07):** the original regex `Equation: <raw LaTeX>` wrap
  (validated only against the brainstorm's own trivial `$$x^2+y^2=z^2$$`
  example) was tested against a real, LaTeX-heavy note
  (`academic_notes/math-camp/ta_notes/processed_outputs/LN_Probability.md`,
  997 `$`-delimited spans) and produced literal, unpronounceable LaTeX
  command syntax in the output (e.g. `\mathbb{E}[X] = \sum_{x} x \mathbb{P}(X
  = x)` passed through verbatim) — exactly the "sounds like a machine
  reading raw syntax" failure this goal exists to prevent. §3.1 replaces that
  step.
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
    cleaner.py       # Deterministic markdown-to-prose logic (code blocks, citations, markup)
    narrate.py       # LLM-based LaTeX-to-narration, chunking + fallback (§3.1)
    engine.py        # Wrapper for Piper / Kokoro-ONNX engines
    pipeline.py       # Batch orchestration, discovery, idempotency, CLI entry point (main())
```

(As shipped, CLI parsing lives in `pipeline.py`'s `main()`, matching
`video_notes/pipeline.py`'s convention, rather than a separate `cli.py` —
this diagram previously listed one; corrected here since v1's actual file
list never included it.)

`narrate.py` is a new, separate module rather than folded into `cleaner.py`,
and — deliberately — **does not import from `cleaner.py` at all, in either
direction.** `cleaner.py` is not modified by this revision: zero code changes,
zero test changes. `pipeline.py` calls `narrate.narrate_for_speech(md_text)`
first, on the raw `.md`, then feeds its output into the existing
`cleaner.clean_markdown_for_speech()` exactly as before (§3.1 explains why
this specific ordering, and not the reverse, is the only one that works).
`narrate.py` adds this subproject's first dependency on
`common/ollama_utils.py` (`call_ollama`/`OLLAMA_TIMEOUT`), already shared by
`viz/` and `problem_gen/`.

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

**Entirely unchanged by this revision** — every step below is exactly what's
already shipped. `pipeline.py` now calls `narrate.narrate_for_speech()` (§3.1)
on the raw `.md` *before* handing the result to
`cleaner.clean_markdown_for_speech()`, so most LaTeX has already become
prose by the time `cleaner.py` ever sees the text — but `cleaner.py` itself
doesn't know or care that `narrate.py` exists. Step 2 below (its own,
much simpler regex wrap) still runs on whatever raw `$...$`/`$$...$$` spans
`narrate.py` wasn't able to successfully rewrite, which is exactly its job:
the pre-revision behavior, now scoped to only the narration failures instead
of every equation in the corpus.

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

## 3.1. LaTeX-to-narration via local LLM (`narrate.py`)

**Why not regex:** LaTeX's structure (arbitrary nesting, `\begin`/`\end`
environments, context-dependent notation) is exactly what regex substitution
handles poorly and an LLM handles well — the real-corpus finding in §1
confirmed this isn't a tunable-threshold problem, it's a wrong-tool problem.
A local LLM was chosen over a third-party LaTeX-to-speech library after
checking one (`LaTeXt` on PyPI/GitHub): 4 stars, 13 commits, explicitly
described by its own maintainer as "just a pile of substitutions," with no
documented coverage of the macros this corpus actually uses
(`\mathbb`, `\sum`, `\int`, `\text`, confirmed via real macro-frequency counts
across the math-camp corpus) — an unmaintained, unverified dependency was
judged riskier than building a small, tested module against this project's
own content.

**Approach — chunked, holistic rewrite, not per-equation extraction, running
on raw `.md` *before* `cleaner.py` (§3):** `narrate_for_speech(md_text) ->
str` is the new call `pipeline.py` makes first, on the untouched source
text. Content is split into ~2-3K character chunks on paragraph boundaries
— never mid-sentence, mid-equation, **or through a fenced code block**
(a code block is treated as an atomic, untouched pass-through unit and
never sent to the LLM at all, since `cleaner.py` hasn't stripped it yet at
this point and a code sample dropped into a "rewrite as spoken prose"
prompt would only confuse the model). Each remaining chunk is sent as one
`call_ollama` prompt: *"Rewrite this passage as natural spoken prose for
audio narration. Describe mathematical notation in words rather than
symbols. Do not omit or summarize any content — rewrite every sentence,
changing only how notation is expressed."* This was chosen over two
alternatives considered and rejected:
- **Per-equation extraction + one batched prompt per file:** cheaper, but
  requires the model to return exactly N correctly-ordered rewrites for N
  extracted spans in one response — a single skipped/merged list item
  silently misaligns every rewrite after it. Rejected: correctness risk on
  exactly the equation-dense files (900+ spans) this is meant to fix.
- **Regex-first, LLM-fallback only for unrecognized macros:** cheaper in
  theory, but this corpus's real macro-frequency data (§1) shows `\begin`/
  `\end` environments — the genuinely hard, structural case — occurring
  thousands of times across the corpus, not as a rare edge case. The
  fallback would fire on a large fraction of real content, eroding most of
  the theoretical savings while adding a second code path to maintain.

**Model:** `qwen2-math:7b` by default (math-specialized, already
`problem_gen`'s choice for the same reason) via `common.ollama_utils.call_ollama`,
overridable via `AUDIOGEN_NARRATE_OLLAMA_MODEL` (same override pattern as
`PROBLEMGEN_OLLAMA_MODEL`/`VIDEONOTES_OLLAMA_MODEL`).

**Reliability — per-chunk sanity check, retry, then fallback (never a hard
failure):** mirrors `problem_gen`'s existing self-verify-and-retry pattern.
After each chunk's rewrite:
1. If the rewrite's length is suspiciously short relative to the input
   (a cheap proxy for "the model summarized or dropped content" — exact
   ratio threshold is a real-content-tuning question, flagged in §9, not a
   guessed constant to trust blindly) or `call_ollama` returns `None`/
   `OLLAMA_TIMEOUT`, retry once.
2. If the retry also fails the check, **return that chunk's original,
   unmodified text** — no rewriting attempted, raw `$...$` spans and all.
   `narrate.py` never generates its own fallback text; it simply declines to
   touch what it couldn't verify. `pipeline.py`'s next step,
   `cleaner.clean_markdown_for_speech()` (§3, unchanged), then applies its
   own existing regex wrap to whatever raw LaTeX survived — the pre-revision
   behavior, now reached only by narration failures instead of every
   equation. Worse narration for that one passage, never a failure of the
   whole file, consistent with every other subproject's "one bad item
   degrades, never blocks the batch" convention (`video_notes`,
   `problem_gen`).

**Persistence — a sibling `.narrated.md`, not a new cache format:** what gets
written to `<name>.narrated.md` is the *final* text — `narrate_for_speech()`'s
output after it has already been through `cleaner.clean_markdown_for_speech()`
(§3) — i.e. exactly the same string that gets handed to `engine.synthesize_speech()`,
not `narrate.py`'s raw intermediate output (which may still contain
unrewritten `$...$` spans for chunks that fell back). `<name>.narrated.md` is
a sibling of the source `<name>.md` and output `<name>.mp3` (§5) —
human-readable, so a chunk's translation quality can be inspected directly
without listening to the audio. Governed by the
exact same source-content-hash check that already gates `<name>.mp3` (§5) —
no new caching schema. This stays an **internal artifact of `audio_generator`
itself**, not a shared interface other subprojects import from; a shared,
promotable version of this idea was explicitly considered and deferred
during brainstorming (no other subproject has yet shown a real, observed
LaTeX-comprehension problem — `problem_gen`'s local `qwen2-math:7b` reading
raw-LaTeX style-anchor passages is a plausible future candidate, not a
confirmed one) — revisit only if real usage shows a need, this project's
established evidence-driven pattern (per `problem_gen`'s own spec).

**Discovery fix required by this new sibling file:** `discovery.py`'s
`_is_real_md_file()` (spec §5, already excluding the textbook pipeline's
`.rag.md` sibling for the identical reason) must also exclude `.narrated.md`
— without this, the next pipeline run would discover `<name>.narrated.md` as
a brand-new source `.md` and generate audio from it too.

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
  needed and the MP3 naturally sits where a sync tool already watches). Also
  writes `<name>.narrated.md`, the fully-cleaned narration text (§3.1) — a
  second sibling, same pattern.
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
| LaTeX-heavy file | Handled by `narrate.py`'s chunked LLM rewrite (§3.1); a chunk that fails its sanity check twice falls back to the old regex wrap for that chunk only, never the whole file. |
| File with no speakable text | `cleaner.py` returns empty/whitespace; pipeline skips and logs a warning. |
| `ffmpeg` missing | Pipeline pre-flight check fails gracefully, logs instructions to install `ffmpeg`. |
| Ollama unreachable (server not running) | Every chunk falls back to the regex wrap (§3.1) — degrades to the pre-revision behavior, never fails the file or the batch, same `None`-vs-`OLLAMA_TIMEOUT` distinction `call_ollama` already provides elsewhere. |
| Image-heavy textbook page / figure | Images and their surrounding markup are silently skipped by `cleaner.py` (§1 non-goal) — no attempt to narrate `describe_images.py` output in v1. |
| `video_notes` note with dense inline citations | Citations stripped before narration (§3); no per-sentence "at timestamp X" clutter. |
| Very long source file (full textbook chapter, long article) | No length cap in v1 — produces one correspondingly long MP3 (§1 non-goal). |
| Source `.md` deleted after its `.mp3` was generated | Out of scope for this spec's first pass — orphaned MP3s are not auto-pruned (no orphan-sweep like the indexer's, since this pipeline doesn't own an index). Flagged in §9 as a candidate follow-on if it turns out to matter in practice. |

## 8. Testing

Mirrors the project's existing flat `tests/` convention (package-qualified
imports via the root `conftest.py` — `tests/test_audio_download.py`,
`tests/test_grouping.py`, etc. are all siblings at the repo root, not nested
inside their subproject packages, and note the `tests/test_discovery.py`/
`tests/test_pipeline.py` collision already resolved once for this subproject
— see the implementation plan's Global Constraints): `tests/test_cleaner.py`,
`tests/test_audio_generator_narrate.py`, `tests/test_engine.py`,
`tests/test_audio_generator_pipeline.py`.

- `cleaner.py`: **entirely unchanged by this revision** — same fixtures,
  same tests, including the existing LaTeX-regex-wrap tests (which still
  cover its behavior directly, on synthetic input, exactly as before).
- `narrate.py`: mocked `call_ollama` throughout (no real Ollama calls in
  tests, matching this project's established testing philosophy) —
  chunking-boundary behavior (never splits mid-sentence, mid-equation, or
  through a fenced code block), the sanity-check/retry sequence
  (short-output triggers one retry; a second short output, or an immediate
  `None`/`OLLAMA_TIMEOUT` with no retry, makes `narrate_for_speech()` return
  that chunk's original text unmodified — asserting *narrate.py's own
  output*, not any regex wrap, which is `cleaner.py`'s separate,
  already-tested concern applied afterward by `pipeline.py`), and that the
  final `.narrated.md` written by `pipeline.py` matches what was actually
  passed to `engine.synthesize_speech()`.
- `engine.py`: Integration test with a mocked engine to confirm input text passed to engine matches cleaned text.
- `pipeline.py`: Content-hash idempotency tested against a temp corpus (change
  file -> regen; don't change -> skip); discovery tested against both
  `academic_notes/` and both textbook-folder aliases; a test that output lands
  as a sibling `.mp3` at the expected hub-relative path for each content type;
  a test that `.narrated.md` is excluded from re-discovery on the next run.

## 9. Open questions / follow-on (not decided by this spec)

- **Real CPU timing for the chunked LLM rewrite (§3.1) is unmeasured.** A
  122KB real note produces roughly 40-60 chunks at the proposed ~2-3K
  character size; this project's own status docs have repeatedly found
  CPU-only local-model calls take real minutes each. The plan should measure
  real timing on one real equation-dense file before assuming a full course
  batch is practical to run in one sitting — same "measure before trusting
  at scale" pattern `problem_gen` and `video_notes` both followed.
- **The per-chunk sanity-check length-ratio threshold (§3.1) needs empirical
  tuning** against real rewritten output, exactly as flagged for
  `journal_discovery`'s relevance threshold and `video_notes`'s
  content-clustering threshold — a starting ratio is a guess, not a
  validated value, until checked against real chunks that did and didn't
  actually lose content.
- **Shared/multi-consumer LaTeX naturalization** (considered and deferred
  during this revision's brainstorming) — `problem_gen`'s local
  `qwen2-math:7b` reads raw-LaTeX style-anchor passages today; whether that's
  actually hurting problem generation quality is unverified. If real usage
  ever shows it is, revisit whether `narrate.py`'s output (or a
  precision-preserving variant of it — narration's full lossy paraphrase is
  likely wrong for a consumer that needs to reason about the actual math, not
  just narrate it) should become a shared artifact. Not this subproject's
  concern to solve speculatively.
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
