# Audio Generator — Design Spec

Date: 2026-09-06 (revised 2026-09-07: LLM-based LaTeX narration; revised
2026-09-09: tiered Gemini API narration, replacing local Ollama; revised
2026-09-09 again: section-aware episode splitting, §3.2)
Status: v1 implemented and shipped (commits d3adf7a..7cccb14, on `main`).
The 2026-09-07 local-LLM revision (§3.1 v2) was also implemented and
shipped (commits e375d2a..83daa83), then measured: real CPU timing on the
real equation-dense `LN_Probability.md` came back at **~6 hours for one
file** (§9) — impractical for any real batch use. §3.1 v3 (tiered Gemini
API narration, replacing local Ollama) was implemented and shipped
(commits 0795d7f, 92041a2), then measured at **13.0 minutes for the same
file** (§9) — confirming it's practical. Running v3 end-to-end against the
real file also surfaced a *new* problem this spec hadn't addressed: the
resulting single MP3 was **3h22m long** (no length cap, spec §1's original
non-goal) — technically correct, not actually useful for commute-length
listening. §3.2 (section-aware episode splitting) was implemented and
shipped (commits b40cb10, fb6fd8d, c46bd30), then validated end-to-end
against the same file: **227.1s narration + 1165.3s parallel synthesis =
23.2 min total**, producing 9 separately listenable episodes instead of
one 3h22m file. One real limitation was confirmed in the process (§9: an
undivided 711-line section produced a 62-minute over-length episode) —
deliberately left unfixed pending a listening-quality review. Full
real-world validation narrative: `docs/status/2026-09-09-audio-generator-status.md`.
Scoped to the `notes` content type only — `textbook` chapter-reuse is a
separate, deferred investigation (§3.2, §9). **Important scope note
(§9): every real test so far, including this one, has exercised the
harder secondary use case (raw LaTeX-heavy notes/textbook → audio)
rather than the intended primary one (LLM-generated summary text → audio,
not yet designed) — see §9 for why that distinction matters for
`narrate.py`'s role going forward.**

## 1. Problem & goals

The academic-hub corpus is entirely text/image-based (markdown notes, textbooks, journal articles, synthesized lecture notes). This limits study opportunities to sedentary scenarios (sitting at a desk, viewing a screen). Students need to consume study material passively (during commutes, exercise, etc.).

This spec designs **`audio_generator`**: a new subproject that converts hub markdown content into high-quality, locally-generated audio MP3 files, optimized for passive listening.

**Goals**
- Every step **except LaTeX narration** runs locally on commodity CPUs, no
  GPU, no external API: discovery, cleaning, idempotency, and TTS synthesis
  (Piper/Kokoro-ONNX) are all unchanged by this revision and remain fully
  offline. **LaTeX narration itself (§3.1) now calls the Gemini Developer
  API**, a deliberate, measured trade-off — see below.
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
  reading raw syntax" failure this goal exists to prevent. §3.1 v2 (local
  `qwen2-math:7b`) fixed the correctness problem but introduced a practical
  one: **real-corpus finding (2026-09-09)** — measured end-to-end against
  the same `LN_Probability.md` file, the local-LLM rewrite took **21,758.5s
  (~6 hours) for one 121,637-character file**, entirely CPU-bound (no GPU
  available on this hardware). At that rate, narrating a course's worth of
  notes/textbook files serially is not practical. §3.1 v3 (this revision)
  moves narration to the Gemini API — still narrowly scoped to this one
  step, with everything else in the pipeline staying local — and adds
  complexity tiers so plain-prose content costs nothing and only genuinely
  LaTeX-heavy content pays for the stronger (more expensive) model.
