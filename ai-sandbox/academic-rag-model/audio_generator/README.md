# audio_generator

Converts a course's Markdown notes and converted textbooks into local MP3
narration for passive/commute listening — no GPU. Discovery, cleaning, and
TTS synthesis are fully offline; LaTeX narration (see below) is the one
step that calls a cloud API (Gemini).

Spec: `docs/superpowers/specs/audio_generator/2026-09-06-audio-generator-design.md`

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

**`textbook` content:** chapter-aware (TODO-0057) — when
`pipelines/convert_textbook/chapter_index.py`'s printed-TOC parser and the
folio tags `convert_textbook` already burned into the converted markdown
(`<!-- page N --><!-- folio F -->`) together resolve at least two chapter
boundaries, each chapter gets its own `<name>__ch01.mp3`,
`<name>__ch02.mp3`, etc. (mirroring notes' `__partNN` naming, with a
distinct `ch` infix so the two content types' outputs are never visually
confusable), plus a sibling `__chNN.narrated.md` per chapter — all next to
the source `<name>.md`, which already lives under `academic_resources/`,
so no path translation is needed. Content before the first resolved
chapter (title page, table of contents, preface, ...) is dropped, not
narrated as its own chapter. A book whose conversion run never derived a
folio offset (so its converted markdown has no folio tags at all), or
whose TOC can't be parsed, falls back to the original single
`<name>.mp3`/`<name>.narrated.md` per source — unchanged from before this
revision. See `audio_generator/textbook_chapters.py`.

**`notes` content:** split into one or more **episodes** targeting 10-20
minutes of listening each (see "Episode splitting" below), instead of one
unbounded MP3 — `<name>__part01.mp3`, `<name>__part02.mp3`, etc., plus a
`<name>__index.md` manifest listing which section titles landed in which
part. A short note with no headers (or headers that fit in one 10-20
minute episode) still produces exactly one `<name>__part01.mp3`.

**2026-09-22: notes MP3s live under `academic_resources/`, mirrored from
their source's `academic_notes/` location** (same `<course>/<category>/...`
relative path, just a different root — see
`docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md`).
Only the `.mp3` moves: `<name>__index.md` and every `__partNN.narrated.md`
stay right next to the source `.md` in `academic_notes/`, since those are
lightweight text, not the heavy binary audio this split exists to keep out
of the git/tablet-synced notes vault. A sync tool that only watches
`academic_notes/` will no longer pick up notes' own audio automatically
(textbook audio is unaffected, since that source was never under
`academic_notes/` to begin with).

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

## LaTeX narration

Math notation (`$...$`/`$$...$$`) is rewritten into natural spoken prose,
chunked per-file, by the **Gemini API** — the only step in this pipeline
that leaves your machine; everything else (discovery, cleaning, TTS
synthesis) stays fully local. Requires `GEMINI_API_KEY` set in
`ai-sandbox/.env` (see `../.env.example`; get a key at
aistudio.google.com/apikey).

Each chunk is classified by LaTeX density before anything is sent anywhere:

| Tier | Trigger | Model | Cost |
|---|---|---|---|
| Skip | No `$...$`/`$$...$$` spans and no stray Greek/math Unicode chars | — | Free — no API call at all |
| Light | Sparse/simple notation | `gemini-3.1-flash-lite` | Cheap |
| Heavy | Dense equations, many backslash commands, or a `\begin`/`\end` environment | `gemini-2.5-flash` | More expensive, used only when needed |

A plain-prose file (no math) costs nothing to narrate. If `GEMINI_API_KEY`
is missing/invalid, or a chunk's rewrite fails a sanity check (its length
relative to the original), that chunk degrades to the old literal-LaTeX-
wrapped narration instead of failing the file — no local fallback model is
used (a prior local-Ollama design was measured at ~6h for one
equation-dense file and dropped for this API-based approach).

The final narration text (after all cleaning) is written to a sibling
`<name>.narrated.md` next to `<name>.md`/`<name>.mp3` — useful for spot-
checking translation quality without listening to the audio.

Chunks within a file are narrated concurrently (`AUDIOGEN_NARRATE_MAX_WORKERS`
threads, default `5`) rather than one at a time — measured at 13.0 minutes
for one real 122K-character equation-dense file, ~28x faster than the prior
local-model design's ~6h for the same file. Raise
`AUDIOGEN_NARRATE_MAX_WORKERS` for more parallelism (watch for API rate
limits at very high values) or lower it to reduce load.

Override the classifier thresholds or model choice via
`AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD` (default `0.15`),
`AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD` (default `3`),
`AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL`, `AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL`.

## Episode splitting (`notes` only)

A long note (e.g. a full lecture-notes file) is split at every Markdown
header level, each section is narrated/cleaned independently, and
consecutive sections are grouped into episodes targeting 10-20 minutes of
resulting audio — using a real, measured conversion (`AUDIOGEN_SECTIONS_CHARS_PER_MINUTE`,
default `969` characters of final text per minute, calibrated against one
real Piper run) rather than a fixed header depth. An oversized section is
split at paragraph boundaries before narration, which otherwise removes
those boundaries. Episode grouping treats the maximum as a ceiling when a
boundary is available; a single indivisible paragraph may still exceed it.

`textbook` content is unaffected by *this* header-based approach — it has
its own separate, more sophisticated chapter-boundary system
(`pipelines/convert_textbook/chapter_index.py`), reused directly (not
reimplemented) by `audio_generator/textbook_chapters.py`; see "Output"
above (TODO-0057).

Idempotency is tracked per-episode but still hashed on the whole source
file — a deliberate simplification: editing any part of a note
regenerates every episode for that file, not just the changed section.

**Parallelized end to end, not just within one narration call:** every
section's chunks across the *entire* document are flattened and narrated
through one shared concurrent dispatch (not one `narrate_for_speech()`
call per section, which would serialize sections against each other), and
every episode's TTS synthesis also runs concurrently
(`AUDIOGEN_SECTIONS_SYNTH_MAX_WORKERS`, default `3` — lower than
narration's default since TTS is CPU-bound, not network-bound).

Override the episode-length target via `AUDIOGEN_SECTIONS_CHARS_PER_MINUTE`,
`AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES` (default `10`),
`AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES` (default `20`).

Existing single-file `<name>.mp3`/`<name>.narrated.md` outputs generated
before this feature become orphaned (not auto-deleted or migrated) — safe
to delete manually.

## Non-goals (see spec for rationale)

Journal-articles, auto-triggering from other pipelines, reading
image/figure descriptions aloud, and indexer/RAG registration are all
explicitly out of scope for this version.
