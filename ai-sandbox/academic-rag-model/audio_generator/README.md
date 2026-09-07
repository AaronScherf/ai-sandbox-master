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