- Covers three content types, all of which live under `academic_hub_root` and are addressable by `--course` (§5): the student's own notes (`academic_notes/<course>/`, all categories — this already includes `video_notes`'s synthesized lecture notes, since those are written to `academic_notes/<course>/lecture-notes/`), and converted textbooks (`academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/`, both folder-name aliases, matching the indexer's existing handling of the same rename — `indexer/index_search.py:206-213`).
- Idempotent batch pipeline: only re-generates audio when the underlying `.md` file changes (tracked by content hash).
- Output MP3s land in the hub content repo, next to the source note they were generated from, so a folder-sync tool (Syncthing, a phone's file-sync app, etc.) picks them up the same way it already picks up the student's markdown notes — never inside `academic-rag-model`'s own gitignored caches.
- Integration: invoked manually per course via CLI (§6) — not auto-triggered as a follow-on of other pipelines in v1 (see Non-goals).

**Non-goals**
- Cloud TTS APIs (ElevenLabs, OpenAI) — TTS synthesis (§4) stays local Piper/Kokoro-ONNX; only LaTeX narration (§3.1) calls a cloud API, and only Gemini (this project's existing `common/gemini_utils.py`, not a new provider).
- Real-time/GPU-heavy model training.
- Interactive audio features (e.g., in-audio navigation markers beyond standard MP3 seeking).
- **Indexer/RAG registration.** Unlike `video_notes`'s synthesized lecture notes (which are new, otherwise-unindexed content and so need a new `index_search.py` discovery path), an MP3 here is a derived, downstream rendering of a `.md` file that's already indexed. The source `.md` remains the single retrieval unit; the tutor never needs to know an audio version exists. No `indexer/index_search.py` changes.
- **Journal articles.** `research/journal-articles/<field>/processed_outputs/` is a genuinely different shape from the other three content types: it lives in a separate sibling repo (`../research`, not `../academic-hub`) and is organized by academic field, not by `--course`. Rather than bolt on a second, mutually-exclusive scoping key (`--field` alongside `--course`) before the core pipeline is proven, this is deferred as a follow-on (§9).
- **Auto-triggering as a follow-on pass.** `postprocessing`/`viz` hook into other pipelines' completion; `audio_generator` v1 is manual-CLI-only (§6) to keep the first version simple. Revisit once the manual flow is proven (§9).
- **Reading image/figure descriptions aloud.** `textbook/describe_images.py` already generates descriptions for diagrams in converted textbook markdown, but wiring `cleaner.py` to find and narrate them is deferred (§9) — v1 silently skips images/figures the same way it skips code blocks.
- **A length cap on generated audio, for `textbook` content.** A full textbook chapter or long article still becomes one MP3 with no length limit — matches the original 1:1 sibling-file design (§5). (For `notes` content, §3.2's episode-splitting revision replaces the 1:1 assumption entirely — see below; `textbook` chapter-reuse is a separate, deferred investigation, §3.2/§9.)

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
`common/gemini_utils.py` (`get_gemini_client`/`call_with_retries`/
`load_dotenv_override`), already shared by `indexer/`, `viz/`, and
`textbook/` — not `common/ollama_utils.py` (§3.1 v2's local-LLM approach,
superseded by this revision after real timing showed it impractical).

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

## 3.1. LaTeX-to-narration via tiered Gemini API calls (`narrate.py`)

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

**Why not local (v2 → v3 change, 2026-09-09):** v2 (a local `qwen2-math:7b`
call via `common/ollama_utils.py`) fixed the correctness problem — see §1 —
but real timing against the same file, measured end-to-end, came back at
~6 hours for one 121,637-character file (§9). That is not usable for any
real batch: even a handful of files a week each cost most of a workday of
wall-clock time on this hardware (no GPU). v3 (this revision) replaces the
local model with the Gemini Developer API, using this project's existing
`common/gemini_utils.py` (`get_gemini_client`/`call_with_retries`) exactly
as `viz/llm_fallback.py`'s `_call_gemini` and `indexer/index_card.py`
already do — no new dependency, no new API-key convention, just a second
caller of an integration this project already has. Everything else in the
pipeline (discovery, cleaning, idempotency, TTS synthesis) stays local and
unchanged — this is a narrowly-scoped substitution, not a broader move to
cloud infrastructure (§1 goals).

**Approach — chunked, holistic rewrite, not per-equation extraction, running
on raw `.md` *before* `cleaner.py` (§3):** unchanged from v2.
`narrate_for_speech(md_text) -> str` is the call `pipeline.py` makes first,
on the untouched source text. Content is split into ~2-3K character chunks
on paragraph boundaries — never mid-sentence, mid-equation, **or through a
fenced code block** (a code block is an atomic, untouched pass-through unit,
never sent to the model at all). This chunking-and-prompt design was already
validated against the real corpus in v2 and is unaffected by which model
answers the prompt; what changes in v3 is *which* prompt gets sent for a
given chunk, and to *which* model. Rejected alternatives (per-equation
extraction with one batched prompt; regex-first with LLM-fallback only for
unrecognized macros) are unchanged from v2 — see the historical spec text
in version control for the full rejection rationale, still valid here.

**New in v3 — chunks are dispatched concurrently, not sequentially:**
v2's local model had exactly one CPU/GPU worth of inference capacity to
run against, so processing chunks one at a time was the only sensible
option — concurrent local calls would have only added contention. The
Gemini API has no such constraint: each chunk's rewrite is independent of
every other chunk's, and the API serves concurrent requests fine. v3 runs
chunks through a thread pool (`AUDIOGEN_NARRATE_MAX_WORKERS`, default 5)
instead of a plain loop, using `ThreadPoolExecutor.map()` specifically
because it preserves input order in its results regardless of which
chunk's network call actually completes first — the document is
reassembled in original order even when completion order differs. This is
a meaningful share of why the real measurement (§9) came back at 13
minutes rather than something closer to 50 chunks × several seconds each
run serially.

**New in v3 — per-chunk complexity tiering, so plain prose costs nothing:**
before sending a chunk anywhere, `narrate.py` classifies it into one of
three tiers by scanning for LaTeX markers (`$...$`/`$$...$$` spans,
backslash commands like `\frac`/`\sum`/`\begin`, and stray Greek-letter/
math-symbol Unicode characters outside any `$` delimiter — notes sometimes
type "α" or "β" directly as prose, not as LaTeX):

1. **No math (skip):** zero LaTeX markers and no stray math-Unicode chars
   found at all. The chunk is returned unmodified, with **no API call
   whatsoever** — `narrate.py`'s whole job is narrating LaTeX; a chunk with
   none needs nothing from it, and `cleaner.py`'s existing pipeline already
   handles plain markdown fine. This is the majority case for most
   machine-generated notes (mostly prose, with occasional light notation),
   and it's the tier that makes the cost model work at scale: a file with no
   equations costs literally $0 to narrate.
2. **Light math (cheap model):** LaTeX markers are present but sparse — below
   a density threshold on both signals (fraction of chunk characters inside
   `$...$`/`$$...$$` spans, and count of distinct backslash-command
   occurrences), and no `\begin{...}`/`\end{...}` environment (the
   genuinely hard, structural case — see v2's rejected-alternatives
   reasoning above). Sent to **`gemini-3.1-flash-lite`** via
   `client.models.generate_content()`.
3. **Heavy math (capable model):** either density signal crosses the
   threshold, or a `\begin`/`\end` environment is present anywhere in the
   chunk. Sent to **`gemini-2.5-flash`**.

Both threshold constants and both model names are overridable via env vars
(`AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD`, `AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD`,
`AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL`, `AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL`)
— the exact density thresholds are a starting guess, not a validated value,
flagged in §9 for empirical tuning against real chunks the same way v2's
sanity-check ratio was. Both model names were confirmed live against the
Gemini API directly (not assumed from documentation or third-party pricing
pages, which can lag or misname what's actually deployed) on 2026-09-09.

**Prompt:** unchanged from v2 — *"Rewrite this passage as natural spoken
prose for audio narration. Describe mathematical notation in words rather
than symbols. Do not omit or summarize any content — rewrite every
sentence, changing only how notation is expressed."*

**Reliability — sanity check, then fallback (never a hard failure, no
local fallback):** `common.gemini_utils.call_with_retries` already handles
transient failures (network errors, rate limits, honoring the API's own
suggested retry-after delay) internally, the same way every other Gemini
caller in this project relies on it — `narrate.py` doesn't reimplement
retry/backoff. On top of that, one content-quality check, mirroring v2's:
1. `call_with_retries` exhausts its retries and raises, or the API key/SDK
   is missing (`get_gemini_client()` returns `None`): **return that chunk's
   original text unmodified.** v2's local-Ollama fallback tier was
   considered and explicitly **dropped** in this revision — no local model
   is called if Gemini is unreachable, keeping exactly one code path to
   maintain instead of two. A missing/invalid `GEMINI_API_KEY` degrades
   every chunk to raw-LaTeX-passthrough (caught downstream by `cleaner.py`'s
   regex wrap, as before), never crashes the batch.
2. A real response whose length is suspiciously short relative to the input
   (same cheap proxy as v2, same flagged-for-tuning ratio, §9): treated as a
   failed rewrite, **return the chunk's original text unmodified** — no
   second attempt at the content-quality check itself (unlike v2, which
   retried a failed sanity check once locally; here, `call_with_retries`
   already retried transient failures before this check ever runs, so a
   sanity-check failure means the model *did* respond, just badly, and a
   second identical prompt to the same model is unlikely to fare
   differently). `narrate.py` still never generates its own fallback text —
   it declines to touch what it couldn't verify, exactly as v2 did.

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

## 3.2. Section-aware episode splitting (`sections.py`)

**Why:** running v3 end-to-end against the real `LN_Probability.md`
produced one continuous, correct MP3 — 3h22m long (§9). No length cap was
an explicit v1 non-goal (§1), but a real listening test makes clear that
"technically one file per source note" and "actually useful for a
commute" are different goals once a note is long enough. This revision
splits a long note into multiple, shorter **episodes**, each targeting a
practical listening length, instead of raising or removing the cap.

**Scope: `notes` content type only.** `textbook` content already has a
separate, more sophisticated chapter-boundary system
(`textbook/chapter_index.py`, anchored to PDF page numbers/outlines during
conversion) — reusing that data, if it's preserved anywhere accessible
after conversion, would likely beat reinventing header-based detection for
textbook markdown (which may not have the same clean, consistent header
structure real course notes do). That's a separate investigation, not
part of this revision (§9).

**Why length-target-driven, not a fixed header level:** an earlier draft
of this design considered simply splitting at a fixed header depth (e.g.
always at `#`, or always at `#`+`##`). Real inspection of `LN_Probability.md`
showed why that's the wrong lever: it has only 4 top-level (`#`) headers,
each spanning hundreds of lines — splitting only at `#` would still
produce 30-60+ minute files, not much better than today's single 3h22m
file. Splitting at every header level regardless of depth, then **grouping**
consecutive sections by their actual resulting audio length until hitting
a target duration band, decouples the output length (what a listener
actually experiences) from how any particular file happens to use
headers (which varies a lot across a real corpus and isn't something this
spec should assume).

**Calibration — measured, not guessed:** `LN_Probability.narrated.md`
(196,109 chars, the real post-narration, post-cleaning text from §3.1 v3's
real run) produced a 12,148.46s (202.5 min) MP3 via Piper
(`en_US-lessac-medium`). That's **~969 characters of final text per minute
of resulting audio** — a real, measured ratio, not an assumed speaking
rate. `AUDIOGEN_SECTIONS_CHARS_PER_MINUTE` (default `969`) makes this
overridable, since it's a single data point from one file and one
engine/voice — flagged in §9 for validation against more files, and it
will need re-measuring if the default TTS engine/voice ever changes (a
different Piper voice, or the Kokoro-ONNX engine, likely speaks at a
different pace).

**Algorithm:**
1. `split_into_sections(md_text) -> list[Section]` (new module
   `sections.py`) splits the **raw** `.md` at every ATX header line
   (`#` through `######`, any depth) — never at `##`/`###` specifically,
   at *every* header, since grouping (step 3) is what actually controls
   output length. `Section.title` is the header text (leading `#`s and
   whitespace stripped); `Section.body` is the raw text from just after
   that header to just before the next one (or EOF). Content before the
   first header, if any, becomes a title-less leading `Section`. **A file
   with no headers at all produces exactly one `Section`** — the whole
   file — which is exactly today's (pre-this-revision) behavior, so this
   is a strict superset, not a breaking change for headerless notes.
2. Every `Section.body` is chunked (reusing `narrate.py`'s existing
   paragraph/code-block-aware chunking, exposed as `narrate.chunk_for_narration()`),
   and **every section's chunks are flattened into one list before
   narrating anything** — dispatched through a single shared
   `narrate.narrate_chunks()` call (one client, one concurrency budget for
   the *whole document*), not one `narrate_for_speech()` call per section.
   The first working version of this design did call
   `narrate_for_speech()` per section in a loop; each call had its own
   internal concurrency across that section's chunks, but sections were
   still processed one after another, confining each section's
   parallelism to its own separate, serialized batch — a document with
   many small sections would have ended up *slower* than the original
   whole-file design, not faster. Flattening first and dispatching once
   fixes this: `narrate_chunks()`'s results are regrouped back into
   per-section text by position afterward (order-preserving, the same
   guarantee it already provides for individual chunks — §3.1). Headers
   are deliberately **not** included in what gets flattened and sent to
   Gemini — a header line folded into a chunk sent for "rewrite as spoken
   prose" is not guaranteed to survive as a clean, literal marker in the
   response, so section boundaries must be resolved *before* any text
   reaches the LLM, on the untouched raw source, never recovered from
   narrated/cleaned output. A section's spoken title is produced
   separately and cheaply — `cleaner.clean_markdown_for_speech(section.title)`
   (regex-only, no LLM call — titles are short and essentially never
   equation-dense) — and prepended to that section's cleaned body. Each
   section's regrouped, narrated body is then cleaned via
   `cleaner.clean_markdown_for_speech()`, completely unchanged — same
   reason `narrate.py` doesn't import `cleaner.py` (§3.1): splitting is a
   pipeline-orchestration concern, not a reason to touch either
   already-tested module.
3. `group_sections_into_episodes(narrated_sections, target_min_minutes=10, target_max_minutes=20, chars_per_minute=AUDIOGEN_SECTIONS_CHARS_PER_MINUTE) -> list[Episode]`
   greedily packs consecutive narrated sections (order preserved) until
   adding the next one would exceed the target-max character equivalent,
   *unless* the current episode hasn't yet reached the target-min
   equivalent (in which case it's included anyway — the same
   floor-then-ceiling shape `narrate.py`'s own `_group_into_chunks` uses,
   just with a floor as well as a ceiling). **A single section that alone
   exceeds the target-max on its own becomes its own, over-length episode
   — this revision never splits *inside* one section.** Expected to be
   rare (most real course notes subdivide well below 10-20 minutes'
   worth of text per header), but a genuinely long, headerless chapter
   would hit this; flagged in §9 as a known limitation, not solved here.
4. One `synthesize_speech()` call per `Episode`, writing
   `<name>__part01.mp3`, `<name>__part02.mp3`, etc. (zero-padded,
   sibling of the source, same directory — §5's existing sibling-output
   convention, just multiplied). These calls also run **concurrently**
   (`AUDIOGEN_SECTIONS_SYNTH_MAX_WORKERS`, default 3 — lower than
   narration's default since TTS is CPU-bound, not network-bound, so more
   threads than spare cores would add contention rather than speed), each
   in its own worker thread that returns a plain outcome value rather than
   mutating the pipeline's shared summary/state dicts directly — those are
   only ever written back on the main thread once every worker completes,
   avoiding a real lost-update race on concurrent dict increments. A
   per-source `<name>__index.md` sibling lists each part's included
   section titles and estimated duration, for a student to jump to the
   right part without listening through all of them — a plain-text
   manifest, not audio metadata (embedding real MP3 chapter markers via
   ID3 tags was considered and deferred as unnecessary complexity for v1).

**Idempotency — a deliberate simplification, not the finest-grained
possible design:** state tracking moves from one entry per source file to
one entry per `(rel_md_path, part_index)` pair, but **still keyed off the
whole file's content hash**, not a per-section hash. A content change
anywhere in the source regenerates *every* part for that file, even if
only one section actually changed. This trades some real efficiency for
avoiding a much harder problem: a per-section hash would need to handle a
small edit shifting which sections land in which part (since grouping is
duration-based, not fixed-boundary), which could ripple into every
downstream part even under finer tracking anyway. Flagged in §9 as a
possible future refinement, not attempted in this revision — matches this
project's established pattern of shipping the workable version first.

**What happens to existing single-file `.mp3`/`.narrated.md` outputs from
before this revision:** they become orphaned (their `rel_md_path` key in
`state.json` won't match the new `(rel_md_path, part_index)` shape, so
they're simply never touched again) — not automatically deleted or
migrated, consistent with the orphaned-MP3-cleanup non-goal already in
§1/§9. A user can delete them manually.

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
| LaTeX-heavy file | Handled by `narrate.py`'s chunked, tiered rewrite (§3.1); a chunk whose rewrite fails the sanity check falls back to the old regex wrap for that chunk only, never the whole file. |
| Plain-prose file, no math | Every chunk hits tier 1 (skip) — no API call made, no cost, passed straight through to `cleaner.py` (§3.1). |
| File with no speakable text | `cleaner.py` returns empty/whitespace; pipeline skips and logs a warning. |
| `ffmpeg` missing | Pipeline pre-flight check fails gracefully, logs instructions to install `ffmpeg`. |
| Gemini unreachable / `GEMINI_API_KEY` missing or invalid | Every math-containing chunk falls back to the regex wrap (§3.1) after `call_with_retries` exhausts its retries or `get_gemini_client()` returns `None` — degrades gracefully, never fails the file or the batch. No local fallback model (v2's Ollama path was dropped in v3). |
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
- `narrate.py`: mocked `client.models.generate_content` throughout (no real
  Gemini calls in tests, matching how `tests/test_llm_fallback.py` and
  `tests/test_llm_gen.py` already mock the same client shape for other
  Gemini callers in this project) — chunking-boundary behavior unchanged
  from v2 (never splits mid-sentence, mid-equation, or through a fenced
  code block); the tier classifier (no-math chunks make zero calls to
  `generate_content`; light/heavy chunks are routed to the correct model
  name); `call_with_retries` exhausting its retries, or `get_gemini_client()`
  returning `None`, each fall back to the chunk's original text unmodified;
  a too-short real response is treated as a failed sanity check with no
  further retry — asserting *narrate.py's own output* (the chunk's original
  text unmodified), not any regex wrap, which is `cleaner.py`'s separate,
  already-tested concern applied afterward by `pipeline.py`; and that the
  final `.narrated.md` written by `pipeline.py` matches what was actually
  passed to `engine.synthesize_speech()`.
- `engine.py`: Integration test with a mocked engine to confirm input text passed to engine matches cleaned text.
- `pipeline.py`: Content-hash idempotency tested against a temp corpus (change
  file -> regen; don't change -> skip); discovery tested against both
  `academic_notes/` and both textbook-folder aliases; a test that output lands
  as a sibling `.mp3` at the expected hub-relative path for each content type;
  a test that `.narrated.md` is excluded from re-discovery on the next run.

## 9. Open questions / follow-on (not decided by this spec)

- **RESOLVED (v2, superseded by v3): real CPU timing for the local-LLM
  chunked rewrite.** Measured end-to-end on 2026-09-09 (after three prior
  attempts were each killed by memory pressure — see git history on this
  spec/plan pair for the full account, including the finding that the
  kills came from the Claude Code harness's own background-task
  memory-safety guard, not genuine Windows OOM): **21,758.5s (~6h 2m) for
  one 121,637-character file**, CPU-only, no GPU on this hardware. This
  number is *why* v3 exists (§1, §3.1) — impractical for any real batch
  use, which is the whole reason narration moved to the Gemini API.
  `qwen2-math:7b`/local Ollama is no longer part of this pipeline's design.
- **RESOLVED (v3): real API timing, measured 2026-09-09.** Same file as
  v2's measurement (`LN_Probability.md`, 121,637 input chars): **777.3s
  (13.0 min)** end-to-end via the tiered Gemini path — roughly **28x
  faster** than v2's ~6h local-CPU number. Output was 198,693 chars, notably
  more verbose than v2's 127,558-char local-model rewrite of the same
  input (both passed the same length-ratio sanity check, so this isn't a
  failure — Gemini's rewrite style is simply more expansive; worth
  watching if narrated audio ends up longer than expected, but not
  investigated further here). Rough per-file cost at ~30.4K input /
  ~49.7K output tokens (chars ÷ 4), blended across the light/heavy tiers
  (exact tier mix for this file wasn't logged) using
  `gemini-3.1-flash-lite` ($0.25/$1.50 per M tokens) and `gemini-2.5-flash`
  ($0.30/$2.50 per M tokens): **roughly $0.08-$0.13 per file** — at the
  target volume of 3-4 files/week (~15/month), call it **$1-2/month**.
  Confirms the tiered-API design is practical at the intended volume; the
  local-CPU approach (§1, ~6h/file) is not.
- **NEW (§3.2): the `AUDIOGEN_SECTIONS_CHARS_PER_MINUTE` calibration
  (default `969`) is a single real data point** — one file, one Piper
  voice (`en_US-lessac-medium`). Needs validation against more real files
  before trusting the 10-20 minute episode target is actually landing
  where intended, and will need re-measuring if the default engine/voice
  ever changes (Kokoro-ONNX, or a different Piper voice, likely speaks at
  a different pace).
- **NEW (§3.2): idempotency is tracked per-episode but hashed on the
  whole source file**, not per-section — a deliberate simplification
  (§3.2 explains the tradeoff) that means any edit anywhere in a source
  regenerates every episode for that file, not just the one that
  changed. Revisit only if real usage shows the wasted regeneration
  matters at the intended volume (a few files/week makes this unlikely to
  bite in practice).
- **CONFIRMED (§3.2), real (2026-09-09): a single header-delimited section
  longer than the target-max on its own becomes its own over-length
  episode** — this revision never splits inside one section. Originally
  flagged as "not expected to be common," but the very first real
  end-to-end run against `LN_Probability.md` hit this: one section
  ("1.5 Probability measures," 711 raw lines with zero sub-headers)
  produced a 60,389-char (~62 min) episode, 3x the 20-minute target — see
  `docs/status/2026-09-09-audio-generator-status.md` for the full account. Not
  common-in-theory turned out to be real-in-practice on the first try.
  **Not fixed yet, deliberately** — deferred pending a listening-quality
  review of the real files this run produced, per the user's explicit
  request, before deciding whether/how to add paragraph-level fallback
  splitting for an over-long leaf section.
- **NEW (§3.2): `textbook` chapter-splitting reuse is unexplored** —
  whether `textbook/chapter_index.py`'s PDF-anchored chapter boundaries
  survive textbook conversion anywhere `audio_generator` could read them
  (a metadata sidecar, embedded markers in the `.md`, etc.) hasn't been
  checked. If they don't, `textbook` content would need its own
  header-based (or other) splitting heuristic, not simply a scope
  extension of §3.2's `notes`-only design.
- **NEW (2026-09-09): every real-world validation of this pipeline so far
  has exercised the wrong primary use case.** `LN_Probability.md` is raw,
  unedited course notes — chosen deliberately as a hard correctness
  stress-test for `narrate.py`'s LaTeX handling, not representative of
  where this pipeline is actually expected to spend most of its time.
  The planned primary consumer is **LLM-generated summary text** (e.g. a
  weekly per-course summary synthesized from several notes/textbook
  chapters — the "notes + textbook chapters → weekly summary → mp3"
  pipeline discussed but not yet designed, see the project's own
  conversation history). Such text is already plain, spoken-friendly
  prose by construction — an LLM writing an explanatory summary has no
  reason to emit raw `$\mathbb{E}[X]$`-style LaTeX unless specifically
  asked to reproduce it. **Routing LLM-generated summary text through
  `narrate.py`'s Gemini rewrite would be a second, unnecessary API call**
  on text that's already narration-ready — that path should likely go
  straight from `cleaner.clean_markdown_for_speech()` to
  `engine.synthesize_speech()`, skipping `narrate.py` entirely. Not
  designed or built — `audio_generator` today only has one entry point
  (`pipeline.py`'s discovery-driven, raw-`.md`-in flow) with no way to
  hand it already-narration-ready text directly. Full details in
  `docs/status/2026-09-09-audio-generator-status.md`.
- **NEW (v3): the tier-classifier density thresholds
  (`AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD`/`_COMMAND_THRESHOLD`, §3.1) are a
  starting guess, not validated values** — needs checking against real
  chunks to confirm the light/heavy split actually separates "occasional
  Greek letter" content from "genuinely equation-dense" content the way
  it's intended to, the same empirical-tuning pattern already flagged below
  for the sanity-check ratio.
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
- **RESOLVED for `notes` (§3.2, this revision):** episode splitting by
  header-delimited sections, grouped to a 10-20 minute target using a
  real measured chars-per-minute calibration. **Still open for
  `textbook`:** reusing `textbook/chapter_index.py`'s existing
  PDF-anchored chapter-boundary detection, rather than reinventing
  header-based splitting for textbook markdown, needs its own
  investigation into whether that boundary data survives conversion
  anywhere accessible.
- **In-audio navigation:** Injecting chapter-titles/section-headings via silent-gap injection.
- **Advanced inflection:** Using a more capable local model for emphasis (if hardware allows).
- **Orphaned-MP3 cleanup:** if a source `.md` is deleted or renamed, decide whether/how to prune or rename its sibling `.mp3` (§7) — not designed here.
