# audio_generator

Converts a course's Markdown notes and converted textbooks into local MP3
narration for passive/commute listening — no GPU. Discovery, cleaning, and
TTS synthesis are fully offline; LaTeX narration (see below) is the one
step that calls a cloud API (Gemini).

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

## Non-goals (see spec for rationale)

Journal-articles, auto-triggering from other pipelines, reading
image/figure descriptions aloud, indexer/RAG registration, and
chapter-level audio splitting are all explicitly out of scope for this
version.
